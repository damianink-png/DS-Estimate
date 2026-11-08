"""Real named STEP XCAF -> disk -> compiled DS Estimate engine regression.

Unlike tests mocking assembly_names.read_occurrences, this creates an actual
multicomponent STEP file on disk with part names and independent B-Rep
geometries, closes the writer, reimports with production XCAF, then runs the
packaged EXE and validates measured geometries against semantic evidence.
No BOM/size/stock/manufacturing route is inferred from the name.
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cad_backend'))
from assembly_names import read_occurrences
from part_name_evidence import parse_part_name
import cad_measure as cad

from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakeCylinder,BRepPrimAPI_MakePrism
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakePolygon,BRepBuilderAPI_MakeFace
from OCC.Core.STEPCAFControl import STEPCAFControl_Writer
from OCC.Core.STEPControl import STEPControl_AsIs
from OCC.Core.TDocStd import TDocStd_Document
from OCC.Core.TCollection import TCollection_ExtendedString
from OCC.Core.XCAFDoc import XCAFDoc_DocumentTool
from OCC.Core.TDataStd import TDataStd_Name
from OCC.Core.TopLoc import TopLoc_Location
from OCC.Core.gp import gp_Trsf,gp_Vec,gp_Pnt
from OCC.Core.IFSelect import IFSelect_RetDone

FIXTURES=[
    ('Kolek walcowy ISO 2338 6x30','pin','dowel-pin'),
    ('Nakretka DIN 934 M12','pin','hex-nut'), # same geometry, deliberately WRONG name
    ('Washer ISO 7089 M8','washer','washer'),
    ('Nakretka DIN 934 M6','nut','hex-nut'),
    ('Plate 100x60x8','plate','plate'),
    ('Bolt hole M10','box','none'),
    ('COMPOUND','box','none'),
    ('Profil 40x40x2x500','profile','profile'),
]

def _hex_nut():
    af=10.;height=5.2;radius=af/math.sqrt(3)
    wire=BRepBuilderAPI_MakePolygon()
    for i in range(6):
        angle=i*math.pi/3
        wire.Add(gp_Pnt(radius*math.cos(angle),radius*math.sin(angle),0))
    wire.Close()
    outer=BRepPrimAPI_MakePrism(
        BRepBuilderAPI_MakeFace(wire.Wire()).Face(),
        gp_Vec(0,0,height)).Shape()
    return BRepAlgoAPI_Cut(outer,BRepPrimAPI_MakeCylinder(3,height).Shape()).Shape()

def _shapes():
    washer=BRepAlgoAPI_Cut(
        BRepPrimAPI_MakeCylinder(8,1.6).Shape(),
        BRepPrimAPI_MakeCylinder(4.2,1.6).Shape()).Shape()
    outer=BRepPrimAPI_MakeBox(40,40,500).Shape()
    inner=BRepPrimAPI_MakeBox(36,36,500).Shape()
    shift=gp_Trsf();shift.SetTranslation(gp_Vec(2,2,0))
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
    tube=BRepAlgoAPI_Cut(outer,BRepBuilderAPI_Transform(inner,shift,True).Shape()).Shape()
    return {
        'pin':BRepPrimAPI_MakeCylinder(3,30).Shape(),
        'washer':washer,
        'nut':_hex_nut(),
        'plate':BRepPrimAPI_MakeBox(100,60,8).Shape(),
        'box':BRepPrimAPI_MakeBox(30,30,10).Shape(),
        'profile':tube,
    }

def build_named_step(path):
    doc=TDocStd_Document(TCollection_ExtendedString('DS Estimate XCAF fixture'))
    tool=XCAFDoc_DocumentTool.ShapeTool(doc.Main())
    root=tool.NewShape()
    TDataStd_Name.Set(root,TCollection_ExtendedString('Named original STEP assembly'))
    shapes=_shapes()
    labels={}
    for key,shape in shapes.items():
        label=tool.AddShape(shape,False)
        TDataStd_Name.Set(label,TCollection_ExtendedString('definition '+key))
        labels[key]=label
    for index,(name,key,_) in enumerate(FIXTURES):
        move=gp_Trsf()
        move.SetTranslation(gp_Vec(index*160,0,0))
        instance=tool.AddComponent(root,labels[key],TopLoc_Location(move))
        TDataStd_Name.Set(instance,TCollection_ExtendedString(name))
    tool.UpdateAssemblies()
    writer=STEPCAFControl_Writer()
    writer.SetNameMode(True)
    if not writer.Transfer(doc,STEPControl_AsIs):
        raise RuntimeError('XCAF STEP export transfer failed')
    if writer.Write(str(path))!=IFSelect_RetDone:
        raise RuntimeError('XCAF STEP file writing failed')
    assert path.is_file() and path.stat().st_size>1500
    return path

def verify(path,engine):
    # Verify the actual serialized names, *without mocked occurrence objects*.
    occurrences,issues=read_occurrences(path)
    if issues:
        raise AssertionError('XCAF name import used fallback: '+str(issues))
    assert len(occurrences)==len(FIXTURES),(
        f'Expected {len(FIXTURES)} STEP occurrences; received {len(occurrences)}')
    actual_names=[row['name'] for row in occurrences]
    expected_names=[f[0] for f in FIXTURES]
    assert sorted(actual_names)==sorted(expected_names),(
        f'XCAF names failed roundtrip: {actual_names}')
    proc=subprocess.run([str(engine),str(path)],capture_output=True,text=True,timeout=110)
    if proc.returncode:
        raise AssertionError('Packaged engine failed: '+proc.stderr[-5000:])
    result=json.loads(proc.stdout)
    rows=result.get('solids') or []
    assert len(rows)==len(FIXTURES),f'Packaged engine imported {len(rows)} instead of {len(FIXTURES)}'
    mapped={row['name']:row for row in rows}
    assert sorted(mapped)==sorted(expected_names)
    assert not result.get('importIssues'),result.get('importIssues')
    truths=[]
    for name,key,expected in FIXTURES:
        row=mapped[name]
        hint=row.get('normaliaHint')
        clue=row.get('nameEvidence')
        if expected=='none':
            assert clue is None,(name,clue)
        elif expected in ('plate','profile'):
            assert clue and clue['stockFamily']==expected,(name,clue)
        else:
            assert clue and clue['normaliaFamily']==expected,(name,clue)
        if key=='pin':
            assert hint and hint.get('families')==['dowel-pin'],(name,hint)
            assert hint.get('catalogCandidates',[{}])[0].get('designation')=='6x30'
            expect_comparison='conflict' if name.startswith('Nakretka') else 'family-compatible'
            assert hint.get('nameCorroboration',{}).get('status')==expect_comparison,(name,hint)
        elif key=='washer':
            assert hint and hint.get('families')==['washer'],hint
            assert hint.get('nameCorroboration',{}).get('status')=='corroborated',hint
        elif key=='nut':
            assert hint and hint.get('families')==['hex-nut'],hint
            assert hint.get('nameCorroboration',{}).get('status')=='corroborated',hint
        else:
            assert not hint,(name,hint)
        assert (row.get('stockHint') or {}).get('kind')!='purchased-component',name
        assert not (hint and ('purchasePrice' in hint or 'cutTimeH' in hint)),name
        truths.append({'name':name,'geometry':key,'nameFamily':expected,
                       'normalia':(hint or {}).get('families'),
                       'nameStatus':(hint or {}).get('nameCorroboration',{}).get('status')})
    pins=[mapped[n] for n,key,_ in FIXTURES if key=='pin']
    assert pins[0]['verifiedShapeKey']==pins[1]['verifiedShapeKey'],(
        'Identical pin geometry lost group across different occurrence names')
    print('NAMED_XCAF_STEP_ROUNDTRIP_PASS '+json.dumps({
        'count':len(FIXTURES),'nameImported':len(FIXTURES),
        'geometryNormalia':sum(bool(r.get('normaliaHint')) for r in rows),
        'nameConflicts':sum(x['nameStatus']=='conflict' for x in truths),
        'placeholderNamesIgnored':2,'noNameBasedManufacturingRoute':True,
        'rows':truths},ensure_ascii=False))
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--engine',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    path=build_named_step(args.out/'named_real_xcaf_assembly.step')
    result=verify(path,args.engine.resolve())
    (args.out/'named_xcaf_inventory.json').write_text(
        json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    main()
