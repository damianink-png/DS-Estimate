"""Conservative STEP stock-section recognition; never a purchasing or steel-grade proof.

Samples OCCT intersections at 10/25/50/75/90% of an elongated solid. An incomplete,
non-manifold, changing or non-standard section stays unknown. This classifier
does not change B-Rep grouping, mass, cutting routes or prices.
"""
import math
try:
    from .section_catalog import match_hint,match_open_loop
except ImportError:
    from section_catalog import match_hint,match_open_loop
try:
    from .stock_patterns import orthogonal_section_kind, convex_polygon_section_kind, beveled_rectangle_section_kind
except ImportError:
    from stock_patterns import orthogonal_section_kind, convex_polygon_section_kind, beveled_rectangle_section_kind


def _section_edges(shape, bounds, axis, fraction):
    try:from . import cad_measure as api
    except ImportError:import cad_measure as api
    BRepAlgoAPI_Section=api.BRepAlgoAPI_Section;gp_Pln=api.gp_Pln;gp_Pnt=api.gp_Pnt;gp_Dir=api.gp_Dir
    TopExp_Explorer=api.TopExp_Explorer;TopAbs_EDGE=api.TopAbs_EDGE
    BRepAdaptor_Curve=api.BRepAdaptor_Curve;GeomAbs_Line=api.GeomAbs_Line;GeomAbs_Circle=api.GeomAbs_Circle

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
        crv = BRepAdaptor_Curve(api.edge_cast(ex.Current()))
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
        straight = [(pts[0],pts[-1])] if not circ else []
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
            if not iscircle:straight.append((segment[0],segment[-1]))
            if r is not None:
                radii.append(r)
        if len(pts) < 4:
            return None
        pts[-1] = pts[0]
        area = abs(sum(pts[i][0]*pts[i+1][1]-pts[i+1][0]*pts[i][1]
                       for i in range(len(pts)-1))) / 2
        if area <= tol*tol:
            return None
        loops.append((pts, kinds, radii, area, straight))
    return loops


def _loop_metrics(loop, tol):
    pts, kinds, radii, area = loop[:4]
    xy = pts[:-1]
    xs, ys = [p[0] for p in xy], [p[1] for p in xy]
    # World-aligned bbox centres are not geometric centres of a rotated
    # rectangular loop, especially when its sides have unequal lengths.
    # Use the section's own edge-aligned frame for rectangular loops below.
    center = ((min(xs)+max(xs))/2, (min(ys)+max(ys))/2)
    if all(kinds) and radii and max(radii)-min(radii) <= tol*2:
        radius = sum(radii)/len(radii)
        return {'w':2*radius,'h':2*radius,'area':math.pi*radius*radius,
                'circle':True,'rectangle':False,'center':center}
    # Align local 2-D dimensions with one straight section edge. Supports
    # rotated square/rectangular bars without assuming a world XY orientation.
    segments = [(math.dist(a,b),a,b) for a,b in loop[4] if math.dist(a,b)>tol] if len(loop)>4 else [(math.dist(pts[i],pts[i+1]),pts[i],pts[i+1]) for i in range(len(pts)-1) if math.dist(pts[i],pts[i+1])>tol]
    if not segments:
        return None
    _, a, b = max(segments)
    angle = math.atan2(b[1]-a[1], b[0]-a[0])
    co, si = math.cos(angle), math.sin(angle)
    uv = [(x*co+y*si, -x*si+y*co) for x,y in xy]
    umin, umax = min(x for x,y in uv), max(x for x,y in uv)
    vmin, vmax = min(y for x,y in uv), max(y for x,y in uv)
    w, h = umax-umin, vmax-vmin
    # The inner and outer loops can have different tessellation or corner
    # detail; world-axis bbox centres can drift despite a concentric hole.
    uc, vc = (umin+umax)/2, (vmin+vmax)/2
    center = (uc*co-vc*si, uc*si+vc*co)
    if min(w,h) <= tol:
        return None
    perim = sum(math.dist(pts[i],pts[i+1]) for i in range(len(pts)-1))
    # A nearly rectangular parallelogram can satisfy area/bbox and
    # perimeter heuristics while having non-orthogonal walls. Demand that
    # EVERY measured straight edge is parallel to one of the local axes.
    # This also permits collinear split edges from STEP topology.
    axis_aligned_edges = all(
        min(abs((q[0]-p[0])*si-(q[1]-p[1])*co),
            abs((q[0]-p[0])*co+(q[1]-p[1])*si))
        <= max(tol, .002 * length)
        for length, p, q in segments
    )
    rectangular = (not any(kinds) and axis_aligned_edges
                   and area/(w*h)>.985 and
                   abs(perim-2*(w+h))<max(tol*10,.01*perim))
    rounded = False
    if any(kinds) and len(segments)>=4 and len(radii)>=4 and axis_aligned_edges:
        radius=sum(radii)/len(radii)
        expected=w*h-(4-math.pi)*radius*radius
        rounded=(max(radii)-min(radii)<=tol*5 and radius<min(w,h)/2
                 and abs(area-expected)<=max(.2,expected*.005))
    return {'w':w,'h':h,'area':area,'circle':False,
            'rectangle':rectangular or rounded,'center':center,'edgeAngleRad':angle}


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
        # A small offset relative to the overall profile size can be a
        # substantial fraction of the wall thickness. Require concentricity
        # relative to the measured wall, not the outside bbox.
        wall_estimate = (min(outer['w']-inner['w'], outer['h']-inner['h']) / 2)
        if wall_estimate <= tol:
            return None
        if math.dist(outer['center'], inner['center']) > max(tol*5, .05*wall_estimate):
            return None
        if outer['circle'] and inner['circle']:
            diameter = outer['w']
            wall = (outer['w']-inner['w'])/2
            if not tol<wall<diameter/2:
                return None
            return {'kind':'round-tube','diameterMm':diameter,'wallMm':wall,
                    'sectionAreaMm2':outer['area']-inner['area']}
        if outer['rectangle'] and inner['rectangle']:
            # Parallel exterior/interior walls are essential evidence of RHS/SHS.
            # Bbox and wall offsets alone incorrectly accept a rotated hole.
            if abs(math.sin(2*(outer['edgeAngleRad'] - inner['edgeAngleRad']))) > 0.02:
                return None
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
        return (orthogonal_section_kind(loops[0][0], tol) or
                match_open_loop(loops[0][0],loops[0][3]) or
                beveled_rectangle_section_kind(loops[0][0], tol) or
                convex_polygon_section_kind(loops[0][0], tol))
    return match_open_loop(loops[0][0],loops[0][3]) if inner is None else None


