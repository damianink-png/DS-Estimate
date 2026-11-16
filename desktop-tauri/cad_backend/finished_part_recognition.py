"""Conservative family recognition of FINISHED STEP geometry.

Reuse only existing physical B-Rep surface measurements and verified section
proposals. Nothing here establishes purchased blank, stock procurement,
machining route, welding, cutting length, operation time or a quote.

A body may have a recognizable finished shape yet remain UNKNOWN as stock.
"""
import math


def _dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def _candidate(family,measurements,source,confidence='geometry-candidate'):
    return {'status':'finished-geometry-candidate',
            'family':family,'confidence':confidence,
            'measurements':measurements,'source':source,
            'blankCertified':False,'processCertified':False,
            'cutTimeCertified':False,
            'limitations':'Finished geometry only; no purchased stock, technology or cost certification'}


def _measured_plate(surfaces,volume):
    """Find a constant-thickness prism with optional axial THROUGH bores.

    Require TWO entire broad faces, matching area, independent whole-solid
    volume and side walls perpendicular to the skin normal. A bbox's smallest
    dimension is never used. In particular, a stepped welded body is NOT a
    plate even if it has several parallel face pairs.
    """
    planes=surfaces.get('planes') or []
    cylinders=surfaces.get('cylinders') or []
    if not 2<=len(planes)<=96 or surfaces.get('coneFaceCount',0)>0:
        return None
    if surfaces.get('cylinderFaceCount',0)>32 or surfaces.get('planeFaceCount',len(planes))!=len(planes):
        return None
    if surfaces.get('otherFaceCount',0):
        return None
    candidates=[]
    for i,a in enumerate(planes):
        na=a.get('normal');aa=a.get('areaMm2');da=a.get('signedOffsetMm')
        if not na or not isinstance(aa,(int,float)) or aa<=0:continue
        for j in range(i+1,len(planes)):
            b=planes[j];nb=b.get('normal')
            if not nb:continue
            parallel=_dot(na,nb)
            if abs(parallel)<.99999:continue
            ab=b.get('areaMm2',0)
            if ab<=0 or min(aa,ab)/max(aa,ab)<.98:continue
            t=abs(da-b['signedOffsetMm']*(1 if parallel>0 else -1))
            if t<.2:continue
            skin_area=(aa+ab)*.5
            if skin_area/(t*t)<5:continue
            predicted=skin_area*t
            error=abs(predicted-volume)/volume
            if error>.01:continue
            # There must be no additional canted or parallel material faces.
            # A true prismatic body's outer side walls are perpendicular to
            # the skin normal; bore cylinders run along the skin normal.
            if any(abs(_dot(p['normal'],na))>.002 for k,p in enumerate(planes)
                   if k!=i and k!=j):
                continue
            if any(abs(_dot(c['axis'],na))<.99999 for c in cylinders):continue
            candidates.append((error,t,skin_area,len(cylinders)))
    if not candidates:return None
    error,t,area,holes=sorted(candidates)[0]
    return _candidate('constant-thickness-plate-body',
                      {'thicknessMm':round(t,5),
                       'profileAreaMm2':round(area,4),
                       'measuredVolumeMm3':round(volume,4),
                       'volumeRelativeDeviation':round(error,7),
                       'axialCylindricalFaceCount':holes},
                      'paired whole planar B-Rep faces, normal-aligned sides and independent volume check',
                      confidence='measured-constant-thickness-body')


def _measured_round_body(surfaces,volume):
    """A near-full solid circular core with small nonanalytic end details.

    A hollow tube, bore, offset cylinder, cone, or large sculpted feature
    intentionally does NOT qualify. End details remain unpriced.
    """
    cylinders=surfaces.get('cylinders') or []
    planes=surfaces.get('planes') or []
    if (len(cylinders)!=1 or len(planes)!=2 or
        surfaces.get('coneFaceCount',0) or
        surfaces.get('cylinderFaceCount',0)!=1 or
        surfaces.get('planeFaceCount',0)!=2):
        return None
    c=cylinders[0];axis=c.get('axis');radius=c.get('radiusMm')
    if not axis or not isinstance(radius,(int,float)) or radius<=0:return None
    length_coords=[]
    for plane in planes:
        normal=plane.get('normal')
        if not normal:return None
        dot=_dot(axis,normal)
        if abs(dot)<.99999:return None
        length_coords.append(plane['signedOffsetMm']/dot)
        nominal_face=math.pi*radius*radius
        if not .5<=plane['areaMm2']/nominal_face<=1.05:return None
    length=abs(length_coords[0]-length_coords[1])
    if length<=radius*2:return None
    expected=math.pi*radius*radius*length
    error=abs(expected-volume)/volume
    if error>.01:return None
    return _candidate('near-round-cylindrical-body',
                      {'cylindricalDiameterMm':round(radius*2,5),
                       'axialLengthMm':round(length,5),
                       'measuredVolumeMm3':round(volume,4),
                       'idealCylinderVolumeMm3':round(expected,4),
                       'volumeRelativeDeviation':round(error,7),
                       'additionalNonAnalyticFaceCount':surfaces.get('otherFaceCount',0)},
                      'single original cylindrical wall, two perpendicular end planes and independent solid volume',
                      confidence='measured-round-core-only')


