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
            # A representative-only comparison permits transitive chaining:
            # three distinct parallel holes at 0, 0.015 and 0.030 mm can
            # incorrectly become one axis at a 0.02 mm threshold.
            # Require agreement with EVERY original B-Rep surface axis.
            compatible = True
            for reference, reference_point in group['_members']:
                dot = sum(a*b for a,b in zip(reference,direction))
                if abs(dot) < axis_cosine_min:
                    compatible = False
                    break
                delta = tuple(a-b for a,b in zip(point,reference_point))
                cross = (delta[1]*reference[2]-delta[2]*reference[1],
                         delta[2]*reference[0]-delta[0]*reference[2],
                         delta[0]*reference[1]-delta[1]*reference[0])
                if math.sqrt(sum(v*v for v in cross)) > position_tol_mm:
                    compatible = False
                    break
            if compatible:
                break
        else:
            group = {'direction': direction, 'point': point,
                     'cylinderRadii': [], 'coneRadii': [],
                     'cylinderFaceCount': 0, 'coneFaceCount': 0,
                     '_members': []}
            groups.append(group)
        group['_members'].append((direction, point))
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
