// Conservative manufacturing takeoff from OCCT inventory.
// Geometry is measured; operations that cannot be inferred are explicitly pending.
const finite=(n)=>typeof n==='number'&&Number.isFinite(n)&&n>=0;
export function analyzeManufacturingInventory(data,{densityKgM3=7850,profileAspectMin=4,plateAspectMin=6}={}){
 if(!data||!Array.isArray(data.solids)||!finite(densityKgM3)||densityKgM3===0)throw new RangeError('inventory/density');
 const items=data.solids.map((s,i)=>{
  if(!finite(s.volumeMm3)||!Array.isArray(s.bboxMm)||s.bboxMm.length!==3||!s.bboxMm.every(finite))throw new RangeError('solid geometry');
  const dims=[...s.bboxMm].sort((a,b)=>a-b),[small,mid,long]=dims;
  // Bounding-box proportions only suggest stock category; not manufacturing proof.
  const suggestedCategory=mid>0&&long/mid>=profileAspectMin?'possible-profile':small>0&&mid/small>=plateAspectMin?'possible-plate':'unclassified';
  return {id:s.id??`solid-${i+1}`,shapeKey:s.verifiedShapeKey??null,volumeMm3:s.volumeMm3,massKg:s.volumeMm3*densityKgM3*1e-9,bboxMm:s.bboxMm,suggestedCategory,confidence:'geometry-only'};
 });
 const grouped=new Map();
 for(const item of items){const key=item.shapeKey??item.id;const row=grouped.get(key);if(row){row.quantity++;row.totalMassKg+=item.massKg;}else grouped.set(key,{geometryId:key,quantity:1,totalMassKg:item.massKg,suggestedCategory:item.suggestedCategory});}
 return {source:data.source??null,solidCount:items.length,uniqueGroups:grouped.size,totalMassKg:items.reduce((s,x)=>s+x.massKg,0),items,groups:[...grouped.values()],unresolved:[
 {operation:'cutting',reason:'Requires stock type, cut planes, cut technology and drawing tolerances'},
 {operation:'welding',reason:'Requires validated weld symbols, joint geometry, throat size and accessibility'},
 {operation:'assembly',reason:'Requires assembly sequence, fixtures, handling and tack schedule'},
 {operation:'cnc',reason:'Requires raw stock geometry, datum and machining requirements'}
 ],quotationReady:false};
}
