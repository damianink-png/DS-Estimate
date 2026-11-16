"""Read-only geometry features derived from the ORIGINAL STEP B-Rep.

These are observations of a FINISHED solid. They never certify purchased
stock, manufacturing method, saw/mill time or cost. Analysis is bounded and
runs once per verified B-Rep geometry through the inventory cache.
"""
import math


def _dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def _axis_match(a,b,position_tol=0.02,axis_cosine_min=0.99999999):
    direction=a.get('axis');other=b.get('axis')
    if not direction or not other or abs(_dot(direction,other))<axis_cosine_min:
        return False
    p,q=a['axisPointMm'],b['axisPointMm']
    delta=tuple(x-y for x,y in zip(p,q))
    cross=(delta[1]*direction[2]-delta[2]*direction[1],
           delta[2]*direction[0]-delta[0]*direction[2],
           delta[0]*direction[1]-delta[1]*direction[0])
    return math.sqrt(_dot(cross,cross))<=position_tol


def _axis_face_range(shape,axis):
    """Project TRUE face vertices onto the original analytical cylinder axis."""
    try:
        from OCC.Core.BRep import BRep_Tool
        from OCC.Core.TopoDS import topods
        from OCC.Core.TopAbs import TopAbs_VERTEX
        from OCC.Core.TopExp import topexp
        from OCC.Core.TopTools import TopTools_IndexedMapOfShape
        vertices=TopTools_IndexedMapOfShape()
        topexp.MapShapes(shape,TopAbs_VERTEX,vertices)
        values=[_dot(BRep_Tool.Pnt(topods.Vertex(vertices.FindKey(i))).Coord(),axis)
                for i in range(1,vertices.Extent()+1)]
    except ImportError:
        from OCP.BRep import BRep_Tool
        from OCP.TopoDS import TopoDS
        from OCP.TopAbs import TopAbs_VERTEX
        from OCP.TopExp import TopExp
        from OCP.TopTools import TopTools_IndexedMapOfShape
        vertices=TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(shape,TopAbs_VERTEX,vertices)
        values=[_dot(BRep_Tool.Pnt_s(TopoDS.Vertex_s(vertices.FindKey(i))).Coord(),axis)
                for i in range(1,vertices.Extent()+1)]
    if not values or not all(math.isfinite(v) for v in values):return None
    return (min(values),max(values))


def _station_touch(a,b,station,tol=0.02):
    """Two walls meet end-to-end, unlike the nested walls of a through tube."""
    ra,rb=a.get('axialRangeMm'),b.get('axialRangeMm')
    if not ra or not rb:return False
    if min(ra[1]-ra[0],rb[1]-rb[0])<=tol:return False
    return ((abs(ra[1]-station)<=tol and abs(rb[0]-station)<=tol)
            or (abs(rb[1]-station)<=tol and abs(ra[0]-station)<=tol))


