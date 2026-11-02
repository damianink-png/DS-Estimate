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
