import test from 'node:test';
import assert from 'node:assert/strict';
import {mergeProjectFiles,preferredStep,moduleReport,csvCell} from '../src/lib/project-files.mjs';
import {defaultMaterial,groupMaterial} from '../src/lib/part-materials.mjs';
import {evaluateModules} from '../src/lib/modular-quote.mjs';
import {DEFAULT_RATES} from '../src/lib/quote-modules/index.mjs';
const inventory={count:2,totalMassKg:15.7,solids:[1,2].map(i=>({id:'solid-'+i,verifiedShapeKey:'A',volumeMm3:1e6,massKg:7.85,bboxMm:[1000,100,10]})),groups:[{geometryId:'A',quantity:2,massKg:7.85}]};
test('dropped files append, deduplicate Windows paths, and preserve selected model',()=>{
 const all=mergeProjectFiles(['C:\\job\\part.STEP'],['c:/job/part.step','C:/job/main.stp','C:/job/drawing.pdf','C:/job/notes.txt']);
 assert.equal(all.length,3);assert.equal(preferredStep(all,'C:\\job\\part.STEP'),'C:\\job\\part.STEP');assert.equal(preferredStep(all),'C:/job/main.stp');
});
test('blank material uses steel density without assigning a grade',()=>{
 const pref=defaultMaterial();assert.equal(pref.grade,'');
 const m=groupMaterial(inventory,inventory.groups[0],pref);assert.ok(Math.abs(m.totalMassKg-15.7)<1e-9);assert.equal(m.costPln,null);
 const aluminum=groupMaterial(inventory,inventory.groups[0],{...pref,density:2700});assert.ok(Math.abs(aluminum.totalMassKg-5.4)<1e-9);
});
test('allowance increases stock only; manual stock mass is independent',()=>{
 const g=inventory.groups[0];const m=groupMaterial(inventory,g,{allowStart:3,allowEnd:3},5);
 assert.ok(Math.abs(m.stockMassKg-7.85*1.006)<1e-9);assert.ok(Math.abs(m.massKg-7.85)<1e-9);
 assert.equal(groupMaterial(inventory,g,{stockMassKg:10},5).costPln,100);
 assert.throws(()=>groupMaterial(inventory,g,{density:0}));assert.throws(()=>groupMaterial(inventory,g,{density:1e308,stockMassKg:1e308}));
});
test('material cost accepts deliberately blank grade after density and scope approval',()=>{
 const q=evaluateModules({inventory,rates:{...DEFAULT_RATES,materialPriceKg:5},partMaterials:{A:defaultMaterial()},materialApproved:true});
 assert.equal(q.modules[0].knownCostPln,78.5);assert.equal(q.modules[0].status,'review');
});
test('export preserves missing operations and manual overrides',()=>{
 const q=evaluateModules({inventory,edits:{welding:{weld:{value:0}}}});const r=moduleReport(q,{step:'part.step'});
 assert.equal(r.complete,false);assert.equal(r.automatedQuoteVerified,false);
 const weld=r.modules.find(m=>m.id==='welding');assert.equal(weld.rows.find(r=>r.name==='Wykonanie spoin').value,0);
 assert.equal(weld.rows[0].value,null);assert.ok(csvCell('=SUM(A1)').startsWith('"\''));
});
