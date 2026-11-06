"""Named, nested, rotated manufacturing assembly shared by CAD and installed UI tests."""
import sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from manufacturing_geometry_test import box,rotated,BRepPrimAPI_MakeCylinder,BRepAlgoAPI_Cut,BRepAlgoAPI_Fuse,BRepBuilderAPI_MakePolygon,BRepBuilderAPI_MakeFace,BRepPrimAPI_MakePrism,gp_Pnt,gp_Vec,gp_Trsf
try:
 from OCC.Core.TDocStd import TDocStd_Document
 from OCC.Core.TCollection import TCollection_ExtendedString as S
 from OCC.Core.XCAFDoc import XCAFDoc_DocumentTool
 from OCC.Core.TDataStd import TDataStd_Name
 from OCC.Core.STEPCAFControl import STEPCAFControl_Writer
 from OCC.Core.TopLoc import TopLoc_Location
 tool_fn=XCAFDoc_DocumentTool.ShapeTool;set_name=TDataStd_Name.Set
except ImportError:
 from OCP.TDocStd import TDocStd_Document
 from OCP.TCollection import TCollection_ExtendedString as S
 from OCP.XCAFDoc import XCAFDoc_DocumentTool
 from OCP.TDataStd import TDataStd_Name
 from OCP.STEPCAFControl import STEPCAFControl_Writer
 from OCP.TopLoc import TopLoc_Location
 tool_fn=XCAFDoc_DocumentTool.ShapeTool_s;set_name=TDataStd_Name.Set_s

def prepared_plate(points):
 wire=BRepBuilderAPI_MakePolygon()
 for x,z in points:wire.Add(gp_Pnt(x,0,z))
 wire.Close();return BRepPrimAPI_MakePrism(BRepBuilderAPI_MakeFace(wire.Wire()).Face(),gp_Vec(0,100,0)).Shape()

def write_fixture(path):
 doc=TDocStd_Document(S('fixture'));tool=tool_fn(doc.Main());root=tool.NewShape();set_name(root,S('Złożenie testowe',True))
 sub=tool.NewShape();set_name(sub,S('Podzespół obrócony',True))
 def location(x,y,z):
  tr=gp_Trsf();tr.SetTranslation(gp_Vec(x,y,z));return TopLoc_Location(tr)
 def part(parent,shape,name,loc=None):
  definition=tool.AddShape(shape,False);set_name(definition,S('Definicja '+name,True))
  instance=tool.AddComponent(parent,definition,loc or TopLoc_Location());set_name(instance,S(name,True))
 left=[(-50,0),(0,0),(0,2),(-8,10),(-50,10)]
 part(root,prepared_plate(left),'Blacha lewa V')
 part(root,prepared_plate([(-x,z) for x,z in reversed(left)]),'Blacha prawa V')
 plate=BRepAlgoAPI_Cut(box(330,210,15),BRepPrimAPI_MakeCylinder(10,15).Shape()).Shape()
 part(sub,rotated(plate),'Płyta P-015')
 part(root,rotated(plate),'Płyta P-015 druga',location(1500,0,0))
 inst=tool.AddComponent(root,sub,location(1000,0,0));set_name(inst,S('Instancja podzespołu',True))
 tube=BRepAlgoAPI_Cut(box(40,40,1000),box(36,36,1000,(2,2,0))).Shape()
 notch=box(10,40,10,(0,0,495));tube=BRepAlgoAPI_Cut(tube,notch).Shape()
 part(root,rotated(tube),'Profil SHS z wycięciem',location(2500,0,0))
 ring=BRepAlgoAPI_Cut(BRepPrimAPI_MakeCylinder(10,100,math.pi/2).Shape(),BRepPrimAPI_MakeCylinder(7,100,math.pi/2).Shape()).Shape()
 bent=BRepAlgoAPI_Fuse(BRepAlgoAPI_Fuse(ring,box(50,3,100,(-50,7,0))).Shape(),box(3,40,100,(7,-40,0))).Shape()
 part(root,rotated(bent),'Blacha gięta BG-003',location(3500,0,0))
 tool.UpdateAssemblies();writer=STEPCAFControl_Writer();assert writer.Transfer(doc);writer.Write(str(path))
 return {'names':['Blacha lewa V','Blacha prawa V','Płyta P-015','Płyta P-015 druga','Profil SHS z wycięciem','Blacha gięta BG-003'],'count':6,'grooveAreaMm2':64,'grooveLengthMm':100}

if __name__=='__main__':
 path=Path(sys.argv[1] if len(sys.argv)>1 else 'build/native-fixture.step');path.parent.mkdir(parents=True,exist_ok=True);data=write_fixture(path);path.with_suffix('.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf8')
