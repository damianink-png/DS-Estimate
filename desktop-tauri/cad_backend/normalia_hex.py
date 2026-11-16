"""Conservative catalogue matches for chamfered *real* hex hardware.

Run on analytically measured ORIGINAL STEP B-Rep faces. The six hex flats,
coaxial cylindrical/conical skins, distinct axial planes, measured length and
independently calculated finished volume must all agree. Smooth thread
cylinders are nominal geometry only and DO NOT verify thread, product grade,
supplier, or purchase price. No machining route is inferred.
"""
import math
try:
    from .rotational_features import coaxial_face_groups
    from .normalia_catalog import lookup_dimensions, normalia_catalog
except ImportError:
    from rotational_features import coaxial_face_groups
    from normalia_catalog import lookup_dimensions, normalia_catalog


def dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def _hex_flats(planes,axis,axis_point):
    """Return measured across-flats for exactly six equidistant hex side planes."""
    sides=[]
    for p in planes:
        n=p['normal']
        if abs(dot(n,axis))>0.001 or p.get('area',0)<=0:
            continue
        distance=abs(dot(n,tuple(a-b for a,b in zip(p['point'],axis_point))))
        if distance<=.1 or not math.isfinite(distance):
            continue
        if not any(dot(n,q['normal'])>0.99999 for q in sides):
            sides.append({'normal':n,'distance':distance,'area':p['area']})
    if len(sides)!=6:
        return None
    distances=[s['distance'] for s in sides]
    if max(distances)-min(distances)>.02:
        return None
    areas=[s['area'] for s in sides]
    if min(areas)<=0 or max(areas)/min(areas)>1.03:
        return None
    # Six normals at the 60-degree increments of a genuine regular hexagon.
    for a in sides:
        cosines=sorted(dot(a['normal'],b['normal']) for b in sides if b is not a)
        expected=(-1.,-.5,-.5,.5,.5)
        if any(abs(x-y)>.001 for x,y in zip(cosines,expected)):
            return None
    return 2*sum(distances)/6


def _axial_planes(planes,axis):
    xs=sorted(dot(p['point'],axis) for p in planes
              if abs(dot(p['normal'],axis))>.99999)
    unique=[]
    for x in xs:
        if not unique or abs(x-unique[-1])>.02:
            unique.append(x)
    return unique


def _cone_evidence(cones,axis,axis_point):
    for cone in cones:
        direction=cone.get('axis')
        location=cone.get('axisPointMm')
        angle=cone.get('semiAngleRad')
        if not isinstance(direction,(tuple,list)) or not isinstance(location,(tuple,list)):
            return False
        if abs(dot(direction,axis))<.99999999 or abs(float(angle)-math.pi/4)>.002:
            return False
        delta=tuple(a-b for a,b in zip(location,axis_point))
        # Do not merge two merely PARALLEL, physically displaced features.
        squared=sum(v*v for v in delta)-dot(delta,axis)**2
        if squared>0.02**2+1e-8:
            return False
    return True


def _envelope_volume_ok(finished,envelope,max_chamfer_loss=.06):
    # A chamfer REMOVES material; this is a product-specific bound on
    # chamfer volume, not a relaxation of unrelated B-Rep tolerances.
    return (math.isfinite(finished) and math.isfinite(envelope)
            and envelope>0 and envelope*(1-max_chamfer_loss)<=finished
            and finished<=envelope+max(.2,envelope*.0005))


