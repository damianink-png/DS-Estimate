import test from 'node:test';
import assert from 'node:assert/strict';
import {estimateAssembly,estimateWelding,estimateFabrication} from '../src/lib/estimate.mjs';
const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-7,`${a} != ${b}`);
const joints=[{count:128,lengthMm:140,throatMm:5},{count:48,lengthMm:180,throatMm:5},{count:80,lengthMm:220,throatMm:5},{count:8,lengthMm:900,throatMm:5},{count:20,lengthMm:180,throatMm:5}];
const operations=[['fixture',1,60],['main chords',4,15],['diagonals',64,6],['crossmembers',24,5],['gussets',40,3],['end mounts',18,5],['tacks',284,.75],['inspection',3,40],['turns',4,20],['adjustment',1,120]].map(([name,count,minutesEach])=>({name,count,minutesEach}));
test('weld length, mass, arc-on and total station time',()=>{
 const r=estimateWelding({joints,setupMin:60});
 near(r.weldLengthMm,54960);
 near(r.massKg,54960*25*1e-9*7850);
 near(r.arcMin,r.massKg/2.5*60);
 near(r.totalMin,60+r.arcMin/.35);
});
test('passes do not multiply deposited volume',()=>{
 const a=estimateWelding({joints:[{count:1,lengthMm:100,throatMm:5,passes:1}]});
 const b=estimateWelding({joints:[{count:1,lengthMm:100,throatMm:5,passes:3}]});
 near(a.massKg,b.massKg);
});
test('assembly is process-based and tacks counted only here',()=>{
 const r=estimateAssembly({operations});
 near(r.totalMin,1367);
});
test('full fabrication breakdown avoids double counting welding setup and tacks',()=>{
 const r=estimateFabrication({assembly:{operations},welding:{joints,setupMin:60},cutting:{contourMm:190400,feedMmMin:1500,pierces:184,pierceSec:3,setupMin:25},cnc:{removedCm3:600,removalCm3Min:10,holes:[{count:40,depthMm:25,feedMmMin:100}],setupMin:60,toolChanges:4,toolChangeMin:2,handlingMin:30},finishing:{operations:[{name:'final inspection',count:1,minutesEach:250}]}});
 near(r.totalMin,Object.values(r.steps).reduce((s,x)=>s+x.totalMin,0));
 near(r.totalCost,r.totalMin*388/60);
});
test('reject invalid arc fraction and negative time',()=>{
 assert.throws(()=>estimateWelding({joints,arcOnFraction:1.2}),RangeError);
 assert.throws(()=>estimateAssembly({operations:[{minutesEach:-1}]}),RangeError);
});