def _measured_solid_volume(solid):
    """Independent 3-D volume check; section sampling alone can miss a slot."""
    try:from . import cad_measure as api
    except ImportError:import cad_measure as api
    volume=api.volume(solid)
    if not math.isfinite(volume) or volume <= 0:
        raise ValueError('Invalid OCCT solid volume')
    return volume


def _recognize_axis_stock(solid, bounds, plate_hint=None, axis_override=None):
    """Recognise prismatic shapes or a measured *candidate* plate; no catalogue proof."""
    dims = [bounds[i+3]-bounds[i] for i in range(3)]
    if any(not math.isfinite(x) or x<=0 for x in dims):
        return {'kind':'unknown','reason':'Invalid STEP dimensions'}
    axis = max(range(3), key=lambda i:dims[i]) if axis_override is None else axis_override
    other = sorted(dims[i] for i in range(3) if i != axis)
    length = dims[axis]
    if length/other[-1]<3.5 and axis_override is None:
        # Prefer geometrically evidenced planar sheet over a bare bbox ratio.
        # The planar-face contour can also be present on pocketed/finished
        # parts, so plate is a procurement CANDIDATE rather than a proof.
        # A planar outline is not sufficient if its independently measured
        # thickness disagrees with the solid's thin bounding dimension.
        # This prevents a cutting hint from another face/feature being
        # mistaken for the raw sheet thickness.
        measured_thickness = plate_hint.get('thicknessMm') if isinstance(plate_hint, dict) else None
        if (isinstance(plate_hint, dict) and plate_hint.get('kind') == 'plate-outline'
                and type(measured_thickness) in (int, float)
                and math.isfinite(measured_thickness) and measured_thickness > 0
                and abs(measured_thickness-other[0]) <= max(.02, .01*other[0])
                and other[1] / other[0] >= 5 - 1e-5):
            return {'kind':'plate-candidate','thicknessMm':other[0],
                    'widthMm':other[1],'lengthMm':length,
                    'confidence':'candidate',
                    'source':'OCCT major planar faces and measured outline',
                    'limitations':'Validate blank outline, material and manufacturing process against drawing/BOM'}
        return {'kind':'unknown','reason':'Not an axis-aligned elongated extrusion; plate or custom stock needs BOM'}
    tol = max(.002,min(other[0]*.0001,.02))
    profiles = []
    try:
        for fraction in (.10,.25,.50,.75,.90):
            edges = _section_edges(solid,bounds,axis,fraction)
            profile = _classify_section(edges,tol) if edges else None
            profiles.append(profile)
    except Exception as exc:
        return {'kind':'unknown','reason':'Section calculation unavailable: '+type(exc).__name__}
    valid=[p for p in profiles if p]
    if not valid:return {'kind':'unknown','reason':'Open, complex or unsupported cross-section'}
    def alike(a,b):
        return a['kind']==b['kind'] and all(abs(v-b.get(k,float('inf')))<=max(tol*10,.02*max(abs(v),abs(b.get(k,0)))) for k,v in a.items() if k!='kind')
    first=max(valid,key=lambda p:sum(alike(p,q) for q in valid));support=sum(alike(first,p) for p in valid)
    expected=first['sectionAreaMm2']*length
    if not math.isfinite(expected) or expected <= 0:
        return {'kind':'unknown','reason':'Invalid predicted extrusion volume'}
    # One independent OCCT volume evaluation is enough for both the raw-stock
    # candidate and the final prism check. It is expensive on large STEP parts.
    # Failure must be explicit, not swallowed by the orientation fallback.
    try:
        measured=_measured_solid_volume(solid) if solid is not None else expected
    except Exception as exc:
        return {'kind':'unknown','reason':'Independent volume check unavailable: '+type(exc).__name__}
    # A chamfer running along a bar is a feature of the FINISHED section,
    # not proof that the purchased raw section has the same missing corner.
    # Recover only a conservative rectangular blank candidate. Keep kind
    # UNKNOWN so no existing cutting/production cost route treats it as a
    # certified prismatic product; the user still sees its measured core.
    if first['kind']=='beveled-rectangle':
        blank_kind=('flat-section' if first['widthMm']/first['heightMm']>=4
                    else 'square-bar' if first['widthMm']/first['heightMm']<=1.02
                    else 'rectangular-bar')
        verified=(support==5 and abs(measured-expected)<=max(1.,expected*.02))
        raw_blank=({'kind':blank_kind,'widthMm':first['widthMm'],
                    'heightMm':first['heightMm'],'lengthMm':length,
                    'sectionAreaMm2':first['blankSectionAreaMm2'],
                    'confidence':'geometric-blank-candidate',
                    'source':'five original B-Rep cross-sections with small corner bevels',
                    'limitations':'Rectangular envelope, not proof of purchased blank or chamfer operation'}
                   if verified else None)
        return {'kind':'unknown','reason':'Finished section contains longitudinal corner bevels',
                'finishedSectionEvidence':{**first,'supportingSections':support,
                                           'sampledSections':5,'finishedVolumeMm3':measured,
                                           'sectionPrismVolumeMm3':expected},
                **({'rawStockCandidate':raw_blank} if raw_blank else {})}
    raw={**first,'lengthMm':length,'confidence':'raw-stock-candidate','supportingSections':support,
         'sampledSections':5,'removedVolumeMm3':max(0,expected-measured),'source':'repeated B-Rep sections, finished part contains stock removal'} if support>=3 and 0<measured<expected*1.02 else None
    # A long, locally oriented SHEET may resemble a flat bar in repeated
    # cross-sections. When the original major planar B-Rep faces independently
    # prove sheet thickness and the solid has volume REMOVED from that flat
    # rectangular envelope, keep the sheet candidate instead of losing it.
    # This is geometry only: stock sourcing, bevels and operations are unknown.
    # Added volume (Portal Frame end features) cannot pass this safeguard.
    measured_plate=(isinstance(plate_hint,dict)
                    and plate_hint.get('kind')=='plate-outline'
                    and type(plate_hint.get('thicknessMm')) in (int,float)
                    and math.isfinite(plate_hint['thicknessMm'])
                    and abs(plate_hint['thicknessMm']-other[0])
                        <= max(.02,.01*other[0]))
    if (support==5 and first['kind']=='flat-section' and raw is not None
            and measured < expected-max(1.,expected*.02)
            and measured_plate and other[1]/other[0]>=5-1e-5):
        return {'kind':'plate-candidate','thicknessMm':other[0],
                'widthMm':other[1],'lengthMm':length,
                'confidence':'candidate','rawStockCandidate':raw,
                'source':'original B-Rep major planar faces and five local flat sections',
                'limitations':'Plate/flat-bar sourcing and removed material/edge treatment require BOM or drawing; no process or cut-time inference'}
    # A verified central section may describe a core, NOT a whole purchasable
    # stock: added end blocks, fittings and bosses can make the solid volume
    # exceed section area times span. Keep the geometric evidence separately.
    # Never feed this field into the cutting or CNC stock calculators.
    core=({**first,'lengthMm':length,'confidence':'geometric-core-only',
           'supportingSections':support,'sampledSections':5,
           'sectionPrismVolumeMm3':expected,'finishedVolumeMm3':measured,
           'source':'five measured B-Rep cross-sections; larger finished volume forbids a stock inference'}
          if support==5 and measured>expected*1.02 else None)
    if support<5:
        return {'kind':'unknown','reason':'Section changes along finished part',**({'rawStockCandidate':raw} if raw else {})}
    # Cross-sections can all match while a pocket or notch exists between
    # sampling planes. Compare independent B-Rep volume against the prism
    # implied by the measured section and its full bounding length.
    if abs(measured-expected) > max(1.0, expected*.02):
        return {'kind':'unknown','reason':'3-D volume inconsistent with constant stock section (possible pocket, notch or end machining)',
                **({'rawStockCandidate':raw} if raw else {}),
                **({'coreSectionCandidate':core} if core else {})}
    return {**first,'lengthMm':length,'confidence':'cross-section-consistent',
            'source':'OCCT sections at 10/25/50/75/90% length',
            'limitations':'Cannot determine material grade, nominal standard, plate vs flat-bar procurement or end-cut stock length'}


