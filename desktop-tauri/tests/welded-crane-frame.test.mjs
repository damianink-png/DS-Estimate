import test from 'node:test';
import assert from 'node:assert/strict';
import {estimateCut, estimateCnc, estimateProject} from '../src/lib/estimate.mjs';

// SYNTHETIC, independently specified stress scenario; NOT a real crane drawing,
// not a verified production quote and not automatic STEP/PDF interpretation.
// Representative 12 m welded lattice boom / frame with 150 parts.
// Every weld is assigned explicitly to a joint; do not infer from touching solids.
const parts=[
 {id:'chord',qty:4,lengthMm:12000,ends:2},
 {id:'diagonal',qty:64,lengthMm:1550,ends:2},
 {id:'crossmember',qty:24,lengthMm:1800,ends:2},
 {id:'gusset',qty:40,lengthMm:0,ends:0},
 {id:'endplate',qty:8,lengthMm:0,ends:0},
 {id:'mount',qty:10,lengthMm:0,ends:0},
];
const welds=[
 {id:'diagonal-to-chord',segments:128,eachMm:140,sides:1},
 {id:'crossmember-to-chord',segments:48,eachMm:180,sides:1},
 {id:'gusset-to-frame',segments:80,eachMm:220,sides:1},
 {id:'endplate',segments:8,eachMm:900,sides:1},
 {id:'mount',segments:20,eachMm:180,sides:1},
];
const sum=(a,f)=>a.reduce((s,x)=>s+f(x),0);
const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-8,`${a} != ${b}`);
const reference={
 partCount:150,
 linearStockMm:4*12000+64*1550+24*1800,
 sawCuts:4*2+64*2+24*2,
 weldLengthMm:128*140+48*180+80*220+8*900+20*180,
};
// Manual process assumptions, NOT inferred from geometry:
// 150 parts sorted 0.8 min each; 284 fit-up/tack positions at 2.5 min;
// 6 crane repositionings 20 min each; dimensional inspection 120 min.
// Welding time: deposition/arc and handling separately, not part of fit-up.
const positions=sum(welds,w=>w.segments);
const assemblyMin=150*0.8+positions*2.5+6*20+120;
const weldingMin=reference.weldLengthMm/180+positions*0.6+90;
const cutFeed=1500, cutSetup=25, cutPierceSec=3;
const cncInput={removedCm3:600,removalCm3Min:10,holes:[{count:40,depthMm:25,feedMmMin:100}],setupMin:60,toolChanges:4,toolChangeMin:2,handlingMin:30};

test('independent welded frame BOM and cut lengths',()=>{
 assert.equal(sum(parts,p=>p.qty),reference.partCount);
 assert.equal(sum(parts,p=>p.qty*p.lengthMm),reference.linearStockMm);
 assert.equal(reference.linearStockMm,190400);
 assert.equal(reference.sawCuts,184);
});
test('independent unique weld ledger and assembly/welding hours',()=>{
 near(sum(welds,w=>w.segments*w.eachMm*w.sides),reference.weldLengthMm);
 assert.equal(reference.weldLengthMm,54960);
 assert.equal(positions,284);
 near(assemblyMin,1070); // 17 h 50 min
 near(weldingMin,565.7333333333333); // 9 h 25 min 44 sec
});
test('DS Estimate existing cutting and CNC arithmetic against independently derived expected values',()=>{
 // This checks formula consistency only. It does NOT prove automated manufacturing recognition.
 const cut=estimateCut({contourMm:reference.linearStockMm,feedMmMin:cutFeed,pierces:reference.sawCuts,pierceSec:cutPierceSec,setupMin:cutSetup});
 near(cut.totalMin,190400/1500+184*3/60+25);
 const cnc=estimateCnc(cncInput);
 near(cnc.totalMin,600/10+40*25/100+60+4*2+30);
});
test('DS Estimate part aggregation counts 150 occurrences, no double count',()=>{
 const rows=parts.map(p=>({geometryId:p.id,quantity:p.qty,features:{}}));
 const result=estimateProject({parts:rows});
 assert.equal(result.occurrences,150);
 assert.equal(result.uniqueCalculations,6);
});
test('known missing production capabilities must not be presented as verified',()=>{
 // There is no estimateWeld or estimateAssembly exported by current engine.
 assert.equal(typeof estimateCut,'function');
 assert.equal(typeof estimateCnc,'function');
});
