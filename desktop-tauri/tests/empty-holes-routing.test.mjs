import test from 'node:test';
import assert from 'node:assert/strict';
import {estimateProject} from '../src/lib/estimate.mjs';

test('empty CNC holes list is not routing evidence',()=>{
 const result=estimateProject({parts:[{geometryId:'plate',quantity:2,features:{cnc:{holes:[]}}}]});
 assert.equal(result.rows[0].routingEvidence,false);
 assert.equal(result.missingRoutingOccurrences,2);
 assert.equal(result.routedCostPln,null);
 assert.equal(result.routingStatus,'PARTIAL');
});

test('explicit zero removal is measured, unlike empty holes',()=>{
 const result=estimateProject({parts:[{geometryId:'plate',features:{cnc:{removedCm3:0,holes:[]}}}]});
 assert.equal(result.rows[0].routingEvidence,true);
 assert.equal(result.missingRoutingOccurrences,0);
 assert.equal(result.routingStatus,'ROUTINGS_ESTIMATED');
 assert.equal(result.fullQuoteVerified,false);
});
