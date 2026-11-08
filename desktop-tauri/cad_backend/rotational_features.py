"""Position-aware features from ORIGINAL B-Rep surface axes.

Geometric diagnostics only. Neither concentric cylinders nor cone faces prove
a bought fastener, finished blank, process, saw cut, or machining time.
"""
import math


def coaxial_face_groups(cylinders, cones, position_tol_mm=0.02, axis_cosine_min=0.99999999):
    """Cluster analytical surfaces by the SAME infinite 3-D axis.

    The direction of a geometric axis is unsigned. Equal directions alone
    are insufficient: parallel OFFSET holes must not become one turned part.
    Only original B-Rep axis points are accepted; bounding boxes are not.
    """
    observations = []
    for kind, faces, radius_field in (
            ('cylinder', cylinders, 'radiusMm'),
            ('cone', cones, 'referenceRadiusMm')):
        for face in faces:
            direction = face.get('axis')
            point = face.get('axisPointMm')
            if (not isinstance(direction, (list, tuple))
                    or not isinstance(point, (list, tuple))
                    or len(direction) != 3 or len(point) != 3
                    or not all(type(v) in (int, float) and math.isfinite(v)
                               for v in (*direction, *point))):
                continue
            norm = math.sqrt(sum(v*v for v in direction))
            if norm <= 0:
                continue
            unit = tuple(v/norm for v in direction)
            radius = face.get(radius_field)
            if type(radius) not in (int, float) or not math.isfinite(radius) or radius <= 0:
                continue
            observations.append((kind, unit, tuple(point), float(radius)))
    groups = []
    for kind, direction, point, radius in observations:
        for group in groups:
            reference = group['direction']
            dot = sum(a*b for a,b in zip(reference,direction))
            if abs(dot) < axis_cosine_min:
                continue
            delta = tuple(a-b for a,b in zip(point,group['point']))
            # Norm of cross product with unit vector = shortest distance
            # from candidate axis point to the existing axis line.
            cross = (delta[1]*reference[2]-delta[2]*reference[1],
                     delta[2]*reference[0]-delta[0]*reference[2],
                     delta[0]*reference[1]-delta[1]*reference[0])
            if math.sqrt(sum(v*v for v in cross)) > position_tol_mm:
                continue
            break
        else:
            group = {'direction': direction, 'point': point,
                     'cylinderRadii': [], 'coneRadii': [],
                     'cylinderFaceCount': 0, 'coneFaceCount': 0}
            groups.append(group)
        group[kind+'FaceCount'] += 1
        group['cylinderRadii' if kind=='cylinder' else 'coneRadii'].append(radius)
    result = []
    for group in groups:
        result.append({
            'axis': [round(v,8) for v in group['direction']],
            'axisPointMm': [round(v,6) for v in group['point']],
            'cylinderFaceCount': group['cylinderFaceCount'],
            'coneFaceCount': group['coneFaceCount'],
            'cylinderRadiiMm': sorted({round(v,6) for v in group['cylinderRadii']}),
            'coneReferenceRadiiMm': sorted({round(v,6) for v in group['coneRadii']}),
            'evidence': 'position-and-direction verified original B-Rep surface axes',
        })
    return sorted(result, key=lambda g: (-(g['cylinderFaceCount']+g['coneFaceCount']),
                                         -g['cylinderFaceCount']))
