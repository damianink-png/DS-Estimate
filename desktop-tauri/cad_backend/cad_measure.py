"""Small OCCT binding adapter: production pythonocc; OCP for local geometric regression."""
try:
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopAbs import TopAbs_FACE,TopAbs_EDGE,TopAbs_SOLID,TopAbs_WIRE
    from OCC.Core.TopoDS import topods
    from OCC.Core.BRepGProp import brepgprop
    from OCC.Core.BRepBndLib import brepbndlib
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.GProp import GProp_GProps
    from OCC.Core.BRepAdaptor import BRepAdaptor_Surface,BRepAdaptor_Curve
    from OCC.Core.GeomAbs import GeomAbs_Plane,GeomAbs_Line,GeomAbs_Circle,GeomAbs_Cylinder
    from OCC.Core.gp import gp_Pln,gp_Pnt,gp_Dir,gp_Trsf,gp_Ax3
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Common,BRepAlgoAPI_Section
    from OCC.Core.BRepExtrema import BRepExtrema_DistShapeShape
    from OCC.Core.STEPControl import STEPControl_Reader
    from OCC.Core.IFSelect import IFSelect_RetDone
    face_cast=topods.Face;edge_cast=topods.Edge
    volume_props=brepgprop.VolumeProperties;surface_props=brepgprop.SurfaceProperties;linear_props=brepgprop.LinearProperties
    add_bounds=brepbndlib.Add
except ImportError:
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE,TopAbs_EDGE,TopAbs_SOLID,TopAbs_WIRE
    from OCP.TopoDS import TopoDS
    from OCP.BRepGProp import BRepGProp
    from OCP.BRepBndLib import BRepBndLib
    from OCP.Bnd import Bnd_Box
    from OCP.GProp import GProp_GProps
    from OCP.BRepAdaptor import BRepAdaptor_Surface,BRepAdaptor_Curve
    from OCP.GeomAbs import GeomAbs_Plane,GeomAbs_Line,GeomAbs_Circle,GeomAbs_Cylinder
    from OCP.gp import gp_Pln,gp_Pnt,gp_Dir,gp_Trsf,gp_Ax3
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common,BRepAlgoAPI_Section
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.STEPControl import STEPControl_Reader
    from OCP.IFSelect import IFSelect_RetDone
    face_cast=TopoDS.Face_s;edge_cast=TopoDS.Edge_s
    volume_props=BRepGProp.VolumeProperties_s;surface_props=BRepGProp.SurfaceProperties_s;linear_props=BRepGProp.LinearProperties_s
    add_bounds=BRepBndLib.Add_s

_is_ocp=GProp_GProps.__module__.startswith("OCP")
_native_volume=volume_props
_native_surface=surface_props
def volume_props(shape,props):return _native_volume(shape,props,Eps=1e-7) if _is_ocp else _native_volume(shape,props,1e-7)
def surface_props(shape,props):return _native_surface(shape,props,Eps=1e-7) if _is_ocp else _native_surface(shape,props,1e-7)

def shapes(shape,kind):
    ex=TopExp_Explorer(shape,kind)
    while ex.More():yield ex.Current();ex.Next()
def bounds(shape):
    b=Bnd_Box();add_bounds(shape,b);return b.Get()
def property_value(shape,fn):
    p=GProp_GProps();fn(shape,p);return abs(float(p.Mass()))
def area(shape):return property_value(shape,surface_props)
def volume(shape):return property_value(shape,volume_props)
def length(shape):return property_value(shape,linear_props)
def load_step(path):
    try:from .assembly_names import read_occurrences
    except ImportError:from assembly_names import read_occurrences
    items,_=read_occurrences(path)
    return [item['shape'] for item in items]



def plate_hint(shape):
    dims=sorted(b-a for a,b in zip(bounds(shape)[:3],bounds(shape)[3:]))
    if dims[0]<=0 or dims[1]/dims[0]<5-1e-5:return None
    faces=[]
    for face in shapes(shape,TopAbs_FACE):
        f=face_cast(face);surface=BRepAdaptor_Surface(f)
        if surface.GetType()==GeomAbs_Plane:faces.append((area(f),f,surface.Plane()))
    faces.sort(key=lambda f:f[0],reverse=True)
    if len(faces)<2 or abs(faces[0][0]-faces[1][0])>max(.01,faces[0][0]*.005):return None
    p,q=faces[0][2],faces[1][2]
    if abs(p.Axis().Direction().Dot(q.Axis().Direction()))<.99999:return None
    if abs(p.Distance(q.Location())-dims[0])>max(.02,dims[0]*.01):return None
    contour=length(faces[0][1]);pierces=sum(1 for _ in shapes(faces[0][1],TopAbs_WIRE))
    return {'kind':'plate-outline','thicknessMm':dims[0],'contourMm':contour,'pierces':pierces,'source':'local planar B-Rep face wires'} if contour>0 and pierces else None
