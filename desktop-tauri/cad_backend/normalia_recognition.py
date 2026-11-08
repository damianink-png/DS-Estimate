"""Conservative geometry-driven nominal normalia candidates from original STEP.

This is an independent, read-only analysis. It neither changes stockHint nor
cutting/welding/milling/assembly estimates. A normal-size dimension is NEVER
proof of an off-the-shelf purchased item or its manufacturing process.
"""
import math
try:
    from .normalia_catalog import lookup_dimensions
    from .rotational_features import coaxial_face_groups
except ImportError:
    from normalia_catalog import lookup_dimensions
    from rotational_features import coaxial_face_groups


def _cad_api():
    # Lazy import: unit tests and nominal catalogue work without OCCT.
    try:
        from . import cad_measure
    except ImportError:
        import cad_measure
    return cad_measure

def _dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def match_brep_signature(measurements):
    """Pure nominal matcher, input must already be measured on physical faces.

    The candidate family is selected ONLY after a strict topology test.
    No match against a name or against bbox dimensions alone is permitted.
    """
    family=measurements.get('family')
    if family=='ring':
        inner=measurements.get('innerDiameter')
        outer=measurements.get('outerDiameter')
        width=measurements.get('axialLength')
        if not all(type(x) in (int,float) and math.isfinite(x) and x>0
                   for x in (inner,outer,width)):
            return []
        if inner>=outer: return []
        matches=[]
        matches.extend(lookup_dimensions('washer',{'innerDiameter':inner,
                                                   'outerDiameter':outer,
                                                   'thickness':width}))
        matches.extend(lookup_dimensions('bearing',{'innerDiameter':inner,
                                                    'outerDiameter':outer,
                                                    'width':width}))
        return matches
    if family=='pin':
        d=measurements.get('diameter')
        length=measurements.get('axialLength')
        if not all(type(x) in (int,float) and math.isfinite(x) and x>0
                   for x in (d,length)):
            return []
        return lookup_dimensions('dowel-pin',{'diameter':d,'length':length})
    if family=='hex-nut':
        diameter=measurements.get('holeNominal')
        flats=measurements.get('acrossFlats')
        height=measurements.get('axialLength')
        if not all(type(x) in (int,float) and math.isfinite(x) and x>0
                   for x in (diameter,flats,height)):
            return []
        # Reference catalog values are nominal height maxima; do not turn
        # manufacturer dimensional variance into a global 3-D CAD tolerance.
        plausible=lookup_dimensions('hex-nut',{'holeNominal':diameter,
                                               'acrossFlats':flats})
        from_catalog=[]
        try:
            from .normalia_catalog import normalia_catalog
        except ImportError:
            from normalia_catalog import normalia_catalog
        for candidate in plausible:
            record=next((r for r in normalia_catalog() if r['id']==candidate['id']),None)
            if record is not None:
                maximum=record['dimensionsMm']['heightReferenceMax']
                if .85*maximum<=height<=maximum+.02:
                    from_catalog.append(candidate)
        return from_catalog
    return []


def _measured_surfaces(solid, face_budget=90):
    cad=_cad_api()
    cylinders=[];planes=[];count=0;other_types=0
    for raw in cad.shapes(solid,cad.TopAbs_FACE):
        count+=1
        if count>face_budget:
            return None
        face=cad.face_cast(raw)
        surface=cad.BRepAdaptor_Surface(face)
        typ=surface.GetType()
        if typ==cad.GeomAbs_Cylinder:
            c=surface.Cylinder()
            axis=c.Axis();loc=axis.Location();dr=axis.Direction()
            cylinders.append({'radiusMm':float(c.Radius()),
                              'axis':tuple(float(v) for v in dr.Coord()),
                              'axisPointMm':tuple(float(v) for v in loc.Coord()),
                              'axialSurfaceSpanMm':abs(float(surface.LastVParameter()-surface.FirstVParameter()))})
        elif typ==cad.GeomAbs_Plane:
            p=surface.Plane();loc=p.Location();direction=p.Axis().Direction()
            normal=tuple(float(v) for v in direction.Coord())
            area=float(cad.area(face))
            planes.append({'normal':normal,
                           'point':tuple(float(v) for v in loc.Coord()),
                           'area':area})
        else:
            other_types+=1
    return cylinders,planes,count,other_types


