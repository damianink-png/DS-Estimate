import test from 'node:test';
import assert from 'node:assert/strict';
import { estimateProject } from '../src/lib/estimate.mjs';

const part = features => ({ geometryId: 'plate', quantity: 2, features });

test('one measured route cannot certify a second declared but empty route', () => {
 const quote = estimateProject({ parts: [part({cut:{contourMm:100},cnc:{}})] });
 assert.equal(quote.rows[0].routingEvidence,false);
 assert.equal(quote.missingRoutingOccurrences,2);
 assert.equal(quote.routedCostPln,null);
 assert.equal(quote.routingStatus,'PARTIAL');
});

test('each declared route with explicit zero measurement counts as routing evidence', () => {
 const quote = estimateProject({parts:[part({cut:{contourMm:0},cnc:{removedCm3:0},bend:{bends:0}})]});
 assert.equal(quote.rows[0].routingEvidence,true);
 assert.equal(quote.missingRoutingOccurrences,0);
 assert.equal(quote.routingStatus,'ROUTINGS_ESTIMATED');
 assert.equal(quote.fullQuoteVerified,false);
});

test('empty and missing routing do not certify a quote', () => {
 for(const features of [{},{cnc:{holes:[]}}, {cut:{pierces:1},cnc:{holes:[]}}]){
  const quote=estimateProject({parts:[part(features)]});
  assert.equal(quote.rows[0].routingEvidence,false);
  assert.equal(quote.routedCostPln,null);
 }
});
