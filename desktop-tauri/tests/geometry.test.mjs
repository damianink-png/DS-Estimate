import test from 'node:test';import assert from 'node:assert/strict';import {massFromVolume,geometrySignature,groupGeometry} from '../src/lib/geometry.mjs';
test('Mass: 1 liter steel 7.85 kg',()=>assert.ok(Math.abs(massFromVolume(1_000_000)-7.85)<1e-12));
test('Orientation-independent dimensions signature',()=>assert.equal(geometrySignature({volumeMm3:1000,bboxMm:[10,20,30]}),geometrySignature({volumeMm3:1000,bboxMm:[30,10,20]})));
test('Verified shapes group with quantity',()=>{const r=groupGeometry([{id:'a',volumeMm3:1_000_000,bboxMm:[100,100,100],verifiedShapeKey:'hash1',quantity:2},{id:'b',volumeMm3:1_000_000,bboxMm:[100,100,100],verifiedShapeKey:'hash1',quantity:3}]);assert.equal(r.groups.length,1);assert.equal(r.groups[0].quantity,5);assert.equal(r.totalMassKg,39.25)});
test('Same dimensions alone do not prove shape identity',()=>{const p={volumeMm3:1000,bboxMm:[10,20,30]};const r=groupGeometry([{...p,id:'a'},{...p,id:'b'}]);assert.equal(r.groups.length,2);assert.equal(r.candidateBuckets.length,1)});
test('Different verified shape keys remain separate',()=>{const p={volumeMm3:1000,bboxMm:[10,20,30]};assert.equal(groupGeometry([{...p,verifiedShapeKey:'A'},{...p,verifiedShapeKey:'B'}]).groups.length,2)});
test('Invalid geometry rejected',()=>assert.throws(()=>massFromVolume(-1),RangeError));

test('Geometric candidate buckets distinguish different volumes and surface areas',()=>{
 const base={volumeMm3:1000,areaMm2:700,bboxMm:[10,20,30]};
 const largerVolume={...base,volumeMm3:1400};
 const largerArea={...base,areaMm2:900};
 assert.notEqual(geometrySignature(base),geometrySignature(largerVolume));
 assert.notEqual(geometrySignature(base),geometrySignature(largerArea));
 const grouped=groupGeometry([base,largerVolume,largerArea]);
 assert.equal(grouped.groups.length,3);
 assert.equal(grouped.candidateBuckets.length,0);
});
test('Geometry signatures remain rotation-independent and validate tolerances',()=>{
 const a={volumeMm3:0.00000005,areaMm2:0.000002,bboxMm:[0.1,0.2,0.3]};
 assert.equal(geometrySignature(a),geometrySignature({...a,bboxMm:[0.3,0.1,0.2]}));
 assert.notEqual(geometrySignature(a),geometrySignature({...a,volumeMm3:0.00000007}));
 assert.throws(()=>geometrySignature(a,{volumeRelTol:0}),RangeError);
 assert.throws(()=>geometrySignature(a,{lengthTolMm:0}),RangeError);
});