def recognize_finished_geometry(stock_hint,volume_mm3,graph=None):
    """Return a single supported geometry family, else explicit unknown.

    The result is a separate inventory field, never a replacement for
    stockHint or any quote route. Uses B-Rep evidence already computed on
    the verified unique shape; expensive CAD passes are not repeated.
    """
    if not isinstance(stock_hint,dict) or not isinstance(volume_mm3,(float,int)) or not math.isfinite(volume_mm3) or volume_mm3<=0:
        return {'status':'unknown','reason':'missing physical B-Rep volume'}
    surfaces=stock_hint.get('finishedBrepSurfaceEvidence') or {}
    if not surfaces or surfaces.get('source')!='original STEP B-Rep face adaptors':
        return {'status':'unknown','reason':'original-face evidence unavailable'}
    family=_measured_plate(surfaces,volume_mm3)
    if family:return family
    family=_measured_round_body(surfaces,volume_mm3)
    if family:return family
    # Stock-recognition core proposals were independently checked against
    # measured B-Rep sections. Preserve their exact confidence, never upgrade
    # them to accepted *raw stock* merely because the family is recognizable.
    candidate=stock_hint.get('rawStockCandidate')
    if (isinstance(candidate,dict) and candidate.get('confidence') in
            ('raw-stock-candidate','geometric-blank-candidate')
            and candidate.get('kind') not in (None,'unknown')):
        return _candidate('extrusion-body-with-secondary-features',
                          {'verifiedCoreKind':candidate['kind'],
                           'crossSection':{k:candidate[k] for k in
                               ('widthMm','heightMm','diameterMm','wallMm','lengthMm')
                               if k in candidate},
                           'originalCoreEvidence':candidate.get('source','')},
                          'independently measured repeated B-Rep section and remaining finished-shape variation',
                          confidence='measured-core-not-verified-blank')
    core=stock_hint.get('coreSectionCandidate')
    if (isinstance(core,dict) and
        core.get('confidence')=='geometric-core-only' and
        core.get('axisEvidence')=='B-Rep cylinder/edge axis' and
        core.get('kind') not in (None,'unknown')):
        return _candidate('core-section-body-with-secondary-features',
                          {'verifiedCoreKind':core['kind'],
                           'crossSection':{k:core[k] for k in
                               ('widthMm','heightMm','diameterMm','wallMm','lengthMm')
                               if k in core},
                           'finishedVolumeMm3':round(volume_mm3,4)},
                          'five B-Rep slices and locally verified face/edge axis; whole finished solid differs from ideal core',
                          confidence='measured-core-not-verified-blank')
    # Avoid inventing a family for fully planar polyhedra or mixed spline
    # shapes with no measured manufacturing evidence.
    # Preserve bounded AAG observations for diagnostics even when no stock
    # family is proven. This does not promote a feature to a raw blank, change
    # the quote, or trigger another expensive OCCT geometry pass.
    observations = []
    if isinstance(graph, dict) and graph.get('status') == 'measured' and graph.get('nonManifoldEdges', 0) == 0:
        patterns = graph.get('featurePatterns')
        if isinstance(patterns, dict) and patterns.get('status') == 'measured' and not patterns.get('truncated'):
            allowed = {'through-cylindrical-opening', 'coaxial-conical-transition',
                       'coaxial-diameter-shoulder', 'reduced-diameter-axial-section',
                       'intersecting-cylinder-axes'}
            counts = patterns.get('counts')
            if isinstance(counts, dict):
                observations = [{'kind': key, 'count': count}
                                for key, count in sorted(counts.items())
                                if key in allowed and type(count) is int and 0 < count <= 96]
    result = {'status':'unknown','reason':'insufficient original B-Rep family evidence',
              'limitations':'Do not infer stock or manufacture from surface counts alone'}
    if observations:
        result['verifiedSecondaryFeatures'] = observations
        result['featureEvidenceSource'] = 'original B-Rep shared-edge adjacency graph'
    return result
