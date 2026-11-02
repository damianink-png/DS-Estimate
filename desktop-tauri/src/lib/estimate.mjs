// DS Estimate 2.0 — estimates operate on normalized features, not STEP files.
const valid=(v,name,positive=false)=>{if(!Number.isFinite(v)||v<0||(positive&&v===0))throw new RangeError(name);return v};
export function estimateCnc({removedCm3=0,removalCm3Min=8,holes=[],setupMin=20,toolChanges=0,toolChangeMin=2,handlingMin=0,ratePerHour=388}={}){
 for(const [k,v] of Object.entries({removedCm3,setupMin,toolChanges,toolChangeMin,handlingMin,ratePerHour}))valid(v,k);valid(removalCm3Min,'removalCm3Min',true);
 const millingMin=removedCm3/removalCm3Min;
 const drillingMin=holes.reduce((s,h)=>s+valid(h.count,'count')*valid(h.depthMm,'depthMm')/valid(h.feedMmMin,'feedMmMin',true),0);
 const totalMin=millingMin+drillingMin+setupMin+toolChanges*toolChangeMin+handlingMin;
 return {millingMin,drillingMin,totalMin,cost:totalMin*ratePerHour/60};
}
export function estimateCut({contourMm=0,feedMmMin=1500,pierces=0,pierceSec=2,rapidMm=0,rapidMmMin=10000,setupMin=10,ratePerHour=388}={}){
 for(const [k,v] of Object.entries({contourMm,pierces,pierceSec,rapidMm,setupMin,ratePerHour}))valid(v,k);
 valid(feedMmMin,'feedMmMin',true);valid(rapidMmMin,'rapidMmMin',true);
 const cuttingMin=contourMm/feedMmMin,piercingMin=pierces*pierceSec/60,rapidMin=rapidMm/rapidMmMin,totalMin=cuttingMin+piercingMin+rapidMin+setupMin;
 return {cuttingMin,piercingMin,rapidMin,totalMin,cost:totalMin*ratePerHour/60};
}
export function estimateBending({bends=0,secondsPerBend=25,setupMin=15,handlingMin=0,ratePerHour=388}={}){
 for(const [k,v] of Object.entries({bends,secondsPerBend,setupMin,handlingMin,ratePerHour}))valid(v,k);
 const totalMin=bends*secondsPerBend/60+setupMin+handlingMin;return {totalMin,cost:totalMin*ratePerHour/60};
}
export function estimateProject({parts=[],ratePerHour=388}={}){
 const cache=new Map();let totalMin=0,totalCost=0,occurrences=0;
 const rows=parts.map(({geometryId,quantity=1,features={}})=>{
  if(!geometryId||!Number.isInteger(quantity)||quantity<1)throw new RangeError('geometryId/quantity');
  const key=JSON.stringify([geometryId,features,ratePerHour]);let unit=cache.get(key);
  if(!unit){const cnc=features.cnc?estimateCnc({...features.cnc,ratePerHour}):null;
   const cut=features.cut?estimateCut({...features.cut,ratePerHour}):null;
   const bend=features.bend?estimateBending({...features.bend,ratePerHour}):null;
   unit={cnc,cut,bend,unitMin:[cnc,cut,bend].reduce((s,x)=>s+(x?.totalMin||0),0),unitCost:[cnc,cut,bend].reduce((s,x)=>s+(x?.cost||0),0)};cache.set(key,unit)}
  const row={geometryId,quantity,...unit,totalMin:unit.unitMin*quantity,totalCost:unit.unitCost*quantity};
  totalMin+=row.totalMin;totalCost+=row.totalCost;occurrences+=quantity;return row;
 });return {rows,totalMin,totalCost,occurrences,uniqueCalculations:cache.size};
}