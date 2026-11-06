import {MATERIALS} from './part-materials.mjs';
export {MATERIALS};
export const ROUTES=Object.freeze({make:'Produkcja własna',purchase:'Zakup',cooperate:'Kooperacja'});
export const partDefaults=()=>({grade:'',density:7850,price:null,route:'make',supplierPrice:null,includesMaterial:false,
 allowances:[0,0,0,0,0,0],stockMassKg:null,catalogId:'',stockKind:'',cutMethod:'auto',cutCount:2,sawAngle:0,contourMm:null,pierces:null,cutAreaMm2:null,bendCount:null});
const finite=(v,label,min=0)=>{if(typeof v!=='number'||!Number.isFinite(v)||v<min)throw new RangeError(label);return v;};
export function preferenceFor(s,prefs={}){
 const old=prefs[s.id]??prefs[s.verifiedShapeKey]??{};
 return {...partDefaults(),...old,allowances:old.allowances??[old.allowStart??0,old.allowEnd??0,0,0,0,0]};
}
export function detailDimensions(s){
 const h=s.stockHint??{};if(Array.isArray(h.localDimsMm)&&h.localDimsMm.length===3)return [...h.localDimsMm].sort((a,b)=>b-a);const dims=[...(s.bboxMm??[])].sort((a,b)=>b-a);
 return [h.lengthMm??dims[0],h.widthMm??h.diameterMm??dims[1],h.thicknessMm??h.heightMm??h.diameterMm??dims[2]];
}
export function partValues(s,pref={},fallbackPrice=null){
 const p={...partDefaults(),...pref};
 if(!ROUTES[p.route])throw new RangeError('Nieprawidłowy sposób realizacji');
 finite(p.density,'Gęstość',Number.MIN_VALUE);finite(s.volumeMm3,'Objętość',Number.MIN_VALUE);
 const dims=detailDimensions(s);if(dims.some(v=>!Number.isFinite(v)||v<=0))throw new RangeError('Brak wymiarów detalu');
 if(!Array.isArray(p.allowances)||p.allowances.length!==6)throw new RangeError('Naddatki');
 p.allowances.forEach(v=>finite(v,'Naddatek'));
 const stockDims=dims.map((v,i)=>v+p.allowances[2*i]+p.allowances[2*i+1]);
 const massKg=s.volumeMm3/1e9*p.density;
 const stockMassKg=p.stockMassKg===null?massKg*stockDims.reduce((ratio,v,i)=>ratio*v/dims[i],1):finite(p.stockMassKg,'Masa półfabrykatu');
 const price=typeof fallbackPrice==='object'&&fallbackPrice!==null?(Object.hasOwn(fallbackPrice,p.grade)?fallbackPrice[p.grade]:(fallbackPrice['']??null)):(p.price??fallbackPrice);
 if(price!==null)finite(price,'Cena materiału');
 if(p.supplierPrice!==null)finite(p.supplierPrice,'Cena zakupu lub kooperacji');
 const materialIncluded=p.route==='purchase'||(p.route==='cooperate'&&p.includesMaterial);
 const materialCost=materialIncluded?0:price!==null?stockMassKg*price:null;
 const supplierCost=p.route==='make'?0:p.supplierPrice;
 [massKg,stockMassKg,...stockDims,materialCost,supplierCost].filter(v=>v!==null).forEach(v=>finite(v,'Przekroczono zakres obliczeń'));
 return {...p,dims,stockDims,massKg,stockMassKg,price,materialCost,supplierCost};
}
export function partsList(inventory,prefs={},price=null){
 return (inventory?.solids??[]).map(s=>({solid:s,id:s.id,name:s.name||s.id,geometryKey:s.verifiedShapeKey,...partValues(s,preferenceFor(s,prefs),price)}));
}
