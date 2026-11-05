"""Conservative STEP stock-section recognition; never a purchasing or steel-grade proof.

Samples OCCT intersections at 25/50/75% of an elongated solid. An incomplete,
non-manifold, changing or non-standard section stays unknown. This classifier
does not change B-Rep grouping, mass, cutting routes or prices.
"""
import math
try:
    from .stock_patterns import orthogonal_section_kind
except ImportError:
    from stock_patterns import orthogonal_section_kind


def _section_edges(shape, bounds, axis, fraction):
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCC.Core.gp import gp_Pln, gp_Pnt, gp_Dir
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopAbs import TopAbs_EDGE
    from OCC.Core.TopoDS import topods
    from OCC.Core.BRepAdaptor import BRepAdaptor_Curve
    from OCC.Core.GeomAbs import GeomAbs_Line, GeomAbs_Circle

    pos = [(bounds[i] + bounds[i+3]) / 2 for i in range(3)]
    pos[axis] = bounds[axis] + (bounds[axis+3]-bounds[axis])*fraction
    normal = [0., 0., 0.]
    normal[axis] = 1.
    cut = BRepAlgoAPI_Section(shape, gp_Pln(gp_Pnt(*pos), gp_Dir(*normal)), False)
    cut.Build()
    if not cut.IsDone():
        return None
    keep = [i for i in range(3) if i != axis]
    ex = TopExp_Explorer(cut.Shape(), TopAbs_EDGE)
    edges = []
    while ex.More():
        crv = BRepAdaptor_Curve(topods.Edge(ex.Current()))
        start, end = crv.FirstParameter(), crv.LastParameter()
        if not (math.isfinite(start) and math.isfinite(end)):
            return None
        kind = crv.GetType()
        if kind not in (GeomAbs_Line, GeomAbs_Circle):
            return None
        circular = kind == GeomAbs_Circle
        n = max(8, min(96, int(abs(end-start)/(2*math.pi)*64)+1)) if circular else 1
        points = []
        for j in range(n+1):
            xyz = crv.Value(start+(end-start)*j/n).Coord()
            points.append((float(xyz[keep[0]]), float(xyz[keep[1]])))
        edges.append((points, circular, float(crv.Circle().Radius()) if circular else None))
        if len(edges) > 80:
            return None
        ex.Next()
    return edges or None


def _closed_loops(edges, tol):
    def near(a, b):
        return math.dist(a, b) <= tol
    pending = list(edges)
    loops = []
    while pending:
        pts, circ, radius = pending.pop()
        pts = pts[:]
        kinds = [circ]
        radii = [radius] if radius is not None else []
        while not near(pts[0], pts[-1]):
            matches = [(idx, rev) for idx, (p, _, _) in enumerate(pending)
                       for rev, endpoint in ((False, p[0]), (True, p[-1]))
                       if near(pts[-1], endpoint)]
            if len(matches) != 1:
                return None
            idx, rev = matches[0]
            other, iscircle, r = pending.pop(idx)
            segment = other[::-1] if rev else other
            pts.extend(segment[1:])
            kinds.append(iscircle)
            if r is not None:
                radii.append(r)
        if len(pts) < 4:
            return None
        pts[-1] = pts[0]
        area = abs(sum(pts[i][0]*pts[i+1][1]-pts[i+1][0]*pts[i][1]
                       for i in range(len(pts)-1))) / 2
        if area <= tol*tol:
            return None
        loops.append((pts, kinds, radii, area))
    return loops


def _loop_metrics(loop, tol):
    pts, kinds, radii, area = loop
    xy = pts[:-1]
    xs, ys = [p[0] for p in xy], [p[1] for p in xy]
    center = ((min(xs)+max(xs))/2, (min(ys)+max(ys))/2)
    if all(kinds) and radii and max(radii)-min(radii) <= tol*2:
        radius = sum(radii)/len(radii)
        return {'w':2*radius,'h':2*radius,'area':math.pi*radius*radius,
                'circle':True,'rectangle':False,'center':center}
    # Align local 2-D dimensions with one straight section edge. Supports
    # rotated square/rectangular bars without assuming a world XY orientation.
    segments = [(math.dist(pts[i],pts[i+1]),pts[i],pts[i+1])
                for i in range(len(pts)-1) if math.dist(pts[i],pts[i+1])>tol]
    if not segments:
        return None
    _, a, b = max(segments)
    angle = math.atan2(b[1]-a[1], b[0]-a[0])
    co, si = math.cos(angle), math.sin(angle)
    uv = [(x*co+y*si, -x*si+y*co) for x,y in xy]
    w = max(x for x,y in uv)-min(x for x,y in uv)
    h = max(y for x,y in uv)-min(y for x,y in uv)
    if min(w,h) <= tol:
        return None
    perim = sum(math.dist(pts[i],pts[i+1]) for i in range(len(pts)-1))
    rectangular = (not any(kinds) and area/(w*h)>.985 and
                   abs(perim-2*(w+h))<max(tol*10,.01*perim))
    return {'w':w,'h':h,'area':area,'circle':False,
            'rectangle':rectangular,'center':center}