def _short_profile(shape,bounds,axis,face_count_cache=None):
    if shape is None or not hasattr(shape,'ShapeType'):return None
    dims=[bounds[i+3]-bounds[i] for i in range(3)];cross=sorted((dims[i] for i in range(3) if i!=axis),reverse=True)
    if dims[axis]/cross[0]>=3.5:return None
    catalog_fit=any(match_hint({'kind':kind,'widthMm':cross[0],'heightMm':cross[1]}) for kind in ('square-hollow','rectangular-hollow','round-tube','angle','channel','tee','i-section'))
    if not catalog_fit:
        # Imperial/non-catalogue closed sections still have geometric evidence.
        # A cheap complexity limit avoids sectioning arbitrary vendor hardware.
        try:from . import cad_measure as api
        except ImportError:import cad_measure as api
        # A short-part probe may try all three world axes. Enumerating every
        # OCCT face for each axis is expensive on large STEP assemblies.
        # Cache only within this solid's recognition call (never across parts).
        # The only decision is <=32 versus >32 faces; stop after the 33rd
        # rather than traversing every face of a complex imported part.
        if face_count_cache is None:
            face_count=sum(1 for _, face in zip(range(33), api.shapes(shape,api.TopAbs_FACE)))
        elif face_count_cache:
            face_count=face_count_cache[0]
        else:
            face_count=sum(1 for _, face in zip(range(33), api.shapes(shape,api.TopAbs_FACE)))
            face_count_cache.append(face_count)
        if face_count>32:return None
        edges=_section_edges(shape,bounds,axis,.5)
        mid=_classify_section(edges,max(.002,min(cross[1]*.0001,.02))) if edges else None
        if not mid or mid.get('kind') not in ('square-hollow','rectangular-hollow','round-tube'):return None
    candidate=_recognize_axis_stock(shape,bounds,axis_override=axis)
    if candidate.get('kind') not in ('square-hollow','rectangular-hollow','round-tube','angle','channel','tee','i-section'):return None
    if candidate.get('lengthMm',0)<max(2,2*candidate.get('wallMm',1)):return None
    if not match_hint(candidate) and candidate['kind'] not in ('square-hollow','rectangular-hollow','round-tube'):return None
    return {**candidate,'source':'five consistent sections and volume along a short extrusion axis'}