def measure_graph_features(faces,info,neighbors,max_candidates=96):
    """Return measured candidates from genuine shared-edge B-Rep topology.

    The local axial extents are obtained from surface boundary vertices,
    NOT axis-aligned bounding boxes, a tessellation or part-name heuristics.
    """
    cylinder_ids=[i for i,f in info.items() if f['type']=='cylinder']
    cone_ids=[i for i,f in info.items() if f['type']=='cone']
    for i in cylinder_ids:
        info[i]['axialRangeMm']=_axis_face_range(faces.FindKey(i),info[i]['axis'])
    found=[];seen=set()
    def add(kind,ids,**extra):
        key=(kind,tuple(sorted(ids)))
        if key in seen or len(found)>=max_candidates:return
        seen.add(key)
        found.append({'kind':kind,'faces':list(sorted(ids)),
                      'confidence':'topology-candidate',**extra})

    # A through-opening has an inward-oriented cylindrical wall touching two
    # distinct multi-loop end faces. A blind hole has no second open end;
    # a plain outer shaft wall is normally not inward-oriented.
    for i in cylinder_ids:
        cylinder=info[i]
        if not cylinder.get('reversed'):continue
        axis=cylinder['axis']
        caps=sorted(j for j in neighbors[i]
                    if info[j]['type']=='plane'
                    and info[j].get('wireCount',0)>=2
                    and abs(_dot(info[j]['normal'],axis))>=.99999)
        for offset,a in enumerate(caps):
            for b in caps[offset+1:]:
                apos=_dot(info[a]['pointMm'],axis)
                bpos=_dot(info[b]['pointMm'],axis)
                if abs(apos-bpos)<=.02:continue
                span=cylinder.get('axialRangeMm')
                if span and (abs(span[0]-min(apos,bpos))>.02
                             or abs(span[1]-max(apos,bpos))>.02):
                    continue
                add('through-cylindrical-opening',(i,a,b),
                    diameterMm=round(2*cylinder['radiusMm'],5),
                    axis=[round(x,8) for x in axis],
                    axialLengthMm=round(abs(apos-bpos),5),
                    evidence='inward cylinder joined to two distinct multi-loop end faces')

    # True shared-edge joins of coaxial conical and cylindrical surfaces.
    # Cones may mean a taper, chamfer, countersink or a cast detail; the
    # particular production operation is deliberately not inferred.
    for c in cone_ids:
        cone=info[c]
        for i in sorted(neighbors[c]):
            cylinder=info[i]
            if cylinder['type']!='cylinder' or not _axis_match(cone,cylinder):
                continue
            add('coaxial-conical-transition',(c,i),
                axis=[round(x,8) for x in cone['axis']],
                coneHalfAngleDeg=round(cone['semiAngleRad']*180/math.pi,5),
                cylindricalDiameterMm=round(2*cylinder['radiusMm'],5),
                evidence='true shared edge between coaxial cone and cylinder')

    # Only report a diameter shoulder when walls with different diameters
    # stop/start on opposite sides of a common perpendicular plane.
    # This specifically prevents the inner+outer walls of a through-tube
    # from being misidentified as consecutive turned shaft diameters.
    shoulders=[]
    cylset=set(cylinder_ids)
    for p,plane in info.items():
        if plane['type']!='plane':continue
        adjacent=sorted(neighbors[p]&cylset)
        for x,a in enumerate(adjacent):
            for b in adjacent[x+1:]:
                left,right=info[a],info[b]
                if not _axis_match(left,right):continue
                if abs(left['radiusMm']-right['radiusMm'])<=.02:continue
                axis=left['axis']
                if abs(_dot(plane['normal'],axis))<.99999:continue
                station=_dot(plane['pointMm'],axis)
                if not _station_touch(left,right,station):continue
                shoulders.append((a,b,p))
                add('coaxial-diameter-shoulder',(a,b,p),
                    diametersMm=sorted([round(2*left['radiusMm'],5),
                                        round(2*right['radiusMm'],5)]),
                    axis=[round(x,8) for x in axis],
                    stationMm=round(station,5),
                    evidence='two different coaxial cylinder faces terminate on opposite sides of one plane')

    # A smaller central wall between TWO shoulder planes provides a bounded
    # recess/neck candidate, not proof of a lathe cut or catalogue groove.
    for i in cylinder_ids:
        center=info[i]
        joins=[(b if a==i else a,p) for a,b,p in shoulders if i in (a,b)]
        for x,(left,p1) in enumerate(joins):
            for right,p2 in joins[x+1:]:
                if p1==p2 or left==right:continue
                if min(info[left]['radiusMm'],info[right]['radiusMm'])-center['radiusMm']<=.02:
                    continue
                station_a=_dot(info[p1]['pointMm'],center['axis'])
                station_b=_dot(info[p2]['pointMm'],center['axis'])
                span=center.get('axialRangeMm')
                if not span or (abs(span[0]-min(station_a,station_b))>.02
                                or abs(span[1]-max(station_a,station_b))>.02):
                    continue
                add('reduced-diameter-axial-section',(left,i,right,p1,p2),
                    centralDiameterMm=round(2*center['radiusMm'],5),
                    axialLengthMm=round(span[1]-span[0],5),
                    evidence='lower-radius section bounded by two independent coaxial shoulder planes')

    # A transverse cylinder touching another cylinder is an analytical
    # intersection; it is NOT automatically a drilled cross-hole.
    for a in cylinder_ids:
        for b in sorted(neighbors[a]&cylset):
            if b<=a:continue
            left,right=info[a],info[b]
            cos=abs(_dot(left['axis'],right['axis']))
            if cos<.985:
                add('intersecting-cylinder-axes',(a,b),
                    axisCosine=round(cos,6),
                    evidence='nonparallel original cylinder walls share an edge')

    counts={}
    for item in found:counts[item['kind']]=counts.get(item['kind'],0)+1
    return {'status':'measured',
            'source':'original B-Rep face orientation, vertex extents and shared edges',
            'candidates':found,'counts':counts,
            'truncated':len(found)>=max_candidates,
            'limitations':'Finished geometry only; stock, purchase, cutting, machining and cost remain unverified'}
