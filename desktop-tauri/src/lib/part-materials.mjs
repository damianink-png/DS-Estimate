export const MATERIALS=Object.freeze([
 {grade:'',label:'—',density:7850},
 {grade:'S235JR',label:'Stal S235JR',density:7850},{grade:'S355J2',label:'Stal S355J2',density:7850},
 {grade:'S690QL',label:'Stal S690QL',density:7850},{grade:'1.4301',label:'Nierdzewna 304',density:7930},
 {grade:'1.4404',label:'Nierdzewna 316L',density:8000},{grade:'EN AW-5754',label:'Aluminium 5754',density:2660},
 {grade:'EN AW-6061',label:'Aluminium 6061',density:2700},{grade:'EN AW-7075',label:'Aluminium 7075',density:2810},
 {grade:'Cu-ETP',label:'Miedź',density:8960},{grade:'CuZn',label:'Mosiądz',density:8500},
 {grade:'EN-GJL',label:'Żeliwo szare',density:7200},{grade:'Ti-6Al-4V',label:'Tytan Grade 5',density:4430}
]);
export const defaultMaterial=()=>({grade:'',density:7850,price:null,allowStart:0,allowEnd:0,stockMassKg:null});
export function groupMaterial(inventory,group,preference={},fallbackPrice=null){
 const p={...defaultMaterial(),...preference};
 if(typeof p.density!=='number'||!Number.isFinite(p.density)||p.density<=0)throw new RangeError('Gęstość musi być dodatnia.');
 for(const k of ['allowStart','allowEnd'])if(typeof p[k]!=='number'||!Number.isFinite(p[k])||p[k]<0)throw new RangeError('Niepoprawny naddatek.');
 const solid=inventory.solids.find(s=>s.verifiedShapeKey===group.geometryId);
 if(!solid||!Number.isFinite(solid.volumeMm3)||solid.volumeMm3<=0)throw new Error('Brak objętości B-Rep.');
 const massKg=solid.volumeMm3/1e9*p.density;
 const hintLength=solid.stockHint?.lengthMm;
 const dims=solid.bboxMm||[];
 const lengthMm=typeof hintLength==='number'&&Number.isFinite(hintLength)&&hintLength>0?hintLength:Math.max(...dims);
 if((p.allowStart+p.allowEnd)>0&&(!Number.isFinite(lengthMm)||lengthMm<=0))throw new RangeError('Brak długości półfabrykatu.');
 if(p.stockMassKg!==null&&(typeof p.stockMassKg!=='number'||!Number.isFinite(p.stockMassKg)||p.stockMassKg<0))throw new RangeError('Niepoprawna masa półfabrykatu.');
 const stockMassKg=p.stockMassKg??massKg*(1+(p.allowStart+p.allowEnd)/(lengthMm||1));
 const price=p.price??fallbackPrice;
 if(price!==null&&(typeof price!=='number'||!Number.isFinite(price)||price<0))throw new RangeError('Niepoprawna cena materiału.');
 const totalMassKg=massKg*group.quantity,totalStockMassKg=stockMassKg*group.quantity;
 const costPln=price!==null&&price>0?totalStockMassKg*price:null;
 if(![massKg,stockMassKg,totalMassKg,totalStockMassKg].every(Number.isFinite)||(costPln!==null&&!Number.isFinite(costPln)))throw new RangeError('Przekroczono zakres obliczeń materiału.');
 return {...p,price,massKg,stockMassKg,totalMassKg,totalStockMassKg,lengthMm,costPln};
}
