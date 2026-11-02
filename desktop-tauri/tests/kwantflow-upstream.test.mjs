import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { pathToFileURL } from 'node:url';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const folder = await mkdtemp(join(tmpdir(), 'kwantflow-test-'));
try {
 const output = join(folder, 'quote.mjs');
 await build({entryPoints:[resolve('src/lib/kwantflow/estimate-calculation.ts')], outfile:output, bundle:true, platform:'node', format:'esm'});
 const { costComponentUnitCost, takeoffItemUnitCost, takeoffItemTotal, estimateTotalCost } = await import(pathToFileURL(output).href);
 const component=(quantity,unit_rate,category='material')=>({quantity,unit_rate,category});
 const item=(quantity,components)=>({quantity,cost_components:components});
 test('Kwantflow upstream component uses quantity times rate',()=>assert.equal(costComponentUnitCost(component(2.5,388)),970));
 test('Kwantflow upstream unit cost sums materials and labour',()=>assert.equal(takeoffItemUnitCost(item(3,[component(2,45),component(1.5,388,'labour')])),672));
 test('Kwantflow upstream takeoff multiplies unit cost by part quantity',()=>assert.equal(takeoffItemTotal(item(3,[component(2,45),component(1.5,388,'labour')])),2016));
 test('Kwantflow upstream full estimate sums multiple items',()=>assert.equal(estimateTotalCost({takeoff_items:[item(3,[component(2,45),component(1.5,388,'labour')]),item(2,[component(4,12.5)])]}),2116));
 test('Kwantflow decimal arithmetic avoids binary float drift',()=>assert.equal(estimateTotalCost({takeoff_items:[item(1,[component(0.1,0.2),component(0.2,0.3)])]}),0.08));
 test('Kwantflow empty estimate is zero',()=>assert.equal(estimateTotalCost({takeoff_items:[]}),0));
 test('Kwantflow invalid numeric input is rejected by decimal.js',()=>assert.throws(()=>costComponentUnitCost(component(Number.NaN,20))));
} finally {
 process.on('exit',()=>{});
}