def _hex_flats(planes,axis,axis_point):
    """Measure six coplanar-in-length hex flats in original 3-D directions."""
    sides=[]
    for plane in planes:
        normal=plane['normal']
        if abs(_dot(normal,axis))>.001:
            continue
        delta=tuple(plane['point'][i]-axis_point[i] for i in range(3))
        distance=abs(_dot(normal,delta))
        if distance<=.1:
            continue
        if all(_dot(normal,existing['normal'])<.99999
               or abs(distance-existing['distance'])>.02
               for existing in sides):
            sides.append({'normal':normal,'distance':distance,'area':plane['area']})
    if len(sides)!=6:
        return None
    distances=[s['distance'] for s in sides]
    if max(distances)-min(distances)>.02:
        return None
    return 2*sum(distances)/len(distances)


def recognize_normalia(solid,volume_mm3=None):
    """Identify *only* geometry candidates, never declare parts purchased.

    Unresolved or multi-body input -> None. No name lookup, no prices,
    inferred machining operations or global tolerance changes.
    """
    if solid is None:
        return None
    try:
        measured=_measured_surfaces(solid)
        if not measured:
            return None
        cylinders,planes,face_count,other_types=measured
        if not cylinders or len(cylinders)>30:
            return None
        group_rows=coaxial_face_groups(cylinders,[])
        # An off-axis bore/hole, even with the same volume, is not the
        # centrally bored ring, hex nut or turned pin in this subset.
        if len(group_rows)!=1:
            return None
        group=group_rows[0]
        direction=group['axis']
        point=group['axisPointMm']
        radii=group['cylinderRadiiMm']
        if len(radii)>2:
            return None
        axial_positions=[
            _dot(p['point'],direction) for p in planes
            if abs(_dot(p['normal'],direction))>.99999
        ]
        if len(axial_positions)<2:
            return None
        length=max(axial_positions)-min(axial_positions)
        if not math.isfinite(length) or length<=0:
            return None
        if volume_mm3 is None:
            volume_mm3=float(_cad_api().volume(solid))
        if not math.isfinite(volume_mm3) or volume_mm3<=0:
            return None
        candidates=[];evidence=None
        if len(radii)==2 and len(cylinders)==2 and other_types==0:
            outer,inner=max(radii),min(radii)
            predicted=math.pi*(outer*outer-inner*inner)*length
            if abs(predicted-volume_mm3)<=max(0.2,predicted*.025):
                evidence={'family':'ring','innerDiameter':2*inner,
                          'outerDiameter':2*outer,'axialLength':length}
                candidates=match_brep_signature(evidence)
        elif len(radii)==1 and len(cylinders)==1 and other_types==0:
            radius=radii[0]
            flats=_hex_flats(planes,direction,point)
            if flats is not None:
                # A regular hexagonal nut is NOT a solid circular pin:
                # compare with the HEXAGON minus its cylindrical through bore.
                hex_area=math.sqrt(3)*flats*flats/2
                predicted=(hex_area-math.pi*radius*radius)*length
                if predicted>0 and abs(predicted-volume_mm3)<=max(.2,predicted*.025):
                    evidence={'family':'hex-nut','holeNominal':2*radius,
                              'acrossFlats':flats,'axialLength':length}
                    candidates=match_brep_signature(evidence)
            elif len(planes)==2:
                predicted=math.pi*radius*radius*length
                if abs(predicted-volume_mm3)<=max(.2,predicted*.025):
                    evidence={'family':'pin','diameter':2*radius,'axialLength':length}
                    candidates=match_brep_signature(evidence)
        if not candidates:
            return None
        return {'status':'geometry-candidate',
                'families':sorted({c['family'] for c in candidates}),
                'catalogCandidates':candidates[:12],
                'candidateCount':len(candidates),
                'measuredBrep':{k:round(v,6) if type(v) is float else v
                                for k,v in evidence.items()},
                'source':'original STEP analytical cylindrical/planar faces, coaxial positions and independent volume',
                'limitations':'Dimensional resemblance only. Stock/purchase, thread, process, strength and price remain undetermined.'}
    except Exception:
        # A malformed analytic face must not change the STEP mass/grouping
        # or turn an unresolved manufacturing cost into a fictitious zero.
        return None
