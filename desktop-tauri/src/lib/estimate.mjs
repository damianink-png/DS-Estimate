// DS Estimate 2.0 — estimates operate on normalized features, not STEP files.
const valid=(v,name,positive=false)=>{if(!Number.isFinite(v)||v<0||(positive&&v===0))throw new RangeError(name);return v};
const count=(v,name)=>{if(!Number.isSafeInteger(v)||v<0)throw new RangeError(name);return v};
export function estimateCnc({removedCm3=0,removalCm3Min=8,holes=[],setupMin=20,toolChanges=0,toolChangeMin=2,handlingMin=0,ratePerHour=388}={}){
 for(const [k,v] of Object.entries({removedCm3,setupMin,toolChanges,toolChangeMin,handlingMin,ratePerHour}))valid(v,k);valid(removalCm3Min,'removalCm3Min',true);count(toolChanges,'toolChanges');
 const millingMin=removedCm3/removalCm3Min;
 if(!Array.isArray(holes))throw new TypeError('holes must be an array');
 const drillingMin=holes.reduce((s,h)=>{
  if(!h||typeof h!=='object'||Array.isArray(h))throw new TypeError('hole must be a plain record');
  if(!Number.isSafeInteger(h.count)||h.count<0)throw new RangeError('hole.count');
  return s+h.count*valid(h.depthMm,'depthMm')/valid(h.feedMmMin,'feedMmMin',true);
 },0);
 const totalMin=valid(millingMin+drillingMin+setupMin+toolChanges*toolChangeMin+handlingMin,'cnc.totalMin');
 return {millingMin,drillingMin,totalMin,cost:valid(totalMin*ratePerHour/60,'cnc.cost')};
}
export function estimateCut({contourMm=0,feedMmMin=1500,pierces=0,pierceSec=2,rapidMm=0,rapidMmMin=10000,setupMin=10,ratePerHour=388}={}){
 for(const [k,v] of Object.entries({contourMm,pierces,pierceSec,rapidMm,setupMin,ratePerHour}))valid(v,k);
 valid(feedMmMin,'feedMmMin',true);valid(rapidMmMin,'rapidMmMin',true);count(pierces,'pierces');
 const cuttingMin=contourMm/feedMmMin,piercingMin=pierces*pierceSec/60,rapidMin=rapidMm/rapidMmMin,totalMin=valid(cuttingMin+piercingMin+rapidMin+setupMin,'cut.totalMin');
 return {cuttingMin,piercingMin,rapidMin,totalMin,cost:valid(totalMin*ratePerHour/60,'cut.cost')};
}
export function estimateBending({bends=0,secondsPerBend=25,setupMin=15,handlingMin=0,ratePerHour=388}={}){
 for(const [k,v] of Object.entries({bends,secondsPerBend,setupMin,handlingMin,ratePerHour}))valid(v,k);
 count(bends,'bends');
 const totalMin=valid(bends*secondsPerBend/60+setupMin+handlingMin,'bend.totalMin');return {totalMin,cost:valid(totalMin*ratePerHour/60,'bend.cost')};
}
export function estimateProject({parts=[],ratePerHour=388}={}){
 valid(ratePerHour,'ratePerHour');
 if(!Array.isArray(parts))throw new TypeError('parts must be an array');
 const cache=new Map(),setupsCharged=new Set();
 let totalMin=0,totalCost=0,occurrences=0,missingRoutingOccurrences=0;
 const rows=parts.map(({geometryId,quantity=1,features={}})=>{
  if(!geometryId||!Number.isSafeInteger(quantity)||quantity<1)throw new RangeError('geometryId/quantity');
  const key=JSON.stringify([geometryId,features,ratePerHour]);let unit=cache.get(key);
  if(!unit){const cnc=features.cnc?estimateCnc({...features.cnc,ratePerHour}):null;
   const cut=features.cut?estimateCut({...features.cut,ratePerHour}):null;
   const bend=features.bend?estimateBending({...features.bend,ratePerHour}):null;
   const unitSetupMin=(cnc?(features.cnc.setupMin??20):0)+(cut?(features.cut.setupMin??10):0)+(bend?(features.bend.setupMin??15):0);
   const unitMin=valid([cnc,cut,bend].reduce((s,x)=>s+(x?.totalMin||0),0),'unit.totalMin');
   unit={cnc,cut,bend,unitMin,unitCost:valid(unitMin*ratePerHour/60,'unit.cost'),unitSetupMin,unitRunMin:unitMin-unitSetupMin};
   cache.set(key,unit)}
  // Setup is paid once per distinct geometry/routing batch, even if the same
  // geometry occurs in several rows. Machine cycles scale with occurrences.
  const setupMin=setupsCharged.has(key)?0:unit.unitSetupMin;
  setupsCharged.add(key);
  const rowMin=valid(setupMin+unit.unitRunMin*quantity,'row.totalMin');
  // Missing process features are unknown, not a free operation. Keep the
  // legacy numeric totals as *known* subtotals for backward compatibility.
  // A selected operation with only default parameters is not measurement evidence.
  // Explicit zero is evidence of a measured zero; absent fields are unknown.
  const hasInput=(route,keys)=>route&&typeof route==='object'&&keys.some(k=>Object.hasOwn(route,k) && (k!=='holes'||(Array.isArray(route.holes)&&route.holes.length>0)));
  // Every declared operation needs its own measured routing input.
  // Evidence for cutting cannot certify an otherwise unspecified CNC step.
  const selectedRoutes=[
   [features.cnc,['removedCm3','holes']],
   // Piercing count alone cannot establish cutting distance or cycle time.
   // A measured contour (including explicit zero) is required for cutting.
   [features.cut,['contourMm']],
   [features.bend,['bends']]
  ].filter(([route])=>route!==null && route!==undefined);
  const routingEvidence=selectedRoutes.length>0 &&
   selectedRoutes.every(([route,keys])=>hasInput(route,keys));
  if(!routingEvidence)missingRoutingOccurrences+=quantity;
  const row={geometryId,quantity,...unit,batchSetupMin:setupMin,totalMin:rowMin,
   totalCost:valid(rowMin*ratePerHour/60,'row.totalCost'),routingEvidence};
  if(!Number.isSafeInteger(occurrences+quantity))throw new RangeError('total occurrences exceed safe integer range');
  totalMin=valid(totalMin+row.totalMin,'project.totalMin');totalCost=valid(totalCost+row.totalCost,'project.totalCost');occurrences+=quantity;return row;
 });
 const hasCompleteRouting=occurrences>0&&missingRoutingOccurrences===0;
 return {rows,totalMin,totalCost,occurrences,uniqueCalculations:cache.size,
  missingRoutingOccurrences,knownCostPln:totalCost,
  routedCostPln:hasCompleteRouting?totalCost:null,
  routingStatus:hasCompleteRouting?'ROUTINGS_ESTIMATED':(occurrences?'PARTIAL':'NO_PARTS'),
  // ROUTINGS_ESTIMATED is NOT full welding/machining/assembly quote certification.
  fullQuoteVerified:false};
}

