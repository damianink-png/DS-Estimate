import test from 'node:test';
import assert from 'node:assert/strict';
import {auditCutting} from '../src/lib/cutting-audit.mjs';
import {planAutomaticCutting} from '../src/lib/automatic-cutting.mjs';
import {evaluateModules} from '../src/lib/modular-quote.mjs';

function solid(id,kind='plate-candidate'){
 return {id,name:'Detal '+id,verifiedShapeKey:'group-'+id,volumeMm3:50000,
  bboxMm:[100,50,10],stockHint:{kind,thicknessMm:10},
  cuttingHint:{kind:'plate-outline',thicknessMm:10,contourMm:300,pierces:1}};
}
function part(id,route='make',overrides={}){
 return {id,name:'Detal '+id,route,grade:'S355J2',density:7850,dims:[100,50,10],
  massKg:0.3925,stockMassKg:0.3925,geometryKey:'group-'+id,cutMethod:'auto',
  cutCount:2,sawAngle:0,solid:solid(id),...overrides};
}
test('audits every STEP occurrence including supplier and cooperation bodies',()=>{
 const parts=[part('a'),part('b','purchase'),part('c','cooperate'),
  part('d','make',{solid:{...solid('d'),cuttingHint:null}})];
 const audit=auditCutting(parts,planAutomaticCutting(parts));
 assert.equal(audit.totalOccurrences,4);
 assert.equal(audit.ownCutOccurrences,2);
 assert.equal(audit.knownTimeOccurrences,1);
 assert.equal(audit.unresolvedOwnOccurrences,1);
 assert.equal(audit.ownCutCoveragePct,50);
 assert.equal(audit.occurrenceCoveragePct,25);
 assert.deepEqual(audit.statusCounts,{CALCULATED:1,PURCHASED_NO_INTERNAL_CUT:1,SUBCONTRACTED:1,PENDING:1});
 assert.equal(audit.rows[3].reasonCode,'UNKNOWN_CUT_PATH');
 assert.equal(audit.complete,false);
});
test('error in planner cannot become a 0 PLN no-own-cutting quote',()=>{
 const parts=[part('a')],failure={rows:[],batches:[],missing:0,error:'CAD cut failed'};
 const audit=auditCutting(parts,failure);
 assert.equal(audit.rows[0].reasonCode,'ANALYSIS_PARTIAL');
 assert.equal(audit.knownTimeOccurrences,0);
 const inventory={solids:parts.map(p=>p.solid),groups:[],totalMassKg:.3925};
 const cutting=evaluateModules({inventory,cuttingPlan:failure}).modules.find(m=>m.id==='cutting');
 assert.equal(cutting.rows.length,1);
 assert.equal(cutting.rows[0].value,null);
 assert.equal(cutting.status,'missing');
 assert.equal(cutting.knownCostPln,0);
});
test('unknown profile area is an unresolved section, not a free saw cut',()=>{
 const tube=part('tube','make',{dims:[1000,40,40],solid:{
  ...solid('tube','square-hollow'),bboxMm:[1000,40,40],
  cuttingHint:null,stockHint:{kind:'square-hollow',lengthMm:1000,widthMm:40,heightMm:40}}});
 const a=auditCutting([tube],planAutomaticCutting([tube]));
 assert.equal(a.rows[0].reasonCode,'AMBIGUOUS_SECTION');
 assert.equal(a.knownTimeMin,0);
 assert.equal(a.complete,false);
});
test('one status per occurrence and identity retained across duplicate geometry',()=>{
 const rows=Array.from({length:251},(_,i)=>part('occ-'+i,'make',{geometryKey:'same',
  solid:{...solid('occ-'+i),verifiedShapeKey:'same',productOccurrenceKey:'prod-'+Math.floor(i/5),
   cuttingHint:i<89?solid('occ-'+i).cuttingHint:null}}));
 const audit=auditCutting(rows,planAutomaticCutting(rows));
 assert.equal(audit.totalOccurrences,251);
 assert.equal(audit.knownTimeOccurrences,89);
 assert.equal(audit.unresolvedOwnOccurrences,162);
 assert.equal(new Set(audit.rows.map(x=>x.occurrenceId)).size,251);
 assert.equal(audit.rows[0].geometryGroupId,'same');
 assert.equal(audit.rows[1].productOccurrenceKey,'prod-0');
 assert.throws(()=>auditCutting([rows[0],rows[0]],{rows:[]}),/Duplicate/);
});
test('explicit zero is classified as known, missing null remains pending',()=>{
 const p=part('zero');
 const a=auditCutting([p],{rows:[{id:'zero',method:'laser',minutes:0}]});
 assert.equal(a.knownTimeOccurrences,1);
 assert.equal(a.complete,true);
 const b=auditCutting([p],{rows:[{id:'zero',method:'laser',minutes:null}]});
 assert.equal(b.knownTimeOccurrences,0);
 assert.equal(b.rows[0].reasonCode,'UNKNOWN_THICKNESS'); // The synthetic row supplies no measured thickness.
});

