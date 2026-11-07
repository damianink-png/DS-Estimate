import test from 'node:test';
import assert from 'node:assert/strict';
import {partDefaults,partValues} from '../src/lib/parts.mjs';
const close=(actual,expected)=>assert.ok(Math.abs(actual-expected)<1e-9,`${actual} != ${expected}`);
function rhs(){
 return {id:'rhs',name:'RHS 40x40x2',volumeMm3:304000,
  bboxMm:[1000,40,40],stockHint:{kind:'square-hollow',lengthMm:1000,
   widthMm:40,heightMm:40,wallMm:2,sectionAreaMm2:304}};
}
test('transverse allowances on a hollow section retain the inner void',()=>{
 const base=partValues(rhs(),partDefaults());
 const expanded=partValues(rhs(),{...partDefaults(),allowances:[0,0,2,0,0,0]});
 close(base.stockMassKg,304000/1e9*7850);
 close(expanded.stockMassKg,312000/1e9*7850);
 close(expanded.massKg,base.massKg);
 assert.match(expanded.stockSource,/zachowana grubość ścianki/);
 // Full 42x40 outer rectangle added as solid would massively overprice the tube.
 assert.ok(expanded.stockMassKg<base.stockMassKg*1.04);
});
test('length allowances on a hollow section do not fill its cavity',()=>{
 const expanded=partValues(rhs(),{...partDefaults(),allowances:[5,0,0,0,0,0]});
 close(expanded.stockMassKg,304*1005/1e9*7850);
});
test('round tube diameter change retains wall, rather than expanding to a solid cylinder',()=>{
 const area=Math.PI*(40*2-2**2);
 const tube={id:'tube',name:'Tube',volumeMm3:area*1000,
  bboxMm:[1000,40,40],stockHint:{kind:'round-tube',diameterMm:40,
   wallMm:2,lengthMm:1000,sectionAreaMm2:area}};
 const blank=partValues(tube,{...partDefaults(),allowances:[0,0,2,0,2,0]});
 close(blank.stockMassKg,(area+Math.PI*2*2)*1000/1e9*7850);
});
test('open section crosswise allowance cannot silently add a filled rectangle',()=>{
 const profile={...rhs(),stockHint:{kind:'channel',lengthMm:1000,widthMm:40,
  heightMm:40,sectionAreaMm2:304}};
 assert.throws(()=>partValues(profile,{...partDefaults(),
  allowances:[0,0,3,0,0,0]}),/Naddatek poprzeczny profilu/);
 const manual=partValues(profile,{...partDefaults(),
  allowances:[0,0,3,0,0,0],stockMassKg:3.5});
 close(manual.stockMassKg,3.5);
 close(manual.massKg,304000/1e9*7850);
});
