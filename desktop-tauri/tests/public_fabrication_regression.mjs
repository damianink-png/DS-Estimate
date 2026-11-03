/**
 * Pinned public CAD regression guard. The four upstream STEP/PDF/BOM files
 * are fixed to immutable commits in public_fabrication_projects.json.
 * Changing their grouping, total volume/mass or priced coverage must be an
 * EXPLICIT reviewed change, not a hidden "optimization" regression.
 *
 * This does not certify a complete fabrication quotation. Runtime is reported
 * but deliberately not gated: hosted Windows runners have variable speed.
 */
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

export const PINNED_BASELINE = Object.freeze({
 'portal-frame': {solids:15,groups:3,massKg:18045.244066,cutCoverage:0,knownCutHours:0},
 'stepgen-frame': {solids:1,groups:1,massKg:24.837464,cutCoverage:0,knownCutHours:0},
 earthpress: {solids:251,groups:97,massKg:333.793279,cutCoverage:35.5,knownCutHours:4.57144},
 // Revert unsafe 110 baseline: independent two-way Cut could not prove
 // occurrence 247 identical to 267 (run 41566796174).
 dockhub: {solids:541,groups:111,massKg:4056.864258,cutCoverage:19.4,knownCutHours:4.69192}
});

export function checkPinnedPublicRegression(results, baseline=PINNED_BASELINE){
 const errors=[];
 if(!Array.isArray(results))return ['Missing comparison.json result array'];
 const seen=new Set();
 for(const row of results){
  const id=row?.id;
  if(!Object.hasOwn(baseline,id)){errors.push('Unknown project '+String(id));continue;}
  if(seen.has(id)){errors.push('Duplicate project '+id);continue;}
  seen.add(id);
  const expected=baseline[id];
  if(row.status!=='ENGINE_OK')errors.push(id+': CAD import/quote input not OK');
  if(row.engine?.solids!==expected.solids)errors.push(id+': STEP solid count changed');
  if(row.engine?.groups!==expected.groups)errors.push(id+': verified grouping changed from '+expected.groups+' to '+row.engine?.groups);
  const mass=row.engine?.massKgAssumed7850;
  if(!Number.isFinite(mass)||Math.abs(mass-expected.massKg)>Math.max(0.001,expected.massKg*1e-6))
   errors.push(id+': steel-equivalent STEP mass changed');
  if(row.cut?.coverage!==expected.cutCoverage)errors.push(id+': calculated cut coverage changed');
  const hours=row.cut?.calculatedTimeH;
  if(!Number.isFinite(hours)||Math.abs(hours-expected.knownCutHours)>0.0001)
   errors.push(id+': calculated partial cutting hours changed');
  if(row.total?.autoFullH!==null)errors.push(id+': partial cutting wrongly labelled as full quote');
 }
 for(const id of Object.keys(baseline))if(!seen.has(id))errors.push('Missing project '+id);
 return errors;
}

if(process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const input=resolve(process.argv[2]||'public_fabrication_output/comparison.json');
 const results=JSON.parse(readFileSync(input,'utf8'));
 const errors=checkPinnedPublicRegression(results);
 if(errors.length){
  console.error('PUBLIC_PINNED_REGRESSION_FAIL',JSON.stringify(errors));
  process.exitCode=1;
 }else{
  console.log('PUBLIC_PINNED_REGRESSION_PASS: four source snapshots unchanged; masses, verified groups, partial cut coverage and hours stable. Full quote remains UNAVAILABLE.');
 }
}
