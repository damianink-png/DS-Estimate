/**
 * One CAD import per unchanged file in this desktop session.
 * An external revision token (size + mtime, supplied by native Rust) prevents
 * stale results after the STEP changes. Rejections never poison the cache.
 * Quote modules consume the JSON snapshot and NEVER call OCCT directly.
 */
export function createCadSession(loadInventory, fileRevision) {
 if(typeof loadInventory!=='function'||typeof fileRevision!=='function')
  throw new TypeError('CAD loader and revision provider required');
 const finished=new Map(), running=new Map();
 async function analyze(path,{refresh=false}={}) {
  if(typeof path!=='string'||!path.trim())throw new RangeError('STEP path');
  const revision=await fileRevision(path);
  const key=JSON.stringify([path,revision]);
  if(refresh)finished.delete(key);
  if(finished.has(key))return finished.get(key);
  if(running.has(key))return running.get(key);
  const task=Promise.resolve().then(()=>loadInventory(path))
    .then(result=>{finished.set(key,result);return result;})
    .finally(()=>running.delete(key));
  running.set(key,task);
  return task;
 }
 return {analyze,clear:()=>{finished.clear();running.clear();},
  stats:()=>({cached:finished.size,inFlight:running.size})};
}
