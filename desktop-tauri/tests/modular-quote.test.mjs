import test from 'node:test';
import assert from 'node:assert/strict';
import {evaluateModules} from '../src/lib/modular-quote.mjs';
import {MODULES,DEFAULT_RATES} from '../src/lib/quote-modules/index.mjs';

const inventory={count:1,totalMassKg:1,groups:[{geometryId:'A',quantity:1,massKg:1}],
 solids:[{id:'solid-1',verifiedShapeKey:'A',massKg:1,volumeMm3:127388.5,bboxMm:[10,20,30]}]};

test('every stage is separately isolated; missing hours are not zero-cost full quote',()=>{
 const quote=evaluateModules({inventory});
 assert.equal(quote.modules.length,12);
 assert.equal(new Set(MODULES.map(x=>x.id)).size,12);
 assert.equal(quote.complete,false);
 assert.equal(quote.verifiedCostPln,null);
 assert.equal(quote.modules.find(x=>x.id==='welding').status,'missing');
 assert.equal(quote.modules.find(x=>x.id==='welding').rows[1].value,null);
 assert.equal(quote.knownCostPln,0);
});

test('edit operation hours and central hourly rate without changing CAD snapshot',()=>{
 const rates={...DEFAULT_RATES,welding:250};
 const edits={welding:{weld:{value:2.5}}};
 const first=evaluateModules({inventory,rates,edits});
 assert.equal(first.modules.find(x=>x.id==='welding').rows[1].costPln,625);
 const second=evaluateModules({inventory,rates:{...rates,welding:300},edits});
 assert.equal(second.modules.find(x=>x.id==='welding').rows[1].costPln,750);
 assert.strictEqual(second.source,first.source);
 assert.strictEqual(inventory.totalMassKg,1);
});

test('unverified material remains unknown; explicit material scope and grade required',()=>{
 const rates={...DEFAULT_RATES,materialPriceKg:7};
 const unchecked=evaluateModules({inventory,rates,grade:'S355'});
 assert.equal(unchecked.modules[0].rows[0].costPln,null);
 const confirmed=evaluateModules({inventory,rates,grade:'S355',materialApproved:true});
 assert.equal(confirmed.modules[0].rows[0].costPln,7);
 assert.equal(confirmed.modules[0].status,'review');
});

test('manual check or explicit not applicable required before green module status',()=>{
 const edits={welding:{setup:{value:1},weld:{value:2},clean:{value:0}}};
 const review=evaluateModules({inventory,edits});
 assert.equal(review.modules.find(x=>x.id==='welding').status,'review');
 const approved=evaluateModules({inventory,edits,confirmed:{welding:true}});
 assert.equal(approved.modules.find(x=>x.id==='welding').status,'verified');
 const omitted=evaluateModules({inventory,excluded:{welding:true}});
 assert.equal(omitted.modules.find(x=>x.id==='welding').status,'excluded');
 assert.equal(omitted.complete,false);
});

test('independent stage error does not break other modules',()=>{
 const rates={...DEFAULT_RATES,welding:NaN};
 const quote=evaluateModules({inventory,rates,edits:{welding:{weld:{value:2}}}});
 assert.equal(quote.modules.find(x=>x.id==='welding').status,'missing');
 assert.equal(quote.modules.find(x=>x.id==='material').status,'missing');
 assert.equal(quote.complete,false);
});

test('user-added operation receives own edit and category rate',()=>{
 const custom={quality:[{key:'custom-1',name:'Pomiar CMM'}]};
 const edits={quality:{'custom-1':{value:1.5}}};
 const quote=evaluateModules({inventory,custom,edits});
 const extra=quote.modules.find(x=>x.id==='quality').rows.at(-1);
 assert.equal(extra.costPln,DEFAULT_RATES.quality*1.5);
});

test('excluded stage does not contribute previously entered hours to the cost',()=>{
 const q=evaluateModules({inventory,edits:{welding:{
  setup:{value:1},weld:{value:2},clean:{value:1}}},
  confirmed:{welding:true},excluded:{welding:true}});
 assert.equal(q.modules.find(x=>x.id==='welding').knownCostPln,0);
 assert.equal(q.knownCostPln,0);
 assert.equal(q.modules.find(x=>x.id==='welding').status,'excluded');
});
test('duplicate custom row ID cannot silently double charge',()=>{
 const q=evaluateModules({inventory,custom:{welding:[
  {key:'custom-1',name:'A',kind:'time'},
  {key:'custom-1',name:'B',kind:'time'}]}});
 assert.equal(q.modules.find(x=>x.id==='welding').status,'error');
 assert.equal(q.modules.find(x=>x.id==='quality').status,'missing');
});
