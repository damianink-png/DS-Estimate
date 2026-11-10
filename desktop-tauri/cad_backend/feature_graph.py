"""Bounded face-adjacency graph of the ORIGINAL STEP B-Rep.

Independent finished-part geometry evidence. Never determines purchased stock,
technology, routing, cut time or price. No mesh or bounding-box substitution.
"""
import math
try:
    from . import cad_measure as cad
    from .rotational_features import coaxial_face_groups
except ImportError:
    import cad_measure as cad
    from rotational_features import coaxial_face_groups


def _topology_maps(solid):
    # Indexed OCCT maps are substantially cheaper than pairwise edge scans.
    try:
        from OCC.Core.TopExp import topexp
        from OCC.Core.TopTools import (TopTools_IndexedMapOfShape,
                                       TopTools_IndexedDataMapOfShapeListOfShape)
        faces=TopTools_IndexedMapOfShape()
        edges=TopTools_IndexedDataMapOfShapeListOfShape()
        topexp.MapShapes(solid,cad.TopAbs_FACE,faces)
        topexp.MapShapesAndUniqueAncestors(solid,cad.TopAbs_EDGE,cad.TopAbs_FACE,edges,False)
    except ImportError:
        from OCP.TopExp import TopExp
        from OCP.TopTools import (TopTools_IndexedMapOfShape,
                                  TopTools_IndexedDataMapOfShapeListOfShape)
        faces=TopTools_IndexedMapOfShape()
        edges=TopTools_IndexedDataMapOfShapeListOfShape()
        TopExp.MapShapes_s(solid,cad.TopAbs_FACE,faces)
        TopExp.MapShapesAndUniqueAncestors_s(solid,cad.TopAbs_EDGE,cad.TopAbs_FACE,edges,False)
    return faces,edges


def _same_axis(a,b,tolerance_mm=.02,cosine_min=.99999999):
    da,db=a['axis'],b['axis']
    if abs(sum(x*y for x,y in zip(da,db)))<cosine_min:return False
    delta=[a['axisPointMm'][i]-b['axisPointMm'][i] for i in range(3)]
    cross=(delta[1]*da[2]-delta[2]*da[1],
           delta[2]*da[0]-delta[0]*da[2],
           delta[0]*da[1]-delta[1]*da[0])
    return math.sqrt(sum(v*v for v in cross))<=tolerance_mm


