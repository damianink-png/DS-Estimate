"""Geometry proposals, not a finished machining or unfolding plan."""
import math
try:from . import cad_measure as cad
except ImportError:import cad_measure as cad

def feature_hints(solid):
    cylinders=[]
    for raw in cad.shapes(solid,cad.TopAbs_FACE):
        face=cad.face_cast(raw);surface=cad.BRepAdaptor_Surface(face)
        if surface.GetType()!=cad.GeomAbs_Cylinder:continue
        c=surface.Cylinder();r=c.Radius();axis=c.Axis();p=axis.Location();d=axis.Direction()
        angle=abs(surface.LastUParameter()-surface.FirstUParameter())
        cylinders.append({'radius':r,'angle':angle,'origin':(p.X(),p.Y(),p.Z()),'axis':(d.X(),d.Y(),d.Z()),'area':cad.area(face)})
    bends=[];used=set()
    for i,a in enumerate(cylinders):
        if i in used or not .05<a['angle']<math.pi*1.95:continue
        for j,b in enumerate(cylinders[i+1:],i+1):
            if j in used or abs(a['angle']-b['angle'])>.01:continue
            dot=abs(sum(x*y for x,y in zip(a['axis'],b['axis'])))
            delta=[x-y for x,y in zip(a['origin'],b['origin'])];along=sum(x*y for x,y in zip(delta,a['axis']))
            off=math.sqrt(sum((x-along*y)**2 for x,y in zip(delta,a['axis'])))
            thickness=abs(a['radius']-b['radius'])
            if dot<.9999 or off>.05 or not .2<=thickness<=25:continue
            la=a['area']/(a['radius']*a['angle']);lb=b['area']/(b['radius']*b['angle'])
            if abs(la-lb)>max(.1,la*.02):continue
            used.update((i,j));bends.append({'angleDeg':round(a['angle']*180/math.pi,3),'radiusMm':min(a['radius'],b['radius']),'thicknessMm':thickness,'lengthMm':(la+lb)/2});break
    return {'bendHint':{'count':len(bends),'bends':bends,'status':'candidate','source':'paired coaxial cylindrical bend faces'} if bends else None}

def sheet_hints(solid,features):
    """Rotation-independent paired plane thickness; cylindrical pairs validate bends.

    A - 2 V/t isolates edge area of a constant-thickness sheet. Its division by t
    estimates the developed cut perimeter, using the mid-surface (K=0.5).
    It is a costing estimate, not an exportable unfolded contour.
    """
    planes=[];total_area=cad.area(solid);volume=cad.volume(solid)
    for raw in cad.shapes(solid,cad.TopAbs_FACE):
        f=cad.face_cast(raw);s=cad.BRepAdaptor_Surface(f);a=cad.area(f)
        if s.GetType()==cad.GeomAbs_Plane and a>total_area*.025:planes.append((a,s.Plane()))
    candidates=[]
    for i,(a,p) in enumerate(planes):
        for b,q in planes[i+1:]:
            if abs(p.Axis().Direction().Dot(q.Axis().Direction()))<.99999:continue
            t=abs(p.Distance(q.Location()))
            if .2<=t<=min(80,math.sqrt(min(a,b))*.25) and abs(a-b)<max(a,b)*.15:
                candidates.append((min(a,b),t))
    bends=features.get('bendHint');bend_rows=bends['bends'] if bends else []
    if candidates:
        # A flat sheet must have two dominant skin faces. Parallel side faces
        # of a hollow/custom section do not establish constant sheet thickness.
        if not bend_rows and max(candidates)[0]<total_area*.35:return None
        thickness=max(candidates)[1]
        if bend_rows and any(abs(b['thicknessMm']-thickness)>max(.05,thickness*.03) for b in bend_rows):return None
    elif bend_rows:
        thickness=bend_rows[0]['thicknessMm']
        if any(abs(b['thicknessMm']-thickness)>.05 for b in bend_rows):return None
    else:return None
    perimeter=(total_area-2*volume/thickness)/thickness
    if perimeter<=0 or volume/thickness<4*thickness**2:return None
    return {'kind':'bent-plate' if bend_rows else 'plate-candidate','thicknessMm':round(thickness,5),
            'estimatedContourMm':perimeter,'midSurfaceAreaMm2':volume/thickness,
            'source':'paired planar/cylindrical faces, constant-thickness mid-surface estimate'}
