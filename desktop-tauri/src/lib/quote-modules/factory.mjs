/** An operation adapter owns only its manufacturing operations, not CAD import. */
export function timedModule(id,title,operations,{rateKey=id,detail='Czasy technologiczne wymagają potwierdzenia.'}={}){
 return Object.freeze({
  id,title,rateKey,detail,
  rows:()=>operations.map(([key,name,detail])=>({
   key,name,detail:detail||'Wprowadź czas wykonania',kind:'time',autoHours:null,
   evidence:'manual-required'
  }))
 });
}
export function fixedModule(id,title,operations,{detail='Wprowadź kwoty z oferty dostawcy.'}={}){
 return Object.freeze({id,title,rateKey:null,detail,
  rows:()=>operations.map(([key,name])=>({
   key,name,detail:'Koszt zakupowy [zł]',kind:'amount',autoAmount:null,
   evidence:'manual-required'
  }))
 });
}
