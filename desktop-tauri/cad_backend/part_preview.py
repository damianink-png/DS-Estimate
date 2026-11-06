"""On-demand tessellation of one STEP occurrence, independent of quote analysis."""
import math
try:from . import cad_measure as cad
except ImportError:import cad_measure as cad

def mesh_part(shape,max_triangles=40000):
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
    bounds=cad.bounds(shape);size=max(bounds[i+3]-bounds[i] for i in range(3))
    BRepMesh_IncrementalMesh(shape,max(.1,size/160),False,.3,True).Perform()
    triangles=[];center=[(bounds[i]+bounds[i+3])/2 for i in range(3)]
    for raw in cad.shapes(shape,cad.TopAbs_FACE):
        face=cad.face_cast(raw);loc=TopLoc_Location();tri=triangulate(face,loc)
        if tri is None:continue
        for i in range(1,tri.NbTriangles()+1):
            ids=list(tri.Triangle(i).Get())
            if face.Orientation()==TopAbs_REVERSED:ids.reverse()
            triangle=[]
            for idx in ids:
                pt=tri.Node(idx).Transformed(loc.Transformation())
                triangle.append([round((pt.Coord()[k]-center[k])/size,6) for k in range(3)])
            triangles.append(triangle)

    total=len(triangles)
    if total>max_triangles:
        step=math.ceil(total/max_triangles);triangles=triangles[::step]
    if not triangles:raise ValueError('OCCT returned no display triangles')
    return {'triangles':triangles,'partial':total>max_triangles,'originalTriangleCount':total,'source':'OCCT B-Rep tessellation'}

def preview(path,index):
    solids=cad.load_step(path)
    if index<0 or index>=len(solids):raise ValueError('Invalid occurrence index')
    return mesh_part(solids[index])
