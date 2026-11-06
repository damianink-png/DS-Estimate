import {partsList,ROUTES} from '../parts.mjs';
export default Object.freeze({id:'purchased',title:'Zakupy / kooperacja',rateKey:null,detail:'Ceny przypisane bezpośrednio do detali. Detal kupowany nie dubluje kosztu materiału i cięcia.',
 rows:({inventory,settings})=>{
  if(!inventory||!settings.partMaterials)return [{key:'parts',name:'Elementy kupowane',kind:'amount',autoAmount:null},{key:'outside',name:'Usługi kooperacyjne',kind:'amount',autoAmount:null}];
  const parts=partsList(inventory,settings.partMaterials,settings.rates.materialPriceKg).filter(p=>p.route!=='make');
  return parts.length?parts.map(p=>({key:p.id,name:p.name,detail:ROUTES[p.route]+(p.includesMaterial?' — z materiałem':''),kind:'amount',autoAmount:p.supplierCost,evidence:'per-part-supplier-price'})):[{key:'parts',name:'Brak detali zewnętrznych',detail:'Wszystkie detale: produkcja własna',kind:'amount',autoAmount:0,evidence:'explicit-routing'}];
 }
});
