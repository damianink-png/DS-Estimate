import {partValues} from './parts.mjs';
// Independent analytic estimators, using OCCT measurements and editable shop assumptions.
export const NORMS=Object.freeze({
 assembly:{enabled:true,setupMin:20,minutesPerPart:2.5,minutesPerJoint:1.5,heavyKg:50,heavyFactor:1.4,turnMinPart:.6,longMm:1500,profileFactor:1.2,bentFactor:1.4,unknownFactor:1.5,tackSpacingMm:250,tackSeconds:8},
 welding:{enabled:true,a:4,deposition:2.5,arcFactor:.35,setupMin:20,density:7850,cleanMinMeter:.8},
 cnc:{enabled:true,setupMin:20,removalCm3Min:8,bevelSetupMin:10,bevelCm3Min:6},
 bending:{enabled:true,secondsPerBend:30,setupMin:20,handlingMin:.5,referenceLengthMm:1000,referenceThicknessMm:6,heavyKg:15},
 coating:{enabled:false,setupMin:30,layers:2,m2Hour:15},
 postweld:{enabled:true,grindMinMeter:3,buttGrindFactor:1.5,filletGrindFactor:0,straightenMinMeter:.5,straightenMin:5,straightenDepositKgMeter:.1,straightenLengthMeter:.5},
 quality:{enabled:true,setupMin:10,minutesPerPart:1,vtMinMeter:2},
 logistics:{enabled:false,setupMin:20,packingMinPart:.5,distanceKm:0,costKm:4},
 engineering:{enabled:false,minutes:0}
});
const good=(n,name,positive=false)=>{if(typeof n!=='number'||!Number.isFinite(n)||n<(positive?Number.MIN_VALUE:0))throw new RangeError(name);return n;};
export function weldPlan(contacts,edits={},norms=NORMS.welding){
 if(!contacts)return null;
 good(norms.deposition,'Wydajność stapiania',true);good(norms.arcFactor,'Wykorzystanie łuku',true);if(norms.arcFactor>1)throw new RangeError('Wykorzystanie łuku');
 const rows=contacts.candidates.map(j=>{
  const e=edits[j.id]??{},enabled=e.enabled!==false,type=e.type??j.suggestedType??'fillet',a=e.a??j.throatSuggestion??norms.a;
  const length=good(e.lengthMm??j.lengthMm,'Długość spoiny'),density=good(e.density??j.defaultDensity??norms.density,'Gęstość stopiwa',true);
  const section=type==='fillet'?good(a,'Gardziel',true)**2:good(e.sectionMm2??j.measuredSectionMm2??(.5*(j.thicknessSuggestion??a*2)**2),'Pole rowka',true);
  const kg=length*section*density/1e9,arcMinutes=kg/norms.deposition*60,minutes=arcMinutes/norms.arcFactor;
  good(minutes,'Czas spawania');return {...j,...e,enabled,type,a,lengthMm:length,sectionMm2:section,kg,arcMinutes,minutes:enabled?minutes:0};
 });
 const active=rows.filter(r=>r.enabled),totalLengthMm=active.reduce((s,r)=>s+r.lengthMm,0),minutes=active.reduce((s,r)=>s+r.minutes,0);
 const grouped=new Map();for(const r of active){const key=r.type+':'+r.sectionMm2;let g=grouped.get(key)||{type:r.type,sectionMm2:r.sectionMm2,a:r.a,lengthMm:0,minutes:0};g.lengthMm+=r.lengthMm;g.minutes+=r.minutes;grouped.set(key,g);}
 return {rows,groups:[...grouped.values()],totalLengthMm,minutes,complete:contacts.complete};
}
export function partBends(p){
 if(p.bendCount!==null)return p.bendCount;
 const k=p.stockKind||p.solid.stockHint?.rawStockCandidate?.kind||p.solid.stockHint?.kind;
 if(['square-hollow','rectangular-hollow','round-tube','angle','channel','i-section','tee','flat-section','round-bar','square-bar','rectangular-bar'].includes(k))return 0;
 // Cylindrical pairs in an unknown extrusion are not proof of a formed sheet.
 return k==='bent-plate'?p.solid.bendHint?.count??null:['plate-candidate','plate'].includes(k)?0:null;
}
export function automaticOperations(parts,contacts,jointEdits={},norms=NORMS){
 const n=Object.fromEntries(Object.keys(NORMS).map(k=>[k,{...NORMS[k],...norms[k]}]));
 const byId=new Map(parts.map(p=>[p.id,p]));
 const proposed=contacts?{...contacts,candidates:contacts.candidates.filter(j=>byId.has(j.partA)&&byId.has(j.partB)).map(j=>{
  const a=byId.get(j.partA),b=byId.get(j.partB),thickness=p=>p?.solid.stockHint?.rawStockCandidate?.wallMm??p?.solid.stockHint?.wallMm??p?.solid.stockHint?.thicknessMm??p?.solid.bendHint?.bends?.[0]?.thicknessMm??p?.dims?.[2];
  const t=Math.min(thickness(a)??Infinity,thickness(b)??Infinity);
  return {...j,thicknessSuggestion:Number.isFinite(t)?t:n.welding.a*2,throatSuggestion:Number.isFinite(t)?Math.max(1,Math.min(n.welding.a,Math.round(.7*t*2)/2)):n.welding.a,defaultDensity:a&&b&&a.density===b.density?a.density:n.welding.density};
 })}:null;
 const w=weldPlan(proposed,jointEdits,n.welding),jointCount=w?.rows.filter(r=>r.enabled).length??0;
 const result={};const operation=(key,value)=>{good(value,key);return value/60;};
 const active=w?.rows.filter(r=>r.enabled)??[],groups=weldGroups(parts,active),notes=[];
 const graphComplete=Boolean(contacts)&&contacts.complete!==false;
 if(n.assembly.enabled){const a=n.assembly;Object.entries(a).filter(([k])=>k!=='enabled').forEach(([k,v])=>good(v,k));
  const factor=p=>{const k=p.stockKind||p.solid.stockHint?.rawStockCandidate?.kind||p.solid.stockHint?.kind;return k==='bent-plate'?a.bentFactor:['plate','plate-candidate'].includes(k)?1:k&&k!=='unknown'?a.profileFactor:a.unknownFactor;};
  result.assembly={fixtures:graphComplete?operation('Stanowisko',groups.length*a.setupMin):null,
   fitup:graphComplete?operation('Ustawianie',groups.reduce((sum,g)=>sum+g.parts.reduce((v,p)=>v+a.minutesPerPart*factor(p)*(p.massKg>a.heavyKg?a.heavyFactor:1),0),0)):null,
   tacks:graphComplete?operation('Sczepianie',active.reduce((sum,r)=>sum+a.minutesPerJoint+Math.max(2,Math.ceil(r.lengthMm/good(a.tackSpacingMm,'Rozstaw sczepów',true)))*a.tackSeconds/60,0)):null,
   turning:graphComplete?operation('Manipulacja podzespołem',groups.reduce((sum,g)=>sum+a.turnMinPart*Math.max(1,g.normalGroups-1)*Math.max(1,Math.sqrt(g.massKg/good(a.heavyKg,'Próg masy',true)),Math.sqrt(g.spanMm/good(a.longMm,'Próg długości',true))),0)):null};
  notes.push('Montaż: '+groups.length+' podzespołów ze styków; części bez aktywnego połączenia pominięto. Manipulacja jest normą na podzespół, nie zaplanowaną kolejnością obrotów.');
 }
 if(n.welding.enabled&&w)result.welding={setup:operation('Przygotowanie',active.length?n.welding.setupMin:0),weld:graphComplete?w.minutes/60:null,clean:graphComplete?operation('Czyszczenie spoin',w.totalLengthMm/1000*n.welding.cleanMinMeter):null};
 const bendRows=n.bending.enabled?parts.filter(p=>p.route==='make').map(p=>bendEstimate(p,n.bending)):[];
 if(n.bending.enabled){const unknown=bendRows.some(r=>r.count===null),batches=new Set(bendRows.flatMap(r=>r.batchKeys));
  result.bending={setup:unknown&&batches.size===0?null:operation('Przezbrojenie',batches.size*n.bending.setupMin),bends:unknown?null:operation('Gięcie',bendRows.reduce((s,r)=>s+(r.minutes??0),0))};
  notes.push('Gięcie: '+batches.size+' grup materiał / grubość / promień. Czas uwzględnia długość linii, grubość i masę; narzędzia i kolejność są założeniem.');
 }
 const machined=parts.filter(p=>p.route==='make').map(p=>{
  const raw=p.solid.stockHint?.rawStockCandidate,base=partValues(p.solid,{...p,stockMassKg:null,allowances:[0,0,0,0,0,0]}).stockMassKg;
  const excess=p.allowances.some(v=>v>0)?Math.max(0,p.stockMassKg-base)/p.density*1e9:0;
  return {part:p,volumeMm3:Math.max(0,raw?.removedVolumeMm3??0)+excess};
 }).filter(r=>r.volumeMm3>1e-3);
 const bevels=active.filter(r=>r.groove?.hasBevel).map(r=>({id:r.id,volumeMm3:Math.max(0,r.groove.sectionMm2-(r.groove.rootGapMm??0)*r.groove.thicknessMm)*r.lengthMm}));
 if(n.cnc.enabled){good(n.cnc.removalCm3Min,'Wydajność CNC',true);good(n.cnc.bevelCm3Min,'Wydajność fazowania',true);
  result.cnc={program:operation('Przygotowanie CNC',new Set(machined.map(r=>r.part.geometryKey??r.part.id)).size*n.cnc.setupMin),
   milling:machined.reduce((s,r)=>s+r.volumeMm3,0)/1000/n.cnc.removalCm3Min/60,drilling:0,
   bevelSetup:graphComplete?operation('Przygotowanie fazowania',bevels.length?n.cnc.bevelSetupMin:0):null,
   bevel:graphComplete?bevels.reduce((s,r)=>s+r.volumeMm3,0)/1000/n.cnc.bevelCm3Min/60:null};
  if(machined.length)notes.push('Usunięcie materiału z profili / naddatków: norma objętościowa obróbki. Wybór frezowania lub lasera do rur wymaga potwierdzenia.');
  if(bevels.length)notes.push('Fazowanie: objętość zmierzonego rowka bez szczeliny; doliczono przygotowanie. Bez osobnych danych o narzędziu jest to norma obróbki, nie ścieżka CAM.');
 }
 const areaM2=parts.reduce((s,p)=>s+(p.solid.areaMm2??0)/1e6,0);
 if(n.coating.enabled){good(n.coating.m2Hour,'Wydajność malowania',true);result.coating={prepare:operation('Przygotowanie',n.coating.setupMin),paint:areaM2*n.coating.layers/n.coating.m2Hour,handle:null};}
 if(n.quality.enabled)result.quality={dimensions:operation('Kontrola',n.quality.setupMin+parts.length*n.quality.minutesPerPart),visual:w&&graphComplete?operation('VT',w.totalLengthMm/1000*n.quality.vtMinMeter):null,ndt:0};
 const weldMeters=(w?.totalLengthMm??0)/1000,depositPerMeter=weldMeters?active.reduce((s,r)=>s+r.kg,0)/weldMeters:0;
 const straightenRisk=weldMeters>=n.postweld.straightenLengthMeter&&depositPerMeter>=n.postweld.straightenDepositKgMeter;
 if(n.postweld.enabled)result.postweld={straighten:graphComplete?operation('Rezerwa prostowania',straightenRisk?n.postweld.straightenMin+weldMeters*n.postweld.straightenMinMeter:0):null,
  grind:graphComplete?operation('Szlifowanie',active.reduce((s,r)=>s+r.lengthMm/1000*n.postweld.grindMinMeter*(r.type==='butt'?n.postweld.buttGrindFactor:n.postweld.filletGrindFactor),0)):null,machining:0};
 if(w)notes.push('Prostowanie: '+(straightenRisk?'rezerwa z progu długości i ilości stopiwa':'bez automatycznej rezerwy poniżej progów')+'; odkształcenie nie jest mierzone. Szlifowanie pachwin domyślnie wyłączone.');
 if(n.logistics.enabled)result.logistics={pack:operation('Pakowanie',parts.length*n.logistics.packingMinPart),load:operation('Załadunek',n.logistics.setupMin),ship:null};
 if(n.engineering.enabled)result.engineering={documentation:operation('Technologia',n.engineering.minutes)};
 const extraRows={};if(n.logistics.enabled){const fee=n.logistics.distanceKm*n.logistics.costKm;good(fee,'Transport');result.logistics.ship=0;extraRows.logistics=[{key:'transport-distance',name:'Przewóz według dystansu',kind:'amount',autoAmount:fee,detail:n.logistics.distanceKm+' km × '+n.logistics.costKm+' zł/km',evidence:'shop-logistics-assumption'}];}
 return {disabledModules:Object.keys(n).filter(k=>!n[k].enabled),modules:result,extraRows,welds:w,areaM2,jointCount,groups:groups.map(g=>({partIds:g.parts.map(p=>p.id),massKg:g.massKg,normalGroups:g.normalGroups})),bendRows,machining:machined.map(r=>({partId:r.part.id,volumeMm3:r.volumeMm3})),bevels,notes};
}
export function bendAllowance({angleDeg,radiusMm,thicknessMm,kFactor=.4}){[angleDeg,radiusMm,thicknessMm,kFactor].forEach(v=>good(v,'Parametr gięcia'));if(kFactor>1||angleDeg>180)throw new RangeError('Parametry gięcia');return angleDeg*Math.PI/180*(radiusMm+kFactor*thicknessMm);}

