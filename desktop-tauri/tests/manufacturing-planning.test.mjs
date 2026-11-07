import test from 'node:test';import assert from 'node:assert/strict';
import {partsList} from '../src/lib/parts.mjs';import {automaticOperations,bendEstimate,NORMS} from '../src/lib/fabrication.mjs';
const close=(a,b)=>assert.ok(Math.abs(a-b)<1e-7,`${a} != ${b}`);
const plate=(id,x=100,y=50,t=10)=>({id,name:id,verifiedShapeKey:id,volumeMm3:x*y*t,bboxMm:[x,y,t],stockHint:{kind:'plate-candidate',localDimsMm:[x,y,t],thicknessMm:t}});
const contacts=(rows=[])=>({complete:true,candidates:rows});
const joint=(a,b)=>({id:a+'|'+b,partA:a,partB:b,lengthMm:100});
test('raw profile and rectangular sheet blank restore material removed from finished geometry',()=>{
 const tube={...plate('tube'),volumeMm3:302880,bboxMm:[1000,40,40],stockHint:{kind:'unknown',rawStockCandidate:{kind:'square-hollow',lengthMm:1000,widthMm:40,heightMm:40,sectionAreaMm2:304,removedVolumeMm3:1120}}};
 const hole={...plate('hole',330,210,15),volumeMm3:(330*210-Math.PI*100/4)*15};const p=partsList({solids:[tube,hole]});
 close(p[0].stockMassKg,2.3864);close(p[0].massKg,2.377608);close(p[1].stockMassKg,8.160075);
 const auto=automaticOperations(p,contacts());close(auto.modules.cnc.milling*60,1.12/8);close(auto.modules.cnc.program*60,20);
});
test('connected weld groups exclude isolated parts and charge setup once per group',()=>{
 const p=partsList({solids:['a','b','c','d','isolated'].map(id=>plate(id))});
 const auto=automaticOperations(p,contacts([joint('a','b'),joint('c','d')]));
 assert.equal(auto.groups.length,2);close(auto.modules.assembly.fixtures*60,40);close(auto.modules.assembly.fitup*60,10);close(auto.modules.assembly.turning*60,1.2);
 const disabled=automaticOperations(p,contacts([joint('a','b')]),{'a|b':{enabled:false}});close(disabled.modules.assembly.fixtures,0);close(disabled.modules.welding.setup,0);
});
test('purchase or cooperation does not erase joining work of a supplied plate',()=>{
 const p=partsList({solids:['a','b','c'].map(id=>plate(id))},{b:{route:'purchase'},c:{route:'cooperate'}});
 const a=automaticOperations(p,contacts([joint('a','b'),joint('a','c')]));assert.equal(a.jointCount,2);assert.ok(a.modules.assembly.tacks>0);assert.ok(a.modules.welding.weld>0);
});
test('partial contact analysis cannot silently yield complete mounting and welding times',()=>{
 const a=automaticOperations(partsList({solids:[plate('a'),plate('b')]}),{complete:false,candidates:[joint('a','b')]});
 assert.equal(a.modules.assembly.fitup,null);assert.equal(a.modules.welding.weld,null);assert.equal(a.modules.postweld.grind,null);assert.equal(a.modules.quality.visual,null);
});
test('one shared part on two welds is counted once; large and heavy groups increase handling',()=>{
 const p=partsList({solids:['a','b','c'].map(id=>plate(id))});const a=automaticOperations(p,contacts([joint('a','b'),joint('b','c')]));close(a.modules.assembly.fitup*60,7.5);
 const heavy=p.map(x=>({...x,massKg:100,dims:[3000,50,10]}));const b=automaticOperations(heavy,contacts([joint('a','b'),joint('b','c')]));assert.ok(b.modules.assembly.turning>a.modules.assembly.turning);
});
test('measured V preparation adds actual bevel volume without counting assembly gap as machining',()=>{
 const p=partsList({solids:[plate('a'),plate('b')]});const j={...joint('a','b'),suggestedType:'butt',measuredSectionMm2:84,groove:{hasBevel:true,sectionMm2:84,rootGapMm:2,thicknessMm:10}};
 const a=automaticOperations(p,contacts([j]));close(a.bevels[0].volumeMm3,6400);close(a.modules.cnc.bevel*60,6.4/6);close(a.modules.cnc.bevelSetup*60,10);
});
test('bend batches share setup, but distinct thicknesses/radii need another setup',()=>{
 const sheet=(id,t=3,length=100)=>({...plate(id),stockHint:{kind:'bent-plate',thicknessMm:t},bendHint:{count:1,bends:[{angleDeg:90,radiusMm:7,thicknessMm:t,lengthMm:length}]}});
 let p=partsList({solids:[sheet('a'),sheet('b')]});let a=automaticOperations(p,contacts());close(a.modules.bending.setup*60,20);close(a.modules.bending.bends*60,2);
 p=partsList({solids:[sheet('a'),sheet('b',12,2000)]});a=automaticOperations(p,contacts());close(a.modules.bending.setup*60,40);assert.ok(a.modules.bending.bends*60>2);
 assert.ok(bendEstimate({...p[0],massKg:100}).minutes>bendEstimate(p[0]).minutes);
});
test('small welds do not automatically require straightening or fillet grinding',()=>{
 const p=partsList({solids:[plate('a'),plate('b')]});let a=automaticOperations(p,contacts([joint('a','b')]));close(a.modules.postweld.straighten,0);close(a.modules.postweld.grind,0);
 const j={...joint('a','b'),lengthMm:1000,suggestedType:'butt',measuredSectionMm2:64};a=automaticOperations(p,contacts([j]));assert.ok(a.modules.postweld.straighten>0);close(a.modules.postweld.grind*60,4.5);
});

test('standard hardware is proposed as purchased; explicit routing always wins',()=>{
 const s={...plate('bolt'),name:'M6x16 - DIN912 v4:1'};assert.equal(partsList({solids:[s]})[0].route,'purchase');assert.equal(partsList({solids:[s]},{bolt:{route:'make'}})[0].route,'make');assert.equal(partsList({solids:[{...s,name:'Bottle Jack_2912T12'}]})[0].route,'purchase');assert.equal(partsList({solids:[{...s,name:'Support Leg_Electrical Enclosure Support Leg'}]})[0].route,'make');
});

test('unknown vendor extrusion corner radii do not invent press-brake operations',()=>{
 const s={...plate('slot'),stockHint:{kind:'unknown'},bendHint:{count:4,bends:[]}};const p=partsList({solids:[s]})[0];assert.equal(bendEstimate(p).count,null);assert.equal(bendEstimate({...p,bendCount:2}).count,2);
});
