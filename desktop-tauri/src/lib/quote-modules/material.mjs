import {groupMaterial} from '../part-materials.mjs';
/** Material is not automatically certified from uniform-density STEP geometry. */
export default Object.freeze({
 id:'material',title:'Materiał',rateKey:null,
 detail:'Masa z B-Rep przy 7850 kg/m³ jest tylko stalowym ekwiwalentem; przypisz gęstość i cenę, sprawdź zakres. Gatunek może pozostać pusty.',
 rows:({inventory,settings})=>{
  if(inventory && settings.partMaterials){return inventory.groups.map(group=>{
   const m=groupMaterial(inventory,group,settings.partMaterials[group.geometryId],settings.rates.materialPriceKg);
   return {key:group.geometryId,name:'Materiał · '+group.geometryId,
    detail:group.quantity+' szt. · '+m.density+' kg/m³ · półfabrykat '+m.totalStockMassKg.toFixed(2)+' kg',
    kind:'amount',autoAmount:settings.materialApproved?m.costPln:null,
    evidence:settings.materialApproved?'manual-scope-approval':'material-unverified'};
  });}
  return [{
  key:'stock',name:'Materiał konstrukcji',
  detail:inventory?('Masa modelu ≈ '+inventory.totalMassKg.toFixed(2)+' kg (7850 kg/m³)'):'Brak modelu',
  kind:'amount',
  autoAmount:inventory && settings.materialApproved && settings.grade!=='unknown' &&
    Number.isFinite(settings.rates.materialPriceKg) && settings.rates.materialPriceKg>0
    ? inventory.totalMassKg*settings.rates.materialPriceKg : null,
  evidence: settings.materialApproved?'manual-scope-approval':'material-unverified'
 }];}
});
