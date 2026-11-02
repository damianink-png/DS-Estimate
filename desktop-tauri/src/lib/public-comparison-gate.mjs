/**
 * Gate for the public four-project benchmark. A successful CAD import is NOT
 * proof of a complete quote, but a missing/failed project or quote input must
 * never be silently accepted because two other projects passed.
 */
export function assessPublicComparison(results, expectedIds){
 if(!Array.isArray(results)||!Array.isArray(expectedIds)||expectedIds.length===0)
  return {ok:false,errors:['Missing benchmark manifest or results']};
 const errors=[];
 const expected=new Set(expectedIds);
 if(expected.size!==expectedIds.length)errors.push('Duplicate expected project ID');
 const actual=new Set();
 for(const r of results){
  if(!r || typeof r.id!=='string' || !expected.has(r.id)){
   errors.push('Unexpected or invalid project '+String(r?.id));continue;
  }
  if(actual.has(r.id))errors.push('Duplicate project '+r.id);
  actual.add(r.id);
  if(r.status!=='ENGINE_OK' || r.quality?.stepImport!=='OK' ||
     !Number.isSafeInteger(r.engine?.solids) || r.engine.solids<1 ||
     !Number.isSafeInteger(r.cut?.rows) || r.cut.rows<1){
   errors.push('Incomplete CAD/quote input '+r.id+': '+String(r.status));
  }
 }
 for(const id of expected)if(!actual.has(id))errors.push('Missing project '+id);
 return {ok:errors.length===0,errors};
}