def analyze_face_graph(solid,max_faces=160,max_edges=1200):
    """Measure shared-edge topology, surface types and coaxial face chains.

    Graph IDs are 1-based; only genuine shared edges count as adjacency.
    Vertex-only contact and similar directions are insufficient evidence.
    The face/edge budget bounds the cost for vendor models with huge topology.
    """
    if solid is None:return {'status':'unavailable','reason':'missing solid'}
    faces,edges=_topology_maps(solid)
    nf,ne=faces.Extent(),edges.Extent()
    if nf==0 or nf>max_faces or ne>max_edges:
        return {'status':'skipped-budget','faceCount':nf,'edgeCount':ne,
                'reason':'topology budget exceeded; no classification made'}
    try:
        from OCC.Core.TopAbs import TopAbs_REVERSED
    except ImportError:
        from OCP.TopAbs import TopAbs_REVERSED
    kind_counts={'plane':0,'cylinder':0,'cone':0,'other':0}
    info={}
    analytic=[]
    for i in range(1,nf+1):
        face=cad.face_cast(faces.FindKey(i))
        surface=cad.BRepAdaptor_Surface(face)
        typ=surface.GetType()
        row={'type':'other','reversed':face.Orientation()==TopAbs_REVERSED}
        if typ==cad.GeomAbs_Plane:
            normal=surface.Plane().Axis().Direction()
            row={'type':'plane','normal':tuple(map(float,normal.Coord())),
                 'pointMm':tuple(map(float,surface.Plane().Location().Coord())),
                 'wireCount':sum(1 for _ in cad.shapes(face,cad.TopAbs_WIRE))}
        elif typ in (cad.GeomAbs_Cylinder,cad.GeomAbs_Cone):
            obj=surface.Cylinder() if typ==cad.GeomAbs_Cylinder else surface.Cone()
            axis=obj.Axis()
            row={'type':'cylinder' if typ==cad.GeomAbs_Cylinder else 'cone',
                 'axis':tuple(map(float,axis.Direction().Coord())),
                 'axisPointMm':tuple(map(float,axis.Location().Coord()))}
            row['reversed']=face.Orientation()==TopAbs_REVERSED
            if row['type']=='cylinder':row['radiusMm']=float(obj.Radius())
            else:
                row['referenceRadiusMm']=float(obj.RefRadius())
                row['semiAngleRad']=abs(float(obj.SemiAngle()))
            radius=row.get('radiusMm',row.get('referenceRadiusMm'))
            if math.isfinite(radius) and radius>0:analytic.append((i,row))
        kind_counts[row['type']]+=1
        info[i]=row
    links=set();singles=0;nonmanifold=0
    for i in range(1,ne+1):
        ids=sorted({faces.FindIndex(f) for f in edges.FindFromIndex(i)})
        ids=[v for v in ids if v>0]
        if len(ids)==1:singles+=1 # may include a cylindrical seam
        if len(ids)>2:nonmanifold+=1
        for p,left in enumerate(ids):
            for right in ids[p+1:]:links.add((left,right))
    neighbors={i:set() for i in range(1,nf+1)}
    for a,b in links:
        neighbors[a].add(b);neighbors[b].add(a)
    not_seen=set(neighbors);components=0
    while not_seen:
        components+=1;stack=[not_seen.pop()]
        while stack:
            for j in neighbors[stack.pop()] & not_seen:
                not_seen.remove(j);stack.append(j)
    cylindrical=[f for _,f in analytic if f['type']=='cylinder']
    conical=[f for _,f in analytic if f['type']=='cone']
    axis_groups=coaxial_face_groups(cylindrical,conical)
    chains=[]
    for group in axis_groups[:24]:
        axis={'axis':group['axis'],'axisPointMm':group['axisPointMm']}
        ids={idx for idx,f in analytic if _same_axis(f,axis)}
        if len(ids)<2:continue
        direct=sum(1 for a,b in links if a in ids and b in ids)
        bridged=set();bridge_faces=0
        for j,face in info.items():
            if face['type']!='plane':continue
            normal=face['normal']
            if abs(sum(x*y for x,y in zip(normal,axis['axis'])))<.99999:continue
            near=sorted(neighbors[j]&ids)
            if len(near)<2:continue
            bridge_faces+=1
            for p,a in enumerate(near):
                for b in near[p+1:]:bridged.add((a,b))
        radii=sorted({round(info[i]['radiusMm'],6) for i in ids
                      if info[i]['type']=='cylinder'})
        chains.append({
            'axis':group['axis'],
            'cylinderFaceCount':sum(info[i]['type']=='cylinder' for i in ids),
            'coneFaceCount':sum(info[i]['type']=='cone' for i in ids),
            'cylinderRadiiMm':radii,
            'directSharedEdgePairs':direct,
            'axialPlaneBridgeFaces':bridge_faces,
            'bridgedSurfacePairs':len(bridged),
            'status':'connected-face-evidence' if direct or bridged
                     else 'coaxial-only-no-topology-proof'})
    # Guarded local face patterns are independent *finished-geometry* clues.
    # A failed descriptor must not change stock, material, times or the graph.
    try:
        try:from .feature_patterns import measure_graph_features
        except ImportError:from feature_patterns import measure_graph_features
        feature_patterns=measure_graph_features(faces,info,neighbors)
    except Exception as exc:
        feature_patterns={'status':'unavailable','reason':type(exc).__name__,
                          'candidates':[],'counts':{},
                          'limitations':'No stock or manufacturing inference'}
    return {
        'status':'measured','source':'original B-Rep OCCT edge-face ancestor map',
        'faceCount':nf,'edgeCount':ne,'sharedFacePairs':len(links),
        'singleFaceEdges':singles,'nonManifoldEdges':nonmanifold,
        'faceComponents':components,'surfaceTypes':kind_counts,
        'axialClusters':chains,'featurePatterns':feature_patterns,
        'limitations':'Finished geometry only; purchased blank, machining, cutting, time and cost remain unverified'
    }
