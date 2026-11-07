import {partsList,ROUTES,commercialUnits} from '../parts.mjs';
export default Object.freeze({id:'purchased',title:'Zakupy / kooperacja',rateKey:null,detail:'Cena za wystąpienie produktu STEP, także gdy zawiera kilka brył. Jednostkę handlową potwierdź z dostawcą.',
 rows:({inventory,settings})=>{
  if(!inventory||!settings.partMaterials)return [{key:'parts',name:'Elementy kupowane',kind:'amount',autoAmount:null},{key:'outside',name:'Usługi kooperacyjne',kind:'amount',autoAmount:null}];
  const units=commercialUnits(partsList(inventory,settings.partMaterials,settings.rates.materialPriceKg)).filter(p=>p.route!=='make');
  return units.length?units.map(p=>({key:p.id,name:p.name,detail:p.conflict?'Sprzeczne ceny lub sposób realizacji brył produktu':(ROUTES[p.route]??'Sprawdź realizację')+' — 1 produkt STEP / '+p.bodyCount+' brył; cena za cały produkt',kind:'amount',autoAmount:p.supplierCost,evidence:'step-product-supplier-price'})):[{key:'parts',name:'Brak detali zewnętrznych',detail:'Wszystkie detale: produkcja własna',kind:'amount',autoAmount:0,evidence:'explicit-routing'}];
 }
});
