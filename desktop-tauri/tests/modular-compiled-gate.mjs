/** Compiled backend -> real STEP inventory -> isolated costing integration.
 * Input MUST be produced by the actual bundled ds-cad-engine.exe in the
 * Windows workflow, never by a mock STEP inventory.
 */
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateStepBom} from '../src/lib/inventory-validate.mjs';
import {evaluateModules} from '../src/lib/modular-quote.mjs';
import {DEFAULT_RATES} from '../src/lib/quote-modules/index.mjs';

const input=process.argv[2];
if(!input)throw Error('Expected compiled CAD engine inventory JSON path');
const inventory=validateStepBom(JSON.parse(readFileSync(input,'utf-8')));
assert.equal(inventory.count,1);
assert.equal(inventory.groups.length,1);
assert.ok(inventory.totalMassKg>0);
const blank=evaluateModules({inventory});
assert.equal(blank.modules.length,12);
assert.equal(blank.verifiedCostPln,null);
assert.equal(blank.modules.find(x=>x.id==='welding').status,'missing');
const quote=evaluateModules({
 inventory,
 rates:{...DEFAULT_RATES,welding:200,materialPriceKg:10},
 materialApproved:true,
 grade:'S355',
 edits:{welding:{setup:{value:0.5},weld:{value:2},clean:{value:0.25}}}
});
assert.equal(quote.modules[0].rows[0].costPln,inventory.totalMassKg*10);
assert.equal(quote.modules.find(x=>x.id==='welding').knownCostPln,550);
assert.equal(quote.modules.find(x=>x.id==='welding').status,'review');
assert.equal(quote.complete,false);
assert.equal(quote.fullQuoteVerified,false);
console.log('COMPILED_CAD_TO_MODULAR_COST_GATE_PASS',JSON.stringify({
 solids:inventory.count,groups:inventory.groups.length,
 massKg:inventory.totalMassKg,manualWeldKnownPln:550,
 source:'bundled ds-cad-engine.exe STEP inventory',
 fullAutomaticQuote:false
}));
