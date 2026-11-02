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
