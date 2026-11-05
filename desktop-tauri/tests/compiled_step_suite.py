"""End-to-end compiled OCCT STEP inventory regression suite. Synthetic known-answer CAD."""
import json, subprocess, tempfile, math
from pathlib import Path
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCC.Core.BRep import BRep_Builder
from OCC.Core.TopoDS import TopoDS_Compound
from OCC.Core.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.gp import gp_Trsf, gp_Vec, gp_Ax1, gp_Dir, gp_Pnt
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform, BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCC.Core.gp import gp_Pnt

from test_stock_patterns import run_suite
from test_public_stock_audit import run_suite as run_stock_report_suite
run_suite()
run_stock_report_suite()

from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform

EXE=Path('src-tauri/cad-backend/ds-cad-engine.exe').resolve()
def check(name, shapes, count, volume, density=7850, expected_stock=None):
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)/(name+'.step')
        builder=BRep_Builder(); compound=TopoDS_Compound();builder.MakeCompound(compound)
        for shape in shapes: builder.Add(compound,shape)
        writer=STEPControl_Writer()
        assert writer.Transfer(compound,STEPControl_AsIs)==IFSelect_RetDone
        assert writer.Write(str(path))==IFSelect_RetDone
        p=subprocess.run([str(EXE),str(path),'--density',str(density)],capture_output=True,text=True,timeout=180)
        assert p.returncode==0,(name,p.stderr)
        d=json.loads(p.stdout)
        expected_mass=volume*density*1e-9
        assert d['count']==count,(name,'count',d['count'],count)
        assert abs(d['totalMassKg']-expected_mass)<max(1e-5,expected_mass*1e-5),(name,'mass',d['totalMassKg'],expected_mass)
        assert abs(sum(x['volumeMm3'] for x in d['solids'])-volume)<max(1e-3,volume*1e-5)
        if expected_stock:
            stock=d['solids'][0].get('stockHint')
            assert stock is not None, (name,'missing stockHint')
            assert stock['kind']==expected_stock['kind'],(name,stock,expected_stock)
            for field, expected in expected_stock.items():
                if field == 'kind':
                    continue
                assert abs(stock.get(field, float('nan'))-expected)<0.05, (name,field,stock,expected)
            if stock['kind']=='unknown':
                assert stock.get('reason'), (name,stock)
            else:
                expected_confidence='candidate' if stock['kind']=='plate-candidate' else 'cross-section-consistent'
                assert stock.get('confidence')==expected_confidence,(name,stock)
        if name == 'plate_100x50x10':
            hint=d['solids'][0].get('cuttingHint')
            assert hint is not None, ('missing measured plate cut loops',d['solids'][0], 'CAD stderr:', p.stderr)
            assert hint['kind']=='plate-outline',hint
            assert abs(hint['thicknessMm']-10.0)<1e-5,hint
            assert abs(hint['contourMm']-300.0)<1e-3,hint
            assert hint['pierces']==1,hint
        if name == 'cylinder_r10_h100':
            assert d['solids'][0].get('cuttingHint') is None, 'round bar is not a sheet plate'
        print(json.dumps({'case':name,'status':'PASS','solids':count,'expected_mass_kg':expected_mass,'actual_mass_kg':d['totalMassKg']}),flush=True)

box=lambda x,y,z:BRepPrimAPI_MakeBox(x,y,z).Shape()
def prismatic_section(points, length=1000):
    wire = BRepBuilderAPI_MakePolygon()
    for x, y in points:
        wire.Add(gp_Pnt(x, y, 0))
    wire.Close()
    face=BRepBuilderAPI_MakeFace(wire.Wire()).Face()
    return BRepPrimAPI_MakePrism(face, gp_Vec(0,0,length)).Shape()

def moved(shape,dx,dy,dz):
    t=gp_Trsf();t.SetTranslation(gp_Vec(dx,dy,dz))
    return BRepBuilderAPI_Transform(shape,t,True).Shape()
