/** Material is not automatically certified from uniform-density STEP geometry. */
export default Object.freeze({
 id:'material',title:'Materiał',rateKey:null,
 detail:'Masa z B-Rep przy 7850 kg/m³ jest tylko stalowym ekwiwalentem; potwierdź gatunek i zakres.',
 rows:({inventory,settings})=>[{
  key:'stock',name:'Materiał konstrukcji',
  detail:inventory?('Masa modelu ≈ '+inventory.totalMassKg.toFixed(2)+' kg (7850 kg/m³)'):'Brak modelu',
  kind:'amount',
  autoAmount:inventory && settings.materialApproved && settings.grade!=='unknown' &&
    Number.isFinite(settings.rates.materialPriceKg) && settings.rates.materialPriceKg>0
    ? inventory.totalMassKg*settings.rates.materialPriceKg : null,
  evidence: settings.materialApproved?'manual-scope-approval':'material-unverified'
 }]
});
