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
