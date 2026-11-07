import test from 'node:test';import assert from 'node:assert/strict';
import {partsList,partDefaults,partValues} from '../src/lib/parts.mjs';
import {planAutomaticCutting,MACHINES} from '../src/lib/automatic-cutting.mjs';
import {automaticOperations,NORMS,weldPlan,bendAllowance} from '../src/lib/fabrication.mjs';
import {evaluateModules} from '../src/lib/modular-quote.mjs';
const solid=(id,t=5)=>({id,verifiedShapeKey:'same',volumeMm3:100*50*t,massKg:100*50*t*7850/1e9,bboxMm:[100,50,t],areaMm2:10000,
 stockHint:{kind:'plate-candidate',thicknessMm:t,lengthMm:100,widthMm:50},cuttingHint:{kind:'plate-outline',thicknessMm:t,contourMm:300,pierces:1}});
const inventory={count:2,solids:[solid('a'),solid('b')],groups:[{geometryId:'same',quantity:2,massKg:.19625}],totalMassKg:.3925};
test('identical occurrences retain independent material, allowance and supplier decisions',()=>{
 const prefs={a:{...partDefaults(),density:2700,grade:'EN AW-6061',allowances:[3,3,2,2,0,0]},b:{...partDefaults(),route:'purchase',supplierPrice:40}};
 const parts=partsList(inventory,prefs,5);assert.equal(parts[0].massKg,.0675);assert.ok(parts[0].stockMassKg>parts[0].massKg);assert.equal(parts[1].materialCost,0);assert.equal(parts[1].supplierCost,40);assert.equal(inventory.solids[0].massKg,.19625);
 const cut=planAutomaticCutting(parts);assert.deepEqual(cut.rows.map(r=>r.id),['a']);
 const q=evaluateModules({inventory,partMaterials:prefs,materialApproved:true,rates:{materialPriceKg:5,cutting:100},cuttingPlan:cut});
 assert.equal(q.modules.find(m=>m.id==='purchased').knownCostPln,40);
});
test('cooperation can include material or use operator supplied stock, never duplicate full supplier material',()=>{
 const p=partValues(solid('a'),{...partDefaults(),route:'cooperate',supplierPrice:30,includesMaterial:false},5);assert.ok(p.materialCost>0);
 assert.equal(partValues(solid('a'),{...partDefaults(),route:'cooperate',supplierPrice:30,includesMaterial:true},5).materialCost,0);
});
test('six allowances affect only stock; explicit stock mass and zero allowance are preserved',()=>{
 const s=solid('a');const p=partValues(s,{...partDefaults(),allowances:[1,2,3,4,5,6]},5);assert.deepEqual(p.stockDims,[103,57,16]);assert.equal(p.massKg,.19625);
 assert.equal(partValues(s,{...partDefaults(),stockMassKg:1},5).stockMassKg,1);assert.throws(()=>partValues(s,{...partDefaults(),allowances:[-1,0,0,0,0,0]}));
});
test('10 mm boundary, thick plate routing and material restrictions',()=>{
 const inv={solids:[solid('ten',10),solid('eleven',11),solid('thick',60)]};const parts=partsList(inv,{},5);let plan=planAutomaticCutting(parts);
 assert.equal(plan.rows.find(r=>r.id==='ten').method,'laser');assert.equal(plan.rows.find(r=>r.id==='eleven').method,'plasma');assert.equal(plan.rows.find(r=>r.id==='thick').method,'oxy');
 const aluminum=partsList({solids:[solid('thick',60)]},{thick:{...partDefaults(),grade:'EN AW-6061',density:2700}},5);plan=planAutomaticCutting(aluminum);assert.equal(plan.rows[0].minutes,null);assert.notEqual(plan.rows[0].method,'oxy');
});
test('same-thickness laser details share setup and missing contour remains unknown',()=>{
 let p=partsList(inventory,{},5),plan=planAutomaticCutting(p);assert.equal(plan.batches.length,1);assert.equal(plan.rows.reduce((s,r)=>s+r.setupMin,0),15);
 const noContour={...solid('x'),cuttingHint:null};plan=planAutomaticCutting(partsList({solids:[noContour]}, {},5));assert.equal(plan.rows[0].minutes,null);
});
test('saw time uses measured area, cut count and miter correction rather than sheet contour',()=>{
 const s={...solid('tube'),bboxMm:[1000,40,40],stockHint:{kind:'square-hollow',lengthMm:1000,widthMm:40,heightMm:40,wallMm:2,sectionAreaMm2:304}};
 const p=partsList({solids:[s]}, {},5),straight=planAutomaticCutting(p).rows[0];assert.equal(straight.method,'saw');assert.ok(straight.minutes>12);
 p[0].sawAngle=45;assert.ok(planAutomaticCutting(p).rows[0].runMin>straight.runMin);
});
test('contact estimates preserve operator corrections and disabled non-welded interfaces',()=>{
 const contacts={complete:true,candidates:[{id:'a|b',partA:'a',partB:'b',lengthMm:90}]};
 let w=weldPlan(contacts,{},NORMS.welding);assert.ok(w.minutes>0);assert.equal(w.totalLengthMm,90);
 w=weldPlan(contacts,{'a|b':{lengthMm:40,a:2}},NORMS.welding);assert.equal(w.totalLengthMm,40);
 assert.equal(weldPlan(contacts,{'a|b':{enabled:false}},NORMS.welding).minutes,0);
 const parts=partsList(inventory,{a:{...partDefaults(),density:2700},b:{...partDefaults(),density:2700}},5);const auto=automaticOperations(parts,contacts);assert.equal(auto.welds.rows[0].defaultDensity,2700);
});
test('rounded stock corners never cause a press-brake operation without an explicit override',()=>{
 const s={...solid('tube'),stockHint:{kind:'square-hollow'},bendHint:{count:4}};
 let parts=partsList({solids:[s]}, {},5);assert.deepEqual(automaticOperations(parts,null).modules.bending,{setup:0,bends:0});
 parts[0].bendCount=1;assert.ok(automaticOperations(parts,null).modules.bending.bends>0);
});
test('CNC from allowances, gross coating area and transport use explicit editable assumptions',()=>{
 const p=partsList(inventory,{a:{...partDefaults(),allowances:[1,1,0,0,0,0]}},5);
 const n={...NORMS,coating:{...NORMS.coating,enabled:true},logistics:{...NORMS.logistics,enabled:true,distanceKm:100,costKm:4}};
 const auto=automaticOperations(p,null,{},n);assert.ok(auto.modules.cnc.milling>0);assert.equal(auto.areaM2,.02);assert.ok(auto.modules.coating.paint>0);assert.equal(auto.extraRows.logistics[0].autoAmount,400);
 assert.ok(Math.abs(bendAllowance({angleDeg:90,radiusMm:3,thicknessMm:2,kFactor:.4})-Math.PI/2*3.8)<1e-10);
});

