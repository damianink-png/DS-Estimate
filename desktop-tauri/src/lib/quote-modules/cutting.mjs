import {planCuttingBatches} from '../cutting-batch.mjs';
import {SAMPLE_MACHINE_SETTINGS} from '../cutting-plan.mjs';

/** Uses a cached STEP inventory; no STEP re-import or B-Rep booleans. */
export default Object.freeze({
 id:'cutting',title:'Cięcie',rateKey:'cutting',
 detail:'Kontur STEP oraz przykładowy profil maszyny. Czas wymaga weryfikacji.',
 rows:({inventory,settings})=>{
  if(!inventory)return [];
  const first=new Map();
  for(const solid of inventory.solids)if(!first.has(solid.verifiedShapeKey))
   first.set(solid.verifiedShapeKey,solid);
  const groups=inventory.groups.map(g=>({
   key:g.geometryId,quantity:g.quantity,massKg:g.massKg,solid:first.get(g.geometryId)
  }));
  const machines=Object.fromEntries(Object.entries(SAMPLE_MACHINE_SETTINGS).map(([k,v])=>
   [k,{...v,ratePlnHour:settings.rates.cutting}]));
  const plan=planCuttingBatches({
   groups,material:settings.grade,machines
  });
  return plan.rows.map(g=>({
   key:g.key,name:'Cięcie · '+g.key,
   detail:g.quantity+' szt. · '+(g.cut.method||'metoda nieustalona')+
    ' · '+(g.cut.hint.kind==='possible-plate'?'blacha':'geometria do weryfikacji'),
   kind:'time',autoHours:g.cut.calculatedMin===null?null:g.cut.calculatedMin/60,
   evidence:g.cut.calculatedMin===null?'missing-contour':'estimated-step-contour'
  }));
 }
});