check('plate_100x50x10',[box(100,50,10)],1,50000,expected_stock={'kind':'plate-candidate','thicknessMm':10})
check('block_200x100x50',[box(200,100,50)],1,1000000)
check('thin_plate_100x100x1',[box(100,100,1)],1,10000)
check('cylinder_r10_h100',[BRepPrimAPI_MakeCylinder(10,100).Shape()],1,math.pi*10000)
check('two_different_parts',[box(100,50,10),moved(box(20,20,20),200,0,0)],2,58000)
check('five_identical_plates',[moved(box(100,50,10),i*150,0,0) for i in range(5)],5,250000)
check('mixed_ten_parts',[moved(box(10+i,20,30),i*100,0,0) for i in range(10)],10,sum((10+i)*20*30 for i in range(10)))
check('aluminium_density',[box(100,50,10)],1,50000,2700)
# Two shapes with identical outside dimensions but DIFFERENT raw stock.
solid40 = box(40,40,1000)
hollow40 = BRepAlgoAPI_Cut(box(40,40,1000),moved(box(36,36,1000),2,2,0)).Shape()
hollow80 = BRepAlgoAPI_Cut(box(80,40,1000),moved(box(74,34,1000),3,3,0)).Shape()
tube60 = BRepAlgoAPI_Cut(BRepPrimAPI_MakeCylinder(30,1000).Shape(),BRepPrimAPI_MakeCylinder(27,1000).Shape()).Shape()
check('stock_square_solid',[solid40],1,1600000,expected_stock={'kind':'square-bar','widthMm':40,'heightMm':40})
check('stock_shs_40x40x2',[hollow40],1,304000,expected_stock={'kind':'square-hollow','widthMm':40,'heightMm':40,'wallMm':2})
check('stock_rhs_80x40x3',[hollow80],1,684000,expected_stock={'kind':'rectangular-hollow','widthMm':80,'heightMm':40,'wallMm':3})
check('stock_round_bar_30',[BRepPrimAPI_MakeCylinder(15,1000).Shape()],1,math.pi*225000,expected_stock={'kind':'round-bar','diameterMm':30})
check('stock_round_tube_60x3',[tube60],1,math.pi*171000,expected_stock={'kind':'round-tube','diameterMm':60,'wallMm':3})
check('stock_flat_section',[box(40,5,1000)],1,200000,expected_stock={'kind':'flat-section','widthMm':40,'heightMm':5})
# Exact prismatic structural outline tests: no inference from bounding boxes.
section_cases = [
 ('stock_L_angle', [(0,0),(40,0),(40,5),(5,5),(5,40),(0,40)], 375000, 'angle'),
 ('stock_C_channel', [(0,0),(40,0),(40,5),(5,5),(5,35),(40,35),(40,40),(0,40)], 550000, 'channel'),
 ('stock_T_tee', [(0,0),(5,0),(5,25),(20,25),(20,30),(-15,30),(-15,25),(0,25)], 300000, 'tee'),
 ('stock_I_section', [(0,0),(40,0),(40,5),(23,5),(23,35),(40,35),(40,40),(0,40),
                      (0,35),(17,35),(17,5),(0,5)], 580000, 'i-section'),
]
for name, section, volume, kind in section_cases:
    check(name, [prismatic_section(section)], 1, volume, expected_stock={'kind':kind})

# Tapered cone has an axial circular section, but NOT a constant-stock
# diameter. It must not be presented as a standard round bar.
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeCone
check('stock_tapered_unknown',[BRepPrimAPI_MakeCone(30,20,1000).Shape()],1,
      math.pi*1000*(30**2+30*20+20**2)/3,
      expected_stock={'kind':'unknown'})
# Invalid RHS impostor: centred rotated square opening has the same bbox
# dimensions/area as a square tube, but the walls are not parallel.
internal=box(40,40,1000)
tr=gp_Trsf()
tr.SetTranslation(gp_Vec(20,20,0))
internal=BRepBuilderAPI_Transform(internal,tr,True).Shape()
rot=gp_Trsf()
rot.SetRotation(gp_Ax1(gp_Pnt(40,40,0),gp_Dir(0,0,1)),math.radians(20))
internal=BRepBuilderAPI_Transform(internal,rot,True).Shape()
invalid_hollow=BRepAlgoAPI_Cut(box(80,80,1000),internal).Shape()
check('stock_rotated_hole_unknown',[invalid_hollow],1,4800000,
      expected_stock={'kind':'unknown'})
# A notch between 50% and 75% samples would escape five 2-D cuts.
# The independent 3-D volume gate must reject it.
hidden_notch = BRepAlgoAPI_Cut(
    box(40,40,1000), moved(box(20,40,100),0,0,580)
).Shape()
check('stock_hidden_notch_unknown',[hidden_notch],1,1520000,
      expected_stock={'kind':'unknown'})
print('ALL 8 INVENTORY + 13 STOCK CROSS-SECTION CASES PASS',flush=True)
