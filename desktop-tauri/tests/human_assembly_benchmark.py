"""Pinned human-designed press (Woods/Brooks/Pearce), no generated test assembly.
Independent reference: separate STEPControl import + signed triangle integration.
No source CAD is redistributed; its source URL and SHA-256 are recorded.
"""
import argparse,hashlib,json,math,subprocess,sys,time,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'cad_backend'))
import cad_measure as cad
from step_inventory import inventory
URL='https://osf.io/nbxzq/download'
SHA='334286309490685981929f69e71b4bdf99d23bc5f7ccd65fd4db48e1f823cb51'
def triangle_volume(shape):
 try:
  from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
  from OCC.Core.BRep import BRep_Tool
  from OCC.Core.TopLoc import TopLoc_Location
  from OCC.Core.TopAbs import TopAbs_REVERSED
  triangulate=BRep_Tool.Triangulation
 except ImportError:
  from OCP.BRepMesh import BRepMesh_IncrementalMesh
  from OCP.BRep import BRep_Tool
  from OCP.TopLoc import TopLoc_Location
  from OCP.TopAbs import TopAbs_REVERSED
  triangulate=BRep_Tool.Triangulation_s
 # Full, unsampled triangles; not the display mesh or BRepGProp integral.
 BRepMesh_IncrementalMesh(shape,.01,False,.08,False).Perform()
 bounds=cad.bounds(shape);origin=[(bounds[k]+bounds[k+3])/2 for k in range(3)];terms=[];count=0
 for raw in cad.shapes(shape,cad.TopAbs_FACE):
  face=cad.face_cast(raw);loc=TopLoc_Location();tri=triangulate(face,loc)
  if tri is None:raise ValueError('Missing reference tessellation')
  for i in range(1,tri.NbTriangles()+1):
   ids=list(tri.Triangle(i).Get())
   if face.Orientation()==TopAbs_REVERSED:ids.reverse()
   a,b,c=[[v-origin[k] for k,v in enumerate(tri.Node(idx).Transformed(loc.Transformation()).Coord())] for idx in ids]
   terms.append((a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6);count+=1
 return abs(math.fsum(terms)),count

def main():
 p=argparse.ArgumentParser();p.add_argument('--step',type=Path,default=Path('build/human-sheet-press.step'));p.add_argument('--compiled',action='store_true');p.add_argument('--inventory',type=Path);p.add_argument('--reference-only',action='store_true');p.add_argument('--output',type=Path,default=Path('build/human-press'));a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 if not a.step.exists():
  a.step.parent.mkdir(parents=True,exist_ok=True)
  with urllib.request.urlopen(URL,timeout=90) as src:a.step.write_bytes(src.read())
 digest=hashlib.sha256(a.step.read_bytes()).hexdigest();assert digest==SHA,'Public source changed; inspect before updating benchmark'
 start=time.monotonic()
 if not a.reference_only:
  if a.inventory:data=json.loads(a.inventory.read_text(encoding='utf8'))
  elif a.compiled:
   exe=Path('src-tauri/cad-backend/ds-cad-engine.exe').resolve();r=subprocess.run([str(exe),str(a.step.resolve())],capture_output=True,text=True,timeout=1200);assert r.returncode==0,r.stderr;data=json.loads(r.stdout)
  else:data=inventory(a.step)
  (a.output/'inventory.json').write_text(json.dumps(data),encoding='utf8');assert data['count']==220;assert not data['importIssues'];assert len(data['solids'])==220;assert all(s['massKg']>0 for s in data['solids'])
 reader=cad.STEPControl_Reader();assert reader.ReadFile(str(a.step))==cad.IFSelect_RetDone;assert reader.TransferRoots();solids=list(cad.shapes(reader.OneShape(),cad.TopAbs_SOLID));assert len(solids)==220
 volumes=[];triangles=0
 for i,shape in enumerate(solids):
  v,n=triangle_volume(shape);volumes.append(v);triangles+=n
  if (i+1)%25==0:print('REFERENCE',i+1,flush=True)
 ref={'source':URL,'sha256':digest,'author':'Morgan C. Woods, Cameron K. Brooks, Joshua M. Pearce','publication':'https://doi.org/10.1016/j.ohx.2024.e00566','solidCount':len(solids),'triangleCount':triangles,'volumeMm3':sum(volumes),'massKgAt7850':sum(volumes)*7850/1e9,'method':'Independent STEPControl import, signed tetrahedron sum of full triangles (0.01 mm, 0.08 rad)'}
 (a.output/'reference.json').write_text(json.dumps(ref,indent=2),encoding='utf8')
 if not a.reference_only:
  error=abs(data['totalMassKg']-ref['massKgAt7850'])/ref['massKgAt7850'];assert error<.001,('Mass mismatch',error)
  result={**ref,'programMassKgAt7850':data['totalMassKg'],'relativeMassError':error,'engineVersion':data['engineVersion'],'mode':'compiled Windows engine' if a.compiled else 'source OCCT engine','elapsedSeconds':time.monotonic()-start,'status':'PASS','limitations':['Uniform steel density is a comparison assumption, not a verified finished machine weight.','Contact candidates are not a reference weld schedule.','Human assembly includes purchased hardware and multi-body components; solid count is not BOM quantity.']}
  (a.output/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
