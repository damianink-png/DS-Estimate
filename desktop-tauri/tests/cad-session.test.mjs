import test from 'node:test';
import assert from 'node:assert/strict';
import {createCadSession} from '../src/lib/cad-session.mjs';

test('one OCCT import per same file revision; input change invalidates cache',async()=>{
 let calls=0,revision='v1';
 const session=createCadSession(async()=>{calls++;return {count:calls}},async()=>revision);
 const [a,b]=await Promise.all([session.analyze('model.step'),session.analyze('model.step')]);
 assert.deepEqual(a,{count:1});
 assert.strictEqual(a,b);
 assert.strictEqual(await session.analyze('model.step'),a);
 assert.equal(calls,1);
 revision='v2';
 assert.deepEqual(await session.analyze('model.step'),{count:2});
 assert.equal(calls,2);
 assert.deepEqual(await session.analyze('model.step',{refresh:true}),{count:3});
});

test('CAD errors are never cached as successful geometry',async()=>{
 let calls=0;
 const s=createCadSession(async()=>{calls++;if(calls===1)throw Error('OCCT');return 'ok'},async()=>1);
 await assert.rejects(s.analyze('bad.step'),/OCCT/);
 assert.equal(await s.analyze('bad.step'),'ok');
 assert.equal(calls,2);
});
