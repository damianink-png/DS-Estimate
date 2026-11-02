import test from 'node:test';
import assert from 'node:assert/strict';
import {extractManufacturingRequirements} from '../src/lib/document-requirements.mjs';
test('annotates explicit technical requirements without inventing machining or weld length',()=>{
 const text=['MATERIAŁ: S355J2+N','Proces MAG 135 / EN ISO 5817 B','UT 100% ISO 17640','Przygotowanie ISO 8501-1 Sa 2,5','RAL 7016, DFT 240 µm','Otwory H7, chropowatość Ra 3,2','ISO 2768-m'].join('\n');
 const r=extractManufacturingRequirements(text);
 const ids=r.requirements.map(x=>x.id);
 for(const id of ['steel-grade','welding-quality','welding-process','ultrasonic-test','surface-prep','painting','roughness','fits','general-tolerances'])assert.ok(ids.includes(id),id);
 assert.ok(r.requirements.every(x=>!x.quotationReady&&x.hits[0].line>=1));
 assert.equal(r.requirements.find(x=>x.id==='steel-grade').hits[0].value,'S355J2+N');
});
test('empty or harmless PDF text does not invent processing or claim ready',()=>{
 const r=extractManufacturingRequirements('PART A\n 100 x 50\n SHEET 2');
 assert.equal(r.requirements.length,0);
 assert.equal(r.needsReview,false);
 assert.throws(()=>extractManufacturingRequirements(null),TypeError);
});
