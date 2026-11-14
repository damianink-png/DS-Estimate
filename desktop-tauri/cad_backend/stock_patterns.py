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
    # An orthogonal section must be a simple perimeter. Revisited
    # non-adjacent vertices can otherwise produce a plausible L/U/I grid
    # even though the contour self-touches. Adjacent duplicate points
    # from split STEP edges are harmless and remain permitted.
    vertices = pts[:-1]
    for i, a in enumerate(vertices):
        for j in range(i + 2, len(vertices)):
            if i == 0 and j == len(vertices) - 1:
                continue
            b = vertices[j]
            if (a[0] - b[0])**2 + (a[1] - b[1])**2 <= tol*tol:
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
    if len(xx) not in (3, 4, 6) or len(yy) not in (3, 4, 6):
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
    # Additional *geometric* section library: Z/zee and top-hat/omega.
    # Exact cell occupancy is required: no size/area-only standard inference.
    if kind is None and (w, h) in ((3, 3), (5, 3), (3, 5)):
        rotated_grid=occupied
        for _ in range(4):
            variants=(rotated_grid, [row[::-1] for row in rotated_grid])
            for grid in variants:
                gh=len(grid);gw=len(grid[0])
                if gh==3 and gw==3:
                    left=[[True,True,False],[False,True,False],[False,True,True]]
                    if grid==left:
                        kind='zee'
                        break
                if gh==3 and gw==5:
                    hat=[[True,True,False,True,True],
                         [False,True,False,True,False],
                         [False,True,True,True,False]]
                    if grid==hat:
                        kind='hat'
                        break
            if kind is not None:
                break
            rotated_grid=[list(row) for row in zip(*rotated_grid[::-1])]
    if kind is None:
        return None
    return {'kind':kind,
            'widthMm':max(xx[-1]-xx[0], yy[-1]-yy[0]),
            'heightMm':min(xx[-1]-xx[0], yy[-1]-yy[0]),
            'sectionAreaMm2':polygon_area}


def beveled_rectangle_section_kind(points, tol):
    """Measure a rectangular core with SMALL straight corner chamfers.

    This intentionally does not classify an arbitrary polygon as a bought
    rectangular bar. A verified core is evidence only; operations and stock
    remain unestablished until the whole original B-Rep is checked.
    """
    if (not math.isfinite(tol) or tol<=0 or not 6<=len(points)<=12
            or math.dist(points[0],points[-1])>tol
            or any(not all(math.isfinite(v) for v in p) for p in points)):
        return None
    vertices=points[:-1]
    # A chamfered rectangle must have a simple perimeter. A non-adjacent
    # repeated/tolerance-close vertex creates a self-touching contour, not
    # an unambiguous rectangular blank candidate. The maximum is 11 vertices.
    for i, a in enumerate(vertices):
        for b in vertices[i+1:]:
            if (a[0]-b[0])**2 + (a[1]-b[1])**2 <= tol*tol:
                return None
    segments=[(a,b) for a,b in zip(points,points[1:])]
    lengths=[math.dist(a,b) for a,b in segments]
    if min(lengths)<tol*5:
        return None
    index=max(range(len(lengths)), key=lambda i:lengths[i])
    a,b=segments[index]
    theta=math.atan2(b[1]-a[1],b[0]-a[0])
    co,si=math.cos(theta),math.sin(theta)
    xy=[(x*co+y*si,-x*si+y*co) for x,y in points]
    umin,umax=min(p[0] for p in xy),max(p[0] for p in xy)
    vmin,vmax=min(p[1] for p in xy),max(p[1] for p in xy)
    w,h=umax-umin,vmax-vmin
    if min(w,h)<=tol*10:
        return None
    epsilon=max(tol*2,max(w,h)*1e-5)
    bevels=0;straight=0
    for p,q in zip(xy,xy[1:]):
        du,dv=q[0]-p[0],q[1]-p[1]
        if abs(du)<=epsilon or abs(dv)<=epsilon:
            straight+=1
            continue
        # A true corner bevel joins adjacent bounding edges, both near the
        # SAME corner. Interior diagonals/notches are never ignored.
        is_corner=False
        for ux in (umin,umax):
            for vy in (vmin,vmax):
                near_p_vertical=abs(p[0]-ux)<=epsilon
                near_q_vertical=abs(q[0]-ux)<=epsilon
                near_p_horizontal=abs(p[1]-vy)<=epsilon
                near_q_horizontal=abs(q[1]-vy)<=epsilon
                max_bevel=.25*min(w,h)
                if ((near_p_vertical and near_q_horizontal
                     and abs(p[1]-vy)<=max_bevel and abs(q[0]-ux)<=max_bevel)
                    or (near_q_vertical and near_p_horizontal
                        and abs(q[1]-vy)<=max_bevel and abs(p[0]-ux)<=max_bevel)):
                    is_corner=True
                    break
            if is_corner:
                break
        if not is_corner:
            return None
        bevels+=1
    if bevels==0 or bevels>4 or straight<4:
        return None
    area=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(xy,xy[1:]))) / 2
    lost=w*h-area
    if lost<=max(tol*tol,epsilon*min(w,h)) or lost>=w*h*.125:
        return None
    return {'kind':'beveled-rectangle','widthMm':max(w,h),
            'heightMm':min(w,h),'sectionAreaMm2':area,
            'blankSectionAreaMm2':w*h,'bevelCount':bevels}


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
    # A self-touching loop can revisit a vertex without any proper crossing
    # of non-neighbouring segments. Such a contour has no unambiguous
    # manufacturable convex stock section. Compare squared distances to
    # avoid sqrt and reject even tolerance-close non-adjacent vertices.
    for i, a in enumerate(vertices):
        for b in vertices[i+1:]:
            if (a[0]-b[0])**2 + (a[1]-b[1])**2 <= tol*tol:
                return None
    edges = [(b[0]-a[0], b[1]-a[1]) for a,b in zip(points, points[1:])]
    lengths = [math.hypot(*e) for e in edges]
    if min(lengths) < tol*5:
        return None
    # A regular star polygon can have same-sign turns at every vertex.
    # Convexity-by-turn-sign alone therefore does NOT prove a simple loop:
    # reject non-neighbouring crossing edges before proposing any raw stock.
    # At most 12 segments are accepted above, so the quadratic check is cheap.
    def proper_cross(a, b, c, d):
        def side(p, q, r):
            return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
        ab_c, ab_d = side(a,b,c), side(a,b,d)
        cd_a, cd_b = side(c,d,a), side(c,d,b)
        # Near-tangent/collinear non-adjacent edges are ambiguous stock
        # geometry and must not be silently accepted as convex sections.
        eps = tol * max(math.dist(a,b), math.dist(c,d))
        if min(abs(ab_c),abs(ab_d),abs(cd_a),abs(cd_b)) <= eps:
            return True
        return ((ab_c > 0) != (ab_d > 0)
                and (cd_a > 0) != (cd_b > 0))
    for i in range(len(edges)):
        for j in range(i+1,len(edges)):
            if j==i+1 or (i==0 and j==len(edges)-1):
                continue
            if proper_cross(points[i],points[i+1],points[j],points[j+1]):
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