export function weldGroups(parts,rows){
 const byId=new Map(parts.map(p=>[p.id,p])),neighbors=new Map();
 for(const r of rows)for(const [a,b] of [[r.partA,r.partB],[r.partB,r.partA]]){if(!byId.has(a)||!byId.has(b))continue;if(!neighbors.has(a))neighbors.set(a,new Set());neighbors.get(a).add(b);}
 const seen=new Set(),groups=[];
 for(const first of neighbors.keys()){if(seen.has(first))continue;const todo=[first],ids=[];while(todo.length){const id=todo.pop();if(seen.has(id))continue;seen.add(id);ids.push(id);for(const b of neighbors.get(id)??[])todo.push(b);}
  const members=ids.map(id=>byId.get(id)),normals=[];
  for(const r of rows.filter(r=>ids.includes(r.partA)))for(const v of r.contactNormals??[]){if(v.length===3&&!normals.some(n=>Math.abs(n.reduce((s,x,i)=>s+x*v[i],0))>.95))normals.push(v);}
  groups.push({parts:members,massKg:members.reduce((s,p)=>s+p.massKg,0),spanMm:Math.max(...members.flatMap(p=>p.dims)),normalGroups:normals.length||1});
 }return groups;
}
export function bendEstimate(p,n=NORMS.bending){
 const count=partBends(p);if(count===null)return {partId:p.id,count:null,minutes:null,batchKeys:[]};if(!count)return {partId:p.id,count:0,minutes:0,batchKeys:[]};
 good(count,'Gięcia');if(!Number.isInteger(count))throw new RangeError('Gięcia całkowite');
 const rows=p.solid.bendHint?.bends??[],keys=new Set();let minutes=0;
 for(let i=0;i<count;i++){
  const b=rows[i],t=b?.thicknessMm??p.solid.stockHint?.thicknessMm??Math.min(...p.dims),length=b?.lengthMm??Math.max(...p.dims);
  const factor=Math.max(1,length/good(n.referenceLengthMm,'Długość odniesienia',true))*Math.max(1,Math.sqrt(t/good(n.referenceThicknessMm,'Grubość odniesienia',true)));
  const handling=Math.max(1,Math.sqrt(p.massKg/good(n.heavyKg,'Masa odniesienia',true)));
  minutes+=n.secondsPerBend/60*factor+n.handlingMin*handling;
  keys.add([p.grade,p.density,t.toFixed(2),b?.radiusMm?.toFixed(2)??'nieznany promień'].join('|'));
 }return {partId:p.id,count,minutes,batchKeys:[...keys]};
}
