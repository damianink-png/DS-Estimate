import test from 'node:test';import assert from 'node:assert/strict';
import {partsList,commercialUnits,preferenceFor} from '../src/lib/parts.mjs';
import {automaticOperations,NORMS} from '../src/lib/fabrication.mjs';import {evaluateModules} from '../src/lib/modular-quote.mjs';
const solid=(id,product='occ-1',definition='def-1')=>({id,name:'Same product name',volumeMm3:10000,bboxMm:[100,10,10],verifiedShapeKey:'same-shape',productIdentityReliable:true,productOccurrenceKey:product,productDefinitionKey:definition,bodyCount:2,stockHint:{kind:'rectangular-bar',lengthMm:100,widthMm:10,heightMm:10,sectionAreaMm2:100}});
const inv={solids:[solid('a'),solid('b')]};
const joint={id:'a|b',partA:'a',partB:'b',lengthMm:100};const contacts={complete:true,geometryValid:true,candidates:[joint]};
test('new XCAF name clues preserve the existing hardware purchase proposal and explicit user override',()=>{
 const item={...solid('named'),name:'Śruba ISO 4017 M10x95',
  nameEvidence:{status:'name-only-unverified',normaliaFamily:'hex-head',nominalDesignation:'M10x95'},
  normaliaHint:{status:'geometry-candidate',families:['hex-head'],catalogCandidates:[{designation:'M10x95'}]}};
 assert.equal(preferenceFor(item).route,'purchase'); // Existing suggestion, not certification
 assert.equal(preferenceFor(item,{named:{route:'make'}}).route,'make'); // Explicit preference wins
 assert.equal(preferenceFor({...item,name:'Profil 40x40x2'}).route,'make');
});

test('five bodies of a single STEP product produce one supplier charge',()=>{
 const inventory={solids:['a','b','c','d','e'].map(id=>solid(id))},prefs=Object.fromEntries(inventory.solids.map(s=>[s.id,{route:'purchase',supplierPrice:40}]));
 const rows=evaluateModules({inventory,partMaterials:prefs}).modules.find(m=>m.id==='purchased').rows;
 assert.equal(rows.length,1);assert.equal(rows[0].value,40);assert.match(rows[0].detail,/5 brył/);
});
test('equal names or geometry never merge two product occurrences',()=>{
 const parts=partsList({solids:[solid('a','occ-1'),solid('b','occ-2')]},{a:{route:'purchase',supplierPrice:40},b:{route:'purchase',supplierPrice:40}});
 assert.equal(commercialUnits(parts).length,2);assert.equal(commercialUnits(parts).reduce((s,u)=>s+u.supplierCost,0),80);
});
test('conflicting body prices or routes do not silently pick a supplier price',()=>{
 const parts=partsList(inv,{a:{route:'purchase',supplierPrice:40},b:{route:'purchase',supplierPrice:50}});assert.equal(commercialUnits(parts)[0].supplierCost,null);assert.equal(commercialUnits(parts)[0].conflict,true);
});
test('inspection counts first piece, repetitions and supplier units rather than all bodies',()=>{
 const inventory={solids:[solid('a','make-1'),solid('b','make-2'),solid('c','make-3'),solid('d','buy-1','pump'),solid('e','buy-1','pump')]};
 const p=partsList(inventory,{d:{route:'purchase'},e:{route:'purchase'}});const a=automaticOperations(p,{complete:true,candidates:[]});
 assert.deepEqual(a.inspection,{firstCount:1,repeatCount:2,supplierSamples:1,suppliedUnits:1,suppliedTypes:1});assert.equal(a.modules.quality.dimensions*60,11.75);
});
test('unknown drawing requirements stay unknown until explicitly configured',()=>{
 const p=partsList(inv),a=automaticOperations(p,contacts);assert.equal(a.modules.cnc.drilling,null);assert.equal(a.modules.quality.ndt,null);assert.equal(a.modules.postweld.machining,null);
 const n={...NORMS,cnc:{...NORMS.cnc,drillingMode:1},quality:{...NORMS.quality,ndtMode:1},postweld:{...NORMS.postweld,machiningMode:1}};
 const b=automaticOperations(p,contacts,{},n);assert.equal(b.modules.cnc.drilling,0);assert.equal(b.modules.quality.ndt,0);assert.equal(b.modules.postweld.machining,0);
});
test('required NDT is a separate editable norm and partial geometry cannot be priced as complete',()=>{
 const p=partsList(inv),n={...NORMS,quality:{...NORMS.quality,ndtMode:2}};
 const a=automaticOperations(p,contacts,{},n);assert.equal(a.modules.quality.ndt*60,21);
 const b=automaticOperations(p,{...contacts,geometryValid:false}, {},n);assert.equal(b.modules.welding.weld,null);assert.equal(b.modules.quality.ndt,null);assert.equal(b.modules.assembly.fitup,null);
});
test('unsupported manufacturing geometry does not become zero milling time',()=>{
 const p=partsList({solids:[{...solid('a'),stockHint:{kind:'unknown'}}]}),a=automaticOperations(p,{complete:true,candidates:[]});assert.equal(a.modules.cnc.milling,null);assert.equal(a.modules.cnc.program,null);assert.deepEqual(a.unknownMachiningPartIds,['a']);
});
test('transport charge is independent of an unknown travel duration',()=>{
 const a=automaticOperations(partsList(inv),contacts,{}, {...NORMS,logistics:{...NORMS.logistics,enabled:true,distanceKm:100}});
 assert.equal(a.modules.logistics.ship,null);assert.equal(a.extraRows.logistics[0].autoAmount,400);
});

test('a named fastener hole or parent assembly never becomes a purchased product',()=>{
 for(const name of ['Bolt hole M10','ISO 4017 M10 mounting hole',
                     'DIN 933 M8 Bohrung','Otwór pod śrubę M8',
                     'Bolt ISO 4017 M20 assembly']){
  const item={...solid('feature'),name};
  assert.equal(preferenceFor(item).route,'make',name);
  assert.equal(preferenceFor(item,{feature:{route:'purchase'}}).route,'purchase',name);
 }
});
