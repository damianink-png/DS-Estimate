import test from 'node:test';
import assert from 'node:assert/strict';
import {recommendCutting, partCuttingHint, SAMPLE_MACHINE_SETTINGS} from '../src/lib/cutting-plan.mjs';
const plate=(thickness,contour=300,pierces=1)=>({
 volumeMm3:600000*thickness,bboxMm:[1000,600,thickness],
 cuttingHint:{kind:'plate-outline',thicknessMm:thickness,contourMm:contour,pierces}
});
test('steel plate under 12 mm uses laser and correctly totals contour, pierces and one setup',()=>{
 const r=recommendCutting({solid:plate(10),quantity:4,material:'S355'});
 assert.equal(r.method,'laser');
 assert.equal(r.hint.contourMm,300);
 assert.equal(r.hint.pierces,1);
 assert.ok(Math.abs(r.calculatedMin-(15+4*(300/1400+3/60)))<1e-8);
 assert.equal(r.costPln,r.calculatedMin*388/60);
 assert.equal(r.confidence,'estimated');
});
test('different thickness selects plasma and oxy only inside thickness capability',()=>{
 const plasma=recommendCutting({solid:plate(20),material:'S355'});
 assert.equal(plasma.method,'plasma');
 const thick=recommendCutting({solid:plate(60),material:'S355'});
 assert.equal(thick.method,'oxy');
 const stainless=recommendCutting({solid:plate(60),material:'stainless'});
 assert.equal(stainless.method,null); // waterjet initially unavailable, oxy forbidden
});
test('identifies long stock as saw candidate but refuses to fabricate saw time',()=>{
 const r=recommendCutting({solid:{bboxMm:[1000,40,40],volumeMm3:700000},quantity:10,material:'S355'});
 assert.equal(r.method,'saw');
 assert.equal(r.calculatedMin,null);
 assert.equal(r.costPln,null);
 assert.equal(r.confidence,'requires-review');
 assert.equal(r.hint.kind,'possible-profile');
});
test('no measured STEP contour means no fabricated cutting time',()=>{
 const r=recommendCutting({solid:{bboxMm:[100,50,8],volumeMm3:40000},material:'S355'});
 assert.equal(r.method,'laser');
 assert.equal(r.calculatedMin,null);
 assert.ok(r.warnings.some(x=>x.includes('konturu')));
});
test('missing material does not silently authorize oxy cutting',()=>{
 const r=recommendCutting({solid:plate(60)});
 assert.equal(r.method,null);
 assert.equal(r.costPln,null);
 assert.ok(r.warnings.some(x=>x.includes('gatunku')));
});
test('available machines, manual method and accepted time override',()=>{
 const machines=structuredClone(SAMPLE_MACHINE_SETTINGS);
 machines.laser.enabled=false;
 const r=recommendCutting({solid:plate(8),quantity:3,material:'S355',machines});
 assert.equal(r.method,'plasma');
 const override=recommendCutting({solid:plate(8),quantity:3,material:'S355',machines,overrideMinutes:50});
 assert.equal(override.acceptedMin,50);
 assert.equal(override.costPln,50*388/60);
 assert.equal(override.confidence,'manual');
 assert.throws(()=>recommendCutting({solid:plate(8),material:'S355',machines,overrideMethod:'laser'}),RangeError);
 assert.throws(()=>recommendCutting({solid:plate(80),material:'S355',overrideMethod:'plasma'}),RangeError);
});
test('invalid dimensions and missing geometry do not invent a method',()=>{
 const r=recommendCutting({solid:{bboxMm:[0,10,100]}});
 assert.equal(r.method,null);
 assert.equal(r.calculatedMin,null);
 assert.throws(()=>recommendCutting({solid:plate(10),quantity:0}),RangeError);
 assert.throws(()=>recommendCutting({solid:plate(10),overrideMinutes:-1}),RangeError);
});

test('OCCT Bnd_Box rounding near 5:1 still recognises nominal plate',()=>{
 const solid={volumeMm3:50000,bboxMm:[100.0000002,50.0000002,10.0000002],
  cuttingHint:{kind:'plate-outline',thicknessMm:10.0000002,contourMm:300,pierces:1}};
 const hint=partCuttingHint(solid);
 assert.equal(hint.kind,'possible-plate');
 assert.equal(hint.contourMm,300);
 const route=recommendCutting({solid,material:'S355'});
 assert.equal(route.method,'laser');
 assert.ok(route.calculatedMin>0);
});
