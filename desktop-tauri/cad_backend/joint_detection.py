"""Propose contact seams from exact OCCT geometry; contact is not weld intent.
No mesh, GPU or learned detection. Bounded broad phase, then coplanar face Commons.
"""
import math,time,re
try:from . import cad_measure as cad
except ImportError:import cad_measure as cad

def overlaps(a,b,tol=.05):return all(a[k]<=b[k+3]+tol and b[k]<=a[k+3]+tol for k in range(3))
def broad_pairs(boxes,gap=.05):
    active=[]
    for i in sorted(range(len(boxes)),key=lambda j:boxes[j][0]):
        box=boxes[i];active=[j for j in active if boxes[j][3]>=box[0]-gap]
        for j in active:
            if overlaps(box,boxes[j],gap):yield min(i,j),max(i,j)
        active.append(i)

def planar_faces(solid):
    result=[]
    for face in cad.shapes(solid,cad.TopAbs_FACE):
        f=cad.face_cast(face);surface=cad.BRepAdaptor_Surface(f)
        if surface.GetType()==cad.GeomAbs_Plane:
            plane=surface.Plane();n=plane.Axis().Direction();origin=plane.Location()
            result.append((f,cad.bounds(f),(n.X(),n.Y(),n.Z()),(origin.X(),origin.Y(),origin.Z())))
    return result

def detect_contacts(solids,max_pairs=2000,max_seconds=90,excluded=None):
    start=time.monotonic();boxes=[cad.bounds(s) for s in solids];face_cache={};rows=[];issues=[];processed=0;complete=True
    excluded=set(excluded or [])
    for i,j in broad_pairs(boxes,3):
        if i in excluded or j in excluded:continue
        if processed>=max_pairs or time.monotonic()-start>max_seconds:
            complete=False;issues.append('Limit czasu lub liczby par; wynik częściowy.');break
        processed+=1
        try:
            distance=cad.BRepExtrema_DistShapeShape(solids[i],solids[j]);distance.Perform()
            if not distance.IsDone() or distance.Value()>3:continue
            try:from .weld_preparation import groove_between,t_groove_between
            except ImportError:from weld_preparation import groove_between,t_groove_between
            groove=groove_between(solids[i],solids[j]) or t_groove_between(solids[i],solids[j])
            if distance.Value()>.05 and groove is None:continue
            # True interpenetration is a collision, not a measured weld groove.
            common=cad.BRepAlgoAPI_Common(solids[i],solids[j]);common.Build()
            if common.IsDone() and cad.volume(common.Shape())>1e-3:
                issues.append(f'solid-{i+1} / solid-{j+1}: przenikanie brył, sprawdź złożenie.');continue
            for k in (i,j):
                if k not in face_cache:face_cache[k]=planar_faces(solids[k])
            contact_area=0.;perimeter=0.;face_pairs=0;contact_normals=[]
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
                        if not any(abs(sum(x*y for x,y in zip(an,n)))>.999 for n in contact_normals):contact_normals.append(an)
                if not complete:break
            source='coplanar B-Rep face intersection perimeter'
            if contact_area<=1e-4:
                # Section also detects genuine edge contact; still requires intent review.
                section=cad.BRepAlgoAPI_Section(solids[i],solids[j]);section.Build()
                if section.IsDone():perimeter=cad.length(section.Shape())
                source='B-Rep section edge contact'
            if groove is not None:perimeter=groove['lengthMm'];source=groove['source']
            if perimeter>0.1 and math.isfinite(perimeter):
                rows.append({'id':f'solid-{i+1}|solid-{j+1}','partA':f'solid-{i+1}','partB':f'solid-{j+1}',
                 'lengthMm':round(perimeter,4),'contactAreaMm2':round(contact_area,4),
                 'facePairs':face_pairs,'contactNormals':contact_normals,'source':source,'status':'candidate',
                 'preparation':groove['kind'] if groove else 'not-inferred','groove':groove,
                 'suggestedType':'butt' if groove else 'fillet',
                 'measuredSectionMm2':groove['sectionMm2'] if groove else None})
            if not complete:issues.append('Przekroczono czas podczas analizy ścian; wynik częściowy.');break
        except Exception as exc:complete=False;issues.append(f'solid-{i+1} / solid-{j+1}: {type(exc).__name__}')
    return {'engineVersion':'0.7.0','schema':'ds-contact-candidates-v2','solidCount':len(solids),'candidates':rows,'testedPairs':processed,
     'excludedPartIds':[f'solid-{i+1}' for i in sorted(excluded)],'complete':complete,'issues':issues,'seconds':round(time.monotonic()-start,2),
     'limitations':['Obwód styku jest propozycją długości spoin, nie dowodem zamiaru spawania.',
      'Zmierzony rowek nie obejmuje nadlewu i nie potwierdza zamiaru spawania. Dostęp i spoiny przerywane wymagają korekty.',
      'Podzielone ściany mogą zawyżać obwód; sprawdź długości.']}

def analyze_joints(path):
    try:from .assembly_names import read_occurrences
    except ImportError:from assembly_names import read_occurrences
    items,issues=read_occurrences(path)
    excluded=[i for i,p in enumerate(items) if re.search(r'\b(?:washer|nut|screw|bolt)(?:[\s_-]|$)|\b(?:bottle[ _-]jack|electrical[ _-]enclosure)\b|\b(?:DIN|ISO)[ _-]?(?:912|933|934|125|9021|4762|4017|4032)\b',p.get('name',''),re.I)]
    result=detect_contacts([p['shape'] for p in items],excluded=excluded)
    if issues:result['issues']+=issues;result['complete']=False
    return result