test('native unknown stock is never mislabeled as missing material because 7850 kg/m3 assumed steel',()=>{
 const nativeReasons=[
  ['Not an axis-aligned elongated extrusion; plate or custom stock needs BOM','NOT_ELONGATED_OR_NONAXIAL'],
  ['Open, complex or unsupported cross-section','UNSUPPORTED_SECTION'],
  ['3-D volume inconsistent with constant stock section (possible pocket, notch or end machining)','STOCK_VOLUME_MISMATCH'],
  ['Section changes along finished part','VARIABLE_SECTION']
 ];
 const parts=nativeReasons.map(([reason],i)=>part('native-'+i,'make',{
  grade:'',density:7850,
  solid:{...solid('native-'+i,'unknown'),stockHint:{kind:'unknown',reason},cuttingHint:null}
 }));
 const planned=planAutomaticCutting(parts);
 assert.ok(planned.rows.every(row=>row.method===null));
 assert.ok(planned.rows.every(row=>row.notes.some(note=>/Przyjęto stal/.test(note))));
 const audit=auditCutting(parts,planned);
 assert.deepEqual(audit.missingReasonCounts,{UNKNOWN_STOCK:4});
 assert.equal(audit.unresolvedOwnOccurrences,4);
 assert.deepEqual(audit.stockFailureCounts,{
  NOT_ELONGATED_OR_NONAXIAL:1,UNSUPPORTED_SECTION:1,STOCK_VOLUME_MISMATCH:1,VARIABLE_SECTION:1
 });
 assert.deepEqual(audit.rows.map(r=>r.stockFailureCode),nativeReasons.map(x=>x[1]));
 assert.deepEqual(audit.rows.map(r=>r.nativeStockReason),nativeReasons.map(x=>x[0]));
});
test('machine unavailable stays distinct from missing geometry for recognized stock',()=>{
 const p=part('plate-disabled');
 const unavailable=planAutomaticCutting([p],{machines:{
  laser:{enabled:false},plasma:{enabled:false},oxy:{enabled:false},saw:{enabled:false}
 }});
 const audit=auditCutting([p],unavailable);
 assert.equal(audit.rows[0].reasonCode,'UNSUPPORTED_MACHINE_RANGE');
 assert.equal(audit.rows[0].stockFailureCode,null);
});

test('special finished section has explicit missing stock reason',()=>{
 const part={id:'poly',name:'Detal',route:'make',solid:{stockHint:{kind:'polygon-bar'}}};
 const audit=auditCutting([part],{rows:[{id:'poly',method:null,minutes:null,notes:[]}]});
 assert.equal(audit.rows[0].reasonCode,'SPECIAL_SECTION_STOCK_UNKNOWN');
 assert.equal(audit.knownTimeOccurrences,0);
});
