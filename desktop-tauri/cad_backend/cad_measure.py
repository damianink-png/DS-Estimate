"""Small OCCT binding adapter: production pythonocc; OCP for local geometric regression."""
import math
try:
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopAbs import TopAbs_FACE,TopAbs_EDGE,TopAbs_SOLID,TopAbs_WIRE
    from OCC.Core.TopoDS import topods
    from OCC.Core.BRepGProp import brepgprop
    from OCC.Core.BRepBndLib import brepbndlib
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.GProp import GProp_GProps
    from OCC.Core.BRepAdaptor import BRepAdaptor_Surface,BRepAdaptor_Curve
    from OCC.Core.GeomAbs import GeomAbs_Plane,GeomAbs_Line,GeomAbs_Circle,GeomAbs_Cylinder,GeomAbs_Cone
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
    from OCP.GeomAbs import GeomAbs_Plane,GeomAbs_Line,GeomAbs_Circle,GeomAbs_Cylinder,GeomAbs_Cone
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
    """Find a sheet's two ORIGINAL major B-Rep planes, even after edge bevels.

    Different top/bottom areas are legitimate when one side is chamfered.
    This is only a plate-outline CANDIDATE; it is not a stock or process proof.
    Geometry checks (parallelism, plane spacing, axis, footprint and wires)
    remain independent of the permitted face-area asymmetry.
    """
    xyz=bounds(shape)
    sizes=[xyz[i+3]-xyz[i] for i in range(3)]
    thin=min(range(3),key=lambda i:sizes[i])
    thickness=sizes[thin]
    others=sorted((sizes[i] for i in range(3) if i!=thin))
    if (not all(math.isfinite(d) and d>0 for d in sizes)
            or others[0]/thickness<5-1e-5):
        return None
    footprint=others[0]*others[1]
    faces=[]
    for raw in shapes(shape,TopAbs_FACE):
        f=face_cast(raw)
        surf=BRepAdaptor_Surface(f)
        if surf.GetType()!=GeomAbs_Plane:
            continue
        plane=surf.Plane()
        direction=plane.Axis().Direction()
        # In a world-frame probe the plate thickness must actually be
        # normal to the thinnest bounding axis. Rotated plates are checked
        # again in the measured local frame by recognize_stock().
        if abs((direction.X(),direction.Y(),direction.Z())[thin])<.99999:
            continue
        face_area=area(f)
        if math.isfinite(face_area) and face_area>footprint*.30:
            faces.append((face_area,f,plane))
    faces.sort(key=lambda item:item[0],reverse=True)
    for i,(area_a,face_a,plane_a) in enumerate(faces):
        for area_b,face_b,plane_b in faces[i+1:]:
            if min(area_a,area_b)/max(area_a,area_b)<.75:
                continue
            if abs(plane_a.Axis().Direction().Dot(plane_b.Axis().Direction()))<.99999:
                continue
            if abs(plane_a.Distance(plane_b.Location())-thickness)>max(.02,thickness*.01):
                continue
            # The larger outline may include a chamfer: use its measured
            # B-Rep wires, not the proxy rectangle perimeter.
            main_face=face_a if area_a>=area_b else face_b
            contour=length(main_face)
            pierces=sum(1 for _ in shapes(main_face,TopAbs_WIRE))
            if contour>0 and pierces:
                return {'kind':'plate-outline','thicknessMm':thickness,
                        'contourMm':contour,'pierces':pierces,
                        'faceAreasMm2':[round(area_a,6),round(area_b,6)],
                        'asymmetricFaces':abs(area_a-area_b)>max(.01,max(area_a,area_b)*.005),
                        'source':'original B-Rep major parallel faces and measured outline',
                        'limitations':'Geometric plate candidate only; bevels, material and blank outline need separate evidence'}
    return None
