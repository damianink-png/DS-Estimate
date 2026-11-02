import test from 'node:test';import assert from 'node:assert/strict';import {estimateCnc,estimateCut,estimateBending,estimateProject} from '../src/lib/estimate.mjs';
test('CNC milling + drilling + setup',()=>{const r=estimateCnc({removedCm3:80,removalCm3Min:10,holes:[{depthMm:20,feedMmMin:100,count:5}],setupMin:12,toolChanges:2,toolChangeMin:1});assert.equal(r.totalMin,23)});
test('Cut includes pierces and rapid',()=>{assert.equal(estimateCut({contourMm:3000,feedMmMin:1000,pierces:6,pierceSec:10,rapidMm:1000,rapidMmMin:1000,setupMin:5}).totalMin,10)});
test('Bending includes setup',()=>{assert.equal(estimateBending({bends:6,secondsPerBend:30,setupMin:10}).totalMin,13)});
test('Same geometry computed once',()=>{const features={cnc:{removedCm3:100,removalCm3Min:10,setupMin:0}};const r=estimateProject({parts:[{geometryId:'A',quantity:3,features},{geometryId:'A',quantity:2,features}]});assert.equal(r.uniqueCalculations,1);assert.equal(r.totalMin,50)});
test('Invalid feed rejected',()=>assert.throws(()=>estimateCut({feedMmMin:0}),RangeError));
test('duplicate parts share one setup, not setup multiplied by quantity',()=>{
 const r=estimateProject({ratePerHour:60,parts:[
  {geometryId:'plate',quantity:3,features:{cnc:{removedCm3:60,removalCm3Min:10,setupMin:30}}},
  {geometryId:'plate',quantity:2,features:{cnc:{removedCm3:60,removalCm3Min:10,setupMin:30}}}
 ]});
 assert.equal(r.rows[0].totalMin,48); // 30 + 3 * 6
 assert.equal(r.rows[1].totalMin,12); // 2 * 6, no second setup
 assert.equal(r.rows[1].batchSetupMin,0);
 assert.equal(r.totalMin,60);
 assert.equal(r.totalCost,60);
 assert.equal(r.uniqueCalculations,1);
});
test('different technology routings require separate setup, valid defaults preserved',()=>{
 const r=estimateProject({ratePerHour:60,parts:[
  {geometryId:'part',quantity:2,features:{cut:{contourMm:1000,feedMmMin:1000,setupMin:10}}},
  {geometryId:'part',quantity:3,features:{bend:{bends:2,secondsPerBend:30,setupMin:15}}}
 ]});
 assert.equal(r.totalMin,10+2+15+3);
 assert.equal(r.uniqueCalculations,2);
});
