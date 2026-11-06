import {partsList} from '../parts.mjs';
export default Object.freeze({id:'material',title:'Detale / materiał',rateKey:null,
 detail:'Materiał, masa, wymiary, przekrój, naddatki i sposób realizacji osobno dla każdego wystąpienia STEP.',
 rows:({inventory,settings})=>{
  if(inventory&&settings.partMaterials){return partsList(inventory,settings.partMaterials,settings.rates.materialPriceKg).map(p=>({
   key:p.id,name:p.name,detail:p.route==='purchase'?'Materiał w cenie zakupu':p.route==='cooperate'&&p.includesMaterial?'Materiał w cenie kooperacji':p.stockMassKg.toFixed(3)+' kg × '+(p.price??'—')+' zł/kg',kind:'amount',
   autoAmount:settings.materialApproved?p.materialCost:null,evidence:settings.materialApproved?'manual-scope-approval':'material-unverified'}));}
  return [{key:'stock',name:'Materiał konstrukcji',detail:'Masa modelu przy 7850 kg/m³',kind:'amount',autoAmount:inventory&&settings.materialApproved&&settings.grade!=='unknown'&&Number.isFinite(settings.rates.materialPriceKg)&&settings.rates.materialPriceKg>0?inventory.totalMassKg*settings.rates.materialPriceKg:null,evidence:'material-unverified'}];
 }
});
