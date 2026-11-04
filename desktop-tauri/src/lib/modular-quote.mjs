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
 confirmed={},excluded={},custom={},grade='unknown',materialApproved=false
}={}){
 const settings={rates,grade,materialApproved,pdfText};
 const modules=MODULES.map(mod=>{
  try{
   const own=mod.rows({inventory,settings});
   const extras=custom[mod.id]||[];
   const specs=[...own,...extras.map(x=>({
    key:x.key,name:x.name,detail:'Ręcznie dodana operacja',
    kind:x.kind||'time',autoHours:null,autoAmount:null,evidence:'manual-required'
   }))];
   const rows=specs.map(x=>{
    const value=rowValue(x,edits[mod.id]?.[x.key]);
    if(value!==null&&value!==undefined&&!nonnegative(value))
     throw new RangeError('Niepoprawny czas lub koszt: '+mod.id+'/'+x.key);
    const known=value!==null&&value!==undefined;
    const rate=x.kind==='time'?rates[mod.rateKey]:null;
    const validRate=x.kind!=='time'||(typeof rate==='number'&&Number.isFinite(rate)&&rate>0);
    return {...x,value:known?value:null,rate:validRate?rate:null,
     costPln:known&&validRate?(x.kind==='time'?value*rate:value):null,
     manuallyEdited:Object.prototype.hasOwnProperty.call(edits[mod.id]?.[x.key]||{},'value')};
   });
   const missing=rows.filter(x=>x.costPln===null).length;
   const full=rows.length>0 && missing===0;
   const omitted=excluded[mod.id]===true;
   const status=omitted?'excluded':!inventory?'idle':!full?
     (missing===rows.length?'missing':'partial'):
     confirmed[mod.id]?'verified':'review';
   const knownCostPln=rows.reduce((s,x)=>s+(x.costPln??0),0);
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
