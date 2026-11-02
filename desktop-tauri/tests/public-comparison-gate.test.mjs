import test from 'node:test';
import assert from 'node:assert/strict';
import {assessPublicComparison} from '../src/lib/public-comparison-gate.mjs';
const ids=['portal-frame','stepgen-frame','earthpress','dockhub'];
const valid=id=>({id,status:'ENGINE_OK',quality:{stepImport:'OK',cutting:'PARTIAL',fullQuote:'UNAVAILABLE'},
 engine:{solids:10},cut:{rows:3,pendingOccurrences:10,coverage:0}});
test('all 4 imported and quoted inputs are required; partial cutting remains explicitly allowed',()=>{
 const results=ids.map(valid);
 assert.deepEqual(assessPublicComparison(results,ids),{ok:true,errors:[]});
});
test('three good models plus failed DockHub cannot pass',()=>{
 const results=ids.map(valid);
 results[3].status='QUOTE_INPUT_FAIL';
 assert.equal(assessPublicComparison(results,ids).ok,false);
});
test('missing, duplicated, unexpected or empty inventories fail',()=>{
 assert.equal(assessPublicComparison(ids.slice(0,3).map(valid),ids).ok,false);
 assert.equal(assessPublicComparison([...ids.map(valid),valid('earthpress')],ids).ok,false);
 assert.equal(assessPublicComparison([...ids.map(valid),valid('fifth')],ids).ok,false);
 const empty=ids.map(valid);
 empty[0].cut.rows=0;
 assert.equal(assessPublicComparison(empty,ids).ok,false);
});
