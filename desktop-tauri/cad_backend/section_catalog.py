"""Match measured geometry against the pinned MIT section catalogue.
A fit is a nominal-geometry candidate, not proof of product standard/process.
"""
import functools,json,math,sys
from pathlib import Path

@functools.lru_cache(maxsize=1)
def catalog():
    roots=[Path(getattr(sys,'_MEIPASS',''))/'data/steel-sections.json',
           Path(__file__).parents[1]/'src/lib/data/steel-sections.json']
    for path in roots:
        if path.is_file():return json.loads(path.read_text(encoding='utf-8'))['sections']
    raise FileNotFoundError('Steel section library is not packaged')

FAMILIES={'SHS':'square-hollow','RHS':'rectangular-hollow','CHS':'round-tube',
          'I':'i-section','I_TAPERED':'i-section','U':'channel','U_TAPERED':'channel','L':'angle','L_EQ':'angle','FLAT':'flat-section'}
def section_size(row):
    d=row['dims'];shape=row['shape']
    if shape=='FLAT':return d['b'],d['t'],None
    if shape=='CHS':return d.get('D',d.get('d')),d.get('D',d.get('d')),d.get('t')
    return max(d.get('h',d.get('b',0)),d.get('b',0)),min(d.get('h',d.get('b',0)),d.get('b',0)),d.get('t')

def match_hint(hint):
    kind=hint.get('kind');w=hint.get('diameterMm',hint.get('widthMm'));h=hint.get('diameterMm',hint.get('heightMm'));t=hint.get('wallMm')
    if not all(type(x) in (int,float) and math.isfinite(x) and x>0 for x in (w,h)):return []
    w,h=max(w,h),min(w,h);matches=[]
    for row in catalog():
        if FAMILIES.get(row['shape'])!=kind:continue
        rw,rh,rt=section_size(row)
        if abs(rw-w)>max(.35,w*.006) or abs(rh-h)>max(.35,h*.006):continue
        if t is not None and (rt is None or abs(rt-t)>max(.2,t*.06)):continue
        a=hint.get('sectionAreaMm2');ra=row.get('areaMm2')
        if a and ra and abs(a-ra)>max(1,a*.06):continue
        error=abs(rw-w)/w+abs(rh-h)/h+(abs(a-ra)/a if a and ra else 0)
        matches.append((error,row))
    return [dict(id=r['id'],name=r['name'],series=r['series'],standard=r['standard'],error=round(e,5)) for e,r in sorted(matches,key=lambda p:(p[0],p[1]['id']))[:12]]

def _inside(p,poly):
    x,y=p;inside=False
    for (ax,ay),(bx,by) in zip(poly,poly[1:]):
        if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax:inside=not inside
    return inside

def match_open_loop(points,area):
    if not points:return None
    xmin=min(p[0] for p in points);ymin=min(p[1] for p in points)
    normalized=tuple((round(x-xmin,4),round(y-ymin,4)) for x,y in points)
    return _match_open_loop(normalized,round(area,3))

@functools.lru_cache(maxsize=2048)
def _match_open_loop(points,area):
    """Open rolled I/U/L: compare bbox, net area, and distributed interior probes.
    The probes validate family topology; no bounding-box-only acceptance.
    """
    if len(points)<7:return None
    segments=sorted(((math.dist(a,b),a,b) for a,b in zip(points,points[1:])),reverse=True)
    for _,a,b in segments[:8]:
        if math.dist(a,b)<1e-6:continue
        theta=math.atan2(b[1]-a[1],b[0]-a[0]);co,si=math.cos(theta),math.sin(theta)
        uv=[(x*co+y*si,-x*si+y*co) for x,y in points]
        for swap in (False,True):
            poly=[(y,x) if swap else (x,y) for x,y in uv]
            xmin,xmax=min(p[0] for p in poly),max(p[0] for p in poly);ymin,ymax=min(p[1] for p in poly),max(p[1] for p in poly)
            w,h=xmax-xmin,ymax-ymin
            if min(w,h)<=0:continue
            for row in catalog():
                if row['shape'] not in ('I','I_TAPERED','U','U_TAPERED','L','L_EQ'):continue
                d=row['dims'];rh=d.get('h',d.get('b'));rw=d.get('b');ra=row.get('areaMm2')
                if abs(w-rw)>max(.35,rw*.006) or abs(h-rh)>max(.35,rh*.006) or not ra or abs(area-ra)>max(1,ra*.025):continue
                tw=d.get('tw',d.get('t'));tf=d.get('tf',d.get('t'));r=max(d.get('r',0),d.get('r1',0))
                for flipx,flipy in ((1,1),(-1,1),(1,-1),(-1,-1)):
                    mismatches=0;tested=0
                    for fx in (-.49,-.35,-.15,0,.15,.35,.49):
                        for fy in (-.49,-.35,-.15,0,.15,.35,.49):
                            x,y=fx*w,fy*h
                            # Ignore probes close to theoretical straight boundaries/fillets.
                            boundaries=[abs(abs(y)-(h/2-tf)),abs(abs(x)-tw/2)] if row['shape'] in ('I','I_TAPERED') else [abs(x-(-w/2+tw)),abs(abs(y)-(h/2-tf))] if row['shape'] in ('U','U_TAPERED') else [abs(x-(-w/2+tw)),abs(y-(-h/2+tf))]
                            if min(boundaries)<max(.12,r*.6):continue
                            expect=(abs(y)>h/2-tf or abs(x)<tw/2) if row['shape'] in ('I','I_TAPERED') else ((x<-w/2+tw or abs(y)>h/2-tf) if row['shape'] in ('U','U_TAPERED') else (x<-w/2+tw or y<-h/2+tf))
                            actual=_inside((xmin+w/2+flipx*x,ymin+h/2+flipy*y),poly)
                            tested+=1;mismatches+=expect!=actual
                    if tested>=12 and mismatches==0:
                        return {'kind':FAMILIES[row['shape']],'widthMm':max(w,h),'heightMm':min(w,h),'sectionAreaMm2':area,'webMm':tw,'flangeMm':tf}
    return None