// Process-based welded assembly estimate. All inputs are explicit routing data;
// no unsupported inference from STEP contact or PDF weld symbols.
export function estimateWelding({joints=[],depositionKgHour=2.5,arcOnFraction=0.35,setupMin=0,ratePerHour=388,densityKgM3=7850}={}){
 for(const [k,v] of Object.entries({depositionKgHour,arcOnFraction,setupMin,ratePerHour,densityKgM3}))valid(v,k,k==='depositionKgHour'||k==='arcOnFraction'||k==='densityKgM3');
 if(arcOnFraction>1)throw new RangeError('arcOnFraction');
 const lines=joints.map((j,i)=>{
  const count=valid(j.count??1,'joint.count',true),lengthMm=valid(j.lengthMm,'joint.lengthMm');
  const throatMm=valid(j.throatMm,'joint.throatMm',true);
  const passes=valid(j.passes??1,'joint.passes',true);
  // Idealized equal-leg fillet cross-section: A = a^2. Passes affect routing,
  // not deposited cross-section: do not multiply weld mass by passes.
  const massKg=count*lengthMm*throatMm**2*1e-9*densityKgM3;
  valid(massKg,'weld.massKg');
  const arcMin=valid(massKg/depositionKgHour*60,'weld.arcMin');
  const processMin=valid(arcMin/arcOnFraction,'weld.processMin');
  return {index:i,count,lengthMm:count*lengthMm,massKg,arcMin,processMin,passes};
 });
 const weldLengthMm=valid(lines.reduce((s,x)=>s+x.lengthMm,0),'weld.lengthMm');
 const massKg=valid(lines.reduce((s,x)=>s+x.massKg,0),'weld.totalMassKg');
 const arcMin=valid(lines.reduce((s,x)=>s+x.arcMin,0),'weld.totalArcMin');
 const totalMin=valid(setupMin+lines.reduce((s,x)=>s+x.processMin,0),'weld.totalMin');
 return {lines,weldLengthMm,massKg,arcMin,totalMin,cost:valid(totalMin*ratePerHour/60,'weld.cost')};
}
export function estimateAssembly({operations=[],ratePerHour=388}={}){
 valid(ratePerHour,'ratePerHour');
 const lines=operations.map((op,i)=>{
  const count=valid(op.count??1,'operation.count');
  const minutesEach=valid(op.minutesEach,'operation.minutesEach');
  const totalMin=valid(count*minutesEach,'assembly.operation.totalMin');
  return {index:i,name:op.name??'Operation',count,minutesEach,totalMin};
 });
 const totalMin=valid(lines.reduce((s,x)=>s+x.totalMin,0),'assembly.totalMin');
 return {lines,totalMin,cost:valid(totalMin*ratePerHour/60,'assembly.cost')};
}
export function estimateFabrication({assembly,welding,cutting,cnc,finishing,ratePerHour=388}={}){
 valid(ratePerHour,'ratePerHour');
 const steps={assembly:assembly?estimateAssembly({...assembly,ratePerHour}):null,
  welding:welding?estimateWelding({...welding,ratePerHour}):null,
  cutting:cutting?estimateCut({...cutting,ratePerHour}):null,
  cnc:cnc?estimateCnc({...cnc,ratePerHour}):null,
  finishing:finishing?estimateAssembly({...finishing,ratePerHour}):null};
 const totalMin=valid(Object.values(steps).reduce((s,x)=>s+(x?.totalMin??0),0),'fabrication.totalMin');
 return {steps,totalMin,totalCost:valid(totalMin*ratePerHour/60,'fabrication.totalCost'),ratePerHour};
}
