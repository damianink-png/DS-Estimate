import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { build } from 'esbuild';

const dir = await mkdtemp(join(tmpdir(), 'ds-bench-'));
try {
 const out = join(dir, 'kwantflow.mjs');
 await build({entryPoints:['src/lib/kwantflow/estimate-calculation.ts'],outfile:out,bundle:true,platform:'node',format:'esm'});
 const {estimateTotalCost} = await import(pathToFileURL(out).href);
 const cases = [
  {id:'quotedpart-bracket-1', source:'https://quotedpart.com/quote-from-a-drawing', qty:1, currency:'USD', material:15.55, setup:222.63, run:12.92, markup:0.30, reference:326.43},
  {id:'quotedpart-bracket-10', source:'https://quotedpart.com/quote-from-a-drawing', qty:10, currency:'USD', material:54.85, setup:222.63, run:129.32, markup:0.30, reference:52.88},
  {id:'quotedpart-bracket-100', source:'https://quotedpart.com/quote-from-a-drawing', qty:100, currency:'USD', material:386.53, setup:222.63, run:1293.84, markup:0.30, reference:24.74},
  {id:'kerfquote-motor-mount-25', source:'https://kerfquote.com/', qty:25, currency:'EUR', material:99.66, setup:45, run:0, markup:0.18, reference:170.70, referenceBasis:'lot'}
 ];
 let failed=0;
 for(const c of cases) {
  const quote = estimateTotalCost({takeoff_items:[
   {quantity:1,cost_components:[{quantity:1,unit_rate:c.material},{quantity:1,unit_rate:c.setup},{quantity:1,unit_rate:c.run}]}
  ]});
  const price = quote*(1+c.markup)/c.qty;
  const comparedPrice=c.referenceBasis==='lot'?price*c.qty:price;
  const delta=comparedPrice-c.reference, percent=delta/c.reference*100;
  const pass=Math.abs(delta)<=0.10;
  if(!pass)failed++;
  console.log(JSON.stringify({case:c.id,source:c.source,mode:'reference-input arithmetic only (NOT CAD/RFQ import)',currency:c.currency,quantity:c.qty,calculated_unit_price:Number(price.toFixed(4)),calculated_comparison_price:Number(comparedPrice.toFixed(4)),reference_price:c.reference,reference_basis:c.referenceBasis||'unit',delta:Number(delta.toFixed(4)),delta_percent:Number(percent.toFixed(3)),status:pass?'PASS':'FAIL'}));
 }
 assert.equal(failed,0,`${failed} benchmark arithmetic deviations exceed 0.10 currency units`);
} finally { await rm(dir,{recursive:true,force:true}); }
