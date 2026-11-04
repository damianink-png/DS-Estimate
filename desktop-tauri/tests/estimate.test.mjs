import test from 'node:test';import assert from 'node:assert/strict';import {estimateCnc,estimateCut,estimateBending,estimateProject} from '../src/lib/estimate.mjs';
test('CNC milling + drilling + setup',()=>{const r=estimateCnc({removedCm3:80,removalCm3Min:10,holes:[{depthMm:20,feedMmMin:100,count:5}],setupMin:12,toolChanges:2,toolChangeMin:1});assert.equal(r.totalMin,23)});
test('Cut includes pierces and rapid',()=>{assert.equal(estimateCut({contourMm:3000,feedMmMin:1000,pierces:6,pierceSec:10,rapidMm:1000,rapidMmMin:1000,setupMin:5}).totalMin,10)});
test('Bending includes setup',()=>{assert.equal(estimateBending({bends:6,secondsPerBend:30,setupMin:10}).totalMin,13)});
test('Same geometry computed once',()=>{const features={cnc:{removedCm3:100,removalCm3Min:10,setupMin:0}};const r=estimateProject({parts:[{geometryId:'A',quantity:3,features},{geometryId:'A',quantity:2,features}]});assert.equal(r.uniqueCalculations,1);assert.equal(r.totalMin,50)});
test('Invalid feed rejected',()=>assert.throws(()=>estimateCut({feedMmMin:0}),RangeError));
test('duplicate parts share one setup, not setup multiplied by quantity',()=>{
 const r=estimateProject({ratePerHour:60,parts:[
  {geometryId:'plate',quantity:3,features:{cnc:{removedCm3:60,removalCm3Min:10,setupMin:30}}},
  {geometryId:'plate',quantity:2,features:{cnc:{removedCm3:60,removalCm3Min:10,setupMin:30}}}
 ]});
 assert.equal(r.rows[0].totalMin,48); // 30 + 3 * 6
 assert.equal(r.rows[1].totalMin,12); // 2 * 6, no second setup
 assert.equal(r.rows[1].batchSetupMin,0);
 assert.equal(r.totalMin,60);
 assert.equal(r.totalCost,60);
 assert.equal(r.uniqueCalculations,1);
});
test('different technology routings require separate setup, valid defaults preserved',()=>{
 const r=estimateProject({ratePerHour:60,parts:[
  {geometryId:'part',quantity:2,features:{cut:{contourMm:1000,feedMmMin:1000,setupMin:10}}},
  {geometryId:'part',quantity:3,features:{bend:{bends:2,secondsPerBend:30,setupMin:15}}}
 ]});
 assert.equal(r.totalMin,10+2+15+3);
 assert.equal(r.uniqueCalculations,2);
});

test('missing routing cannot silently become a complete zero-cost estimate',()=>{
 const r=estimateProject({parts:[{geometryId:'unknown',quantity:5}]});
 assert.equal(r.totalCost,0); // Legacy numeric subtotal remains compatible.
 assert.equal(r.knownCostPln,0);
 assert.equal(r.routedCostPln,null);
 assert.equal(r.missingRoutingOccurrences,5);
 assert.equal(r.routingStatus,'PARTIAL');
 assert.equal(r.fullQuoteVerified,false);
});
test('mixed project retains known subtotal, but complete routing price stays unknown',()=>{
 const r=estimateProject({parts:[
  {geometryId:'A',quantity:2,features:{cnc:{removedCm3:10,removalCm3Min:10,setupMin:0}}},
  {geometryId:'B',quantity:3,features:{}}
 ]});
 assert.equal(r.missingRoutingOccurrences,3);
 assert.equal(r.routedCostPln,null);
 assert.ok(r.knownCostPln>0);
 assert.equal(r.rows[1].routingEvidence,false);
});
test('complete explicit routing and empty inventory are distinguished',()=>{
 const known=estimateProject({parts:[{geometryId:'A',quantity:2,features:{
  cnc:{removedCm3:10,removalCm3Min:10,setupMin:0}}}]});
 assert.equal(known.missingRoutingOccurrences,0);
 assert.equal(known.routingStatus,'ROUTINGS_ESTIMATED');
 assert.equal(known.routedCostPln,known.totalCost);
 assert.equal(known.fullQuoteVerified,false);
 const empty=estimateProject();
 assert.equal(empty.routingStatus,'NO_PARTS');
 assert.equal(empty.routedCostPln,null);
});

test('project rejects invalid rates even when inventory is empty',()=>{
 for(const ratePerHour of [-1,NaN,Infinity])assert.throws(()=>estimateProject({parts:[],ratePerHour}),RangeError);
 assert.equal(estimateProject({parts:[],ratePerHour:0}).totalCost,0);
});
test('project rejects malformed parts collections before estimating',()=>{
 for(const parts of [null,{},'parts'])assert.throws(()=>estimateProject({parts}),TypeError);
});

test('default-only operation does not certify missing routing evidence',()=>{
 const r=estimateProject({parts:[{geometryId:'unknown',quantity:2,features:{cnc:{}}}]});
 assert.equal(r.rows[0].routingEvidence,false);
 assert.equal(r.missingRoutingOccurrences,2);
 assert.equal(r.routedCostPln,null);
 assert.equal(r.fullQuoteVerified,false);
});
test('explicit measured zero is distinct from absent routing measurement',()=>{
 const r=estimateProject({parts:[{geometryId:'zero',features:{cut:{contourMm:0,setupMin:0}}}]});
 assert.equal(r.rows[0].routingEvidence,true);
 assert.equal(r.missingRoutingOccurrences,0);
 assert.equal(r.routingStatus,'ROUTINGS_ESTIMATED');
 assert.equal(r.fullQuoteVerified,false);
});


test('project rejects unsafe integer quantities before pricing',()=>{
 for(const quantity of [0,-1,1.5,Number.MAX_SAFE_INTEGER+1,Infinity,NaN]){
  assert.throws(()=>estimateProject({parts:[{geometryId:'A',quantity,features:{cut:{contourMm:10}}}]}),RangeError);
 }
 assert.equal(estimateProject({parts:[{geometryId:'A',quantity:Number.MAX_SAFE_INTEGER,features:{cut:{contourMm:0,setupMin:0}}}]}).occurrences,Number.MAX_SAFE_INTEGER);
});
test('project rejects aggregate occurrence overflow across valid rows',()=>{
 assert.throws(()=>estimateProject({parts:[
  {geometryId:'A',quantity:Number.MAX_SAFE_INTEGER,features:{cut:{contourMm:0,setupMin:0}}},
  {geometryId:'B',quantity:1,features:{cut:{contourMm:0,setupMin:0}}}
 ]}),RangeError);
});
