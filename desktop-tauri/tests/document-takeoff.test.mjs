import test from 'node:test';import assert from 'node:assert/strict';import {analyzeManufacturingInventory} from '../src/lib/document-takeoff.mjs';
test('inventory derives measured mass and occurrence groups without inventing welds',()=>{
 const data={solids:[{id:'a',verifiedShapeKey:'x',volumeMm3:50000,bboxMm:[100,50,10]},{id:'b',verifiedShapeKey:'x',volumeMm3:50000,bboxMm:[100,50,10]}]};
 const r=analyzeManufacturingInventory(data);
 assert.equal(r.solidCount,2);assert.equal(r.uniqueGroups,1);assert.equal(r.groups[0].quantity,2);
 assert.ok(Math.abs(r.totalMassKg-.785)<1e-10);assert.equal(r.quotationReady,false);
 assert.ok(r.unresolved.some(x=>x.operation==='welding'));
 assert.equal(r.items[0].suggestedCategory,'unclassified');
});
test('different solids never merge based on equal dimensions alone',()=>{
 const r=analyzeManufacturingInventory({solids:[{id:'a',volumeMm3:10,bboxMm:[1,2,3]},{id:'b',volumeMm3:10,bboxMm:[1,2,3]}]});
 assert.equal(r.uniqueGroups,2);
});
test('invalid CAD measurements fail rather than produce plausible cost',()=>{
 assert.throws(()=>analyzeManufacturingInventory({solids:[{volumeMm3:-1,bboxMm:[1,2,3]}]}),RangeError);
});