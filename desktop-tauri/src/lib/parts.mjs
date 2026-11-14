import {MATERIALS} from './part-materials.mjs';
export {MATERIALS};
export const ROUTES=Object.freeze({make:'Produkcja własna',purchase:'Zakup',cooperate:'Kooperacja'});
export const partDefaults=()=>({grade:'',density:7850,price:null,route:'make',supplierPrice:null,includesMaterial:false,
 allowances:[0,0,0,0,0,0],stockMassKg:null,catalogId:'',stockKind:'',cutMethod:'auto',cutCount:2,sawAngle:0,contourMm:null,pierces:null,cutAreaMm2:null,bendCount:null});
const finite=(v,label,min=0)=>{if(typeof v!=='number'||!Number.isFinite(v)||v<min)throw new RangeError(label);return v;};
export function preferenceFor(s,prefs={}){
 const old=prefs[s.id]??prefs[s.verifiedShapeKey]??{};
 const label=s.name??'';
 // A named HOLE or an assembly reference is not a purchased fastener even if
 // its name contains ISO 4017, M10, 'bolt', etc. Names never prove purchasing.
 const featureOrAssembly=/\b(?:hole\w*|bohrung\w*|gewindebohrung\w*|otw[oó]r\w*|gniazdo\w*|pocket\w*|assembly|baugruppe|z[oł]o[zż]eni\w*)\b/i.test(label);
 const hardware=!featureOrAssembly&&/\b(?:washer|nut|screw|bolt)(?:[\s_-]|$)|\bbottle[ _-]jack(?:[\s_-]|$)|^electrical[ _-]enclosure(?:[\s:_-]|$)|\b(?:DIN|ISO)[ _-]?(?:912|933|934|125|9021|4762|4017|4032)\b/i.test(label);
 return {...partDefaults(),...(hardware?{route:'purchase'}:{}),...old,allowances:old.allowances??[old.allowStart??0,old.allowEnd??0,0,0,0,0]};
}
export function detailDimensions(s){
 const h=s.stockHint?.kind==='unknown'&&s.stockHint?.rawStockCandidate?s.stockHint.rawStockCandidate:(s.stockHint??{});
 const spans=[...(s.bboxMm??[])].sort((a,b)=>b-a);
 if(h.lengthMm&&['square-hollow','rectangular-hollow','round-tube','round-bar','square-bar','rectangular-bar','polygon-bar','flat-section','angle','channel','tee','i-section'].includes(h.kind))return [h.lengthMm,h.widthMm??h.diameterMm??spans[1],h.heightMm??h.diameterMm??spans[2]];
 if(Array.isArray(h.localDimsMm)&&h.localDimsMm.length===3)return [...h.localDimsMm].sort((a,b)=>b-a);const dims=[...(s.bboxMm??[])].sort((a,b)=>b-a);
 return [h.lengthMm??dims[0],h.widthMm??h.diameterMm??dims[1],h.thicknessMm??h.heightMm??h.diameterMm??dims[2]];
}
// Material blank is separate from the finished solid. Unknown sections retain
// an explicit volume-based estimate; recognized stock restores removed material.
export function stockVolume(s,dims,stockDims){
 const h=s.stockHint?.rawStockCandidate??s.stockHint??{},v=s.volumeMm3;
 if(Number.isFinite(h.sectionAreaMm2)&&h.sectionAreaMm2>0&&h.lengthMm>0){
  const dw=stockDims[1]-dims[1],dh=stockDims[2]-dims[2];
  let area=h.sectionAreaMm2,source='Pole przekroju × długość półfabrykatu';
  if(dw>0||dh>0){
   // A larger RHS/SHS is NOT a solid rectangle added to a tube: its inner
   // void remains. The old full-bbox delta could overstate stock mass tenfold.
   // Keep the same measured wall, and require manual confirmation of the
   // non-standard enlarged section (or supply a measured blank mass).
   const wall=h.wallMm;
   if(['square-hollow','rectangular-hollow'].includes(h.kind)&&
      Number.isFinite(wall)&&wall>0&&2*wall<Math.min(dims[1],dims[2])){
    area+=2*wall*(dw+dh);
    source='Przekrój zamknięty: zachowana grubość ścianki; poszerzony wyrób wymaga potwierdzenia';
   }else if(['round-tube','round-bar'].includes(h.kind)&&
     Math.abs(stockDims[1]-stockDims[2])<=Math.max(0.02,stockDims[1]*1e-4)){
    const delta=stockDims[1]-dims[1];
    if(h.kind==='round-tube'&&Number.isFinite(wall)&&wall>0&&2*wall<dims[1]){
     area+=Math.PI*wall*delta;
     source='Rura: zachowana grubość ścianki; większą średnicę potwierdź w katalogu';
    }else if(h.kind==='round-bar'){
     area+=Math.PI/4*(stockDims[1]**2-dims[1]**2);
     source='Pręt okrągły: zmieniona średnica przygotówki wymaga potwierdzenia';
    }else throw new RangeError('Naddatek poprzeczny rury: brak wiarygodnej średnicy lub ścianki');
   }else if(['square-bar','rectangular-bar','flat-section'].includes(h.kind)){
    area+=stockDims[1]*stockDims[2]-dims[1]*dims[2];
    source='Pręt pełny: zwiększony przekrój przygotówki wymaga potwierdzenia';
   }else{
    throw new RangeError('Naddatek poprzeczny profilu nie wyznacza przekroju. Ustaw tylko naddatek długościowy lub podaj znaną masę półfabrykatu.');
   }
  }
  return {volume:Math.max(v,area*stockDims[0]),source};
 }
 if(['plate','plate-candidate'].includes(h.kind))return {volume:Math.max(v,stockDims.reduce((a,b)=>a*b,1)),source:'Prostokątny półfabrykat blachy; bez optymalizacji rozkroju'};
 return {volume:v*stockDims.reduce((ratio,x,i)=>ratio*x/dims[i],1),source:h.kind==='bent-plate'?'Objętość blachy giętej; kontur bez odpadu rozkroju':'Objętość gotowego detalu × naddatki; półfabrykat nierozpoznany'};
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
 const blank=p.stockMassKg===null?stockVolume(s,dims,stockDims):{volume:s.volumeMm3,source:'Masa półfabrykatu podana ręcznie'};
 const stockMassKg=p.stockMassKg===null?blank.volume/1e9*p.density:finite(p.stockMassKg,'Masa półfabrykatu');
 const price=typeof fallbackPrice==='object'&&fallbackPrice!==null?(Object.hasOwn(fallbackPrice,p.grade)?fallbackPrice[p.grade]:(fallbackPrice['']??null)):(p.price??fallbackPrice);
 if(price!==null)finite(price,'Cena materiału');
 if(p.supplierPrice!==null)finite(p.supplierPrice,'Cena zakupu lub kooperacji');
 const materialIncluded=p.route==='purchase'||(p.route==='cooperate'&&p.includesMaterial);
 const materialCost=materialIncluded?0:price!==null?stockMassKg*price:null;
 const supplierCost=p.route==='make'?0:p.supplierPrice;
 [massKg,stockMassKg,...stockDims,materialCost,supplierCost].filter(v=>v!==null).forEach(v=>finite(v,'Przekroczono zakres obliczeń'));
 return {...p,dims,stockDims,massKg,stockMassKg,stockSource:p.stockMassKg===null?blank.source:'Masa półfabrykatu podana ręcznie',price,materialCost,supplierCost};
}
export function partsList(inventory,prefs={},price=null){
 return (inventory?.solids??[]).map(s=>({solid:s,id:s.id,name:s.name||s.id,geometryKey:s.verifiedShapeKey,...partValues(s,preferenceFor(s,prefs),price)}));
}

// The identity is an occurrence in the XCAF tree, never a name or volume hash.
export function commercialUnits(parts){
 const groups=new Map();for(const p of parts){const key=p.solid.productIdentityReliable&&p.solid.productOccurrenceKey?p.solid.productOccurrenceKey:p.id;
  if(!groups.has(key))groups.set(key,[]);groups.get(key).push(p);}
 return [...groups].map(([id,members])=>{const routes=new Set(members.map(p=>p.route)),prices=new Set(members.map(p=>p.supplierCost).filter(v=>v!==null));
  const route=routes.size===1?members[0].route:'mixed',conflict=routes.size>1||prices.size>1;
  return {id,name:members[0].name,route,parts:members,bodyCount:members.length,definitionKey:members[0].solid.productDefinitionKey??members[0].geometryKey??id,
   massKg:members.reduce((s,p)=>s+p.massKg,0),supplierCost:conflict?null:prices.size===1?[...prices][0]:null,conflict};});
}
