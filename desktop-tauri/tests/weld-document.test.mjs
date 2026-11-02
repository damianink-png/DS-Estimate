import test from 'node:test';import assert from 'node:assert/strict';
import {parseExplicitFilletNotes,createWeldTakeoff,normalizeWeldCallout} from '../src/lib/weld-document.mjs';
test('PDF extracted note parsed but cannot be quoted without joint validation',()=>{
 const rows=parseExplicitFilletNotes('Detal A\na5 120 x2\na 4 L=85');
 assert.equal(rows.length,2);assert.equal(rows[0].throatMm,5);assert.equal(rows[0].lengthMm,120);assert.equal(rows[0].count,2);
 const t=createWeldTakeoff(rows);assert.equal(t.ready.length,0);assert.equal(t.pending.length,2);
});
test('verified fillet with explicit geometry becomes routing input',()=>{
 const t=createWeldTakeoff([{kind:'fillet',throatMm:5,lengthMm:120,count:2,verified:true}]);
 assert.deepEqual(t.ready,[{count:2,lengthMm:120,throatMm:5}]);assert.equal(t.allVerified,true);
});
test('butt weld is not incorrectly costed as fillet',()=>{
 const t=createWeldTakeoff([{kind:'butt',throatMm:5,lengthMm:100,verified:true}]);
 assert.equal(t.ready.length,0);
});
test('all-around symbol without verified length is pending',()=>{
 const r=normalizeWeldCallout({kind:'fillet',throatMm:5,allAround:true,verified:true});
 assert.equal(r.quotationReady,false);
});
test('bad weld values rejected',()=>assert.throws(()=>normalizeWeldCallout({kind:'fillet',throatMm:-1,lengthMm:20}),RangeError));
