import {MODULES,DEFAULT_RATES} from './quote-modules/index.mjs';

function nonnegative(v) {
 return typeof v==='number' && Number.isFinite(v) && v>=0;
}
function rowValue(entry,override){
 // Missing is NOT 0; explicit zero must be distinguishable from no data.
 return Object.prototype.hasOwnProperty.call(override||{},'value')?
  override.value:(entry.kind==='time'?entry.autoHours:entry.autoAmount);
}
/** Pure, cheap costing from a single verified CAD JSON inventory snapshot.
 * No CAD import, B-Rep, file system, OCR or networking. Failure is per-module.
 */
export function evaluateModules({
 inventory=null, pdfText='',rates=DEFAULT_RATES,edits={},
 confirmed={},excluded={},custom={},grade='unknown',materialApproved=false,partMaterials=null,materialPrices=null,cuttingPlan=null,automation=null
}={}){
 const settings={rates,grade,materialApproved,pdfText,partMaterials,materialPrices,cuttingPlan,automation};
 const modules=MODULES.map(mod=>{
  try{
   let own=mod.rows({inventory,settings});
   const automatic=automation?.modules?.[mod.id];
   if(automatic)own=own.map(row=>Object.hasOwn(automatic,row.key)?{...row,autoHours:automatic[row.key],detail:automation?.basis?.[mod.id]?.[row.key]??'Geometria STEP × edytowalne normy',evidence:'geometry-and-shop-assumptions'}:row);
   if(automation?.extraRows?.[mod.id])own=[...own,...automation.extraRows[mod.id]];
   const extras=custom[mod.id]||[];
   const specs=[...own,...extras.map(x=>({
    key:x.key,name:x.name,detail:'Ręcznie dodana operacja',
    kind:x.kind||'time',autoHours:null,autoAmount:null,evidence:'manual-required'
   }))];
   if(new Set(specs.map(x=>x.key)).size!==specs.length)
    throw new Error('Powtarzające się identyfikatory operacji w module: '+mod.id);
   const rows=specs.map(x=>{
    // Material is priced centrally in 0.5; obsolete hidden per-row amount edits
    // must not override the material total displayed on the parts screen.
    const override=mod.id==='material'&&materialPrices?undefined:edits[mod.id]?.[x.key];
    const value=rowValue(x,override);
    if(value!==null&&value!==undefined&&!nonnegative(value))
     throw new RangeError('Niepoprawny czas lub koszt: '+mod.id+'/'+x.key);
    const known=value!==null&&value!==undefined;
    const rate=x.kind==='time'?(x.hourlyRate??rates[mod.rateKey]):null;
    const validRate=x.kind!=='time'||(typeof rate==='number'&&Number.isFinite(rate)&&rate>0);
    return {...x,value:known?value:null,rate:validRate?rate:null,
     costPln:known&&validRate?(x.kind==='time'?value*rate:value):null,
     manuallyEdited:Object.prototype.hasOwnProperty.call(override||{},'value')};
   });
   if(rows.some(r=>r.costPln!==null&&!Number.isFinite(r.costPln)))throw new RangeError('Przekroczono zakres kosztu operacji');
   const missing=rows.filter(x=>x.costPln===null).length;
   const full=rows.length>0 && missing===0;
   const omitted=excluded[mod.id]??(automation?.disabledModules?.includes(mod.id)??false);
   const status=omitted?'excluded':!inventory?'idle':!full?
     (missing===rows.length?'missing':'partial'):
     confirmed[mod.id]?'verified':'review';
   const knownCostPln=omitted?0:rows.reduce((s,x)=>s+(x.costPln??0),0);
   if(!Number.isFinite(knownCostPln))throw new RangeError('Przekroczono zakres kosztu modułu');
   return {id:mod.id,title:mod.title,detail:mod.detail,rows,missing,status,omitted,
    knownCostPln,verifiedCostPln:status==='verified'?knownCostPln:null,
    requiredReview:status!=='verified'&&status!=='excluded',
    evidence:mod.id==='welding'?{
     pdfTextPresent:pdfText.trim().length>0,
     note:'Symbol spoiny w PDF nie jest potwierdzonym połączeniem 3D. Bez ręcznej weryfikacji nie wyceniaj automatycznie.'
    }:null};
  }catch(error){
   return {id:mod.id,title:mod.title,detail:mod.detail,rows:[],missing:1,
    status:'error',omitted:false,knownCostPln:0,verifiedCostPln:null,
    requiredReview:true,error:String(error)};
  }
 });
 const knownCostPln=modules.reduce((s,m)=>s+m.knownCostPln,0);
 const openModules=modules.filter(m=>m.requiredReview);
 const completedModules=modules.filter(m=>m.status==='verified'||m.status==='excluded').length;
 return {modules,knownCostPln,verifiedCostPln:openModules.length===0&&
   inventory?knownCostPln:null,
  completedModules,openModules:openModules.length,totalModules:modules.length,
  complete:Boolean(inventory)&&openModules.length===0,
  fullQuoteVerified:false,  // Manual confirmations do not certify automated technology.
  massKgSteelEquivalent:inventory?.totalMassKg??null,
  source:'STEP geometric inventory + independently editable modules'
 };
}
