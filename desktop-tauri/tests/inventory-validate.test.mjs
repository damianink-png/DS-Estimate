import test from 'node:test';
import assert from 'node:assert/strict';
import {validateStepBom} from '../src/lib/inventory-validate.mjs';
const fixture={
 count:3,totalMassKg:3.7,
 solids:[
  {id:'1',verifiedShapeKey:'A',volumeMm3:100000,massKg:0.785,bboxMm:[100,100,10]},
  {id:'2',verifiedShapeKey:'A',volumeMm3:100000,massKg:0.785,bboxMm:[100,100,10]},
  {id:'3',verifiedShapeKey:'B',volumeMm3:271337.58,massKg:2.13,bboxMm:[100,100,27.13]}
 ],
 groups:[{geometryId:'A',quantity:2,massKg:0.785},{geometryId:'B',quantity:1,massKg:2.13}]
};
test('full STEP BOM agrees with per-solid mass and quantity',()=>{
 assert.equal(validateStepBom(fixture),fixture);
});
test('detect duplicate, missing and inconsistent mass instead of silently quoting',()=>{
 assert.throws(()=>validateStepBom({...fixture,count:4}),/Liczba brył/);
 assert.throws(()=>validateStepBom({...fixture,totalMassKg:4}),/Masa sumaryczna/);
 assert.throws(()=>validateStepBom({...fixture,groups:[{...fixture.groups[0],quantity:3},fixture.groups[1]]}),/Niezgodna/);
 assert.throws(()=>validateStepBom({...fixture,groups:[fixture.groups[0],fixture.groups[0]]}),/duplikat/);
 assert.throws(()=>validateStepBom({...fixture,solids:[...fixture.solids.slice(0,2),{...fixture.solids[2],massKg:0}]}),/Niepełne/);
});
test('reject two distinct solid masses sharing one group key',()=>{
 const changed=structuredClone(fixture);
 changed.solids[1].massKg=0.9;
 assert.throws(()=>validateStepBom(changed),/Różne masy/);
});
