import test from 'node:test';
import assert from 'node:assert/strict';
import {millingFromCuttingData} from '../src/lib/milling-physics.mjs';
const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-8,`${a} != ${b}`);
const base={cuttingSpeedMMin:100,toolDiameterMm:20,teeth:4,feedPerToothMm:.1,axialDepthMm:2,radialWidthMm:8,removedCm3:100};
test('milling spindle feed and MRR equations (Sandvik metric)',()=>{
 const r=millingFromCuttingData(base);
 near(r.rpm,100000/(Math.PI*20));
 near(r.feedMmMin,100000/(Math.PI*20)*.4);
 near(r.removalCm3Min,2*8*r.feedMmMin/1000);
 near(r.cuttingMin,100/r.removalCm3Min);
});
test('machine limits reduce predicted throughput rather than fabricating faster cuts',()=>{
 const b=millingFromCuttingData(base);
 const r=millingFromCuttingData({...base,maxSpindleRpm:1000,maxFeedMmMin:300,cuttingEfficiency:0.5});
 near(r.rpm,1000);near(r.feedMmMin,300);near(r.removalCm3Min,2.4);near(r.cuttingMin,100/2.4);
 assert.ok(r.cuttingMin>b.cuttingMin);
});
test('power warning and rigorous validation',()=>{
 const r=millingFromCuttingData({...base,specificCuttingForceNmm2:2000,availableSpindlePowerKw:0.1});
 assert.equal(r.powerOverload,true);
 assert.ok(r.requiredPowerKw>0.1);
 assert.throws(()=>millingFromCuttingData({...base,toolDiameterMm:0}),RangeError);
 assert.throws(()=>millingFromCuttingData({...base,radialWidthMm:21}),RangeError);
 assert.throws(()=>millingFromCuttingData({...base,cuttingEfficiency:1.2}),RangeError);
 assert.throws(()=>millingFromCuttingData({...base,teeth:3.5}),RangeError);
});
