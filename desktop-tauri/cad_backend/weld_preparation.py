"""Measure butt-joint preparation from transverse B-Rep sections.
Supports prismatic I / V / half-V / X and sampled curved grooves. This measures
void to fill, not weld intent, reinforcement, strength or a welding procedure.
"""
import math
try:from . import cad_measure as cad
except ImportError:import cad_measure as cad

def primary_skin(shape):
    faces=[];total=cad.area(shape)
    for raw in cad.shapes(shape,cad.TopAbs_FACE):
        f=cad.face_cast(raw);s=cad.BRepAdaptor_Surface(f)
        if s.GetType()==cad.GeomAbs_Plane:faces.append((cad.area(f),f,s.Plane()))
    faces.sort(key=lambda row:-row[0])
    for area,face,plane in faces:
        if area<total*.25:break
        normal=plane.Axis().Direction()
        for other,of,op in faces:
            if face.IsSame(of) or other<area*.6 or abs(normal.Dot(op.Axis().Direction()))<.99999:continue
            thickness=abs(plane.Distance(op.Location()))
            if thickness<.2:continue
            if thickness>math.sqrt(min(area,other))*.45:continue
            dist=cad.BRepExtrema_DistShapeShape(face,of);dist.Perform()
            if dist.IsDone() and abs(dist.Value()-thickness)<.03:
                return {'normal':normal,'thickness':thickness,'faces':faces}
    return None

def center(shape):
    props=cad.GProp_GProps();cad.volume_props(shape,props);return props.CentreOfMass()

def section_points(shape,bounds,z):
    try:from .stock_recognition import _section_edges,_closed_loops
    except ImportError:from stock_recognition import _section_edges,_closed_loops
    if bounds[5]-bounds[2]<1e-6:return None
    edges=_section_edges(shape,bounds,2,(z-bounds[2])/(bounds[5]-bounds[2]))
    loops=_closed_loops(edges,.005) if edges else None
    return [loop[0] for loop in loops] if loops else None

def intersections(loops,y):
    points=[]
    for pts in loops:
        for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
            if (y1<=y<y2) or (y2<=y<y1):points.append(x1+(y-y1)*(x2-x1)/(y2-y1))
    return sorted(points)

def measured_section(a,b,lo,hi):
    levels=sorted(set([lo,hi]+[max(lo,min(hi,p[1])) for loop in a+b for p in loop]))
    area=0.;rows=[]
    def width(y):
        aa=intersections(a,y);bb=intersections(b,y)
        if not aa or not bb:return None
        return bb[0]-aa[-1],aa[-1],bb[0]
    for low,high in zip(levels,levels[1:]):
        if high-low<1e-6:continue
        mid=(low+high)/2;sample=width(mid)
        if sample is None or sample[0]<-.02:return None
        area+=max(0,sample[0])*(high-low);rows.append((low,high,sample))
    if not rows:return None
    eps=min(.0001,(hi-lo)*.00001)
    samples=[width(v) for v in [lo+eps,(lo+hi)/2,hi-eps]]
    if any(v is None for v in samples):return None
    fine=[width(low+eps) for low,high,_ in rows]+[width(high-eps) for low,high,_ in rows]
    fine=[r for r in fine if r is not None];gap=max(0,min(r[0] for r in fine));maximum=max(r[0] for r in fine)
    if maximum>max(1,(hi-lo)*4):return None
    bottom,middle,top=(max(0,r[0]) for r in samples)
    bevel=maximum-gap>.3
    kind='X' if bottom>middle+.3 and top>middle+.3 else 'V'
    if not bevel:kind='I'
    elif max(r[1] for r in fine)-min(r[1] for r in fine)<.2 or max(r[2] for r in fine)-min(r[2] for r in fine)<.2:kind='half-V'
    land=sum(high-low for low,high,r in rows if abs(r[0]-gap)<.05)
    return {'kind':kind,'sectionMm2':max(0,area),'rootGapMm':gap,'rootLandMm':land,'depthMm':hi-lo-land,
            'bottomWidthMm':bottom,'topWidthMm':top,'maximumWidthMm':maximum,'hasBevel':bevel}

