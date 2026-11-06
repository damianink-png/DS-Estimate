// Independent analytic estimators, using OCCT measurements and editable shop assumptions.
export const NORMS=Object.freeze({
 assembly:{enabled:true,setupMin:20,minutesPerPart:2.5,minutesPerJoint:1.5,heavyKg:50,heavyFactor:1.4,turnMinPart:.6,tackSpacingMm:250,tackSeconds:8},
 welding:{enabled:true,a:4,deposition:2.5,arcFactor:.35,setupMin:20,density:7850,cleanMinMeter:.8},
 cnc:{enabled:true,setupMin:20,removalCm3Min:8},
 bending:{enabled:true,secondsPerBend:30,setupMin:20,handlingMin:.5},
 coating:{enabled:false,setupMin:30,layers:2,m2Hour:15},
 postweld:{enabled:true,grindMinMeter:3,buttGrindFactor:1.5,straightenMinMeter:.5,straightenMin:5},
 quality:{enabled:true,setupMin:10,minutesPerPart:1,vtMinMeter:2},
 logistics:{enabled:false,setupMin:20,packingMinPart:.5,distanceKm:0,costKm:4},
 engineering:{enabled:false,minutes:0}
});
const good=(n,name,positive=false)=>{if(typeof n!=='number'||!Number.isFinite(n)||n<(positive?Number.MIN_VALUE:0))throw new RangeError(name);return n;};
export function weldPlan(contacts,edits={},norms=NORMS.welding){
 if(!contacts)return null;
 good(norms.deposition,'Wydajność stapiania',true);good(norms.arcFactor,'Wykorzystanie łuku',true);if(norms.arcFactor>1)throw new RangeError('Wykorzystanie łuku');
 const rows=contacts.candidates.map(j=>{
  const e=edits[j.id]??{},enabled=e.enabled!==false,type=e.type??'fillet',a=e.a??j.throatSuggestion??norms.a;
  const length=good(e.lengthMm??j.lengthMm,'Długość spoiny'),density=good(e.density??j.defaultDensity??norms.density,'Gęstość stopiwa',true);
  const section=type==='fillet'?good(a,'Gardziel',true)**2:good(e.sectionMm2??(.5*(j.thicknessSuggestion??a*2)**2),'Pole rowka',true);
  const kg=length*section*density/1e9,arcMinutes=kg/norms.deposition*60,minutes=arcMinutes/norms.arcFactor;
  good(minutes,'Czas spawania');return {...j,...e,enabled,type,a,lengthMm:length,sectionMm2:section,kg,arcMinutes,minutes:enabled?minutes:0};
 });
 const active=rows.filter(r=>r.enabled),totalLengthMm=active.reduce((s,r)=>s+r.lengthMm,0),minutes=active.reduce((s,r)=>s+r.minutes,0);
 const grouped=new Map();for(const r of active){const key=r.type+':'+r.sectionMm2;let g=grouped.get(key)||{type:r.type,sectionMm2:r.sectionMm2,a:r.a,lengthMm:0,minutes:0};g.lengthMm+=r.lengthMm;g.minutes+=r.minutes;grouped.set(key,g);}
 return {rows,groups:[...grouped.values()],totalLengthMm,minutes,complete:contacts.complete};
}
export function partBends(p){
 if(p.bendCount!==null)return p.bendCount;
 const k=p.stockKind||p.solid.stockHint?.kind;
 if(['square-hollow','rectangular-hollow','round-tube','angle','channel','i-section','tee','flat-section','round-bar','square-bar','rectangular-bar'].includes(k))return 0;
 return p.solid.bendHint?.count??(['plate-candidate','plate'].includes(k)?0:null);
}
export function automaticOperations(parts,contacts,jointEdits={},norms=NORMS){
 const n=Object.fromEntries(Object.keys(NORMS).map(k=>[k,{...NORMS[k],...norms[k]}]));
 const byId=new Map(parts.map(p=>[p.id,p]));
 const proposed=contacts?{...contacts,candidates:contacts.candidates.map(j=>{
  const a=byId.get(j.partA),b=byId.get(j.partB),thickness=p=>p?.solid.stockHint?.wallMm??p?.solid.stockHint?.thicknessMm??p?.solid.bendHint?.bends?.[0]?.thicknessMm??p?.dims?.[2];
  const t=Math.min(thickness(a)??Infinity,thickness(b)??Infinity);
  return {...j,thicknessSuggestion:Number.isFinite(t)?t:n.welding.a*2,throatSuggestion:Number.isFinite(t)?Math.max(1,Math.min(n.welding.a,Math.round(.7*t*2)/2)):n.welding.a,defaultDensity:a&&b&&a.density===b.density?a.density:n.welding.density};
 })}:null;
 const w=weldPlan(proposed,jointEdits,n.welding),jointCount=w?.rows.filter(r=>r.enabled).length??0;
 const result={};const operation=(key,value)=>{good(value,key);return value/60;};
 if(n.assembly.enabled){const a=n.assembly;[a.setupMin,a.minutesPerPart,a.minutesPerJoint,a.heavyKg,a.heavyFactor].forEach(v=>good(v,'Norma montażu'));
  result.assembly={fixtures:operation('Stanowisko',a.setupMin),fitup:operation('Ustawianie',parts.reduce((s,p)=>s+a.minutesPerPart*(p.massKg>a.heavyKg?a.heavyFactor:1),0)),tacks:contacts?operation('Sczepianie',jointCount*a.minutesPerJoint+(w?.rows.filter(r=>r.enabled).reduce((s,r)=>s+Math.max(2,Math.ceil(r.lengthMm/good(a.tackSpacingMm,'Rozstaw sczepów',true)))*a.tackSeconds/60,0)??0)):null,turning:operation('Obracanie',parts.reduce((s,p)=>s+a.turnMinPart*(p.massKg>a.heavyKg?a.heavyFactor:1),0))};}
 if(n.welding.enabled&&w)result.welding={setup:operation('Przygotowanie',n.welding.setupMin),weld:w.minutes/60,clean:operation('Czyszczenie spoin',w.totalLengthMm/1000*n.welding.cleanMinMeter)};
 if(n.bending.enabled){let count=0,unknown=false;for(const p of parts.filter(p=>p.route==='make')){let c=partBends(p);if(c===null){unknown=true;continue;}good(c,'Gięcia');if(!Number.isInteger(c))throw new RangeError('Gięcia całkowite');count+=c;}
  result.bending={setup:unknown&&count===0?null:operation('Przezbrojenie',count>0?n.bending.setupMin:0),bends:unknown?null:operation('Gięcie',count*(n.bending.secondsPerBend/60+n.bending.handlingMin))};}
 const machined=parts.filter(p=>p.route==='make'&&p.allowances.some(v=>v>0));
 if(n.cnc.enabled&&machined.length){good(n.cnc.removalCm3Min,'Wydajność CNC',true);const volume=machined.reduce((s,p)=>s+Math.max(0,p.stockMassKg-p.massKg)/p.density*1e6,0);
  result.cnc={program:operation('Przygotowanie CNC',new Set(machined.map(p=>p.geometryKey)).size*n.cnc.setupMin),milling:volume/n.cnc.removalCm3Min/60,drilling:0};}
 if(n.cnc.enabled&&!machined.length)result.cnc={program:0,milling:0,drilling:0};
 const areaM2=parts.reduce((s,p)=>s+(p.solid.areaMm2??0)/1e6,0);
 if(n.coating.enabled){good(n.coating.m2Hour,'Wydajność malowania',true);result.coating={prepare:operation('Przygotowanie',n.coating.setupMin),paint:areaM2*n.coating.layers/n.coating.m2Hour,handle:null};}
 if(n.quality.enabled)result.quality={dimensions:operation('Kontrola',n.quality.setupMin+parts.length*n.quality.minutesPerPart),visual:w?operation('VT',w.totalLengthMm/1000*n.quality.vtMinMeter):null,ndt:0};
 if(n.postweld.enabled)result.postweld={straighten:w?operation('Prostowanie',w.totalLengthMm>0?n.postweld.straightenMin+w.totalLengthMm/1000*n.postweld.straightenMinMeter:0):null,grind:w?operation('Szlifowanie',w.rows.filter(r=>r.enabled).reduce((s,r)=>s+r.lengthMm/1000*n.postweld.grindMinMeter*(r.type==='butt'?n.postweld.buttGrindFactor:1),0)):null,machining:0};
 if(n.logistics.enabled)result.logistics={pack:operation('Pakowanie',parts.length*n.logistics.packingMinPart),load:operation('Załadunek',n.logistics.setupMin),ship:null};
 if(n.engineering.enabled)result.engineering={documentation:operation('Technologia',n.engineering.minutes)};
 const extraRows={};if(n.logistics.enabled){const fee=n.logistics.distanceKm*n.logistics.costKm;good(fee,'Transport');result.logistics.ship=0;extraRows.logistics=[{key:'transport-distance',name:'Przewóz według dystansu',kind:'amount',autoAmount:fee,detail:n.logistics.distanceKm+' km × '+n.logistics.costKm+' zł/km',evidence:'shop-logistics-assumption'}];}
 return {disabledModules:Object.keys(n).filter(k=>!n[k].enabled),modules:result,extraRows,welds:w,areaM2,jointCount};
}
export function bendAllowance({angleDeg,radiusMm,thicknessMm,kFactor=.4}){[angleDeg,radiusMm,thicknessMm,kFactor].forEach(v=>good(v,'Parametr gięcia'));if(kFactor>1||angleDeg>180)throw new RangeError('Parametry gięcia');return angleDeg*Math.PI/180*(radiusMm+kFactor*thicknessMm);}
