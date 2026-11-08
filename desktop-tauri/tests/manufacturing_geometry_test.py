"""Real OCCT geometry regression; supports production OCC and local OCP bindings."""
import sys,unittest,math,tempfile,subprocess,json
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'cad_backend'))
import cad_measure as cad
from joint_detection import detect_contacts
from weld_preparation import groove_between,t_groove_between
from stock_recognition import recognize_stock
from manufacturing_features import feature_hints,sheet_hints
from part_preview import mesh_part
from assembly_names import assembly_names,signature,extended_text,read_occurrences
from section_catalog import catalog
try:
 from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakeCylinder,BRepPrimAPI_MakePrism
 from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform,BRepBuilderAPI_MakePolygon,BRepBuilderAPI_MakeFace
 from OCC.Core.BRepFilletAPI import BRepFilletAPI_MakeFillet
 from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut,BRepAlgoAPI_Fuse
 from OCC.Core.gp import gp_Pnt,gp_Trsf,gp_Dir,gp_Ax1,gp_Vec
 from OCC.Core.BRep import BRep_Builder
 from OCC.Core.TopoDS import TopoDS_Compound
 from OCC.Core.STEPControl import STEPControl_Writer,STEPControl_AsIs
except ImportError:
 from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakeCylinder,BRepPrimAPI_MakePrism
 from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform,BRepBuilderAPI_MakePolygon,BRepBuilderAPI_MakeFace
 from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
 from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut,BRepAlgoAPI_Fuse
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
 def test_interrupted_face_pair_never_emits_a_partial_seam(self):
  a=box(100,100,10);b=box(100,100,10,(100,0,0));state={'faces':0};real=cad.BRepAlgoAPI_Common
  def common(x,y):
   if x.ShapeType()==cad.TopAbs_FACE:state['faces']+=1
   return real(x,y)
  def clock():return 100 if state['faces'] else 0
  with patch('joint_detection.time.monotonic',side_effect=clock),patch.object(cad,'BRepAlgoAPI_Common',side_effect=common):
   data=detect_contacts([a,b],max_seconds=5)
  self.assertFalse(data['complete']);self.assertEqual(data['candidates'],[]);self.assertEqual(data['completedPairs'],0);self.assertEqual(data['pendingPairs'],1)
 def test_collision_invalidates_geometry_even_after_all_pairs_finished(self):
  data=detect_contacts([box(100,100,10),box(100,100,10,(50,0,0))]);self.assertTrue(data['complete']);self.assertFalse(data['geometryValid']);self.assertEqual(data['pendingPairs'],0);self.assertEqual(len(data['collisions']),1)
 def test_skin_measurements_are_cached_per_occurrence_during_contact_scan(self):
  import weld_preparation
  with patch.object(weld_preparation,'primary_skin',wraps=weld_preparation.primary_skin) as fn:
   data=detect_contacts([box(100,100,10,(x,0,0)) for x in [0,100,200]])
  self.assertTrue(data['complete']);self.assertEqual(fn.call_count,3);self.assertEqual(data['skinCacheEntries'],3)
 def test_short_imperial_hollow_is_not_four_sheet_bends(self):
  outer=rounded_box(25.4,25.4,25.4,6.35)
  inner=rounded_box(19.05,19.05,25.4,3.175,(3.175,3.175,0))
  shape=BRepAlgoAPI_Cut(outer,inner).Shape()
  for part in [shape,rotated(shape)]:
   hint=recognize_stock(part,cad.bounds(part));self.assertEqual(hint['kind'],'square-hollow',hint)
   self.assertAlmostEqual(hint['wallMm'],3.175,places=3)
 def test_prepared_t_joint_measures_foot_void_not_contact_perimeter(self):
  def plate(points):
   wire=BRepBuilderAPI_MakePolygon()
   for x,z in points:wire.Add(gp_Pnt(x,0,z))
   wire.Close();return BRepPrimAPI_MakePrism(BRepBuilderAPI_MakeFace(wire.Wire()).Face(),gp_Vec(0,100,0)).Shape()
  base=box(100,100,10,(-50,0,-10));stem=plate([(-5,5),(0,0),(5,0),(5,50),(-5,50)])
  for aa,bb in [(base,stem),(rotated(base),rotated(stem))]:
   result=t_groove_between(aa,bb);self.assertIsNotNone(result);self.assertAlmostEqual(result['sectionMm2'],12.5,places=3)
   joints=detect_contacts([aa,bb]);self.assertAlmostEqual(joints['candidates'][0]['measuredSectionMm2'],12.5,places=3);self.assertEqual(joints['candidates'][0]['preparation'],'T-half-V')
 def test_nested_assembly_occurrences_and_complete_inventory(self):
  from build_assembly_fixture import write_fixture
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'nested.step';expected=write_fixture(path);items,issues=read_occurrences(path)
   from step_inventory import inventory
   report=inventory(path);self.assertEqual(report['productCount'],6);self.assertTrue(all(s.get('productOccurrenceKey') for s in report['solids']));self.assertEqual(len({s['productOccurrenceKey'] for s in report['solids']}),6)
   self.assertFalse(issues);self.assertEqual(len(items),6);self.assertEqual(set(i['name'] for i in items),set(expected['names']))
   lookup={i['name']:i for i in items};a=lookup['Płyta P-015'];b=lookup['Płyta P-015 druga']
   self.assertGreaterEqual(len(a['assemblyPath']),3);self.assertAlmostEqual(cad.bounds(b['shape'])[0]-cad.bounds(a['shape'])[0],500,places=4)
   if '--compiled' in sys.argv:
    exe=Path('src-tauri/cad-backend/ds-cad-engine.exe').resolve();p=subprocess.run([str(exe),str(path)],capture_output=True,text=True,timeout=180)
    self.assertEqual(p.returncode,0,p.stderr);data=json.loads(p.stdout);self.assertEqual(data['engineVersion'],'0.7.1');self.assertEqual(data['count'],6)
    lookup={s['name']:s for s in data['solids']};self.assertEqual(set(lookup),set(expected['names']))
    for s in lookup.values():self.assertGreater(len(data['previews'][s['previewKey']]['triangles']),0)
    self.assertAlmostEqual(lookup['Płyta P-015']['stockHint']['thicknessMm'],15,places=3)
    self.assertAlmostEqual(lookup['Blacha gięta BG-003']['stockHint']['thicknessMm'],3,places=3)
    self.assertEqual(lookup['Blacha gięta BG-003']['bendHint']['count'],1)
    self.assertEqual(lookup['Profil SHS z wycięciem']['stockHint']['rawStockCandidate']['kind'],'square-hollow')
    p=subprocess.run([str(exe),str(path),'--joints'],capture_output=True,text=True,timeout=180);self.assertEqual(p.returncode,0,p.stderr)
    joints=json.loads(p.stdout)['candidates'];self.assertEqual(len(joints),1);self.assertEqual(joints[0]['preparation'],'V');self.assertAlmostEqual(joints[0]['measuredSectionMm2'],64,places=3)
 def test_measured_v_x_and_root_gap_preparations(self):
  def plate(points):
   wire=BRepBuilderAPI_MakePolygon()
   for x,z in points:wire.Add(gp_Pnt(x,0,z))
   wire.Close();return BRepPrimAPI_MakePrism(BRepBuilderAPI_MakeFace(wire.Wire()).Face(),gp_Vec(0,100,0)).Shape()
  for kind,left in [('V',[(-50,0),(0,0),(0,2),(-8,10),(-50,10)]),('X',[(-50,0),(-8,0),(0,4),(0,6),(-8,10),(-50,10)])]:
   a=plate(left);b=plate([(-x,z) for x,z in reversed(left)])
   for rotate in [False,True]:
    aa,bb=(rotated(a),rotated(b)) if rotate else (a,b)
    result=groove_between(aa,bb);self.assertIsNotNone(result)
    self.assertEqual(result['kind'],kind);self.assertAlmostEqual(result['includedAngleDeg'],90 if kind=='V' else 2*math.degrees(math.atan(2)),places=3);self.assertAlmostEqual(result['sectionMm2'],64,places=3);self.assertAlmostEqual(result['lengthMm'],100,places=3)
    contacts=detect_contacts([aa,bb]);self.assertEqual(len(contacts['candidates']),1)
    self.assertAlmostEqual(contacts['candidates'][0]['measuredSectionMm2'],64,places=3)
   tr=gp_Trsf();tr.SetTranslation(gp_Vec(2,0,0));b=BRepBuilderAPI_Transform(b,tr,True).Shape()
   result=detect_contacts([a,b]);self.assertEqual(len(result['candidates']),1);self.assertAlmostEqual(result['candidates'][0]['measuredSectionMm2'],84,places=3)
 def test_catalog_has_pinned_real_dimensions(self):
  self.assertGreater(len(catalog()),1700);row=next(r for r in catalog() if r['name']=='IPE 200');self.assertEqual(row['dims']['h'],200)
 def test_rotated_bar_and_plate_have_local_geometry_and_measured_contour(self):
  bar=rotated(box(40,40,1000));hint=recognize_stock(bar,cad.bounds(bar));self.assertEqual(hint['kind'],'square-bar');self.assertAlmostEqual(hint['lengthMm'],1000,places=3)
  plate=rotated(box(100,50,5));hint=recognize_stock(plate,cad.bounds(plate));self.assertEqual(hint['kind'],'plate-candidate');self.assertAlmostEqual(hint['localCuttingHint']['contourMm'],300,places=3)
 def test_small_plate_rotation_does_not_use_world_bbox_thickness(self):
  t=gp_Trsf();t.SetRotation(gp_Ax1(gp_Pnt(0,0,0),gp_Dir(1,0,0)),.03)
  shape=BRepBuilderAPI_Transform(box(100,50,5),t,True).Shape()
  bounds=cad.bounds(shape);wrong_thickness=min(bounds[i+3]-bounds[i] for i in range(3))
  hint=recognize_stock(shape,bounds,{'kind':'plate-outline','thicknessMm':wrong_thickness,'contourMm':300,'pierces':1})
  self.assertEqual(hint['kind'],'plate-candidate');self.assertAlmostEqual(hint['thicknessMm'],5,places=3)
  for actual,expected in zip(hint['localDimsMm'],[100,50,5]):self.assertAlmostEqual(actual,expected,places=3)
 def test_short_hollow_profiles_do_not_require_the_extrusion_axis_to_be_longest(self):
  shape=BRepAlgoAPI_Cut(box(40,40,20),box(36,36,20,(2,2,0))).Shape()
  for s in [shape,rotated(shape)]:
   hint=recognize_stock(s,cad.bounds(s));self.assertEqual(hint['kind'],'square-hollow');self.assertAlmostEqual(hint['lengthMm'],20,places=3);self.assertAlmostEqual(hint['wallMm'],2,places=3)
 def test_real_brep_beveled_plate_preserves_plate_candidate(self):
  # An actual 100x50x10 STEP-ready prism, with a 5x45 degree
  # longitudinal chamfer. Top area=95*50; bottom=100*50.
  # A strict equal-face-area assumption rejects this genuine plate.
  wire=BRepBuilderAPI_MakePolygon()
  for x,z in [(0,0),(100,0),(100,10),(5,10),(0,5)]:
   wire.Add(gp_Pnt(x,0,z))
  wire.Close()
  shape=BRepPrimAPI_MakePrism(BRepBuilderAPI_MakeFace(wire.Wire()).Face(),
                             gp_Vec(0,50,0)).Shape()
  face_evidence=cad.plate_hint(shape)
  self.assertIsNotNone(face_evidence)
  self.assertTrue(face_evidence['asymmetricFaces'])
  self.assertAlmostEqual(face_evidence['thicknessMm'],10,places=4)
  hint=recognize_stock(shape,cad.bounds(shape),face_evidence)
  self.assertEqual(hint['kind'],'plate-candidate',hint)
  self.assertAlmostEqual(hint['thicknessMm'],10,places=4)
  self.assertEqual(hint['confidence'],'candidate')
  self.assertNotIn('manufacturingProcess',hint)

 def test_real_brep_longitudinal_chamfer_has_unverified_blank(self):
  wire=BRepBuilderAPI_MakePolygon()
  for x,y in [(0,0),(40,0),(40,40),(5,40),(0,35)]:
   wire.Add(gp_Pnt(x,y,0))
  wire.Close()
  shape=BRepPrimAPI_MakePrism(BRepBuilderAPI_MakeFace(wire.Wire()).Face(),
                             gp_Vec(0,0,500)).Shape()
  hint=recognize_stock(shape,cad.bounds(shape))
  self.assertEqual(hint['kind'],'unknown',hint)
  self.assertEqual(hint['finishedSectionEvidence']['bevelCount'],1)
  raw=hint['rawStockCandidate']
  self.assertEqual(raw['kind'],'square-bar')
  self.assertEqual(raw['confidence'],'geometric-blank-candidate')
  self.assertAlmostEqual(raw['widthMm'],40,places=3)
  self.assertAlmostEqual(raw['heightMm'],40,places=3)
  self.assertNotIn('cutTimeH',hint)

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
 def test_rotated_bent_sheet_thickness_and_estimated_developed_perimeter(self):
  ring=BRepAlgoAPI_Cut(BRepPrimAPI_MakeCylinder(10,100,math.pi/2).Shape(),BRepPrimAPI_MakeCylinder(7,100,math.pi/2).Shape()).Shape()
  shape=BRepAlgoAPI_Fuse(BRepAlgoAPI_Fuse(ring,box(50,3,100,(-50,7,0))).Shape(),box(3,40,100,(7,-40,0))).Shape()
  shape=rotated(shape);features=feature_hints(shape);hint=sheet_hints(shape,features)
  self.assertEqual(features['bendHint']['count'],1);self.assertEqual(hint['kind'],'bent-plate');self.assertAlmostEqual(hint['thicknessMm'],3,places=3)
  self.assertAlmostEqual(hint['estimatedContourMm'],2*(50+40+8.5*math.pi/2+100),places=2)
 def test_custom_hollow_and_notched_stock_are_not_flat_sheets(self):
  inner=box(40,40,1000,(20,20,0));t=gp_Trsf();t.SetRotation(gp_Ax1(gp_Pnt(40,40,0),gp_Dir(0,0,1)),math.radians(20))
  hollow=BRepAlgoAPI_Cut(box(80,80,1000),BRepBuilderAPI_Transform(inner,t,True).Shape()).Shape()
  notch=BRepAlgoAPI_Cut(box(40,40,1000),box(20,40,100,(0,0,580))).Shape()
  for shape in [hollow,notch]:
   self.assertEqual(recognize_stock(shape,cad.bounds(shape))['kind'],'unknown')
   self.assertIsNone(sheet_hints(shape,feature_hints(shape)))
 def test_actual_mesh_preview_not_bounding_box(self):
  shape=BRepAlgoAPI_Cut(box(40,40,100),box(36,36,100,(2,2,0))).Shape();mesh=mesh_part(shape)
  self.assertGreaterEqual(len(mesh['triangles']),32);self.assertFalse(mesh['partial'])
  self.assertTrue(all(math.isfinite(v) for tri in mesh['triangles'] for point in tri for v in point))
 def test_utf16_name_buffer_preserves_polish_and_surrogate_pairs(self):
  import ctypes
  text='Płyta 🔩';encoded=text.encode('utf-16-le');buffer=ctypes.create_string_buffer(encoded)
  class Wrapped:
   def ToExtString(self):return ctypes.addressof(buffer)
   def Length(self):return len(encoded)//2
  self.assertEqual(extended_text(Wrapped()),text)
 def test_xcaf_product_names_survive_step_roundtrip(self):
  try:
   from OCC.Core.TDocStd import TDocStd_Document
   from OCC.Core.TCollection import TCollection_ExtendedString as S
   from OCC.Core.XCAFDoc import XCAFDoc_DocumentTool
   from OCC.Core.TDataStd import TDataStd_Name
   from OCC.Core.STEPCAFControl import STEPCAFControl_Writer
   tool_fn=XCAFDoc_DocumentTool.ShapeTool;set_name=TDataStd_Name.Set
  except ImportError:
   from OCP.TDocStd import TDocStd_Document
   from OCP.TCollection import TCollection_ExtendedString as S
   from OCP.XCAFDoc import XCAFDoc_DocumentTool
   from OCP.TDataStd import TDataStd_Name
   from OCP.STEPCAFControl import STEPCAFControl_Writer
   tool_fn=XCAFDoc_DocumentTool.ShapeTool_s;set_name=TDataStd_Name.Set_s
  doc=TDocStd_Document(S('test'));tool=tool_fn(doc.Main());label=tool.AddShape(box(100,50,5));set_name(label,S('Płyta P-101',True))
  writer=STEPCAFControl_Writer();writer.Transfer(doc)
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'names.step';writer.Write(str(path));names=assembly_names(path)
   self.assertEqual(next(iter(names.values()))[0]['name'],'Płyta P-101')
   if '--compiled' in sys.argv:
    exe=Path('src-tauri/cad-backend/ds-cad-engine.exe').resolve();p=subprocess.run([str(exe),str(path)],capture_output=True,text=True,timeout=120)
    self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout)['solids'][0]['name'],'Płyta P-101')
 def test_packaged_joint_command_when_requested(self):
  if '--compiled' not in sys.argv:self.skipTest('Packaged Windows EXE checked in Windows CI')
  with tempfile.TemporaryDirectory() as td:
   builder=BRep_Builder();compound=TopoDS_Compound();builder.MakeCompound(compound)
   for shape in [box(100,50,10),box(40,5,60,(20,10,10))]:builder.Add(compound,shape)
   writer=STEPControl_Writer();writer.Transfer(compound,STEPControl_AsIs);path=Path(td)/'joint.step';writer.Write(str(path))
   exe=Path('src-tauri/cad-backend/ds-cad-engine.exe').resolve();p=subprocess.run([str(exe),str(path),'--joints'],capture_output=True,text=True,timeout=120);self.assertEqual(p.returncode,0,p.stderr);data=json.loads(p.stdout);self.assertAlmostEqual(data['candidates'][0]['lengthMm'],90)
   preview=subprocess.run([str(exe),str(path),'--preview','0'],capture_output=True,text=True,timeout=120);self.assertEqual(preview.returncode,0,preview.stderr);self.assertGreaterEqual(len(json.loads(preview.stdout)['triangles']),12)
 def test_rotational_axes_do_not_chain_offset_holes(self):
  from rotational_features import coaxial_face_groups
  def cylinder(y):return {'axis':[1,0,0],'axisPointMm':[0,y,0],'radiusMm':3}
  groups=coaxial_face_groups([cylinder(0),cylinder(0.015),cylinder(0.030)],[])
  self.assertEqual(len(groups),2)
  self.assertEqual(sorted(g['cylinderFaceCount'] for g in groups),[1,2])
  reverse={'axis':[-1,0,0],'axisPointMm':[100,0,0],'radiusMm':2}
  self.assertEqual(len(coaxial_face_groups([cylinder(0),reverse],[])),1)
if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)
