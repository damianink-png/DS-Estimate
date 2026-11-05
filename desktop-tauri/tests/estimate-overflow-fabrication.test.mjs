import test from 'node:test';
import assert from 'node:assert/strict';
import {estimateWelding, estimateAssembly, estimateFabrication} from '../src/lib/estimate.mjs';

test('welding rejects finite inputs that overflow deposited mass', () => {
 assert.throws(() => estimateWelding({joints:[{lengthMm:1e308, throatMm:1e308}]}), RangeError);
});
test('welding rejects overflow of otherwise finite quoted cost', () => {
 assert.throws(() => estimateWelding({joints:[], setupMin:1e308, ratePerHour:1e308}), RangeError);
});
test('assembly rejects overflow of operation duration', () => {
 assert.throws(() => estimateAssembly({operations:[{count:1e308,minutesEach:1e308}]}), RangeError);
});
test('fabrication rejects overflow of aggregate quote', () => {
 assert.throws(() => estimateFabrication({assembly:{operations:[{count:1,minutesEach:1e308}]},ratePerHour:1e308}), RangeError);
});
test('valid explicit welding and assembly routing remains calculable', () => {
 const weld=estimateWelding({joints:[{lengthMm:100,throatMm:3}]});
 const assembly=estimateAssembly({operations:[{count:2,minutesEach:5}]});
 assert.ok(Number.isFinite(weld.cost));
 assert.equal(assembly.totalMin,10);
});
