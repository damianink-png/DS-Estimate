"""Propose contact seams from exact OCCT geometry; contact is not weld intent.
No mesh, GPU or learned detection. Bounded broad phase, then coplanar face Commons.
"""
import math,time
try:from . import cad_measure as cad
except ImportError:import cad_measure as cad

def overlaps(a,b,tol=.05):return all(a[k]<=b[k+3]+tol and b[k]<=a[k+3]+tol for k in range(3))
def broad_pairs(boxes):
    active=[]
    for i in sorted(range(len(boxes)),key=lambda j:boxes[j][0]):
        box=boxes[i];active=[j for j in active if boxes[j][3]>=box[0]-.05]
        for j in active:
            if overlaps(box,boxes[j]):yield min(i,j),max(i,j)
        active.append(i)

def planar_faces(solid):
    result=[]
    for face in cad.shapes(solid,cad.TopAbs_FACE):
        f=cad.face_cast(face);surface=cad.BRepAdaptor_Surface(f)
        if surface.GetType()==cad.GeomAbs_Plane:
            plane=surface.Plane();n=plane.Axis().Direction();origin=plane.Location()
            result.append((f,cad.bounds(f),(n.X(),n.Y(),n.Z()),(origin.X(),origin.Y(),origin.Z())))
    return result

def detect_contacts(solids,max_pairs=2000,max_seconds=90):
    start=time.monotonic();boxes=[cad.bounds(s) for s in solids];face_cache={};rows=[];issues=[];processed=0;complete=True
    for i,j in broad_pairs(boxes):
        if processed>=max_pairs or time.monotonic()-start>max_seconds:
            complete=False;issues.append('Limit czasu lub liczby par; wynik częściowy.');break
        processed+=1
        try:
            distance=cad.BRepExtrema_DistShapeShape(solids[i],solids[j]);distance.Perform()
            if not distance.IsDone() or distance.Value()>.05:continue
            # True interpenetration is a collision, not a measured weld groove.
            common=cad.BRepAlgoAPI_Common(solids[i],solids[j]);common.Build()
            if common.IsDone() and cad.volume(common.Shape())>1e-3:
                issues.append(f'solid-{i+1} / solid-{j+1}: przenikanie brył, sprawdź złożenie.');continue
            for k in (i,j):
                if k not in face_cache:face_cache[k]=planar_faces(solids[k])
            contact_area=0.;perimeter=0.;face_pairs=0
            for a,ab,an,ap in face_cache[i]:
                for b,bb,bn,bp in face_cache[j]:
                    if time.monotonic()-start>max_seconds:
                        complete=False;break
                    if not overlaps(ab,bb) or abs(sum(x*y for x,y in zip(an,bn)))<.99999:continue
                    if abs(sum((x-y)*z for x,y,z in zip(ap,bp,an)))>.01:continue
                    op=cad.BRepAlgoAPI_Common(a,b);op.Build()
                    if not op.IsDone():continue
                    result=op.Shape();surface_area=cad.area(result)
                    if surface_area>1e-4:
                        contact_area+=surface_area;perimeter+=cad.length(result);face_pairs+=1
                if not complete:break
            source='coplanar B-Rep face intersection perimeter'
            if contact_area<=1e-4:
                # Section also detects genuine edge contact; still requires intent review.
                section=cad.BRepAlgoAPI_Section(solids[i],solids[j]);section.Build()
                if section.IsDone():perimeter=cad.length(section.Shape())
                source='B-Rep section edge contact'
            if perimeter>0.1 and math.isfinite(perimeter):
                rows.append({'id':f'solid-{i+1}|solid-{j+1}','partA':f'solid-{i+1}','partB':f'solid-{j+1}',
                 'lengthMm':round(perimeter,4),'contactAreaMm2':round(contact_area,4),
                 'facePairs':face_pairs,'source':source,'status':'candidate','preparation':'not-inferred'})
            if not complete:issues.append('Przekroczono czas podczas analizy ścian; wynik częściowy.');break
        except Exception as exc:complete=False;issues.append(f'solid-{i+1} / solid-{j+1}: {type(exc).__name__}')
    return {'schema':'ds-contact-candidates-v1','solidCount':len(solids),'candidates':rows,'testedPairs':processed,
     'complete':complete,'issues':issues,'seconds':round(time.monotonic()-start,2),
     'limitations':['Obwód styku jest propozycją długości spoin, nie dowodem zamiaru spawania.',
      'Fazy, dostęp palnika, spoiny przerywane i niewymodelowane szczeliny wymagają korekty.',
      'Podzielone ściany mogą zawyżać obwód; sprawdź długości.']}

def analyze_joints(path):return detect_contacts(cad.load_step(path))
