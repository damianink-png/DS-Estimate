"""Geometry proposals, not a finished machining or unfolding plan."""
import math
try:from . import cad_measure as cad
except ImportError:import cad_measure as cad

def feature_hints(solid):
    # Merge artificial STEP face splits before pairing cylindrical skins.
    try:
        try:from OCC.Core.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
        except ImportError:from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
        unify=ShapeUpgrade_UnifySameDomain(solid,True,True,False);unify.Build();solid=unify.Shape()
    except Exception:pass
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
            if dot<.9999 or off>.05 or not .2<=thickness<=80:continue
            la=a['area']/(a['radius']*a['angle']);lb=b['area']/(b['radius']*b['angle'])
            if abs(la-lb)>max(.1,la*.05):continue
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
        if s.GetType()==cad.GeomAbs_Plane and a>total_area*.025:planes.append((a,s.Plane(),f))
    candidates=[]
    for i,(a,p,pf) in enumerate(planes):
        for b,q,qf in planes[i+1:]:
            if abs(p.Axis().Direction().Dot(q.Axis().Direction()))<.99999:continue
            t=abs(p.Distance(q.Location()))
            if not .2<=t<=min(80,math.sqrt(min(a,b))*.45) or min(a,b)<max(a,b)*.55:continue
            distance=cad.BRepExtrema_DistShapeShape(pf,qf);distance.Perform()
            if not distance.IsDone() or abs(distance.Value()-t)>.03:continue
            # Extents of the skin in its own plane, not a world-axis bbox.
            normal=p.Axis().Direction();direction=None;longest=0
            for edge in cad.shapes(pf,cad.TopAbs_EDGE):
                curve=cad.BRepAdaptor_Curve(cad.edge_cast(edge))
                if curve.GetType()!=cad.GeomAbs_Line:continue
                start,end=curve.Value(curve.FirstParameter()),curve.Value(curve.LastParameter());length=start.Distance(end)
                if length>longest and length>.001:
                    d=cad.gp_Dir(end.X()-start.X(),end.Y()-start.Y(),end.Z()-start.Z())
                    if abs(d.Dot(normal))<.001:direction=d;longest=length
            if direction is None:continue
            tr=cad.gp_Trsf();tr.SetTransformation(cad.gp_Ax3(cad.gp_Pnt(0,0,0),normal,direction))
            skin=cad.BRepBuilderAPI_Transform(pf,tr,True).Shape();bounds=cad.bounds(skin)
            width=min(bounds[3]-bounds[0],bounds[4]-bounds[1])
            if width/t<3-1e-5:continue
            candidates.append((min(a,b),t))
    bends=features.get('bendHint');bend_rows=bends['bends'] if bends else []
    if candidates:
        # A flat sheet must have two dominant skin faces. Parallel side faces
        # of a hollow/custom section do not establish constant sheet thickness.
        if not bend_rows and max(candidates)[0]<total_area*.30:return None
        if bend_rows:
            target=bend_rows[0]['thicknessMm'];consistent=[row for row in candidates if abs(row[1]-target)<=max(.05,target*.03)]
            thickness=max(consistent)[1] if consistent else target
        else:thickness=max(candidates)[1]
        if bend_rows and any(abs(b['thicknessMm']-thickness)>max(.05,thickness*.03) for b in bend_rows):return None
    elif bend_rows:
        thickness=bend_rows[0]['thicknessMm']
        if any(abs(b['thicknessMm']-thickness)>.05 for b in bend_rows):return None
    else:return None
    perimeter=(total_area-2*volume/thickness)/thickness
    if perimeter<=0 or volume/thickness<4*thickness**2:return None
    cut=None
    if not bend_rows and planes:
        _,_,face=max(planes,key=lambda row:row[0]);contour=cad.length(face);pierces=sum(1 for _ in cad.shapes(face,cad.TopAbs_WIRE))
        if contour>0 and pierces:cut={'kind':'plate-outline','thicknessMm':round(thickness,5),'contourMm':contour,'pierces':pierces,'estimated':True,'source':'largest planar skin as blank outline; review edge preparation allowance'}
    return {'planarCuttingHint':cut,'kind':'bent-plate' if bend_rows else 'plate-candidate','thicknessMm':round(thickness,5),
            'estimatedContourMm':perimeter,'midSurfaceAreaMm2':volume/thickness,
            'source':'paired planar/cylindrical faces, constant-thickness mid-surface estimate'}
