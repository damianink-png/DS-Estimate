"""Pure section-shape recognition; no inference of catalogue or material grade."""
import math


def _unique_coordinates(vals, tol):
    out = []
    for value in sorted(vals):
        if not out or value - out[-1] > tol:
            out.append(value)
    return out


def _inside_polygon(point, polygon):
    x, y = point
    inside = False
    for a, b in zip(polygon, polygon[1:]):
        x1, y1 = a
        x2, y2 = b
        if (y1 > y) != (y2 > y):
            crossed = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < crossed:
                inside = not inside
    return inside


def orthogonal_section_kind(pts, tol):
    """Recognise L, channel, T and I from a closed straight-edge polygon.

    Strict grid occupancy prevents classifying a similar-looking arbitrary
    profile as a certified hot-rolled / standard structural section.
    """
    if (not math.isfinite(tol) or tol <= 0 or len(pts) < 7
            or any(not math.isfinite(v) for p in pts for v in p)
            or math.dist(pts[0], pts[-1]) > tol):
        return None
    segments = [(math.dist(a, b), a, b) for a, b in zip(pts, pts[1:])
                if math.dist(a, b) > tol]
    if len(segments) < 6:
        return None
    _, a, b = max(segments)
    theta = math.atan2(b[1] - a[1], b[0] - a[0])
    co, si = math.cos(theta), math.sin(theta)
    rotated = [(x*co+y*si, -x*si+y*co) for x, y in pts]
    length = max(math.dist(a, b) for a, b in zip(rotated, rotated[1:]))
    epsilon = max(tol * 5, length * 1e-5)
    for a, b in zip(rotated, rotated[1:]):
        if math.dist(a, b) <= tol:
            continue
        if min(abs(b[0]-a[0]), abs(b[1]-a[1])) > epsilon:
            return None
    xx = _unique_coordinates([x for x, _ in rotated], epsilon)
    yy = _unique_coordinates([y for _, y in rotated], epsilon)
    if len(xx) not in (3, 4) or len(yy) not in (3, 4):
        return None
    widths = [b - a for a, b in zip(xx, xx[1:])]
    heights = [b - a for a, b in zip(yy, yy[1:])]
    if min(widths + heights) < tol * 5:
        return None
    occupied = [[_inside_polygon(((xx[i]+xx[i+1])/2, (yy[j]+yy[j+1])/2), rotated)
                 for i in range(len(xx)-1)] for j in range(len(yy)-1)]
    w, h = len(xx)-1, len(yy)-1
    expected_area = sum(widths[i]*heights[j] for j in range(h) for i in range(w) if occupied[j][i])
    polygon_area = abs(sum(a[0]*b[1] - b[0]*a[1] for a, b in zip(rotated, rotated[1:]))) / 2
    if abs(expected_area-polygon_area) > max(1.0, polygon_area*.002):
        return None
    kind = None
    if w == 2 and h == 2 and sum(sum(row) for row in occupied) == 3:
        kind = 'angle'
    elif (w, h) in ((2, 3), (3, 2)):
        grid = occupied if w == 2 else [list(col) for col in zip(*occupied)]
        # A genuine U/C shape has two full flanges and a web on
        # the SAME side. A central web is an I/H-like section.
        if (all(grid[row][0] and grid[row][1] for row in (0, 2))
                and grid[1] in ([True, False], [False, True])):
            kind = 'channel'
    elif w == 3 and h == 3:
        if all(occupied[row] == [True, True, True] for row in (0, 2)) and occupied[1] == [False, True, False]:
            kind = 'i-section'
        elif all(occupied[j][i] for j in range(3) for i in (0, 2)) and [occupied[j][1] for j in range(3)] == [False, True, False]:
            kind = 'i-section'
    if (w, h) in ((3, 2), (2, 3)) and kind is None:
        grid = occupied if w == 3 else [list(col) for col in zip(*occupied)]
        if [sum(row) for row in grid] in ([3, 1], [1, 3]):
            narrow = grid[0] if sum(grid[0]) == 1 else grid[1]
            if narrow == [False, True, False]:
                kind = 'tee'
    if kind is None:
        return None
    return {'kind':kind,
            'widthMm':max(xx[-1]-xx[0], yy[-1]-yy[0]),
            'heightMm':min(xx[-1]-xx[0], yy[-1]-yy[0]),
            'sectionAreaMm2':polygon_area}


def convex_polygon_section_kind(points, tol):
    """A measured, NON-standard polygonal bar profile — never a catalogue size.

    Use only as a fallback after exact round/rectangular and certified rolled
    section checks. Axial persistence and the independent 3-D volume test
    in stock_recognition are mandatory before this becomes stock evidence.
    Slightly skewed almost-rectangles are left unknown rather than relabelled
    as intentional special sections.
    """
    if (not math.isfinite(tol) or tol <= 0 or
            not 4 <= len(points) <= 13 or
            any(not all(math.isfinite(z) for z in p) for p in points) or
            math.dist(points[0], points[-1]) > tol):
        return None
    vertices = points[:-1]
    edges = [(b[0]-a[0], b[1]-a[1]) for a,b in zip(points, points[1:])]
    lengths = [math.hypot(*e) for e in edges]
    if min(lengths) < tol*5:
        return None
    orientation = 0
    for e, f in zip(edges, edges[1:] + edges[:1]):
        cross = e[0]*f[1]-e[1]*f[0]
        if abs(cross) <= tol*max(math.hypot(*e),math.hypot(*f))*3:
            continue
        sign = 1 if cross > 0 else -1
        if orientation and orientation != sign:
            return None # concave or self-intersecting, not a simple raw bar
        orientation = sign
    if not orientation:
        return None
    area = abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(points,points[1:]))) / 2
    if area <= tol*tol*25:
        return None
    _, axis = max(zip(lengths, edges),key=lambda x:x[0])
    co, si = axis[0]/math.hypot(*axis), axis[1]/math.hypot(*axis)
    uv = [(x*co+y*si,-x*si+y*co) for x,y in vertices]
    w = max(x for x,y in uv)-min(x for x,y in uv)
    h = max(y for x,y in uv)-min(y for x,y in uv)
    if min(w,h) <= tol or area > w*h*1.001:
        return None
    # Do not misclassify a dimensionally noisy rectangle/parallelogram.
    if area >= w*h*.985:
        return None
    return {'kind':'polygon-bar','widthMm':max(w,h),'heightMm':min(w,h),
            'sectionAreaMm2':area,'sideCount':len(vertices)}