def match_chamfered_hex(cylinders,planes,cones,volume_mm3):
    """Return a candidate only when a hex-head bolt/nut is physically evidenced."""
    if len(cylinders)!=1 or len(cones) not in (2,3):
        return None
    groups=coaxial_face_groups(cylinders,cones)
    if len(groups)!=1 or groups[0]['cylinderFaceCount']!=1 or groups[0]['coneFaceCount']!=len(cones):
        return None
    main=cylinders[0]
    axis=main['axis']
    loc=main['axisPointMm']
    radius=main['radiusMm']
    if radius<=0 or not math.isfinite(radius):
        return None
    flats=_hex_flats(planes,axis,loc)
    if flats is None or not _cone_evidence(cones,axis,loc):
        return None
    axial=_axial_planes(planes,axis)
    circ=flats/math.sqrt(3)
    if any(abs(c['referenceRadiusMm']-circ)>.03 for c in cones[:2]):
        # Cone ordering is not guaranteed; check any pair below.
        head_cones=[c for c in cones if abs(c['referenceRadiusMm']-circ)<=.03]
    else:
        head_cones=cones[:2]
    if len(head_cones)!=2:
        return None
    if len(cones)==2:
        # A nut has two end faces. Its one full cylindrical wall is the
        # smooth surrogate for a tapped hole in this STEP.
        if len(axial)!=2 or len(planes)!=8:
            return None
        height=axial[1]-axial[0]
        if abs(main['axialSurfaceSpanMm']-height)>.03:
            return None
        area=math.sqrt(3)/2*flats**2-math.pi*radius**2
        if not _envelope_volume_ok(volume_mm3,area*height):
            return None
        plausible=lookup_dimensions('hex-nut',{'holeNominal':radius*2,'acrossFlats':flats})
        rows={r['id']:r for r in normalia_catalog()}
        hits=[c for c in plausible if .85*rows[c['id']]['dimensionsMm']['heightReferenceMax']
              <=height<=rows[c['id']]['dimensionsMm']['heightReferenceMax']+.02]
        if not hits:
            return None
        return {'family':'hex-nut','candidates':hits,
                'measurements':{'holeDiameterMm':radius*2,'acrossFlatsMm':flats,
                                'heightMm':height,'coneFaceCount':2},
                'threadEvidence':'not modelled (smooth bore)'}
    # Hex head: two chamfer cones around the hex and one conical rod end.
    if len(axial)!=3 or len(planes)!=9:
        return None
    tail=[c for c in cones if c not in head_cones]
    if len(tail)!=1 or abs(tail[0]['referenceRadiusMm']-radius)>.03:
        return None
    a=axial[1]-axial[0]
    b=axial[2]-axial[1]
    if a<=0 or b<=0:
        return None
    for head_height,length in ((a,b),(b,a)):
        matches=lookup_dimensions('hex-head',{'threadDiameter':radius*2,
                                             'acrossFlats':flats,
                                             'headHeight':head_height,
                                             'underheadLength':length})
        envelope=(math.sqrt(3)/2*flats**2*head_height
                  +math.pi*radius**2*length)
        if not matches or not _envelope_volume_ok(volume_mm3,envelope):
            continue
        if not (length*.75<=main['axialSurfaceSpanMm']<=length+.03):
            continue
        return {'family':'hex-head','candidates':matches,
                'measurements':{'shaftDiameterMm':radius*2,
                                'acrossFlatsMm':flats,
                                'headHeightMm':head_height,
                                'underheadLengthMm':length,
                                'coneFaceCount':3},
                'threadEvidence':'not modelled (smooth cylinder); ISO 4014 vs 4017 unverified'}
    return None


def match_simplified_grease_nipple(cylinders,planes,cones,volume_mm3):
    """Identify the distinctive nipple family, *not* exact DIN product.

    The original Earthpress grease-fitting shape has three coaxial full
    cylindrical portions (Ø6, Ø4.4, Ø6), two 45 degree cone skins, a
    7 mm regular hex, five axial level planes and independently measured
    3-D volume. It has a 17 mm modelled length while published DIN 71412 A
    M6 reference rows commonly specify 15-16 mm: flag the mismatch.
    """
    if len(cylinders)!=3 or len(cones)!=2 or len(planes)!=11:
        return None
    groups=coaxial_face_groups(cylinders,cones)
    if len(groups)!=1 or groups[0]['cylinderFaceCount']!=3 or groups[0]['coneFaceCount']!=2:
        return None
    axis=groups[0]['axis']
    point=groups[0]['axisPointMm']
    flats=_hex_flats(planes,axis,point)
    if flats is None or abs(flats-7)>.02 or not _cone_evidence(cones,axis,point):
        return None
    if any(abs(c['referenceRadiusMm']-flats/math.sqrt(3))>.03 for c in cones):
        return None
    radius=sorted(round(c['radiusMm'],6) for c in cylinders)
    if radius!=[2.2,3.,3.]:
        return None
    axial=_axial_planes(planes,axis)
    if len(axial)!=5:
        return None
    length=axial[-1]-axial[0]
    if abs(length-17)>.02:
        return None
    cylindrical_length=sum(c['axialSurfaceSpanMm'] for c in cylinders)
    if cylindrical_length<=0 or cylindrical_length>=length:
        return None
    envelope=sum(math.pi*c['radiusMm']**2*c['axialSurfaceSpanMm']
                 for c in cylinders)
    envelope+=(math.sqrt(3)/2*flats**2)*(length-cylindrical_length)
    if not _envelope_volume_ok(volume_mm3,envelope,max_chamfer_loss=.04):
        return None
    # The published nominal 16 mm DIN/KIPP value differs from this STEP by
    # 1 mm; no DIN compliance or exact purchased variant is asserted.
    return {'family':'grease-nipple',
            'candidates':[{'family':'grease-nipple',
                           'designation':'M6x1, SW7 (only geometry-family match)',
                           'id':'grease-nipple:M6x1',
                           'standard':'DIN 71412 A (reference only; length mismatch)',
                           'matchLevel':'family-only'}],
            'measurements':{'shaftDiameterMm':6,'neckDiameterMm':4.4,
                            'acrossFlatsMm':flats,'overallLengthMm':length,
                            'publishedReferenceLengthMm':16,
                            'coneFaceCount':2},
            'threadEvidence':'not modelled; pitch/type unverified',
            'standardMatch':'not certified (STEP 17 mm; published DIN 71412 A 16 mm)'}
