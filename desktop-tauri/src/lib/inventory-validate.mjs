/** A STEP estimate must not be constructed from a partial or inconsistent BOM. */
const near=(a,b)=>Math.abs(a-b)<=Math.max(1e-6,Math.max(Math.abs(a),Math.abs(b))*1e-5);
const good=(x)=>typeof x==='number'&&Number.isFinite(x)&&x>0;
export function validateStepBom(data){
 if(!data||!Array.isArray(data.solids)||!Array.isArray(data.groups))
  throw new TypeError('Brak pełnego zestawienia B-Rep');
 if(!Number.isSafeInteger(data.count)||data.count<1||data.solids.length!==data.count)
  throw new RangeError('Liczba brył STEP jest niezgodna z raportem');
 if(!good(data.totalMassKg))throw new RangeError('Niepoprawna masa złożenia');
 const counts=new Map();
 let solidsMass=0;
 for(const s of data.solids){
  if(!s||!good(s.massKg)||!good(s.volumeMm3)||typeof s.verifiedShapeKey!=='string'||!s.verifiedShapeKey)
   throw new RangeError('Niepełne parametry pojedynczej bryły');
  solidsMass+=s.massKg;
  const old=counts.get(s.verifiedShapeKey)??{quantity:0,massKg:s.massKg};
  if(!near(old.massKg,s.massKg))throw new RangeError('Różne masy w grupie identycznych brył');
  counts.set(s.verifiedShapeKey,{quantity:old.quantity+1,massKg:s.massKg});
 }
 let groupsMass=0,groupCount=0;
 const ids=new Set();
 for(const g of data.groups){
  if(!g||typeof g.geometryId!=='string'||ids.has(g.geometryId)||!good(g.massKg)||
     !Number.isSafeInteger(g.quantity)||g.quantity<1)
   throw new RangeError('Niepoprawna grupa części / duplikat');
  ids.add(g.geometryId);
  const matched=counts.get(g.geometryId);
  if(!matched||matched.quantity!==g.quantity||!near(matched.massKg,g.massKg))
   throw new RangeError('Niezgodna liczba wystąpień lub masa detalu');
  groupsMass+=g.massKg*g.quantity;groupCount+=g.quantity;
 }
 if(groupCount!==data.count||ids.size!==counts.size||
   !near(solidsMass,data.totalMassKg)||!near(groupsMass,data.totalMassKg))
  throw new RangeError('Masa sumaryczna STEP nie zgadza się z BOM');
 return data;
}
