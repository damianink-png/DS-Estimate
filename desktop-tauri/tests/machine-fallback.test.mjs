import test from 'node:test';
import assert from 'node:assert/strict';
import {planAutomaticCutting,MACHINES} from '../src/lib/automatic-cutting.mjs';
const part={id:'p',name:'Plate',route:'make',grade:'S235',density:7850,dims:[100,80,8],cutMethod:'auto',solid:{stockHint:{kind:'plate-candidate',thicknessMm:8},cuttingHint:{kind:'plate-outline',contourMm:360,pierces:1}}};
test('disabled laser falls back to available plasma',()=>{
 const machines={...MACHINES,laser:{...MACHINES.laser,enabled:false}};
 const row=planAutomaticCutting([part],{machines}).rows[0];
 assert.equal(row.method,'plasma');assert.ok(row.minutes>0);
});
test('explicit disabled laser remains unresolved',()=>{
 const machines={...MACHINES,laser:{...MACHINES.laser,enabled:false}};
 assert.equal(planAutomaticCutting([{...part,cutMethod:'laser'}],{machines}).rows[0].minutes,null);
});
test('stainless cannot fall back to oxygen cutting',()=>{
 const machines={...MACHINES,laser:{...MACHINES.laser,enabled:false},plasma:{...MACHINES.plasma,enabled:false}};
 assert.equal(planAutomaticCutting([{...part,grade:'1.4301'}],{machines}).rows[0].minutes,null);
});
