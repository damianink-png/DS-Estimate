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
 let generation=0;
 const versions=new Map();
 async function analyze(path,{refresh=false}={}) {
  if(typeof path!=='string'||!path.trim())throw new RangeError('STEP path');
  // Capture invalidation before the asynchronous fingerprint read: clear() may run while it is pending.
  const epoch=generation;
  const revision=await fileRevision(path);
  const key=JSON.stringify([path,revision]);
  if(refresh){finished.delete(key);versions.set(key,(versions.get(key)||0)+1);running.delete(key);}
  const version=versions.get(key)||0;
  // A stale fingerprint request must not join or populate the current generation.
  if(epoch!==generation)return loadInventory(path);
  if(finished.has(key))return finished.get(key);
  if(running.has(key))return running.get(key);
  const task=Promise.resolve().then(()=>loadInventory(path))
    .then(result=>{if(epoch===generation && version===(versions.get(key)||0))finished.set(key,result);return result;})
    .finally(()=>{if(running.get(key)===task)running.delete(key);});
  running.set(key,task);
  return task;
 }
 return {analyze,clear:()=>{generation++;finished.clear();running.clear();versions.clear();},
  stats:()=>({cached:finished.size,inFlight:running.size})};
}