def groove_between(a,b,max_gap=3):
    sa,sb=primary_skin(a),primary_skin(b)
    if not sa or not sb or abs(sa['normal'].Dot(sb['normal']))<.99999:return None
    n=sa['normal'];ca,cb=center(a),center(b)
    delta=[v-u for u,v in zip(ca.Coord(),cb.Coord())];dot=sum(v*u for v,u in zip(delta,n.Coord()));trans=[v-dot*u for v,u in zip(delta,n.Coord())]
    if math.sqrt(sum(v*v for v in trans))<.01:return None
    # Use a real longitudinal contact edge when available; centre-to-centre is
    # only the fallback for a separated butt joint with aligned ends.
    direction=None;section=cad.BRepAlgoAPI_Section(a,b);section.Build();best=0
    if section.IsDone():
        for edge in cad.shapes(section.Shape(),cad.TopAbs_EDGE):
            c=cad.BRepAdaptor_Curve(cad.edge_cast(edge))
            if c.GetType()!=cad.GeomAbs_Line:continue
            p,q=c.Value(c.FirstParameter()),c.Value(c.LastParameter());length=p.Distance(q)
            d=cad.gp_Dir(q.X()-p.X(),q.Y()-p.Y(),q.Z()-p.Z()) if length>.01 else None
            if d and abs(d.Dot(n))<.01 and length>best:direction=d;best=length
    if direction is None:
        u=cad.gp_Dir(*trans);direction=u.Crossed(n)
    u=n.Crossed(direction)
    if sum(v*w for v,w in zip(u.Coord(),trans))<0:u.Reverse();direction.Reverse()
    frame=cad.gp_Ax3(cad.gp_Pnt(0,0,0),direction,u);tr=cad.gp_Trsf();tr.SetTransformation(frame)
    aa=cad.BRepBuilderAPI_Transform(a,tr,True).Shape();bb=cad.BRepBuilderAPI_Transform(b,tr,True).Shape();ab=cad.bounds(aa);bc=cad.bounds(bb)
    lo=max(ab[1],bc[1]);hi=min(ab[4],bc[4]);thickness=hi-lo
    if thickness<.2 or thickness<min(sa['thickness'],sb['thickness'])*.85:return None
    if abs(ab[1]-bc[1])>thickness*.1+.02 or abs(ab[4]-bc[4])>thickness*.1+.02:return None
    lateral=bc[0]-ab[3]
    if lateral<-.05 or lateral>max_gap+.01:return None
    zlo=max(ab[2],bc[2]);zhi=min(ab[5],bc[5]);length=zhi-zlo
    if length<max(1,thickness*.5):return None
    profiles=[]
    for fraction in [.25,.5,.75]:
        z=zlo+length*fraction;pa=section_points(aa,ab,z);pb=section_points(bb,bc,z)
        if not pa or not pb:return None
        result=measured_section(pa,pb,lo,hi)
        if result is None or result['rootGapMm']>max_gap+.01:return None
        profiles.append(result)
    mean=sum(p['sectionMm2'] for p in profiles)/3
    if not any(p['hasBevel'] for p in profiles) and mean<.01:
        return {'kind':'I','sectionMm2':None,'lengthMm':length,'thicknessMm':thickness,'hasBevel':False,'rootGapMm':0,'rootLandMm':thickness,'source':'three transverse OCCT sections','status':'square-butt-candidate'}
    variable=max(p['sectionMm2'] for p in profiles)-min(p['sectionMm2'] for p in profiles)>max(.1,mean*.05)
    return {**profiles[1],'sectionMm2':mean,'lengthMm':length,'thicknessMm':thickness,'variable':variable,
            'samplesMm2':[p['sectionMm2'] for p in profiles],'source':'three transverse OCCT sections; measured void area','status':'variable-groove-candidate' if variable else 'measured-groove-candidate'}

def t_groove_between(a,b,max_gap=3):
    """Foot preparation of a plate on another plate (half-V or double/K).
    Only void under the prepared foot is measured; an unprepared square T joint
    remains a fillet proposal instead of being invented as a butt groove.
    """
    for base,stem in [(a,b),(b,a)]:
        sa,sb=primary_skin(base),primary_skin(stem)
        if not sa or not sb or abs(sa['normal'].Dot(sb['normal']))>.01:continue
        n=cad.gp_Dir(*sa['normal'].Coord());u=cad.gp_Dir(*sb['normal'].Coord());cb,cs=center(base),center(stem)
        delta=[v-w for w,v in zip(cb.Coord(),cs.Coord())]
        if sum(v*w for v,w in zip(delta,n.Coord()))<0:n.Reverse()
        d=u.Crossed(n);tr=cad.gp_Trsf();tr.SetTransformation(cad.gp_Ax3(cad.gp_Pnt(0,0,0),d,u))
        aa=cad.BRepBuilderAPI_Transform(base,tr,True).Shape();bb=cad.BRepBuilderAPI_Transform(stem,tr,True).Shape();ab=cad.bounds(aa);bc=cad.bounds(bb)
        foot=bc[3]-bc[0];height=bc[4]-bc[1]
        if foot<=.2 or height<foot*2 or ab[3]-ab[0]<foot*2:continue
        if bc[1]<ab[4]-.03 or bc[1]>ab[4]+max_gap+.03:continue
        if bc[0]<ab[0]-.03 or bc[3]>ab[3]+.03:continue
        zlo=max(ab[2],bc[2]);zhi=min(ab[5],bc[5]);length=zhi-zlo
        if length<max(1,foot*.5):continue
        profiles=[]
        for fraction in [.25,.5,.75]:
            z=zlo+length*fraction;pa=section_points(aa,ab,z);pb=section_points(bb,bc,z)
            if not pa or not pb:break
            # Rotate the 2-D section axes so the existing integrator finds
            # base's upper skin and stem's lower boundary at every foot x.
            pa=[[(y,x) for x,y in loop] for loop in pa];pb=[[(y,x) for x,y in loop] for loop in pb]
            result=measured_section(pa,pb,bc[0],bc[3])
            if result is None or not result['hasBevel'] or result['rootGapMm']>max_gap+.03:break
            profiles.append(result)
        if len(profiles)!=3:continue
        result=profiles[1];result['kind']='K' if result['kind']=='X' else 'T-half-V'
        area=sum(p['sectionMm2'] for p in profiles)/3
        return {**result,'sectionMm2':area,'lengthMm':length,'thicknessMm':foot,'samplesMm2':[p['sectionMm2'] for p in profiles],
                'source':'three transverse OCCT sections under prepared T-joint foot','status':'measured-t-groove-candidate'}
    return None
