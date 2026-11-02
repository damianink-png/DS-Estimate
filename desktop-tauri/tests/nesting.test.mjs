import test from 'node:test';
import assert from 'node:assert/strict';
import { estimateNestedCut } from '../src/lib/nesting.mjs';
const job={sheetWidthMm:2000,sheetHeightMm:1000,sheetCostPln:500,feedMmMin:1000,pierceSeconds:2,ratePlnHour:388};
test('rejects a fabricated or absent Deepnest result',()=>assert.throws(()=>estimateNestedCut(job,{placements:[]}),/Deepnest/));
test('calculates sheet utilization and laser cutting cost from verified placements',()=>{
 const r=estimateNestedCut(job,{engine:'deepnest',verified:true,placements:[
  {sheetIndex:0,areaMm2:500000,cutLengthMm:3000,pierces:2},
  {sheetIndex:0,areaMm2:250000,cutLengthMm:2000,pierces:1}]});
 assert.equal(r.sheets,1);assert.equal(r.utilization,0.375);assert.equal(r.contourMm,5000);
 assert.ok(Math.abs(r.cuttingMinutes-5.1)<1e-9);
});
test('rejects impossible area',()=>assert.throws(()=>estimateNestedCut(job,{engine:'deepnest',verified:true,placements:[{sheetIndex:0,areaMm2:3000000,cutLengthMm:1000,pierces:1}]}),/przekracza/));
