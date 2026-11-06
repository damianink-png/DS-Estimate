"""OCCT inventory API shared by production pythonocc and OCP validation."""
try:
 from OCC.Core.GProp import GProp_GProps
 from OCC.Core.BRepGProp import brepgprop_VolumeProperties,brepgprop_SurfaceProperties,brepgprop_LinearProperties
 from OCC.Core.BRepBndLib import brepbndlib_Add
 from OCC.Core.Bnd import Bnd_Box
 from OCC.Core.TopExp import TopExp_Explorer
 from OCC.Core.TopAbs import TopAbs_FACE,TopAbs_WIRE,TopAbs_SOLID,TopAbs_EDGE,TopAbs_VERTEX
 from OCC.Core.TopoDS import topods
 from OCC.Core.BRep import BRep_Tool
 from OCC.Core.gp import gp_Trsf,gp_Vec
 from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
 from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut,BRepAlgoAPI_Common
 from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
 from OCC.Core.GeomAbs import GeomAbs_Plane
 from OCC.Core.STEPControl import STEPControl_Reader
 from OCC.Core.IFSelect import IFSelect_RetDone
except ImportError:
 from types import SimpleNamespace
 from OCP.GProp import GProp_GProps
 from OCP.BRepGProp import BRepGProp
 from OCP.BRepBndLib import BRepBndLib
 from OCP.Bnd import Bnd_Box
 from OCP.TopExp import TopExp_Explorer
 from OCP.TopAbs import TopAbs_FACE,TopAbs_WIRE,TopAbs_SOLID,TopAbs_EDGE,TopAbs_VERTEX
 from OCP.TopoDS import TopoDS
 from OCP.BRep import BRep_Tool as Tool
 from OCP.gp import gp_Trsf,gp_Vec
 from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
 from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut,BRepAlgoAPI_Common
 from OCP.BRepAdaptor import BRepAdaptor_Surface
 from OCP.GeomAbs import GeomAbs_Plane
 from OCP.STEPControl import STEPControl_Reader
 from OCP.IFSelect import IFSelect_RetDone
 brepgprop_VolumeProperties=BRepGProp.VolumeProperties_s
 brepgprop_SurfaceProperties=BRepGProp.SurfaceProperties_s
 brepgprop_LinearProperties=BRepGProp.LinearProperties_s
 brepbndlib_Add=BRepBndLib.Add_s
 topods=SimpleNamespace(Face=TopoDS.Face_s,Wire=TopoDS.Wire_s,Vertex=TopoDS.Vertex_s)
 BRep_Tool=SimpleNamespace(Pnt=Tool.Pnt_s)

# Adaptive B-Rep integration bounds cost on vendor spline surfaces. This is
# still surface integration, not a display mesh approximation. Requested
# relative integration tolerance is 1e-7; exact analytic solids are unchanged.
_is_ocp=GProp_GProps.__module__.startswith("OCP")
_native_volume=brepgprop_VolumeProperties
_native_surface=brepgprop_SurfaceProperties
def brepgprop_VolumeProperties(shape,props):return _native_volume(shape,props,Eps=1e-7) if _is_ocp else _native_volume(shape,props,1e-7)
def brepgprop_SurfaceProperties(shape,props):return _native_surface(shape,props,Eps=1e-7) if _is_ocp else _native_surface(shape,props,1e-7)
