/**
 * Run ACTUAL DS Estimate production inventory + cutting-plan.mjs unchanged.
 * Independent manual work-time ranges are loaded only AFTER all DS Estimate
 * predictions are finalized. Never inject manual times into auto output.
 *
 * CLI: node tests/public_fabrication_compare.mjs public_fabrication_output
 */
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { recommendCutting } from '../src/lib/cutting-plan.mjs';
import { validateStepBom } from '../src/lib/inventory-validate.mjs';

const root=resolve(process.argv[2]||'public_fabrication_output');
const source=JSON.parse(readFileSync(resolve('tests/public_fabrication_projects.json'),'utf8'));
const cases=JSON.parse(readFileSync(join(root,'public_cases.json'),'utf8'));
const csv=(v)=>'"'+String(v??'').replaceAll('"','""')+'"';
const human=(v)=>typeof v==='number'?v.toFixed(2):'brak';
const rows=[['project','part_key','count','kg_each','hint','method','auto_time_h','status','warnings']];
const results=[];
for(const c of cases){
 const cfg=source.cases.find(x=>x.id===c.id);
 const inventoryFile=join(root,c.id,'ds_estimate_inventory.json');
 const r={id:c.id,name:c.name,status:c.status,sourceDocumentation:c.pdf?.length||0,
  scope:c.scope,manualReference:cfg.manual,engine:c.engine??null,errors:[...c.errors],
  cut:{methodOccurrences:{},rows:0,proposedOccurrences:0,knownTimeOccurrences:0,
      calculatedTimeH:0,pendingGroupCount:0,pendingOccurrences:0},
  total:{manualLowH:null,manualHighH:null,autoFullH:null},
  limitation:'All non-cutting operations remain unknown in current DS Estimate quick workflow.'};
 if(existsSync(inventoryFile)&&c.status==='ENGINE_OK'){
  try{
   const data=validateStepBom(JSON.parse(readFileSync(inventoryFile,'utf8')));
   // Deliberately no manual time inputs or BOM-derived grade here.
   // Mirror QuickEstimate's actual PDF text -> material heuristic and default.
   const pdfTexts=(c.pdf??[]).slice(0,15).map(p=>{
    const textFile=join(root,c.id,p.path.split('/').pop().replace(/\\.pdf$/i,'.txt'));
    return existsSync(textFile)?readFileSync(textFile,'utf8').slice(0,30000):'';
   }).join('\\n');
   const grade=pdfTexts.match(/\\b(?:S355(?:J2(?:\\+N)?|J0|JR)?|S235(?:JR)?|S690QL|S960QL)\\b/i);
   const material=grade?(grade[0].toUpperCase().startsWith('S355')?'S355':
      grade[0].toUpperCase().startsWith('S235')?'S235':grade[0].toUpperCase()):'S355';
   r.cut.materialAssumption=material;
   r.cut.materialSource=grade?'PDF text match (unverified)':'DS Estimate default S355 (unverified)';
   for(const group of data.groups){
    const solid=data.solids.find(s=>s.verifiedShapeKey===group.geometryId);
    const prediction=recommendCutting({solid,quantity:group.quantity,material});
    r.cut.rows++;
    if(prediction.method){
     r.cut.proposedOccurrences+=group.quantity;
     r.cut.methodOccurrences[prediction.method]=(r.cut.methodOccurrences[prediction.method]||0)+group.quantity;
    }
    if(prediction.calculatedMin==null){
     r.cut.pendingGroupCount++;r.cut.pendingOccurrences+=group.quantity;
    }else{
     r.cut.knownTimeOccurrences+=group.quantity;
     r.cut.calculatedTimeH+=prediction.calculatedMin/60;
    }
    rows.push([c.id,group.geometryId,group.quantity,group.massKg,
      prediction.hint.kind,prediction.method||'brak',
      prediction.calculatedMin==null?'':(prediction.calculatedMin/60).toFixed(4),
      prediction.calculatedMin==null?'NIEUSTALONY':'CZAS SZACUNKOWY',
      prediction.warnings.join(' | ')]);
   }
   // Even if every cut had a time, this is NOT a complete quote; other
   // operation times have no credible automatic evidence yet.
   r.cut.calculatedTimeH=Number(r.cut.calculatedTimeH.toFixed(5));
   r.cut.coverage= data.count?Number((r.cut.knownTimeOccurrences/data.count*100).toFixed(1)):0;
  }catch(e){r.errors.push('QUOTE_INPUT_FAIL '+String(e));r.status='QUOTE_INPUT_FAIL';}
 }
 const ops=cfg.manual.operations||[];
 if(ops.length){
  const low=ops.reduce((s,x)=>s+x.low,0);
  const high=ops.reduce((s,x)=>s+x.high,0);
  r.total.manualLowH=low;r.total.manualHighH=high;
  const cutReference=ops.find(x=>x.id==='cutting');
  if(cutReference)r.cut.manualIndependentRangeH=[cutReference.low,cutReference.high];
  r.total.autoFullH=null;
 }
 results.push(r);
 console.log('INDEPENDENT_TIME_COMPARISON',JSON.stringify({
  id:r.id,status:r.status,solids:r.engine?.solids,groups:r.engine?.groups,
  kg:r.engine?.massKgAssumed7850,
  cutCoveragePct:r.cut.coverage??0,autoCutHoursKnownOnly:r.cut.calculatedTimeH,
  independentCuttingRangeH:r.cut.manualIndependentRangeH??null,
  independentTotalRangeH:[r.total.manualLowH,r.total.manualHighH],
  completeAutomaticQuote:false,missingCutOccurrences:r.cut.pendingOccurrences,
  warnings:r.errors.slice(0,3)
 }));
}
writeFileSync(join(root,'comparison.json'),JSON.stringify(results,null,2),'utf8');
writeFileSync(join(root,'cutting_rows.csv'),rows.map(x=>x.map(csv).join(';')).join('\n')+'\n','utf8');
const md=[
 '# DS Estimate — real public projects, independent manual time ranges',
 '',
 'The SOURCE datasets were created and published by their respective upstream authors, not generated for this benchmark.',
 'The independent reference is an engineering PRELIMINARY ESTIMATE (ranges), NOT measured factory time or a certified quote.',
 'Program results are taken from the actual compiled DS Estimate STEP inventory and unchanged DS Estimate cutting-plan.mjs.',
 'A missing calculation is **not** converted to zero hours. All material rates are example/default and not a cost comparison.',
 '',
 '| Project | STEP solids | STEP groups | Mass at 7850 kg/m³* | DS Estimate automatic cut [h]** | Cut coverage | Independent cutting [h] | Independent entire scope [h] |',
 '|---|---:|---:|---:|---:|---:|---:|---:|',
 ...results.map(r=>`| ${r.name} | ${r.engine?.solids??'ERROR'} | ${r.engine?.groups??'—'} | ${human(r.engine?.massKgAssumed7850)} | ${human(r.cut.calculatedTimeH)} | ${r.cut.coverage??0}% | ${r.cut.manualIndependentRangeH?.join('–')??'insufficient documentation'} | ${r.total.manualLowH==null?'not assessable':r.total.manualLowH+'–'+r.total.manualHighH} |`),
 '',
 '*The CAD engine uses a single steel density for all solids. For mixed-material assemblies, that is not an actual physical total mass.',
 '**This is the sum of only operations for which DS Estimate generated a number. It is NOT a complete cutting time; compare coverage before interpreting it.',
 '',
 '## Machine comparison limitations',
 '- Current application does not calculate automatically welding, fit-up, machining and inspection hours from an uploaded assembly: fields remain unestablished.',
 '- A welded frame STEP is often a fused solid or contains mixed materials and purchased parts. Raw count of STEP solids does not imply a valid fabrication BOM.',
 '- Drawings and build instructions are read as evidence but do not automatically establish weld lengths, stock cuts, machine capabilities, or elapsed time.',
 '- Independent times in the source manifest are *manually estimated bands* with detailed assumptions; the band is not supplied to the program.',
 '',
 '## Cases and source snapshots',
 ...results.flatMap(r=>[
  `### ${r.name}`,
  `- Source: https://github.com/${r.sourceDocumentation?cases.find(c=>c.id===r.id)?.repo:''}; commit ${cases.find(c=>c.id===r.id)?.revision}`,
  `- Status: **${r.status}**. ${r.errors.join('; ')||'No errors.'}`,
  `- Source package: ${r.scope}`,
  `- Manual methodology: ${r.manualReference.basis}`,
  ...r.manualReference.operations.map(x=>`  - ${x.id}: ${x.low}–${x.high} h. ${x.assumption}`),
  ''
 ])
];
writeFileSync(join(root,'COMPARISON.md'),md.join('\n'),'utf8');
if(results.filter(x=>x.status==='ENGINE_OK').length<2)process.exitCode=1;