test('material prices follow selected grade without per-detail approval or price entry',()=>{
 const prices={'':5,S235JR:7,'1.4301':20};const prefs={a:{...partDefaults(),grade:'S235JR'},b:{...partDefaults(),grade:'1.4301'}};
 const parts=partsList(inventory,prefs,prices);assert.equal(parts[0].price,7);assert.equal(parts[1].price,20);
 const quote=evaluateModules({inventory,partMaterials:prefs,materialPrices:prices,rates:{materialPriceKg:null},edits:{material:{a:{value:999}}}});
 assert.equal(quote.modules.find(m=>m.id==='material').rows[0].value,parts[0].materialCost);
 assert.ok(quote.modules.find(m=>m.id==='material').knownCostPln>0);
 prices.S235JR=10;assert.equal(partsList(inventory,prefs,prices)[0].price,10);
 prices.S235JR=null;assert.equal(partsList(inventory,prefs,prices)[0].materialCost,null);
});
test('weld type edits recalculate welding and postweld while assembly includes tacks and turns',()=>{
 const parts=partsList(inventory,{},5),contacts={complete:true,candidates:[{id:'a|b',partA:'a',partB:'b',lengthMm:1000}]};
 const a=automaticOperations(parts,contacts),b=automaticOperations(parts,contacts,{'a|b':{type:'butt'}});
 assert.ok(a.modules.assembly.tacks>0);assert.ok(a.modules.assembly.turning>0);
 assert.notEqual(a.modules.welding.weld,b.modules.welding.weld);assert.ok(a.modules.welding.clean>0);
 assert.ok(b.modules.postweld.grind>a.modules.postweld.grind);assert.equal(a.modules.postweld.straighten,0);
 const quote=evaluateModules({inventory,partMaterials:{},automation:a});assert.equal(quote.modules.find(m=>m.id==='coating').omitted,true);
});

