import test from 'node:test';
import assert from 'node:assert/strict';
import {planCuttingBatches} from '../src/lib/cutting-batch.mjs';

const plate=(thickness,contour=300,pierces=1)=>({
 volumeMm3:600000*thickness,bboxMm:[1000,600,thickness],
 cuttingHint:{kind:'plate-outline',thicknessMm:thickness,contourMm:contour,pierces}
});
const group=(key,thickness,quantity=1,contour=300)=>({key,solid:plate(thickness,contour),quantity});

test('laser setup is charged ONCE for a batch of same steel and thickness',()=>{
 const result=planCuttingBatches({material:'S355',groups:[group('a',10,3),group('b',10,4),group('c',10,2)]});
 assert.equal(result.batchCount,1);
 assert.equal(result.setupMinutes,15);
 const unit=300/1400+3/60;
 assert.ok(Math.abs(result.calculatedTimeMin-(15+9*unit))<1e-9);
 assert.deepEqual(result.rows.map(r=>r.cut.setupAllocatedMin),[15,0,0]);
 assert.equal(result.coveragePct,100);
 assert.equal(result.complete,true);
});

test('different machines, nominal thickness and materials require distinct setups',()=>{
 const mix=planCuttingBatches({material:'S355',groups:[group('laser1',5),group('laser2',10),
  group('plasma1',20),group('plasma2',20),group('oxy',60)]});
 assert.equal(mix.batchCount,4);
 assert.equal(mix.setupMinutes,15+15+18+25);
 assert.equal(mix.rows[3].cut.setupAllocatedMin,0);
});

test('EarthPress-like 72 distinct plate geometries no longer produce 72 setup charges',()=>{
 const groups=[
  ...Array.from({length:57},(_,i)=>group('laser-'+i,10,1)),
  ...Array.from({length:13},(_,i)=>group('plasma-'+i,20,1)),
  ...Array.from({length:2},(_,i)=>group('oxy-'+i,60,1))
 ];
 const r=planCuttingBatches({groups,material:'S355'});
 assert.equal(r.batchCount,3);
 assert.equal(r.setupMinutes,15+18+25);
 assert.equal(r.knownTimeOccurrences,72);
 const oldSetup=57*15+13*18+2*25;
 assert.ok(r.setupMinutes<oldSetup/10);
 assert.equal(r.pendingOccurrences,0);
});

test('manual time remains editable, and the next automatically quoted part gets the shared setup',()=>{
 const r=planCuttingBatches({material:'S355',groups:[group('first',10),group('second',10)],
  overrides:{first:{minutes:90}}});
 assert.equal(r.rows[0].cut.acceptedMin,90);
 assert.equal(r.rows[0].cut.confidence,'manual');
 assert.equal(r.rows[1].cut.setupAllocatedMin,15);
 assert.equal(r.setupMinutes,15);
 assert.equal(r.batchCount,1);
});

test('unknown saw machining time remains unknown; no fake zero from partial coverage',()=>{
 const r=planCuttingBatches({material:'S355',groups:[
  group('plate',10,2),
  {key:'tube',quantity:5,solid:{bboxMm:[1000,40,40],volumeMm3:50000}}
 ]});
 assert.equal(r.knownTimeOccurrences,2);
 assert.equal(r.pendingOccurrences,5);
 assert.equal(r.rows[1].cut.method,'saw');
 assert.equal(r.rows[1].cut.calculatedMin,null);
 assert.equal(r.coveragePct,28.6);
 assert.equal(r.complete,false);
 assert.throws(()=>planCuttingBatches({material:'S355',groups:[group('a',10),group('a',10)]}),/duplicate/);
});


test('disabling a manually chosen machine never crashes quote or silently changes its route',()=>{
 const machines={
  laser:{enabled:false,maxThicknessMm:15,feedMmMin:1400,pierceSec:3,setupMin:15,ratePlnHour:388},
  plasma:{enabled:true,maxThicknessMm:35,feedMmMin:900,pierceSec:5,setupMin:18,ratePlnHour:388}
 };
 const result=planCuttingBatches({material:'S355',machines,groups:[group('part',10)],
  overrides:{part:{method:'laser'}}});
 assert.equal(result.rows[0].cut.method,null);
 assert.equal(result.rows[0].cut.acceptedMin,null);
 assert.equal(result.rows[0].cut.costPln,null);
 assert.equal(result.pendingOccurrences,1);
 assert.equal(result.complete,false);
 assert.ok(result.rows[0].cut.warnings.some(w=>w.includes('niedostępna')));
});

test('EarthPress-like partial cutting evidence exposes only a known-cost subtotal',()=>{
 const r=planCuttingBatches({material:'S355',groups:[
  group('known-plate',10,2),
  {key:'unknown-profile',quantity:5,solid:{bboxMm:[1000,40,40],volumeMm3:50000}}
 ]});
 assert.equal(r.knownTimeOccurrences,2);
 assert.equal(r.pendingOccurrences,5);
 assert.equal(r.pricedOccurrences,2);
 assert.equal(r.coveragePct,28.6);
 assert.equal(r.costCoveragePct,28.6);
 assert.equal(r.complete,false);
 assert.equal(r.completeness,'PARTIAL');
 assert.equal(r.acceptedCostPln,null);
 assert.ok(r.knownCostPln>0);
});

test('no cutting evidence is NEVER reported as an accepted 0 PLN quotation',()=>{
 const missing=planCuttingBatches({groups:[{key:'unclassified',quantity:3,
  solid:{bboxMm:[80,60,40],volumeMm3:80000}}]});
 assert.equal(missing.knownCostPln,0);
 assert.equal(missing.acceptedCostPln,null);
 assert.equal(missing.costCoveragePct,0);
 assert.equal(missing.complete,false);
 const empty=planCuttingBatches({groups:[]});
 assert.equal(empty.complete,false);
 assert.equal(empty.completeness,'NO_PARTS');
 assert.equal(empty.acceptedCostPln,null);
});

test('fully priced evidence retains the previous complete batch cost',()=>{
 const r=planCuttingBatches({material:'S355',groups:[group('sheet',10,3)]});
 assert.equal(r.complete,true);
 assert.equal(r.costCoveragePct,100);
 assert.equal(r.acceptedCostPln,r.knownCostPln);
 assert.equal(r.completeness,'CUTTING_ESTIMATED');
});


test('cutting batch rejects monetary overflow rather than reporting Infinity PLN',()=>{
 assert.throws(()=>planCuttingBatches({material:'S355',groups:[group('sheet',10)],
  overrides:{sheet:{minutes:1e308}}}),RangeError);
});

test('cutting batch rejects overflow of total occurrences even for unknown routes',()=>{
 const unknown=(key,quantity)=>({key,quantity,solid:{bboxMm:[1000,40,40],volumeMm3:50000}});
 assert.throws(()=>planCuttingBatches({groups:[
  unknown('first',Number.MAX_SAFE_INTEGER),unknown('second',1)
 ]}),RangeError);
});
