import test from 'node:test';
import assert from 'node:assert/strict';
import {PINNED_BASELINE,ACTIVE_PINNED_BASELINE,checkPinnedPublicRegression} from './public_fabrication_regression.mjs';

const results=()=>Object.entries(ACTIVE_PINNED_BASELINE).map(([id,v])=>({
 id,status:'ENGINE_OK',engine:{solids:v.solids,groups:v.groups,massKgAssumed7850:v.massKg},
 cut:{coverage:v.cutCoverage,calculatedTimeH:v.knownCutHours},
 total:{autoFullH:null}
}));
test('pinned 3-active-case geometry, mass and partial cutting reference passes',()=>{
 assert.deepEqual(checkPinnedPublicRegression(results()),[]);
});
test('a fast engine that loses duplicate grouping cannot silently pass',()=>{
 const rows=results();rows.find(x=>x.id==='earthpress').engine.groups=129;
 assert.ok(checkPinnedPublicRegression(rows).some(x=>x.includes('grouping')));
});
test('changed mass, coverage or partial cut hours must be reviewed',()=>{
 const rows=results();rows[0].engine.massKgAssumed7850*=1.1;
 rows[2].cut.coverage=0;
 rows[2].cut.calculatedTimeH=0;
 assert.ok(checkPinnedPublicRegression(rows).length>=2);
});
test('a missing project or false full quote fails',()=>{
 const rows=results();rows.pop();rows[0].total.autoFullH=1;
 assert.ok(checkPinnedPublicRegression(rows).length>=2);
});

test('DockHub is suspended without deleting its historical pinned baseline',()=>{
 assert.equal(PINNED_BASELINE.dockhub.solids,541);
 assert.equal(PINNED_BASELINE.dockhub.groups,111);
 assert.equal(ACTIVE_PINNED_BASELINE.dockhub,undefined);
 const rows=results();
 rows.push({id:'dockhub',status:'ENGINE_OK',engine:{...PINNED_BASELINE.dockhub},cut:{coverage:19.4,calculatedTimeH:4.69192},total:{autoFullH:null}});
 assert.ok(checkPinnedPublicRegression(rows).some(e=>e.includes('Unknown project dockhub')));
});
