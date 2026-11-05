import {planCuttingBatches} from '../cutting-batch.mjs';
import {SAMPLE_MACHINE_SETTINGS,CUTTING_METHODS} from '../cutting-plan.mjs';
const family=g=>/^S235/.test(g)?'S235':/^S355/.test(g)?'S355':/^1\./.test(g)?'stainless':/^EN AW/.test(g)?'aluminium':g||'unknown';
/** Cached B-Rep snapshot; batch setups remain shared within the same material. */
export default Object.freeze({
 id:'cutting',title:'Cięcie',rateKey:'cutting',
 detail:'Kontur STEP i przykładowe parametry maszyny. Czasy i dobór technologii wymagają sprawdzenia.',
 rows:({inventory,settings})=>{
  if(!inventory)return [];
  const first=new Map();
  for(const solid of inventory.solids)if(!first.has(solid.verifiedShapeKey))first.set(solid.verifiedShapeKey,solid);
  const materials=new Map();
  for(const group of inventory.groups){
   const material=family(settings.partMaterials?.[group.geometryId]?.grade??settings.grade);
   if(!materials.has(material))materials.set(material,[]);
   materials.get(material).push({key:group.geometryId,quantity:group.quantity,massKg:group.massKg,solid:first.get(group.geometryId)});
  }
  const machines=Object.fromEntries(Object.entries(SAMPLE_MACHINE_SETTINGS).map(([k,v])=>[k,{...v,ratePlnHour:settings.rates.cutting}]));
  return [...materials].flatMap(([material,groups])=>planCuttingBatches({groups,material,machines}).rows.map(g=>({
   key:g.key,name:'Cięcie · '+g.key,
   detail:g.quantity+' szt. · '+(CUTTING_METHODS[g.cut.method]||'metoda nieustalona')+
    ' · '+(g.cut.hint.kind==='possible-plate'?'kontur blachy':'geometria do weryfikacji'),
   kind:'time',autoHours:g.cut.calculatedMin===null?null:g.cut.calculatedMin/60,
   evidence:g.cut.calculatedMin===null?'missing-contour':'estimated-step-contour'
  })));
 }
});
