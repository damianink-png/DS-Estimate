/**
 * Cutting coverage and evidence, one row per STEP body occurrence.
 *
 * Do not infer purchasing units from body count or geometry groups.
 * No quoted cut time (null) is different from an explicit manual zero.
 * This is a diagnostic report, NOT confirmation of complete manufacturing.
 */
export const CUTTING_MISSING_REASONS = Object.freeze({
 UNKNOWN_STOCK:'Nieustalony półfabrykat',
 AMBIGUOUS_SECTION:'Niepotwierdzony przekrój lub pole metalu',
 UNKNOWN_THICKNESS:'Nieustalona grubość',
 UNKNOWN_CUT_PATH:'Brak wiarygodnej długości konturu lub liczby przebić',
 BENT_BLANK_UNRESOLVED:'Brak potwierdzonego rozwinięcia blachy giętej',
 FUSED_ASSEMBLY:'Możliwa konstrukcja scalona; brak rozbicia technologicznego',
 INVALID_GEOMETRY:'Geometria uniemożliwia wiarygodny pomiar',
 UNSUPPORTED_MACHINE_RANGE:'Brak dostępnej maszyny w wymaganym zakresie',
 MATERIAL_TECHNOLOGY_UNKNOWN:'Brak potwierdzonych danych do doboru technologii',
 ANALYSIS_PARTIAL:'Analiza cięcia niekompletna lub przerwana'
});
const finiteNonnegative=n=>typeof n==='number'&&Number.isFinite(n)&&n>=0;
const known=n=>n!==null&&n!==undefined&&finiteNonnegative(n);
function stockHint(solid){
 const hint=solid?.stockHint??{};
 return hint.kind==='unknown'&&hint.rawStockCandidate?hint.rawStockCandidate:hint;
}
function classifyMissing(part,cut){
 const s=part.solid??{},hint=stockHint(s),kind=part.stockKind||hint.kind||'unknown';
 if(s.fusedAssembly===true||hint.reasonCode==='FUSED_ASSEMBLY')return 'FUSED_ASSEMBLY';
 if(s.geometryValid===false||hint.reasonCode==='INVALID_GEOMETRY')return 'INVALID_GEOMETRY';
 if(kind==='bent-plate'&&s.cuttingHint?.estimated)return 'BENT_BLANK_UNRESOLVED';
 if(!cut?.method){
  if((cut?.notes??[]).some(n=>/Maszyna wyłączona|zakres maszyny|brak dostępnej maszyny/i.test(n)))return 'UNSUPPORTED_MACHINE_RANGE';
  if((cut?.notes??[]).some(n=>/materiał|gatunek/i.test(n)))return 'MATERIAL_TECHNOLOGY_UNKNOWN';
  return 'UNKNOWN_STOCK';
 }
 if(cut.method==='saw')return kind==='unknown'?'UNKNOWN_STOCK':'AMBIGUOUS_SECTION';
 if(!finiteNonnegative(cut.thickness)||cut.thickness===0)return 'UNKNOWN_THICKNESS';
 if((cut?.notes??[]).some(n=>/zakres maszyny/i.test(n)))return 'UNSUPPORTED_MACHINE_RANGE';
 if((cut?.notes??[]).some(n=>/materiał|gatunek/i.test(n)))return 'MATERIAL_TECHNOLOGY_UNKNOWN';
 return 'UNKNOWN_CUT_PATH';
}
/**
 * @param {Array} parts - partsList result (one item per imported STEP solid)
 * @param {object} plan - planAutomaticCutting result
 */
