"""End-to-end compiled OCCT STEP inventory regression suite. Synthetic known-answer CAD."""
import json, subprocess, tempfile, math
from pathlib import Path
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCC.Core.BRep import BRep_Builder
from OCC.Core.TopoDS import TopoDS_Compound
from OCC.Core.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.gp import gp_Trsf, gp_Vec
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform

EXE=Path('src-tauri/cad-backend/ds-cad-engine.exe').resolve()
def check(name, shapes, count, volume, density=7850):
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
        if name == 'plate_100x50x10':
            hint=d['solids'][0].get('cuttingHint')
            assert hint is not None, ('missing measured plate cut loops',d['solids'][0])
            assert hint['kind']=='plate-outline',hint
            assert abs(hint['thicknessMm']-10.0)<1e-5,hint
            assert abs(hint['contourMm']-300.0)<1e-3,hint
            assert hint['pierces']==1,hint
        if name == 'cylinder_r10_h100':
            assert d['solids'][0].get('cuttingHint') is None, 'round bar is not a sheet plate'
        print(json.dumps({'case':name,'status':'PASS','solids':count,'expected_mass_kg':expected_mass,'actual_mass_kg':d['totalMassKg']}),flush=True)

box=lambda x,y,z:BRepPrimAPI_MakeBox(x,y,z).Shape()
def moved(shape,dx,dy,dz):
    t=gp_Trsf();t.SetTranslation(gp_Vec(dx,dy,dz))
    return BRepBuilderAPI_Transform(shape,t,True).Shape()
check('plate_100x50x10',[box(100,50,10)],1,50000)
check('block_200x100x50',[box(200,100,50)],1,1000000)
check('thin_plate_100x100x1',[box(100,100,1)],1,10000)
check('cylinder_r10_h100',[BRepPrimAPI_MakeCylinder(10,100).Shape()],1,math.pi*10000)
check('two_different_parts',[box(100,50,10),moved(box(20,20,20),200,0,0)],2,58000)
check('five_identical_plates',[moved(box(100,50,10),i*150,0,0) for i in range(5)],5,250000)
check('mixed_ten_parts',[moved(box(10+i,20,30),i*100,0,0) for i in range(10)],10,sum((10+i)*20*30 for i in range(10)))
check('aluminium_density',[box(100,50,10)],1,50000,2700)
print('ALL 8 COMPILED STEP INVENTORY CASES PASS',flush=True)
