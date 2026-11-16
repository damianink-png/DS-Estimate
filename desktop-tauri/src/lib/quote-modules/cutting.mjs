import {METHOD_LABELS} from '../automatic-cutting.mjs';
export default Object.freeze({id:'cutting',title:'Cięcie',rateKey:'cutting',
 detail:'Dobór technologii i grupowanie partii według materiału, grubości lub przekroju. Parametry maszyn są edytowalnymi założeniami zakładowymi.',
 rows:({inventory,settings})=>{
  if(!inventory)return [];
  if(settings.cuttingPlan){
   // A failed planner or part material evaluation must NEVER be presented as
   // "no own cutting" with a manufactured zero. Preserve an unresolved row.
   if(settings.cuttingPlan.error)return [{
    key:'cutting-analysis-incomplete',name:'Nieukończona analiza cięcia',
    kind:'time',autoHours:null,
    detail:'Błąd planowania: '+settings.cuttingPlan.error,
    evidence:'analysis-partial'
   }];
   return settings.cuttingPlan.rows.length?
    settings.cuttingPlan.rows.map(p=>({key:p.id,name:p.name,kind:'time',
     autoHours:p.minutes===null?null:p.minutes/60,hourlyRate:p.rate,
     detail:(METHOD_LABELS[p.method]||'Technologia nieustalona')+' · '+p.batchKey+
      (p.minutes===null?' · wymaga uzupełnienia danych':''),
     evidence:p.minutes===null?'missing-geometry':'estimated-per-part-cutting'})):
    [{key:'no-own-cutting',name:'Brak cięcia własnego',kind:'time',autoHours:0,
      detail:'Wszystkie rozpatrzone detale są zakupowe lub w kooperacji',
      evidence:'routing-proposal-not-purchasing-proof'}];
  }
  return inventory.groups.map(g=>({key:g.geometryId,name:'Cięcie · '+g.geometryId,kind:'time',autoHours:null,detail:'Uzupełnij dane detali',evidence:'missing-cutting-plan'}));
 }
});
