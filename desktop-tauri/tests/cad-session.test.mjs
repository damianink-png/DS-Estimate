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

test('refresh during pending import does not let stale result overwrite new snapshot',async()=>{
 let releaseOld, calls=0;
 const s=createCadSession(()=>{calls++;return calls===1?new Promise(resolve=>{releaseOld=resolve}):Promise.resolve({version:2})},async()=>1);
 const stale=s.analyze('frame.step');
 await new Promise(resolve=>setImmediate(resolve));
 const fresh=await s.analyze('frame.step',{refresh:true});
 releaseOld({version:1});
 assert.deepEqual(await stale,{version:1});
 assert.deepEqual(await s.analyze('frame.step'),fresh);
 assert.equal(calls,2);
});

test('clear invalidates pending imports and never caches their late completion',async()=>{
 let releaseOld, calls=0;
 const s=createCadSession(()=>{calls++;return calls===1?new Promise(resolve=>{releaseOld=resolve}):Promise.resolve({version:2})},async()=>1);
 const old=s.analyze('frame.step');
 await new Promise(resolve=>setImmediate(resolve));
 s.clear();
 const current=await s.analyze('frame.step');
 releaseOld({version:1});
 await old;
 assert.deepEqual(await s.analyze('frame.step'),current);
 assert.equal(calls,2);
});


test('clear while revision fingerprint is pending cannot cache stale inventory',async()=>{
 let releaseRevision, calls=0, revisions=0;
 const s=createCadSession(async()=>({call:++calls}),()=>++revisions===1?new Promise(resolve=>{releaseRevision=resolve}):Promise.resolve('new'));
 const old=s.analyze('frame.step');
 await new Promise(resolve=>setImmediate(resolve));
 s.clear();
 const current=await s.analyze('frame.step');
 releaseRevision('old');
 await old;
 assert.deepEqual(await s.analyze('frame.step'),current);
 assert.equal(calls,2);
 assert.equal(s.stats().cached,1);
});
