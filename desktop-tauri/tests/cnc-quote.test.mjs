import test from 'node:test';
import assert from 'node:assert/strict';
import { estimateCncOperations } from '../src/lib/cnc-quote.mjs';
test('setup charged once, machining per piece',()=>{
 const r=estimateCncOperations([{name:'Frezowanie',setupMinutes:30,cycleMinutes:60,quantity:3}]);
 assert.equal(r.lines[0].setupCostPln,194);
 assert.equal(r.lines[0].machiningCostPln,1164);
 assert.equal(r.totalCostPln,1358);
});
test('rejects negative and invalid machining time',()=>assert.throws(()=>estimateCncOperations([{cycleMinutes:-2}]),RangeError));
