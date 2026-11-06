"""Resolve STEP product/occurrence names through XCAF, including nested locations."""
try:from . import cad_measure as cad
except ImportError:import cad_measure as cad

def signature(shape):
    return tuple(round(v,3) for v in cad.bounds(shape))+(round(cad.volume(shape),2),)

def extended_text(value):
    raw=value.ToExtString()
    if isinstance(raw,str):
        text=raw
    elif isinstance(raw,bytes):
        text=raw.decode('utf-8')
    else:
        # pythonocc exposes Standard_ExtString as an opaque SWIG pointer.
        # Its owned OCCT buffer consists of Length() UTF-16 code units, even
        # on platforms where wchar_t is 32-bit. Keep value alive while reading.
        import ctypes,sys
        text=ctypes.string_at(int(raw),value.Length()*2).decode('utf-16-le' if sys.byteorder=='little' else 'utf-16-be')
    try:return text.encode('latin1').decode('utf-8')
    except (UnicodeEncodeError,UnicodeDecodeError):return text

def load_occurrences(path):
    try:
        from OCC.Core.STEPCAFControl import STEPCAFControl_Reader
        from OCC.Core.TDocStd import TDocStd_Document
        from OCC.Core.TCollection import TCollection_ExtendedString
        from OCC.Core.XCAFDoc import XCAFDoc_DocumentTool
        from OCC.Core.TDF import TDF_Label,TDF_LabelSequence
        from OCC.Core.TDataStd import TDataStd_Name
        from OCC.Core.TopLoc import TopLoc_Location
        tool_fn=XCAFDoc_DocumentTool.ShapeTool;name_id=TDataStd_Name.GetID
    except ImportError:
        from OCP.STEPCAFControl import STEPCAFControl_Reader
        from OCP.TDocStd import TDocStd_Document
        from OCP.TCollection import TCollection_ExtendedString
        from OCP.XCAFDoc import XCAFDoc_DocumentTool
        from OCP.TDF import TDF_Label,TDF_LabelSequence
        from OCP.TDataStd import TDataStd_Name
        from OCP.TopLoc import TopLoc_Location
        tool_fn=XCAFDoc_DocumentTool.ShapeTool_s;name_id=TDataStd_Name.GetID_s
    def call(obj,name,*args):return getattr(obj,name,getattr(obj,name+'_s',None))(*args)
    def label_name(label):
        # pythonocc provides this native UTF-8 accessor specifically to avoid
        # SWIG output-handle replacement in FindAttribute. OCP fills the supplied
        # attribute in place and uses the fallback below.
        if hasattr(label,'GetLabelName'):
            text=label.GetLabelName()
            return text.decode('utf-8') if isinstance(text,bytes) else text
        value=TDataStd_Name()
        if label.FindAttribute(name_id(),value):
            return extended_text(value.Get())
        return ''
    doc=TDocStd_Document(TCollection_ExtendedString('DS Estimate'));reader=STEPCAFControl_Reader();reader.SetNameMode(True)
    if reader.ReadFile(str(path))!=cad.IFSelect_RetDone or not reader.Transfer(doc):raise ValueError('XCAF STEP transfer failed')
    tool=tool_fn(doc.Main());roots=TDF_LabelSequence();tool.GetFreeShapes(roots);result=[]
    def walk(label,parent,trail,depth=0):
        if depth>64:return
        ref=TDF_Label();is_ref=call(tool,'IsReference',label)
        target=label
        if is_ref:
            call(tool,'GetReferredShape',label,ref);target=ref
        own=label_name(label);definition=label_name(target)
        # STEP translators often assign numeric occurrence labels; prefer the product then.
        name=own if own and not own.replace('.','').isdigit() else definition or own
        loc=parent.Multiplied(call(tool,'GetLocation',label))
        components=TDF_LabelSequence()
        if call(tool,'GetComponents',target,components):
            for i in range(1,components.Length()+1):walk(components.Value(i),loc,trail+[name] if name else trail,depth+1)
        else:
            shape=call(tool,'GetShape',label).Moved(parent)
            solids=list(cad.shapes(shape,cad.TopAbs_SOLID))
            for index,s in enumerate(solids):
                result.append({'shape':s,'name':name,'assemblyPath':trail+[name],
                    'nameSource':'XCAF occurrence/product' if name else 'missing',
                    'bodyIndex':index,'bodyCount':len(solids)})
    for i in range(1,roots.Length()+1):walk(roots.Value(i),TopLoc_Location(),[])
    return result

def assembly_names(path):
    # Compatibility adapter for callers needing a geometry-indexed name report.
    result={}
    for occurrence in load_occurrences(path):
        result.setdefault(signature(occurrence['shape']),[]).append({k:v for k,v in occurrence.items() if k!='shape'})
    return result

def read_occurrences(path):
    """One authoritative occurrence order shared by inventory, joints and preview."""
    try:
        items=load_occurrences(path)
        if not items:raise ValueError('No solid occurrences in XCAF document')
        return items,[]
    except Exception as exc:
        # Never silently pretend that a failed name import succeeded.
        reader=cad.STEPControl_Reader()
        if reader.ReadFile(str(path))!=cad.IFSelect_RetDone or not reader.TransferRoots():raise ValueError('STEP transfer failed')
        items=[{'shape':s,'name':'','assemblyPath':[],'nameSource':'missing'} for s in cad.shapes(reader.OneShape(),cad.TopAbs_SOLID)]
        return items,['XCAF import failed; unnamed STEPControl fallback: '+type(exc).__name__+': '+str(exc)]