def recognize_stock(solid, bounds, plate_hint=None):
    """Try the existing world frame, then a frame aligned with the longest straight edge."""
    result=_recognize_axis_stock(solid,bounds,plate_hint)
    if result.get('kind')=='unknown' and solid is not None:
        face_count_cache=[]
        for axis in range(3):
            short=_short_profile(solid,bounds,axis,face_count_cache)
            if short:result=short;break
    if result.get('kind') in ('unknown','plate-candidate') and solid is not None:
        try:
            try:from . import cad_measure as api
            except ImportError:import cad_measure as api
            TopExp_Explorer=api.TopExp_Explorer;TopAbs_EDGE=api.TopAbs_EDGE
            BRepAdaptor_Curve=api.BRepAdaptor_Curve;GeomAbs_Line=api.GeomAbs_Line
            gp_Trsf=api.gp_Trsf;gp_Ax3=api.gp_Ax3;gp_Pnt=api.gp_Pnt;gp_Dir=api.gp_Dir
            BRepBuilderAPI_Transform=api.BRepBuilderAPI_Transform;Bnd_Box=api.Bnd_Box
            edges=TopExp_Explorer(solid,TopAbs_EDGE)
            edge_axes=[];cylinder_axes=[];plane_axes=[]
            while edges.More():
                curve=BRepAdaptor_Curve(api.edge_cast(edges.Current()))
                if curve.GetType()==GeomAbs_Line:
                    a=curve.Value(curve.FirstParameter());b=curve.Value(curve.LastParameter())
                    length=a.Distance(b)
                    if length>1e-6:
                        edge_axes.append((length,gp_Dir(b.X()-a.X(),b.Y()-a.Y(),b.Z()-a.Z())))
                edges.Next()
            # A long tube tilted by even 1 degree produces ellipses in a world
            # section. Prefer the actual cylindrical-face axis, not just the
            # longest edge (which may be part of a welded end plate).
            for raw in api.shapes(solid,api.TopAbs_FACE):
                surface=api.BRepAdaptor_Surface(api.face_cast(raw))
                if surface.GetType()==api.GeomAbs_Cylinder:
                    cylinder_axes.append((surface.Cylinder().Radius(),
                                          surface.Cylinder().Axis().Direction()))
                elif surface.GetType()==api.GeomAbs_Plane:
                    plane_axes.append((0,surface.Plane().Axis().Direction()))
            # Only the first eight unique candidate axes are ever tested.
            # Stop deduplication as soon as the budget is filled: on a complex
            # imported part, scanning hundreds of extra edges/planes performs
            # unnecessary OCCT direction comparisons without affecting output.
            sorted_edges=sorted(edge_axes,key=lambda item:-item[0])
            ordered=(sorted(cylinder_axes,key=lambda item:-item[0])+
                     sorted_edges+plane_axes)
            axes=[]
            for _,d in ordered:
                if not any(abs(d.Dot(old))>.99999 for old in axes):
                    axes.append(d)
                    if len(axes)==8:break
            best_local=None
            for direction in axes:
                try:
                    # gp_Ax3 requires a truly perpendicular X direction, not
                    # merely abs(dot)<.001. Project the reference edge into
                    # the cutting plane to prevent an OCC constructor error.
                    cross=next((d for _,d in sorted_edges
                                if abs(d.Dot(direction))<.95),None)
                    if cross is None:
                        frame=gp_Ax3(gp_Pnt(0,0,0),direction)
                    else:
                        dot=cross.Dot(direction)
                        x=(cross.X()-dot*direction.X(),
                           cross.Y()-dot*direction.Y(),
                           cross.Z()-dot*direction.Z())
                        frame=gp_Ax3(gp_Pnt(0,0,0),direction,gp_Dir(*x))
                    tr=gp_Trsf();tr.SetTransformation(frame)
                    local=BRepBuilderAPI_Transform(solid,tr,True).Shape()
                    box=Bnd_Box();api.add_bounds(local,box)
                    local_hint=api.plate_hint(local)
                    candidate=_recognize_axis_stock(local,box.Get(),local_hint)
                    if candidate.get('kind')=='unknown':
                        candidate=_short_profile(local,box.Get(),2) or candidate
                    local_dims=sorted((b-a for a,b in zip(box.Get()[:3],box.Get()[3:])),reverse=True)
                    if best_local is None or math.prod(local_dims)<math.prod(best_local):
                        best_local=local_dims
                    if candidate.get('kind')!='unknown':
                        result={**candidate,'localFrame':'B-Rep edge/face axis','localDimsMm':local_dims}
                        if local_hint:result['localCuttingHint']=local_hint
                        break
                    if candidate.get('rawStockCandidate'):
                        result={**result,'rawStockCandidate':{**candidate['rawStockCandidate'],
                                                               'localDimsMm':local_dims}}
                    if candidate.get('coreSectionCandidate'):
                        result={**result,'coreSectionCandidate':{**candidate['coreSectionCandidate'],
                                                                  'localDimsMm':local_dims,
                                                                  'axisEvidence':'B-Rep cylinder/edge axis'}}
                    if local_hint:result={**result,'localCuttingHint':local_hint}
                except Exception:
                    # One malformed edge/reference frame must not disable all
                    # other axis proposals for this solid.
                    continue
            if best_local and 'localDimsMm' not in result:result['localDimsMm']=best_local
        except Exception:
            pass # An unsupported orientation stays unknown; never a bbox-only match.
    # Capture coaxiality from axis LOCATIONS, not just their directions.
    try:
        from .rotational_features import coaxial_face_groups
    except ImportError:
        from rotational_features import coaxial_face_groups
    # Diagnostic evidence measured on the ORIGINAL imported B-Rep, never on
    # a bounding-box proxy. It is deliberately not used for stock/cost decisions.
    # Expose only unresolved solids to keep the STEP inventory reasonably small.
    if result.get('kind') == 'unknown' and solid is not None:
        try:
            try:from . import cad_measure as api
            except ImportError:import cad_measure as api
            cylinders=[]
            cones=[]
            planes=[]
            plane_face_count=0
            other_face_count=0
            for raw_face in api.shapes(solid, api.TopAbs_FACE):
                surface=api.BRepAdaptor_Surface(api.face_cast(raw_face))
                kind=surface.GetType()
                if kind == api.GeomAbs_Plane:
                    plane_face_count+=1
                    # Only the first 64 plane measurements are ever exported.
                    # On large vendor assemblies, GProp surface integration for
                    # every additional face was wasted CPU and memory.
                    if len(planes)>=64:
                        continue
                    plane=surface.Plane()
                    direction=plane.Axis().Direction()
                    origin=plane.Location()
                    normal=tuple(float(v) for v in direction.Coord())
                    # The signed plane offset is orientation-dependent. Together
                    # with face area it permits future parallel-face/thickness
                    # audits without mistaking a small bevel for a plate face.
                    props=api.GProp_GProps()
                    api.surface_props(api.face_cast(raw_face), props)
                    face_area=abs(float(props.Mass()))
                    offset=sum(normal[i]*float(origin.Coord()[i]) for i in range(3))
                    if math.isfinite(face_area) and math.isfinite(offset):
                        planes.append({'normal':[round(v,8) for v in normal],
                                       'areaMm2':round(face_area,6),
                                       'signedOffsetMm':round(offset,6)})
                elif kind == api.GeomAbs_Cylinder:
                    cyl=surface.Cylinder()
                    direction=cyl.Axis().Direction()
                    cylinders.append({'radiusMm':round(float(cyl.Radius()),6),
                                      'axis':[round(float(v),8) for v in direction.Coord()],
                                      'axisPointMm':[round(float(v),6) for v in cyl.Axis().Location().Coord()]})
                elif kind == api.GeomAbs_Cone:
                    cone=surface.Cone()
                    direction=cone.Axis().Direction()
                    cones.append({'referenceRadiusMm':round(float(cone.RefRadius()),6),
                                  'semiAngleRad':round(float(cone.SemiAngle()),8),
                                  'axis':[round(float(v),8) for v in direction.Coord()],
                                  'axisPointMm':[round(float(v),6) for v in cone.Axis().Location().Coord()]})
                else:
                    other_face_count+=1
            if cylinders or cones or planes:
                result['finishedBrepSurfaceEvidence']={
                    'source':'original STEP B-Rep face adaptors',
                    'cylinders':cylinders[:64], 'cones':cones[:64], 'planes':planes[:64],
                    'cylinderFaceCount':len(cylinders), 'coneFaceCount':len(cones),
                    'planeFaceCount':plane_face_count, 'otherFaceCount':other_face_count,
                    'coaxialSurfaceGroups':coaxial_face_groups(cylinders,cones),
                    'limitations':'Position-verified surface axes/radii describe finished geometry, not purchased stock or operations'}
        except Exception:
            pass  # Missing diagnostic evidence must never certify a stock or cost.
    if result.get('kind')!='unknown':
        candidates=match_hint(result)
        result={**result,'catalogCandidates':candidates,'catalogStatus':'unique-fit' if len(candidates)==1 else 'multiple-fits' if candidates else 'no-catalog-fit'}
        if len(candidates)==1:result['catalogDesignation']=candidates[0]['name']
    if result.get('rawStockCandidate'):
        raw=result['rawStockCandidate'];candidates=match_hint(raw);raw['catalogCandidates']=candidates
        if len(candidates)==1:raw['catalogDesignation']=candidates[0]['name']
    return result
