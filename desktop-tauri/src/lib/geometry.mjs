// DS Compare-inspired two-stage grouping of geometry descriptors.
// Input descriptors must come from a trusted CAD/B-Rep importer. This module DOES NOT import STEP.
// Bounding dimensions are sorted to ignore axis permutation; volume and area prefilter.
// A verified B-Rep equivalence key is required for automatic exact grouping.
// Without that key, candidates remain separate rather than assuming equal geometry.
const finite=(x,n)=>{if(!Number.isFinite(x)||x<0)throw new RangeError(n);return x};
export function massFromVolume(volumeMm3,densityKgM3=7850){finite(volumeMm3,'volumeMm3');finite(densityKgM3,'densityKgM3');return volumeMm3*1e-9*densityKgM3}
export function geometrySignature(part,{volumeRelTol=1e-6,lengthTolMm=0.01}={}){
 const v=finite(part.volumeMm3,'volumeMm3');if(!Array.isArray(part.bboxMm)||part.bboxMm.length!==3)throw new TypeError('bboxMm');
 const d=part.bboxMm.map((x)=>finite(x,'bboxMm')).sort((a,b)=>a-b);
 const area=finite(part.areaMm2??0,'areaMm2');
 // Dividing by x*relativeTolerance gives ~1/relativeTolerance for almost
 // every positive x: the former fingerprint lost volume/area information.
 // Logarithmic buckets keep relative resolution across CAD scales. A bucket
 // only suggests possible matches; never treat it as proof of identity.
 if(!Number.isFinite(volumeRelTol)||volumeRelTol<=0||volumeRelTol>=1||
    !Number.isFinite(lengthTolMm)||lengthTolMm<=0)throw new RangeError('geometry signature tolerance');
 const relBucket=(x)=>x===0?'zero':String(Math.round(Math.log(x)/Math.log1p(volumeRelTol*4)));
 const dimensionBucket=(x)=>Math.round(x/lengthTolMm);
 return [relBucket(v),...d.map(dimensionBucket),relBucket(area)].join(':');
}
export function groupGeometry(parts,{densityKgM3=7850}={}){
 if(!Array.isArray(parts))throw new TypeError('parts');
 const groups=[],byExact=new Map(),candidates=new Map();
 for(const part of parts){
  const quantity=part.quantity??1;if(!Number.isInteger(quantity)||quantity<1)throw new RangeError('quantity');
  const signature=geometrySignature(part);const massKg=massFromVolume(part.volumeMm3,part.densityKgM3??densityKgM3);
  const exactKey=typeof part.verifiedShapeKey==='string'&&part.verifiedShapeKey.length>0?part.verifiedShapeKey:null;
  const matchKey=exactKey?JSON.stringify([exactKey,part.volumeMm3,part.bboxMm.slice().sort((a,b)=>a-b)]):null;
  let group=matchKey?byExact.get(matchKey):null;
  if(!group){group={geometryId:part.id??'geometry-'+groups.length,signature,verified:!!matchKey,quantity:0,massKg,instances:[],materialIds:new Set()};groups.push(group);if(matchKey)byExact.set(matchKey,group)}
  group.quantity+=quantity;group.instances.push(part.id??null);if(part.materialId)group.materialIds.add(part.materialId);
  if(!candidates.has(signature))candidates.set(signature,[]);candidates.get(signature).push(part.id??null);
 }
 return {groups:groups.map(g=>({...g,totalMassKg:g.massKg*g.quantity,materialIds:[...g.materialIds]})),candidateBuckets:[...candidates.values()].filter(a=>a.length>1),totalMassKg:groups.reduce((s,g)=>s+g.massKg*g.quantity,0),totalOccurrences:groups.reduce((s,g)=>s+g.quantity,0)};
}
