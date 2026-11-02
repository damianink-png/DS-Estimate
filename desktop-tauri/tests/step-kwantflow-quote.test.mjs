import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { pathToFileURL } from 'node:url';
import { mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const dir=await mkdtemp(join(tmpdir(),'step-kwantflow-'));
const output=join(dir,'step-quote.mjs');
await build({entryPoints:[resolve('src/lib/kwantflow/step-quote.ts')],outfile:output,bundle:true,platform:'node',format:'esm'});
const {buildStepQuote,parseStepInventory}=await import(pathToFileURL(output).href);
const fixture={source:'fixture.step',count:4,totalMassKg:17.5,
 groups:[{geometryId:'a',quantity:3,massKg:2.5},{geometryId:'b',quantity:1,massKg:10}]};
test('real Kwantflow takeoff: STEP duplicate quantities and material per kg',()=>{
 const r=buildStepQuote(fixture,{materialRatePlnKg:12,ratePlnHour:388});
 assert.equal(r.groups.length,2);
 assert.equal(r.estimate.takeoff_items.length,2);
 assert.equal(r.groups[0].totalMassKg,7.5);
 assert.equal(r.materialCostPln,210);
 assert.equal(r.totalCostPln,210);
 assert.equal(r.estimate.takeoff_items[0].quantity,3);
 assert.equal(r.estimate.takeoff_items[0].cost_components[0].unit_rate,12);
});
test('routing is explicitly billed once as Kwantflow operations',()=>{
 const r=buildStepQuote(fixture,{materialRatePlnKg:12,ratePlnHour:388,routing:{assemblyMin:60,weldingMin:120}});
 assert.equal(r.routingCostPln,1164);
 assert.equal(r.totalCostPln,1374);
 assert.equal(r.estimate.takeoff_items.length,4);
 assert.equal(r.estimate.takeoff_items[2].quantity,1);
});
test('rejects mismatched counts or mass; never fabricates a quote',()=>{
 assert.throws(()=>buildStepQuote({...fixture,count:5},{materialRatePlnKg:12,ratePlnHour:388}),/Liczba/);
 assert.throws(()=>buildStepQuote({...fixture,totalMassKg:18},{materialRatePlnKg:12,ratePlnHour:388}),/Masa/);
 assert.throws(()=>buildStepQuote(fixture,{materialRatePlnKg:0,ratePlnHour:388}),RangeError);
 assert.throws(()=>buildStepQuote(fixture,{materialRatePlnKg:12,ratePlnHour:388,routing:{weldingMin:-2}}),RangeError);
 assert.throws(()=>buildStepQuote({...fixture,groups:[fixture.groups[0],fixture.groups[0]]},{materialRatePlnKg:12,ratePlnHour:388}),/Powielony/);
});
test('accepts compiled STEP engine JSON and rejects invalid JSON',()=>{
 assert.equal(parseStepInventory(JSON.stringify(fixture)).groups.length,2);
 assert.throws(()=>parseStepInventory('invalid'),/JSON/);
});

test('original Kwantflow general markup prices STEP quote',()=>{
 const r=buildStepQuote(fixture,{materialRatePlnKg:12,ratePlnHour:388,routing:{assemblyMin:60,weldingMin:120},markup:{generalPercent:10}});
 assert.equal(r.totalCostPln,1374);
 assert.ok(Math.abs(r.sellingPricePln-1511.4)<1e-9);
 assert.ok(Math.abs(r.markupAmountPln-137.4)<1e-9);
});
test('original Kwantflow category markups override general markup',()=>{
 const r=buildStepQuote(fixture,{materialRatePlnKg:12,ratePlnHour:388,routing:{assemblyMin:60,weldingMin:120},markup:{generalPercent:10,materialPercent:20,labourPercent:5}});
 assert.ok(Math.abs(r.sellingPricePln-1474.2)<1e-9);
 assert.throws(()=>buildStepQuote(fixture,{materialRatePlnKg:12,ratePlnHour:388,markup:{generalPercent:Number.NaN}}),RangeError);
});

test('purchased stock, not finished mass, drives raw material cost',()=>{
 const r=buildStepQuote(fixture,{materialRatePlnKg:12,ratePlnHour:388,stockAllowancePercent:20});
 assert.ok(Math.abs(r.purchasedStockMassKg-21)<1e-8);
 assert.ok(Math.abs(r.stockWasteMassKg-3.5)<1e-8);
 assert.ok(Math.abs(r.materialCostPln-252)<1e-8);
 assert.equal(r.routingCostPln,0);
 const manual=buildStepQuote(fixture,{materialRatePlnKg:12,ratePlnHour:388,stockKgPerPart:{a:3,b:12}});
 assert.equal(manual.materialCostPln,252);
 assert.throws(()=>buildStepQuote(fixture,{materialRatePlnKg:12,ratePlnHour:388,stockKgPerPart:{a:1}}),/Półfabrykat/);
});
test('one setup per geometry and per-part CNC cycles, not one setup per duplicate',()=>{
 const r=buildStepQuote(fixture,{materialRatePlnKg:12,ratePlnHour:60,groupOperations:{
  a:[{name:'Frezowanie',setupMin:30,cycleMinPerPart:10,ratePlnHour:120,toolingPlnBatch:45,consumablesPlnPart:2}],
  b:[{name:'Wiercenie',setupMin:15,cycleMinPerPart:12,ratePlnHour:60}]
 }});
 assert.equal(r.setupCostPln,75); // 30 min at 120 + 15 min at 60
 assert.equal(r.perPartOperationCostPln,72); // 3*10 min at 120 + 1*12 min at 60
 assert.equal(r.toolingCostPln,45);
 assert.equal(r.consumablesCostPln,6);
 assert.equal(r.routingCostPln,198);
 assert.equal(r.totalCostPln,408);
 assert.equal(r.estimate.takeoff_items.filter(x=>x.properties.source==='manual once per geometry group').length,2);
});
test('group-specific workstations, unsupported groups and unsafe process parameters rejected',()=>{
 const base={materialRatePlnKg:12,ratePlnHour:388};
 assert.throws(()=>buildStepQuote(fixture,{...base,groupOperations:{unknown:[{name:'CNC',cycleMinPerPart:10}]}}),/Nieznana/);
 assert.throws(()=>buildStepQuote(fixture,{...base,stockAllowancePercent:-2}),RangeError);
 assert.throws(()=>buildStepQuote(fixture,{...base,groupOperations:{a:[{name:'',setupMin:10}]}}),TypeError);
 assert.throws(()=>buildStepQuote(fixture,{...base,groupOperations:{a:[{name:'CNC',cycleMinPerPart:-1}]}}),RangeError);
 assert.throws(()=>buildStepQuote(fixture,{...base,groupOperations:{a:[{name:'CNC',category:'material'}]}}),RangeError);
});

test('true 20% gross margin differs from 20% markup',()=>{
 const byMarkup=buildStepQuote(fixture,{materialRatePlnKg:12,ratePlnHour:388,markup:{mode:'markup',generalPercent:20}});
 const byMargin=buildStepQuote(fixture,{materialRatePlnKg:12,ratePlnHour:388,markup:{mode:'grossMargin',generalPercent:20}});
 assert.equal(byMarkup.totalCostPln,210);
 assert.equal(byMarkup.sellingPricePln,252);
 assert.equal(byMargin.sellingPricePln,262.5);
 assert.ok(Math.abs(byMargin.achievedGrossMarginPercent-20)<1e-8);
 assert.throws(()=>buildStepQuote(fixture,{materialRatePlnKg:12,ratePlnHour:388,markup:{mode:'grossMargin',generalPercent:100}}),RangeError);
 assert.throws(()=>buildStepQuote(fixture,{materialRatePlnKg:12,ratePlnHour:388,markup:{mode:'invalid',generalPercent:20}}),RangeError);
});
