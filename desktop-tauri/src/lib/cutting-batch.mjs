/**
 * Batch-aware scheduling for one project. Geometry groups do NOT each require a
 * fresh laser/plasma/oxy setup. A setup is paid once per machine, material and
 * nominal thickness (0.1 mm), unless the operator changes the routing.
 *
 * Does not infer nesting, NC moves, saw stock cuts or unknown cut lengths.
 * It operates on the existing B-Rep cutting hints; unknown stays unknown.
 */
import {recommendCutting, SAMPLE_MACHINE_SETTINGS} from './cutting-plan.mjs';

const valid=(n)=>typeof n==='number' && Number.isFinite(n) && n>=0;
const thicknessBucket=(n)=>Math.round(n*10)/10;

export function planCuttingBatches({
  groups, material='unknown', machines=SAMPLE_MACHINE_SETTINGS,
  overrides={}
}={}){
 if(!Array.isArray(groups))throw new TypeError('groups must be an array');
 const seen=new Set(), charged=new Set();
 let knownTimeOccurrences=0,pendingOccurrences=0,pricedOccurrences=0,setupMinutes=0,runMinutes=0;
 let totalCostPln=0,hasUnpriced=false;
 const output=[];
 for(const group of groups){
  if(!group || typeof group.key!=='string' || !group.key || seen.has(group.key))
   throw new Error('Missing or duplicate geometry group key');
  seen.add(group.key);
  if(!Number.isSafeInteger(group.quantity) || group.quantity<1)throw new RangeError('quantity');
  const manual=overrides[group.key]??{};
  const manuallyAccepted=manual.minutes!==null && manual.minutes!==undefined;
  if(manuallyAccepted && !valid(manual.minutes))throw new RangeError('manual minutes');
  // Per-part operation is independent from the grouping of geometry duplicates.
  let prediction;
  try {
   prediction=recommendCutting({solid:group.solid,quantity:group.quantity,
    material,machines,overrideMethod:manual.method??null});
  } catch(error) {
   // A machine may be disabled after a user selected it. Do not crash the
   // entire quote or silently switch the manually selected technology.
   if(!manual.method || !(error instanceof RangeError))throw error;
   const fallback=recommendCutting({solid:group.solid,quantity:group.quantity,
    material,machines});
   prediction={...fallback,method:null,ratePlnHour:null,setupMin:null,
    perPieceMin:null,calculatedMin:null,acceptedMin:null,costPln:null,
    confidence:'requires-review',warnings:[...fallback.warnings,
     'Wybrana ręcznie metoda jest niedostępna — wybierz technologię ponownie']};
  }
  const canCalculate=prediction.perPieceMin!==null && prediction.perPieceMin!==undefined;
  const groupSetup=canCalculate ? (prediction.setupMin??0) : 0;
  const thickness=prediction.hint.thicknessMm;
  const nominalThickness=Number.isFinite(thickness)?thicknessBucket(thickness):null;
  const batchId=canCalculate && nominalThickness!==null ?
   [prediction.method,material,nominalThickness].join('|'):null;
  // Do not create setup for an unknown/unpriced operation.
  // Manual complete time has priority and does not consume the automatic setup
  // for other groups in the same machine/material batch.
  let chargedSetup=0;
  if(!manuallyAccepted && batchId && !charged.has(batchId)){
   charged.add(batchId);
   chargedSetup=groupSetup;
  }
  const calculatedMin=canCalculate ?
   Number((chargedSetup+prediction.perPieceMin*group.quantity).toFixed(9)):null;
  const acceptedMin=manuallyAccepted?manual.minutes:calculatedMin;
  const rate=prediction.ratePlnHour;
  const costPln=acceptedMin===null||rate===null?null:acceptedMin*rate/60;
  if(acceptedMin===null)pendingOccurrences+=group.quantity;
  else{
   knownTimeOccurrences+=group.quantity;
   if(costPln!==null){
    totalCostPln+=costPln;
    pricedOccurrences+=group.quantity;
   } else hasUnpriced=true;
  }
  if(calculatedMin!==null){setupMinutes+=chargedSetup;runMinutes+=prediction.perPieceMin*group.quantity;}
  output.push({...group,cut:{...prediction,batchId,nominalThicknessMm:nominalThickness,
   setupAllocatedMin:chargedSetup,calculatedMin,acceptedMin,costPln,
   confidence:manuallyAccepted?'manual':prediction.confidence,
   warnings:manuallyAccepted?[...prediction.warnings,'Czas zmieniony ręcznie']:prediction.warnings}});
 }
 const occurrences=knownTimeOccurrences+pendingOccurrences;
 const complete=occurrences>0 && pendingOccurrences===0 && !hasUnpriced;
 return {rows:output,knownTimeOccurrences,pendingOccurrences,pricedOccurrences,
  setupMinutes,runMinutes,
  // These are explicitly PARTIAL subtotals when any occurrence has unknown time/cost.
  calculatedTimeMin:setupMinutes+runMinutes,
  knownCostPln:totalCostPln,
  acceptedCostPln:complete?totalCostPln:null,
  batchCount:charged.size,
  coveragePct:occurrences>0?Number((knownTimeOccurrences/occurrences*100).toFixed(1)):0,
  costCoveragePct:occurrences>0?Number((pricedOccurrences/occurrences*100).toFixed(1)):0,
  completeness:complete?'CUTTING_ESTIMATED':(occurrences?'PARTIAL':'NO_PARTS'),
  complete};
}
