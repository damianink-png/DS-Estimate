import test from 'node:test';
import assert from 'node:assert/strict';
import {estimateProject} from '../src/lib/estimate.mjs';

const quote = (cut) => estimateProject({parts:[{geometryId:'cut-test',quantity:2,features:{cut}}]});

test('pierce count alone is not proof of measured cutting length',()=>{
 const result=quote({pierces:3});
 assert.equal(result.rows[0].routingEvidence,false);
 assert.equal(result.missingRoutingOccurrences,2);
 assert.equal(result.routedCostPln,null);
 assert.equal(result.fullQuoteVerified,false);
});

test('measured contour certifies routing input, but not full quote',()=>{
 const result=quote({contourMm:120,pierces:3});
 assert.equal(result.rows[0].routingEvidence,true);
 assert.equal(result.missingRoutingOccurrences,0);
 assert.equal(result.fullQuoteVerified,false);
});

test('explicit zero contour remains an accepted measurement',()=>{
 const result=quote({contourMm:0,pierces:0});
 assert.equal(result.rows[0].routingEvidence,true);
 assert.equal(result.fullQuoteVerified,false);
});