test('measured groove area drives deposition time and external raw-stock proposal drives saw routing',()=>{
 const contacts={engineVersion:'0.7.1',complete:true,candidates:[{id:'a|b',partA:'a',partB:'b',lengthMm:100,suggestedType:'butt',measuredSectionMm2:64,preparation:'V'}]};
 const parts=partsList(inventory,{},5);const auto=automaticOperations(parts,contacts);
 assert.equal(auto.welds.rows[0].type,'butt');assert.equal(auto.welds.rows[0].sectionMm2,64);
 const edited=automaticOperations(parts,contacts,{'a|b':{sectionMm2:80}});assert.ok(edited.welds.minutes>auto.welds.minutes);
 const tube={...solid('raw'),stockHint:{kind:'unknown',rawStockCandidate:{kind:'square-hollow',widthMm:40,heightMm:40,wallMm:2,lengthMm:1000,sectionAreaMm2:304,confidence:'raw-stock-candidate',localDimsMm:[1000,40,40]}}};
 const rows=partsList({solids:[tube]}, {},5);const plan=planAutomaticCutting(rows);assert.equal(plan.rows[0].method,'saw');assert.ok(plan.rows[0].minutes>0);assert.deepEqual(rows[0].dims,[1000,40,40]);
});

test('short profile length remains the first allowance dimension instead of the longest bounding span',()=>{
 const s={...solid('stub'),volumeMm3:6080,bboxMm:[40,40,20],stockHint:{kind:'square-hollow',lengthMm:20,widthMm:40,heightMm:40,wallMm:2,sectionAreaMm2:304,localDimsMm:[40,40,20]}};
 const p=partValues(s,{...partDefaults(),allowances:[2,0,0,0,0,0]},5);assert.deepEqual(p.dims,[20,40,40]);assert.deepEqual(p.stockDims,[22,40,40]);
});

test('measured polygonal profile uses actual 15 mm2 section for saw cut, not 5x5 bounding area',()=>{
 const s={...solid('rib'),bboxMm:[5,5,50],volumeMm3:750,
  stockHint:{kind:'polygon-bar',widthMm:5,heightMm:5,sectionAreaMm2:15,lengthMm:50,sideCount:4,
   confidence:'cross-section-consistent',source:'five B-Rep sections'}};
 const parts=partsList({count:1,solids:[s],groups:[],totalMassKg:750*7850/1e9},{},5);
 assert.deepEqual(parts[0].dims,[50,5,5]);
 assert.ok(Math.abs(parts[0].stockMassKg-750*7850/1e9)<1e-9);
 const cut=planAutomaticCutting(parts);
 assert.equal(cut.rows[0].method,'saw');
 assert.equal(cut.rows[0].sectionArea,15);
 assert.ok(cut.rows[0].minutes>0);
 assert.equal(automaticOperations(parts,null).bendRows[0].count,0);
});