def _classify_section(edges, tol):
    loops = _closed_loops(edges, tol)
    if loops is None or not 1 <= len(loops) <= 2:
        return None
    loops.sort(key=lambda loop:loop[3], reverse=True)
    outer = _loop_metrics(loops[0],tol)
    inner = _loop_metrics(loops[1],tol) if len(loops)==2 else None
    if outer is None or (len(loops)==2 and inner is None):
        return None
    if inner:
        if math.dist(outer['center'],inner['center']) > max(tol*5,.01*max(outer['w'],outer['h'])):
            return None
        if outer['circle'] and inner['circle']:
            diameter = outer['w']
            wall = (outer['w']-inner['w'])/2
            if not tol<wall<diameter/2:
                return None
            return {'kind':'round-tube','diameterMm':diameter,'wallMm':wall,
                    'sectionAreaMm2':outer['area']-inner['area']}
        if outer['rectangle'] and inner['rectangle']:
            dx,dy=(outer['w']-inner['w'])/2,(outer['h']-inner['h'])/2
            if min(dx,dy)<=tol or abs(dx-dy)>max(tol*5,.08*max(dx,dy)):
                return None
            square=abs(outer['w']-outer['h'])<=.02*max(outer['w'],outer['h'])
            return {'kind':'square-hollow' if square else 'rectangular-hollow',
                    'widthMm':max(outer['w'],outer['h']),
                    'heightMm':min(outer['w'],outer['h']),
                    'wallMm':(dx+dy)/2,'sectionAreaMm2':outer['area']-inner['area']}
        return None
    if outer['circle']:
        return {'kind':'round-bar','diameterMm':outer['w'],'sectionAreaMm2':outer['area']}
    if outer['rectangle']:
        small,large=sorted((outer['w'],outer['h']))
        kind = 'flat-section' if large/small>=4 else 'square-bar' if large/small<=1.02 else 'rectangular-bar'
        return {'kind':kind,'widthMm':large,'heightMm':small,'sectionAreaMm2':outer['area']}
    if inner is None and not any(loops[0][1]):
        # Unmodified one-loop orthogonal sections only. Rounded corners or
        # unexpected transitions stay unclassified, not catalogued by bbox.
        return orthogonal_section_kind(loops[0][0], tol)
    return None


def recognize_stock(solid, bounds):
    """Analyze measured cross-sections. Return explicit UNKNOWN on uncertainty."""
    dims = [bounds[i+3]-bounds[i] for i in range(3)]
    if any(not math.isfinite(x) or x<=0 for x in dims):
        return {'kind':'unknown','reason':'Invalid STEP dimensions'}
    axis = max(range(3), key=lambda i:dims[i])
    other = sorted(dims[i] for i in range(3) if i != axis)
    length = dims[axis]
    if length/other[-1]<3.5:
        return {'kind':'unknown','reason':'Not an axis-aligned elongated extrusion; plate or custom stock needs BOM'}
    tol = max(.002,min(other[0]*.0001,.02))
    profiles = []
    try:
        for fraction in (.25,.5,.75):
            edges = _section_edges(solid,bounds,axis,fraction)
            profile = _classify_section(edges,tol) if edges else None
            if profile is None:
                return {'kind':'unknown','reason':'Open, complex or unsupported cross-section'}
            profiles.append(profile)
    except Exception as exc:
        return {'kind':'unknown','reason':'Section calculation unavailable: '+type(exc).__name__}
    first = profiles[0]
    for other in profiles[1:]:
        if first['kind'] != other['kind']:
            return {'kind':'unknown','reason':'Section type changes along part'}
        if any(abs(v-other[k])>max(tol*10,.02*max(abs(v),abs(other[k])))
               for k,v in first.items() if k!='kind'):
            return {'kind':'unknown','reason':'Section size changes along part'}
    return {**first,'lengthMm':length,'confidence':'cross-section-consistent',
            'source':'OCCT sections at 25/50/75% length',
            'limitations':'Cannot determine material grade, nominal standard, plate vs flat-bar procurement or end-cut stock length'}
