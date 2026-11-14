/**
 * Companion to the pinned historical public comparison. This uses EXACTLY
 * the per-part cutting implementation used by ModuleEstimate.svelte:
 * partsList -> planAutomaticCutting -> auditCutting.
 *
 * IMPORTANT: no changes to the legacy reference baseline here. The old
 * grouped quick-cut planner and the current desktop path must be compared
 * rather than accidentally presented as identical algorithms.
 *
 * Run after public_fabrication_benchmark.py:
 *   node tests/public_cutting_occurrence_audit.mjs public_fabrication_output
 */
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {validateStepBom} from '../src/lib/inventory-validate.mjs';
import {partsList} from '../src/lib/parts.mjs';
import {planAutomaticCutting} from '../src/lib/automatic-cutting.mjs';
import {auditCutting} from '../src/lib/cutting-audit.mjs';
import {csvCell} from '../src/lib/project-files.mjs';

const root=resolve(process.argv[2]||'public_fabrication_output');
const cases=JSON.parse(readFileSync(join(root,'public_cases.json'),'utf8'));
const output=[],csvRows=[['Projekt','Wystąpienie STEP','Produkt STEP','Grupa geometrii',
 'Nazwa STEP','Droga realizacji','Półfabrykat','Stan','Kod przyczyny',
 'Opis przyczyny','Kod przyczyny CAD','Opis z silnika CAD','Technologia','Czas automatyczny [min]','Gatunek',
 'Grubość [mm]','Pole przekroju [mm2]','Kontur [mm]','Przebicia']];
for(const c of cases){
 const path=join(root,c.id,'ds_estimate_inventory.json');
 if(c.status!=='ENGINE_OK'||!existsSync(path))throw new Error('Missing compiled STEP inventory '+c.id);
 const inventory=validateStepBom(JSON.parse(readFileSync(path,'utf8')));
 const parts=partsList(inventory);
 const plan=planAutomaticCutting(parts);
 const audit=auditCutting(parts,plan);
 if(audit.totalOccurrences!==inventory.count ||
    audit.knownTimeOccurrences+audit.unresolvedOwnOccurrences+
    (audit.statusCounts.PURCHASED_NO_INTERNAL_CUT??0)+
    (audit.statusCounts.SUBCONTRACTED??0)!==inventory.count)
  throw new Error('Cutting audit lost STEP occurrences in '+c.id);
 const item={project:c.id,engineVersion:inventory.engineVersion,
  sourceStep:c.files?.find?.(f=>/\.st(e)?p$/i.test(f.path??''))?.path??null,
  statusCounts:audit.statusCounts,missingReasonCounts:audit.missingReasonCounts,
  stockFailureCounts:audit.stockFailureCounts,
  totalOccurrences:audit.totalOccurrences,ownCutOccurrences:audit.ownCutOccurrences,
  knownTimeOccurrences:audit.knownTimeOccurrences,
  unresolvedOwnOccurrences:audit.unresolvedOwnOccurrences,
  ownCutCoveragePct:audit.ownCutCoveragePct,
  knownTimeMin:audit.knownTimeMin,
  warnings:[
   'This is the desktop per-part planner, not the historical grouped QuickEstimate benchmark.',
   'Default 7850 kg/m3 and assumed steel are NOT a documented material grade.',
   'A calculated time does NOT establish the complete manufacturing route or full quotation.'
  ]};
 output.push(item);
 for(const r of audit.rows)csvRows.push([c.id,r.occurrenceId,r.productOccurrenceKey,
  r.geometryGroupId,r.name,r.route,r.stockKind,r.status,r.reasonCode,
  r.reasonText,r.stockFailureCode,r.nativeStockReason,r.method,r.automaticMinutes,r.grade,r.thicknessMm,
  r.sectionAreaMm2,r.contourMm,r.pierces]);
 console.log('DESKTOP_CUTTING_OCCURRENCE_AUDIT',JSON.stringify({
  project:c.id,solids:inventory.count,known:audit.knownTimeOccurrences,
  pending:audit.unresolvedOwnOccurrences,reasons:audit.missingReasonCounts,
  stockFailures:audit.stockFailureCounts,
  note:'proposed methods and known partial time only'
 }));
}
writeFileSync(join(root,'cutting_occurrence_audit.json'),JSON.stringify(output,null,2),'utf8');
writeFileSync(join(root,'cutting_occurrence_audit.csv'),
 '\uFEFF'+csvRows.map(row=>row.map(csvCell).join(';')).join('\r\n')+'\r\n','utf8');
