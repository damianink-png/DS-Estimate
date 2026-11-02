import test from 'node:test';
import assert from 'node:assert/strict';
import {calculateWeld} from '../src/lib/welding.mjs';
test('zero length',()=>{const r=calculateWeld({lengthM:0,throatMm:4,depositionKgH:2,arcFactor:.35,setupMin:20});assert.equal(r.massKg,0);assert.equal(r.totalMinutes,20)});
test('8m a4 steel',()=>{const r=calculateWeld({lengthM:8,throatMm:4,depositionKgH:2,arcFactor:.35,setupMin:20});assert.ok(Math.abs(r.massKg-1.0048)<1e-8);assert.ok(r.totalMinutes>100)});
test('invalid deposition',()=>assert.throws(()=>calculateWeld({lengthM:8,throatMm:4,depositionKgH:0,arcFactor:.35,setupMin:20}),RangeError));