export function auditCutting(parts,plan){
 if(!Array.isArray(parts))throw new TypeError('parts must be an array');
 const indexed=new Map();
 for(const cut of plan?.rows??[]){
  if(!cut?.id||indexed.has(cut.id))throw new Error('Duplicate or missing cutting operation ID');
  indexed.set(cut.id,cut);
 }
 const ids=new Set(),statusCounts={},missingReasonCounts={};
 let knownTimeMin=0,knownTimeOccurrences=0,unresolvedOwnOccurrences=0,ownCutOccurrences=0;
 const rows=parts.map((part,index)=>{
  if(!part||!part.id||ids.has(part.id))throw new Error('Duplicate or missing STEP occurrence ID');
  ids.add(part.id);
  const s=part.solid??{},h=stockHint(s),cut=indexed.get(part.id);
  const route=part.route??'make';
  let status,reason=null;
  if(route==='purchase')status='PURCHASED_NO_INTERNAL_CUT';
  else if(route==='cooperate')status='SUBCONTRACTED';
  else if(route!=='make')throw new RangeError('Invalid manufacturing route: '+route);
  else {
   ownCutOccurrences++;
   if(plan?.error||!cut){status='PENDING';reason='ANALYSIS_PARTIAL';}
   else if(known(cut.minutes)){status='CALCULATED';knownTimeOccurrences++;knownTimeMin+=cut.minutes;}
   else{status='PENDING';reason=classifyMissing(part,cut);}
   if(status==='PENDING')unresolvedOwnOccurrences++;
  }
  statusCounts[status]=(statusCounts[status]??0)+1;
  if(reason)missingReasonCounts[reason]=(missingReasonCounts[reason]??0)+1;
  return {
   index,occurrenceId:part.id,productOccurrenceKey:s.productOccurrenceKey??null,
   productDefinitionKey:s.productDefinitionKey??null,bodyIndex:s.bodyIndex??null,
   bodyCount:s.bodyCount??null,name:part.name??s.name??null,
   nameSource:s.nameSource??null,geometryGroupId:part.geometryKey??s.verifiedShapeKey??null,
   route,status,reasonCode:reason,reasonText:reason?CUTTING_MISSING_REASONS[reason]:null,
   stockKind:part.stockKind||h.kind||'unknown',
   stockConfidence:h.confidence??null,stockEvidence:h.source??null,
   grade:part.grade??'',densityKgM3:part.density??null,
   dimensionsMm:part.dims??s.bboxMm??null,volumeMm3:s.volumeMm3??null,
   netMassKg:part.massKg??null,stockMassKg:part.stockMassKg??null,
   thicknessMm:cut?.thickness??h.thicknessMm??null,
   sectionAreaMm2:cut?.sectionArea??h.sectionAreaMm2??null,
   contourMm:cut?.contour??null,pierces:cut?.pierces??null,
   method:cut?.method??null,automaticMinutes:status==='CALCULATED'?cut.minutes:null,
   notes:cut?.notes??[],analysisError:plan?.error??null
  };
 });
 for(const id of indexed.keys())if(!ids.has(id))throw new Error('Cutting row without STEP occurrence: '+id);
 if(!Number.isFinite(knownTimeMin))throw new RangeError('Cutting time overflow');
 return {
  schemaVersion:1,scope:'STEP body occurrences; purchasing units not confirmed',
  totalOccurrences:rows.length,ownCutOccurrences,knownTimeOccurrences,
  unresolvedOwnOccurrences,knownTimeMin,
  ownCutCoveragePct:ownCutOccurrences===0?null:Number((100*knownTimeOccurrences/ownCutOccurrences).toFixed(1)),
  occurrenceCoveragePct:rows.length===0?null:Number((100*knownTimeOccurrences/rows.length).toFixed(1)),
  complete:rows.length>0&&unresolvedOwnOccurrences===0&&!plan?.error,
  statusCounts,missingReasonCounts,rows,
  limitations:[
   'A manufacturing route or geometry group is not evidence of a purchasing BOM unit.',
   'Unknown cutting time is not zero; known time is only a subtotal of estimated operations.',
   'STEP geometry alone cannot certify welding, tolerances, cutting order, or full fabrication.'
  ]
 };
}
