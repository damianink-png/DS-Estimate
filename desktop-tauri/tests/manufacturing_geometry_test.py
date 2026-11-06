"""Real OCCT geometry regression; supports production OCC and local OCP bindings."""
import sys,unittest,math,tempfile,subprocess,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'cad_backend'))
import cad_measure as cad
from joint_detection import detect_contacts
from stock_recognition import recognize_stock
from manufacturing_features import feature_hints
from section_catalog import catalog
try:
 from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakeCylinder,BRepPrimAPI_MakePrism
 from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform,BRepBuilderAPI_MakePolygon,BRepBuilderAPI_MakeFace
 from OCC.Core.BRepFilletAPI import BRepFilletAPI_MakeFillet
 from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
 from OCC.Core.gp import gp_Pnt,gp_Trsf,gp_Dir,gp_Ax1,gp_Vec
 from OCC.Core.BRep import BRep_Builder
 from OCC.Core.TopoDS import TopoDS_Compound
 from OCC.Core.STEPControl import STEPControl_Writer,STEPControl_AsIs
except ImportError:
 from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakeCylinder,BRepPrimAPI_MakePrism
 from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform,BRepBuilderAPI_MakePolygon,BRepBuilderAPI_MakeFace
 from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
 from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
 from OCP.gp import gp_Pnt,gp_Trsf,gp_Dir,gp_Ax1,gp_Vec
 from OCP.BRep import BRep_Builder
 from OCP.TopoDS import TopoDS_Compound
 from OCP.STEPControl import STEPControl_Writer,STEPControl_AsIs
box=lambda x,y,z,origin=(0,0,0):BRepPrimAPI_MakeBox(gp_Pnt(*origin),x,y,z).Shape()
def rounded_box(w,h,length,r,origin=(0,0,0)):
 shape=box(w,h,length,origin);fillet=BRepFilletAPI_MakeFillet(shape)
 for edge in cad.shapes(shape,cad.TopAbs_EDGE):
  b=cad.bounds(edge)
  if b[5]-b[2]>length*.99:fillet.Add(r,cad.edge_cast(edge))
 fillet.Build();return fillet.Shape()
def rotated(shape):
 t=gp_Trsf();t.SetRotation(gp_Ax1(gp_Pnt(0,0,0),gp_Dir(1,1,1)),.41);return BRepBuilderAPI_Transform(shape,t,True).Shape()
class Geometry(unittest.TestCase):
 def test_catalog_has_pinned_real_dimensions(self):
  self.assertGreater(len(catalog()),1700);row=next(r for r in catalog() if r['name']=='IPE 200');self.assertEqual(row['dims']['h'],200)
 def test_rotated_bar_and_plate_have_local_geometry_and_measured_contour(self):
  bar=rotated(box(40,40,1000));hint=recognize_stock(bar,cad.bounds(bar));self.assertEqual(hint['kind'],'square-bar');self.assertAlmostEqual(hint['lengthMm'],1000,places=3)
  plate=rotated(box(100,50,5));hint=recognize_stock(plate,cad.bounds(plate));self.assertEqual(hint['kind'],'plate-candidate');self.assertAlmostEqual(hint['localCuttingHint']['contourMm'],300,places=3)
 def test_rounded_rhs_has_area_and_nominal_catalog_candidates(self):
  outer=rounded_box(40,40,1000,4);inner=rounded_box(36,36,1000,2,(2,2,0));shape=BRepAlgoAPI_Cut(outer,inner).Shape()
  hint=recognize_stock(shape,cad.bounds(shape));self.assertEqual(hint['kind'],'square-hollow');self.assertAlmostEqual(hint['wallMm'],2,places=3)
  self.assertTrue(any(c['name']=='SHS 40x40x2' for c in hint['catalogCandidates']))
 def test_i_profile_matches_library(self):
  h,b,tw,tf=80,46,3.8,5.2;w=BRepBuilderAPI_MakePolygon()
  for x,y in [(0,0),(b,0),(b,tf),((b+tw)/2,tf),((b+tw)/2,h-tf),(b,h-tf),(b,h),(0,h),(0,h-tf),((b-tw)/2,h-tf),((b-tw)/2,tf),(0,tf)]:w.Add(gp_Pnt(x,y,0))
  w.Close();shape=BRepPrimAPI_MakePrism(BRepBuilderAPI_MakeFace(w.Wire()).Face(),gp_Vec(0,0,1000)).Shape();hint=recognize_stock(shape,cad.bounds(shape))
  self.assertEqual(hint['kind'],'i-section');self.assertTrue(any(c['name']=='IPE 80' for c in hint['catalogCandidates']))
 def test_face_contact_perimeter_not_summed_twice(self):
  result=detect_contacts([box(100,50,10),box(40,5,60,(20,10,10))]);self.assertTrue(result['complete']);self.assertEqual(len(result['candidates']),1);self.assertAlmostEqual(result['candidates'][0]['lengthMm'],90)
 def test_gap_collision_and_budget_do_not_become_verified_welds(self):
  base=box(100,50,10)
  self.assertEqual(detect_contacts([base,box(40,5,60,(20,10,10.2))])['candidates'],[])
  collision=detect_contacts([base,box(40,5,60,(20,10,9))]);self.assertEqual(collision['candidates'],[]);self.assertTrue(collision['issues'])
  partial=detect_contacts([base,box(40,5,60,(20,10,10))],max_pairs=0);self.assertFalse(partial['complete'])
 def test_edge_contact_and_no_point_seam(self):
  edge=detect_contacts([box(10,10,10),box(10,10,10,(10,10,0))]);self.assertEqual(len(edge['candidates']),1);self.assertAlmostEqual(edge['candidates'][0]['lengthMm'],10)
  self.assertEqual(detect_contacts([box(10,10,10),box(10,10,10,(10,10,10))])['candidates'],[])
 def test_bend_pair_from_cylindrical_faces(self):
  outer=BRepPrimAPI_MakeCylinder(10,100,math.pi/2).Shape();inner=BRepPrimAPI_MakeCylinder(7,100,math.pi/2).Shape();hint=feature_hints(BRepAlgoAPI_Cut(outer,inner).Shape())['bendHint']
  self.assertEqual(hint['count'],1);self.assertAlmostEqual(hint['bends'][0]['thicknessMm'],3)
 def test_packaged_joint_command_when_requested(self):
  if '--compiled' not in sys.argv:self.skipTest('Packaged Windows EXE checked in Windows CI')
  with tempfile.TemporaryDirectory() as td:
   builder=BRep_Builder();compound=TopoDS_Compound();builder.MakeCompound(compound)
   for shape in [box(100,50,10),box(40,5,60,(20,10,10))]:builder.Add(compound,shape)
   writer=STEPControl_Writer();writer.Transfer(compound,STEPControl_AsIs);path=Path(td)/'joint.step';writer.Write(str(path))
   exe=Path('src-tauri/cad-backend/ds-cad-engine.exe').resolve();p=subprocess.run([str(exe),str(path),'--joints'],capture_output=True,text=True,timeout=120);self.assertEqual(p.returncode,0,p.stderr);data=json.loads(p.stdout);self.assertAlmostEqual(data['candidates'][0]['lengthMm'],90)
if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)
