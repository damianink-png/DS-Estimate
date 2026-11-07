<script lang="ts">
 import {onMount} from 'svelte';
 import PartPreview from './PartPreview.svelte';
 import {call as invoke,native,pickInputs,watchDrops,saveReport} from './lib/desktop-api';
 import {Layers3,FolderOpen,FilePlus2,Plus,Upload,Scale,Settings2,Sun,Moon,Download,Check,ChevronRight,X,Files,RotateCcw,ClipboardList,Search} from 'lucide-svelte';
 import {mergeProjectFiles,preferredStep,moduleReport,csvCell} from './lib/project-files.mjs';
 import {MATERIALS,ROUTES,partDefaults,partsList,partValues,preferenceFor,commercialUnits} from './lib/parts.mjs';
 import sectionCatalog from './lib/data/steel-sections.json';
 import {MACHINES,METHOD_LABELS,planAutomaticCutting} from './lib/automatic-cutting.mjs';
 import {auditCutting} from './lib/cutting-audit.mjs';
 import {NORMS,NORM_CHOICES,automaticOperations,partBends,bendEstimate} from './lib/fabrication.mjs';
 import {createCadSession} from './lib/cad-session.mjs';
 import {validateStepBom} from './lib/inventory-validate.mjs';
 import {evaluateModules} from './lib/modular-quote.mjs';
 import {MODULES,DEFAULT_RATES} from './lib/quote-modules/index.mjs';
 import {parseExplicitFilletNotes} from './lib/weld-document.mjs';
 import {kwantflowKnownCost} from './lib/modular-kwantflow.js';

 type StockHint={kind:string;confidence?:string;reason?:string;source?:string;limitations?:string;lengthMm?:number;widthMm?:number;heightMm?:number;diameterMm?:number;thicknessMm?:number;wallMm?:number;sectionAreaMm2?:number};
 type Inv={productCount?:number;engineVersion?:string;previews?:Record<string,any>;importIssues?:string[];count:number;totalMassKg:number;solids:any[];groups:any[];limitations?:string[]};
 type Edit={value:number|null};
 type CustomRow={key:string;name:string;kind:'time'|'amount'};
 const money=(x:number)=>x.toLocaleString('pl-PL',{minimumFractionDigits:2,maximumFractionDigits:2});
 const number=(x:number)=>x.toLocaleString('pl-PL',{maximumFractionDigits:2});
 const stockLabels:Record<string,string>={
  'plate-candidate':'Płyta',
  'bent-plate':'Blacha gięta',
  'flat-section':'Przekrój płaskownika (kandydat)',
  'square-bar':'Pręt kwadratowy',
  'rectangular-bar':'Pręt prostokątny',
  'round-bar':'Pręt okrągły',
  'round-tube':'Rura okrągła',
  'square-hollow':'Profil zamknięty kwadratowy',
  'rectangular-hollow':'Profil zamknięty prostokątny',
  'angle':'Kątownik',
  'channel':'Ceownik',
  'tee':'Teownik',
  'i-section':'Dwuteownik',
  'unknown':'Nieustalony'
 };
 const stockText=(stock:StockHint|undefined)=>{
  if(!stock || stock.kind==='unknown') return stock?.reason||'Nie potwierdzono półfabrykatu';
  const parts:[string,number|undefined][]=[['szer.',stock.widthMm],['wys.',stock.heightMm],
   ['Ø',stock.diameterMm],['ścianka',stock.wallMm],['grubość',stock.thicknessMm],['L',stock.lengthMm]];
  return parts.filter((x):x is [string,number]=>typeof x[1]==='number'&&Number.isFinite(x[1]))
   .map(([key,v])=>key+' '+number(v)+' mm').join(' · ')||'Wymiary do weryfikacji';
 };
 const filename=(p:string)=>p.split(/[\\/]/).pop()||p;
 const isStep=(p:string)=>/\.(step|stp)$/i.test(p);
 const isPdf=(p:string)=>/\.pdf$/i.test(p);
 const modelScore=(p:string)=>/assembly|assembl|z[lł]o[żz]en|monta[żz]|komplet|main/i.test(filename(p))?0:1;
 const storageSettings='ds-estimate-modules-rates-v1';
 const cad=createCadSession(
  async(path:string)=>{const data=JSON.parse(await invoke<string>('analyze_step',{path}));if(data.engineVersion!=='0.7.1')throw Error('Niezgodny silnik CAD. Uruchom instalator DS Estimate 0.7.1 i sprawdź wersję w tytule okna.');return validateStepBom(data) as Inv;},
  (path:string)=>invoke<string>('step_fingerprint',{path})
 );
 let inputPath=$state('');
 let files=$state<string[]>([]);
 let candidateSteps=$state<string[]>([]);
 let selectedStep=$state('');
 let inventory=$state<Inv|null>(null);
 let pdfText=$state('');
 let notes=$state<string[]>([]);
 let busy=$state(false);
 let status=$state('Wybierz folder lub plik STEP');
 let error=$state('');
 let active=$state('material');
 let showSettings=$state(false);
 let rates=$state<Record<string,number|null>>({...DEFAULT_RATES});
 let edits=$state<Record<string,Record<string,Edit>>>({});
 let confirmed=$state<Record<string,boolean>>({});
 let excluded=$state<Record<string,boolean>>({});
 let custom=$state<Record<string,CustomRow[]>>({});
 let grade=$state('unknown');
 let partMaterials=$state<Record<string,any>>({});
 let theme=$state('dark');
 let dragActive=$state(false);
 let showFiles=$state(false);
 let showReport=$state(false);
 let materialQuery=$state('');
 let notice=$state('');
 let machines=$state<any>(structuredClone(MACHINES)),norms=$state<any>(structuredClone(NORMS)),laserLimit=$state(10),jointSeconds=$state(180);
 let contacts=$state<any>(null),jointEdits=$state<Record<string,any>>({}),jointBusy=$state(false);
 let partDialog:HTMLDialogElement;let editingPart=$state(''),draft=$state<any>(null),catalogQuery=$state('');
 let catalogOptions=$derived(sectionCatalog.sections.filter(c=>!catalogQuery||(c.name+' '+c.series).toLowerCase().includes(catalogQuery.toLowerCase())).slice(0,100));
 let partsResult=$derived.by(()=>{try{return {parts:inventory?partsList(inventory,partMaterials,materialPrices):[],error:''};}catch(e){return {parts:[],error:String(e)};}});
 let detailRows=$derived(partsResult.parts);
 let cutPlan=$derived.by(()=>{try{if(partsResult.error)throw new Error(partsResult.error);return planAutomaticCutting(detailRows,{machines,laserLimit,rate:rates.cutting,catalog:sectionCatalog.sections});}catch(e){return {rows:[],batches:[],missing:0,error:String(e)};}});
 let cuttingAudit=$derived.by(()=>inventory&&!partsResult.error?auditCutting(detailRows,cutPlan):null);
 let automatic=$derived.by(()=>{try{return automaticOperations(detailRows,contacts,jointEdits,norms);}catch(e){return {modules:{},welds:null,areaM2:0,jointCount:0,error:String(e)};}});
 let visibleParts=$derived(detailRows.filter(p=>(p.name+' '+p.id+' '+p.geometryKey+' '+(p.solid.stockHint?.catalogDesignation||'')).toLowerCase().includes(materialQuery.toLowerCase())));

 let materialPrices=$state<Record<string,number|null>>(Object.fromEntries(MATERIALS.map(m=>[m.grade,m.density<3000?22:m.grade.startsWith('1.')?18:m.grade.startsWith('Cu')?40:m.grade.startsWith('Ti')?150:5])));
 let materialApproved=$state(false);
 let selectedSolid=$state(0);
 let projectKey=$state('');
 let added=$state(0);
 let report=$derived(evaluateModules({inventory,pdfText,rates,edits,confirmed,excluded,custom,grade,materialApproved,partMaterials,materialPrices,cuttingPlan:cutPlan,automation:automatic}));
 let selected=$derived(report.modules.find(m=>m.id===active)??report.modules[0]);
 let part=$derived(inventory?.solids[selectedSolid]??null);
 let weldNotes=$derived(pdfText?parseExplicitFilletNotes(pdfText):[]);
 let knownHours=$derived(report.modules.filter(m=>!m.omitted).flatMap(m=>m.rows||[])
  .reduce((sum,r)=>sum+(r.kind==='time'?(r.value??0):0),0));
 let knownCost=$derived(kwantflowKnownCost(report));

 const projectStorage=()=>projectKey?'ds-estimate-project-xcaf-v2:'+projectKey:'';
 function saveSettings(){
  try{localStorage.setItem(storageSettings,JSON.stringify(rates));}catch{}
 }
 function saveProject(){
  if(!projectKey)return;
  try{localStorage.setItem(projectStorage(),JSON.stringify({calculationVersion:'0.7.1',edits,confirmed,excluded,custom,grade,materialApproved,partMaterials,contacts,jointEdits}));}catch{}
 }
 function restoreProject(){
  edits={};confirmed={};excluded={};custom={};grade='unknown';materialApproved=false;partMaterials={};contacts=null;jointEdits={};
  try{
   const saved=JSON.parse(localStorage.getItem(projectStorage())||'null');
   if(saved && typeof saved==='object'){
    edits=saved.edits||{};confirmed=saved.calculationVersion==='0.7.1'?(saved.confirmed||{}):{};
    excluded=saved.excluded||{};custom=saved.custom||{};
    grade=saved.grade||'unknown';materialApproved=saved.materialApproved===true;partMaterials=saved.partMaterials||{};contacts=saved.contacts?.engineVersion==='0.7.1'?saved.contacts:null;jointEdits=saved.jointEdits||{};
   }
  }catch{}
 }
 function editValue(moduleId:string,key:string,raw:string){
  const value=raw.trim()===''?null:Number(raw.replace(',','.'));
  if(value!==null&&(!Number.isFinite(value)||value<0))return;
  edits={...edits,[moduleId]:{...(edits[moduleId]||{}),[key]:{value}}};
  confirmed={...confirmed,[moduleId]:false};saveProject();
 }
 function addOperation(){
  added++;
  const list=custom[active]||[];
  const category=MODULES.find(x=>x.id===active);
  custom={...custom,[active]:[...list,{key:'custom-'+Date.now()+'-'+added,
   name:'Nowa operacja',kind:category?.rateKey?'time':'amount'}]};
  confirmed={...confirmed,[active]:false};saveProject();
 }
 function renameOperation(key:string,raw:string){
  custom={...custom,[active]:(custom[active]||[]).map(x=>x.key===key?{...x,name:raw}:x)};
  confirmed={...confirmed,[active]:false};saveProject();
 }
 function toggleConfirmed(checked:boolean){
  confirmed={...confirmed,[active]:checked};saveProject();
 }
 function toggleExcluded(checked:boolean){
  excluded={...excluded,[active]:checked};
  confirmed={...confirmed,[active]:false};saveProject();
 }
 function changeRate(key:string,raw:string){
  const v=raw.trim()===''?null:Number(raw);
  if(v!==null&&(!Number.isFinite(v)||v<0))return;
  rates={...rates,[key]:v};confirmed={};saveSettings();saveProject();
 }
 async function analyzeSelected(){
  if(!selectedStep)return;
  busy=true;error='';status='Analiza B-Rep / STEP…';
  try{
   const rev=await invoke<string>('step_fingerprint',{path:selectedStep});
   const key=JSON.stringify([selectedStep,rev]);
   const data=await cad.analyze(selectedStep);
   inventory=data;
   if(projectKey!==key){projectKey=key;restoreProject();}
   selectedSolid=0;
   const migrating=data.solids.some(s=>!Object.hasOwn(partMaterials,s.id)&&Object.hasOwn(partMaterials,s.verifiedShapeKey));
   partMaterials=Object.fromEntries(data.solids.map(s=>[s.id,{...preferenceFor(s,partMaterials),catalogId:preferenceFor(s,partMaterials).catalogId||(s.stockHint?.catalogCandidates?.length===1?s.stockHint.catalogCandidates[0].id:'')} ]));
   if(migrating){confirmed={};materialApproved=false;saveProject();notice='Przeniesiono ustawienia grup na detale. Sprawdź ceny i potwierdzenia.';}
   const documents=files.filter(isPdf);
   const texts:string[]=[];
   notes=[];
   for(const pdf of documents.slice(0,15)){
    try{
     const t=await invoke<string>('extract_pdf_text',{path:pdf});
     if(t.trim())texts.push(t.slice(0,30000));
     else notes.push('PDF bez warstwy tekstowej: '+filename(pdf)+' (OCR niepodłączony)');
    }catch{notes.push('PDF wymaga weryfikacji: '+filename(pdf));}
   }
   if(documents.length>15)notes.push('Przeczytano 15 pierwszych PDF');
   if(files.some(f=>!isPdf(f)&&!isStep(f)))
    notes.push('DXF/DWG/obrazy/Excel rozpoznano jako pliki, ale nie włączono do automatycznych czasów');
   pdfText=texts.join('\n');
   if(!contacts)await detectJoints(true);
   active='material';
   status='Analiza zakończona · wycena przeliczona automatycznie';
  }catch(e){inventory=null;error=String(e);status='Analiza nieudana';}
  finally{busy=false;}
 }
 async function openInputs(paths:string[]){
  if(busy||!paths.length)return;
  busy=true;error='';status='Przegląd plików…';
  try{
   const lists=await Promise.allSettled(paths.map(path=>invoke<string[]>('scan_project',{path})));
   const added=lists.flatMap(r=>r.status==='fulfilled'?r.value:[]);
   const failed=lists.filter(r=>r.status==='rejected');
   if(!added.length&&failed.length)throw (failed[0] as PromiseRejectedResult).reason;
   files=mergeProjectFiles(files,added);
   if(failed.length)notice='Nie udało się dodać '+failed.length+' ścieżek. Pozostałe pliki są dostępne.';
   candidateSteps=files.filter(isStep).sort((a,b)=>modelScore(a)-modelScore(b)||a.localeCompare(b));
   if(!candidateSteps.length){status='Dokumenty dodane · dodaj model STEP';busy=false;return;}
   selectedStep=preferredStep(files,selectedStep);
  }catch(e){error=String(e);status='Sprawdź wskazaną ścieżkę';busy=false;return;}
  busy=false;
  await analyzeSelected();
 }
 onMount(()=>{
  try{
   const v=JSON.parse(localStorage.getItem(storageSettings)||'null');
   if(v && typeof v==='object'){
    for(const [k,n] of Object.entries(v)){
     if(Object.hasOwn(DEFAULT_RATES,k) && (n===null||(typeof n==='number'&&Number.isFinite(n)&&n>=0)))
      rates={...rates,[k]:n as number|null};
    }
   }
  }catch{}
  try{const v=JSON.parse(localStorage.getItem('ds-estimate-material-prices-v1')||'null');if(v)materialPrices={...materialPrices,...v};}catch{}
  try{theme=localStorage.getItem('ds-estimate-theme')==='light'?'light':'dark';}catch{}
  try{const v=JSON.parse(localStorage.getItem('ds-estimate-automation-v2')||'null');if(v){
   machines=Object.fromEntries(Object.entries(MACHINES).map(([k,m])=>[k,{...m,...v.machines?.[k]}]));
   norms=Object.fromEntries(Object.entries(NORMS).map(([k,n])=>[k,{...n,...v.norms?.[k]}]));laserLimit=v.laserLimit??10;jointSeconds=Number.isFinite(v.jointSeconds)&&v.jointSeconds>=1&&v.jointSeconds<=600?v.jointSeconds:180;
  }}catch{}
  let unlisten:(()=>void)|null=null,alive=true;
  watchDrops((paths,hover)=>{if(!alive)return;dragActive=hover;if(paths)void openInputs(paths);})
   .then(cb=>{if(alive)unlisten=cb;else cb();}).catch(e=>{error='Nie można uruchomić przeciągania: '+String(e);});
  return ()=>{alive=false;unlisten?.();};
 });
 const severity=(s:string)=>s==='verified'?'ok':s==='excluded'?'idle':
  s==='review'||s==='partial'?'warn':s==='idle'?'idle':'bad';
 const statusName=(s:string)=>({
  verified:'OK',excluded:'Nie dotyczy',review:'Do potwierdzenia',
  partial:'Niepełne',missing:'Brak danych',idle:'Nieanalizowane',error:'Błąd modułu'
 } as Record<string,string>)[s]||'Weryfikacja';

 let totalMass=$derived(detailRows.reduce((sum,p)=>sum+p.massKg,0));
 let stockMass=$derived(detailRows.filter(p=>p.route!=='purchase'&&!(p.route==='cooperate'&&p.includesMaterial)).reduce((sum,p)=>sum+p.stockMassKg,0));
 async function chooseInputs(folder=false){try{const paths=await pickInputs(folder);if(paths.length)await openInputs(paths);}catch(e){error=String(e);}}
 function changeProduct(id:string,patch:any){
  const solid=inventory?.solids.find(s=>s.id===id);if(!solid)return;
  const targets=solid.productIdentityReliable&&solid.productOccurrenceKey?inventory.solids.filter(s=>s.productOccurrenceKey===solid.productOccurrenceKey):[solid];
  const next={...partMaterials};for(const s of targets)next[s.id]={...preferenceFor(s,next),...patch};partMaterials=next;
 }
 function changeMaterial(key:string,field:string,value:any){
  if(field==='route'){changeProduct(key,{route:value});confirmed={};saveProject();return;}
  partMaterials={...partMaterials,[key]:{...preferenceFor(inventory.solids.find(s=>s.id===key),partMaterials),[field]:value}};
  confirmed={};materialApproved=false;saveProject();
 }
 function chooseGrade(key:string,value:string){const m=MATERIALS.find(x=>x.grade===value);if(!m)return;
  partMaterials={...partMaterials,[key]:{...preferenceFor(inventory.solids.find(s=>s.id===key),partMaterials),grade:m.grade,density:m.density}};
  materialApproved=false;confirmed={};saveProject();
 }
 function resetValue(moduleId:string,key:string){const own={...edits[moduleId]};delete own[key];
  edits={...edits,[moduleId]:own};confirmed={...confirmed,[moduleId]:false};saveProject();}
 function removeFile(path:string){if(busy)return;files=files.filter(f=>f!==path);candidateSteps=files.filter(isStep);
  if(path===selectedStep){selectedStep=preferredStep(files);inventory=null;projectKey='';restoreProject();if(selectedStep)void analyzeSelected();}}
 function newProject(){if(busy)return;files=[];candidateSteps=[];selectedStep='';inventory=null;projectKey='';pdfText='';notes=[];error='';notice='';restoreProject();status='Dodaj pliki projektu';showReport=false;showSettings=false;active='material';}
 function toggleTheme(){theme=theme==='dark'?'light':'dark';try{localStorage.setItem('ds-estimate-theme',theme);}catch{}}
 function autoText(row:any){const value=row.kind==='time'?row.autoHours:row.autoAmount;return typeof value==='number'?number(value):'—';}
 async function exportStatus(format:'json'|'csv'){
  try{const data=moduleReport(report,{step:selectedStep,files,productCount:inventory?.productCount??inventory?.count??0,commercialProducts:commercialUnits(detailRows).map(u=>({id:u.id,name:u.name,route:u.route,bodyCount:u.bodyCount,supplierCost:u.supplierCost,conflict:u.conflict})),inspection:automatic.inspection,cuttingAudit:cuttingAudit??{error:cutPlan.error??partsResult.error??'Audyt niedostępny'},coverage:{unknownMachiningPartIds:automatic.unknownMachiningPartIds,contacts:contacts?{complete:contacts.complete,geometryValid:contacts.geometryValid,pendingPairs:contacts.pendingPairs}:null},solidCount:inventory?.count??0,totalMassKg:totalMass,stockMassKg:stockMass,parts:detailRows.map(p=>({id:p.id,productOccurrenceKey:p.solid.productOccurrenceKey,bodyIndex:p.solid.bodyIndex,bodyCount:p.solid.bodyCount,priceScope:'STEP product occurrence',name:p.name,grade:p.grade,density:p.density,dims:p.dims,massKg:p.massKg,stockMassKg:p.stockMassKg,allowances:p.allowances,route:p.route,catalogId:p.catalogId,supplierPrice:p.supplierPrice,includesMaterial:p.includesMaterial})),weldCandidates:automatic.welds?.rows??[]});
   const text=format==='json'?JSON.stringify(data,null,2):'\uFEFF'+[
    ['Moduł','Stan','Brakujące pozycje','Znany koszt PLN'],
    ...data.modules.map(m=>[m.name,statusName(m.status),m.missing,m.costPln]),[],
    ['Moduł','Operacja','Rodzaj','Automat','Przyjęto','Koszt PLN','Korekta'],
    ...data.modules.flatMap(m=>m.rows.map(r=>[m.name,r.name,r.kind,r.automatic,r.value,r.costPln,r.manuallyEdited?'tak':'nie'])),[],
    ['Produkt STEP','Id wystąpienia','Realizacja','Liczba brył','Cena dostawcy PLN za cały produkt'],
    ...commercialUnits(detailRows).filter(u=>u.route!=='make').map(u=>[u.name,u.id,ROUTES[u.route]??'Sprzeczna realizacja',u.bodyCount,u.supplierCost]),[],
    ['Detal','Realizacja','Gatunek','Gęstość kg/m³','Wymiary mm','Masa kg','Półfabrykat kg','Naddatki mm','Id produktu STEP'],
    ...detailRows.map(p=>[p.name,ROUTES[p.route],p.grade,p.density,p.dims.join(' x '),p.massKg,p.stockMassKg,p.allowances.join(' / '),p.solid.productOccurrenceKey??p.id]),[],
    ['AUDYT CIĘCIA — wystąpienie STEP','Produkt STEP','Grupa geometrii','Nazwa detalu','Realizacja','Półfabrykat','Stan czasu','Kod braku','Opis braku','Kod CAD','Powód CAD','Technologia','Czas auto [min]','Grubość [mm]','Przekrój [mm²]','Kontur [mm]','Przebicia','Gatunek','Gęstość kg/m³'],
    ...(cuttingAudit?.rows??[]).map(x=>[x.occurrenceId,x.productOccurrenceKey,x.geometryGroupId,x.name,x.route,x.stockKind,x.status,x.reasonCode,x.reasonText,x.stockFailureCode,x.nativeStockReason,x.method,x.automaticMinutes,x.thicknessMm,x.sectionAreaMm2,x.contourMm,x.pierces,x.grade,x.densityKgM3])
   ].map(row=>row.map(csvCell).join(';')).join('\r\n');
   if(await saveReport(text,format))notice='Zapisano zestawienie '+format.toUpperCase()+'.';
  }catch(e){error=String(e);}
 }
 function saveAutomation(){
  try{localStorage.setItem('ds-estimate-automation-v2',JSON.stringify({machines,norms,laserLimit,jointSeconds}));}catch{}
  confirmed={};saveProject();
 }
 function changeMachine(key:string,field:string,value:number){if(!Number.isFinite(value)||value<0)return;machines={...machines,[key]:{...machines[key],[field]:value}};saveAutomation();}
 function changeNorm(key:string,field:string,value:any){if(typeof value==='number'&&(!Number.isFinite(value)||value<0))return;norms={...norms,[key]:{...norms[key],[field]:value}};saveAutomation();}
 function editPart(id:string){const p=detailRows.find(p=>p.id===id);if(!p)return;editingPart=id;draft=structuredClone(preferenceFor(p.solid,$state.snapshot(partMaterials)));catalogQuery='';partDialog.showModal();}
 function savePart(){try{const solid=inventory?.solids.find(s=>s.id===editingPart);partValues(solid,draft,materialPrices);
  partMaterials={...partMaterials,[editingPart]:structuredClone($state.snapshot(draft))};changeProduct(editingPart,{route:draft.route,supplierPrice:draft.supplierPrice,includesMaterial:draft.includesMaterial});confirmed={};materialApproved=false;saveProject();partDialog.close();
 }catch(e){error=String(e);}}
 function setDraftCatalog(id:string){draft.catalogId=id;const c=sectionCatalog.sections.find(c=>c.id===id);if(c){draft.stockKind=({SHS:'square-hollow',RHS:'rectangular-hollow',CHS:'round-tube',I:'i-section',I_TAPERED:'i-section',U:'channel',U_TAPERED:'channel',L:'angle',L_EQ:'angle',FLAT:'flat-section'} as any)[c.shape]||'';}}
 async function detectJoints(inAnalysis=false,force=false){
  if(!inventory||jointBusy||(busy&&!inAnalysis)||(contacts&&!force))return;if(force){contacts=null;confirmed={};}jointBusy=true;busy=true;error='';status='Analiza styków B-Rep i kandydatów spoin…';
  try{const source=selectedStep,expected=JSON.parse(projectKey)[1];
   if(await invoke<string>('step_fingerprint',{path:source})!==expected)throw Error('Model zmienił się. Wczytaj ponownie STEP przed analizą spoin.');
   const data=JSON.parse(await invoke<string>('analyze_joints',{path:source,maxSeconds:jointSeconds}));
   if(source!==selectedStep||await invoke<string>('step_fingerprint',{path:source})!==expected)throw Error('Model zmienił się podczas analizy.');
   if(data.solidCount!==inventory.count||!Array.isArray(data.candidates))throw Error('Niezgodny wynik analizy styków.');
   contacts=data;confirmed={...confirmed,welding:false,assembly:false,quality:false,cnc:false,postweld:false};saveProject();status='Analiza styków zakończona — sprawdź propozycje spoin';
  }catch(e){error=String(e);if(inAnalysis)throw e;}finally{jointBusy=false;if(!inAnalysis)busy=false;}
 }
 function changeJoint(id:string,field:string,value:any){jointEdits={...jointEdits,[id]:{...jointEdits[id],[field]:value}};confirmed={...confirmed,welding:false,assembly:false,quality:false,postweld:false};saveProject();}
 function materialPrice(grade:string,raw:string){const value=raw===''?null:Number(raw);if(value!==null&&(!Number.isFinite(value)||value<0))return;materialPrices={...materialPrices,[grade]:value};try{localStorage.setItem('ds-estimate-material-prices-v1',JSON.stringify(materialPrices));}catch{}confirmed={};saveProject();}
 function partDescription(p:any){const h=p.solid.stockHint?.kind==='unknown'&&p.solid.stockHint?.rawStockCandidate?p.solid.stockHint.rawStockCandidate:(p.solid.stockHint??{}),kind=p.stockKind||h.kind;const label=sectionCatalog.sections.find(c=>c.id===p.catalogId)?.name||h.catalogDesignation;
  if(label)return label;
  if(['plate-candidate','plate','bent-plate'].includes(kind))return (kind==='bent-plate'?'Blacha gięta ':'Płyta ')+number(h.thicknessMm??p.solid.cuttingHint?.thicknessMm??p.dims[2])+' mm';
  return (stockLabels[kind]||'Detal')+' '+[h.widthMm,h.heightMm,h.wallMm].filter(v=>v!==undefined).map(number).join(' × ');
 }
 const jointName=(id:string)=>detailRows.find(p=>p.id===id)?.name||id;
</script>
<div class="app" data-theme={theme}>
 <dialog bind:this={partDialog} class="part-dialog">
  {#if draft}
  <form onsubmit={e=>{e.preventDefault();savePart();}}>
   <div class="panel-title"><div><h2>Parametry detalu · {detailRows.find(p=>p.id===editingPart)?.name||editingPart}</h2><p>Ustawienia dotyczą tylko tego wystąpienia w złożeniu.</p></div><button type="button" class="icon-button" aria-label="Zamknij parametry" onclick={()=>partDialog.close()}><X size={18}/></button></div>
   {#key editingPart}<PartPreview mesh={inventory?.previews?.[inventory?.solids.find(s=>s.id===editingPart)?.previewKey]} path={selectedStep} index={inventory?.solids.findIndex(s=>s.id===editingPart)??0} name={detailRows.find(p=>p.id===editingPart)?.name||editingPart}/>{/key}
   <div class="form-grid">
    <label>Sposób realizacji<select bind:value={draft.route}>{#each Object.entries(ROUTES) as [id,label]}<option value={id}>{label}</option>{/each}</select></label>
    <label>Cena dostawcy [zł / produkt STEP]<input type="number" min="0" step=".01" value={draft.supplierPrice??''} onchange={e=>draft.supplierPrice=e.currentTarget.value===''?null:Number(e.currentTarget.value)}/></label>
   </div>
   {#if draft.route==='cooperate'}<label class="check"><input type="checkbox" bind:checked={draft.includesMaterial}/>Cena kooperacji obejmuje materiał</label>{/if}
   <p class="hint">Realizacja i cena dostawcy dotyczą całego wystąpienia produktu STEP. Materiał i naddatki dotyczą tej bryły. Produkt STEP nie zawsze odpowiada jednostce handlowej.</p><h3>Naddatki na sześciu stronach [mm]</h3><div class="form-grid">{#each ['Długość — początek','Długość — koniec','Szerokość — strona 1','Szerokość — strona 2','Grubość / wysokość — strona 1','Grubość / wysokość — strona 2'] as label,i}<label>{label}<input type="number" min="0" step=".1" bind:value={draft.allowances[i]} required/></label>{/each}</div>
   <label class="stacked">Znana masa półfabrykatu [kg] — puste = automatyczny półfabrykat i naddatki<input type="number" min="0" step=".001" value={draft.stockMassKg??''} onchange={e=>draft.stockMassKg=e.currentTarget.value===''?null:Number(e.currentTarget.value)}/></label>
   <h3>Biblioteka przekrojów · {sectionCatalog.sections.length} pozycji</h3>
   <p>Dopasowanie wymiarów nie potwierdza gatunku ani normy dostawy. Wybierz oznaczenie, gdy kilka pozycji pasuje do geometrii.</p>
   <div class="form-grid"><label>Szukaj przekroju<input bind:value={catalogQuery} placeholder="np. IPE 200, SHS 40x40x2"/></label><label>Pasujące pozycje<select aria-label="Przekrój katalogowy" value={draft.catalogId} onchange={e=>setDraftCatalog(e.currentTarget.value)}><option value="">Bez przypisania katalogowego</option>{#if draft.catalogId&&!catalogOptions.some(c=>c.id===draft.catalogId)}<option value={draft.catalogId}>{sectionCatalog.sections.find(c=>c.id===draft.catalogId)?.name||draft.catalogId}</option>{/if}{#each catalogOptions as c}<option value={c.id}>{c.name} · {c.series}</option>{/each}</select></label>
    <label>Rodzaj wyrobu<select bind:value={draft.stockKind}><option value="">Z rozpoznania geometrii</option>{#each Object.entries(stockLabels) as [key,label]}<option value={key}>{label}</option>{/each}<option value="bent-plate">Blacha gięta</option></select></label></div>
   <h3>Parametry cięcia i gięcia</h3><div class="form-grid">
    <label>Technologia<select bind:value={draft.cutMethod}><option value="auto">Dobór automatyczny</option>{#each Object.entries(METHOD_LABELS) as [key,label]}<option value={key}>{label}</option>{/each}</select></label>
    <label>Liczba cięć piłą<input type="number" min="0" step="1" bind:value={draft.cutCount} required/></label>
    <label>Kąt cięcia piłą [°]<input type="number" min="0" max="75" step="1" bind:value={draft.sawAngle} required/></label>
    <label>Ręczne pole cięcia [mm²]<input type="number" min=".001" step="any" value={draft.cutAreaMm2??''} onchange={e=>draft.cutAreaMm2=e.currentTarget.value===''?null:Number(e.currentTarget.value)}/></label>
    <label>Kontur / kontur rozwinięcia [mm]<input type="number" min="0" step="any" value={draft.contourMm??''} onchange={e=>draft.contourMm=e.currentTarget.value===''?null:Number(e.currentTarget.value)}/></label>
    <label>Liczba przebić<input type="number" min="0" step="1" value={draft.pierces??''} onchange={e=>draft.pierces=e.currentTarget.value===''?null:Number(e.currentTarget.value)}/></label>
    <label>Ręczna liczba gięć<input type="number" min="0" step="1" value={draft.bendCount??''} onchange={e=>draft.bendCount=e.currentTarget.value===''?null:Number(e.currentTarget.value)}/></label>
   </div>
   <div class="panel-actions"><button type="button" onclick={()=>partDialog.close()}>Anuluj</button><button class="primary" type="submit">Zapisz detal</button></div>
  </form>{/if}
 </dialog>

 <aside class="rail">
  <div class="brand"><span class="brand-mark"><Layers3 size={23}/></span><strong>DS Estimate</strong></div>
  <nav aria-label="Moduły wyceny">
   <button class:active={!showSettings&&!showReport&&active==='project'} onclick={()=>{active='project';showSettings=false;showReport=false;}}><Files size={18}/><span>Pliki projektu</span><small class="nav-count">{files.length}</small></button>
   {#if inventory&&!busy}<div class="rail-caption">ETAPY WYCENY</div>
   {#each report.modules as mod}
    <button class:active={!showSettings&&!showReport&&active===mod.id} title={mod.title+' — '+statusName(mod.status)} onclick={()=>{active=mod.id;showSettings=false;showReport=false;if(mod.id==='welding')void detectJoints();}}>
     <span class={'stage-dot '+severity(mod.status)}>{mod.status==='verified'?'✓':mod.status==='excluded'?'–':''}</span>
     <span>{mod.title}</span>
    </button>
   {/each}{/if}
  </nav>
  <div class="rail-bottom">
   <button class:active={showReport} onclick={()=>{showReport=true;showSettings=false;}}><ClipboardList size={18}/><span>Stan modułów</span></button>
   <button class:active={showSettings} onclick={()=>{showSettings=true;showReport=false;}}><Settings2 size={18}/><span>Stawki i ustawienia</span></button>
   <small>DS Estimate 0.7.1 · zapis lokalny</small>
  </div>
 </aside>
 <div class="workspace">
  <header>
   <div class="breadcrumb"><strong>{busy?'Analiza STEP':showSettings?'Stawki i ustawienia':showReport?'Stan modułów':!inventory||active==='project'?'Pliki projektu':selected.title}</strong><ChevronRight size={14}/><span>{selectedStep?filename(selectedStep):'Nowy projekt'}</span></div>
   <div class="header-actions">
    <button class="subtle" disabled={busy} onclick={newProject}><Plus size={16}/>Nowy projekt</button>
    <button class="subtle" onclick={()=>exportStatus('csv')} disabled={!inventory||busy}><Download size={16}/>Eksport CSV</button>
    <button class="icon-button" onclick={toggleTheme} aria-label="Zmień motyw">{#if theme==='dark'}<Sun size={18}/>{:else}<Moon size={18}/>{/if}</button>
   </div>
  </header>
  <main>
   {#if !native}<div class="banner info">Podgląd interfejsu. Dodawanie lokalnych plików i analiza CAD działają w programie Windows.</div>{/if}
   {#each inventory?.importIssues??[] as issue}<div class="banner warning">{issue}</div>{/each}
   {#if inventory&&!busy&&!showSettings}<details class="machine-editor"><summary>Założenia automatycznej wyceny</summary>{#each automatic.notes??[] as note}<p class="muted">{note}</p>{/each}<p class="muted">Standardowe śruby, nakrętki i podkładki są proponowane jako zakup na podstawie nazwy. Sposób realizacji można zmienić przy detalu.</p></details>{/if}
   {#if partsResult.error}<div class="banner danger">{partsResult.error}</div>{/if}
   {#if error}<div class="banner danger" role="alert"><div><strong>Nie udało się ukończyć operacji</strong><p>{error}</p></div><button aria-label="Zamknij błąd" onclick={()=>error=''}><X size={16}/></button></div>{/if}
   {#if notice}<div class="banner info" role="status"><span>{notice}</span><button aria-label="Zamknij informację" onclick={()=>notice=''}><X size={16}/></button></div>{/if}
   <div class="page-heading">
    <div><h1>{busy?'Analiza modelu':showSettings?'Stawki i ustawienia':showReport?'Stan poszczególnych modułów':!inventory?'Wczytaj konstrukcję':active==='project'?'Pliki projektu':selected.title}</h1>
     <p>{showSettings?'Jedno miejsce dla cen materiału i stawek stanowisk.':showReport?'Sprawdź, co jest policzone, a co wymaga uzupełnienia.':!inventory?'Dodaj modele STEP i dokumentację. Przejdź przez kolejne etapy wyceny.':active==='project'?'Wybierz model główny. Pozostałe pliki pozostają dokumentacją projektu.':selected.detail}</p>
    </div>
    <div class="heading-actions"><button class="primary" disabled={busy} onclick={()=>chooseInputs()}><FilePlus2 size={17}/>Dodaj pliki</button><button disabled={busy} onclick={()=>chooseInputs(true)}><FolderOpen size={17}/>Dodaj folder</button></div>
   </div>

   {#if !showSettings&&(!inventory||busy||active==='project')}
    <div class:drop-active={dragActive} class:compact={inventory&&active!=='project'} class="upload-panel panel" aria-label="Obszar dodawania plików">
     <Upload size={inventory?22:32}/><div><strong>{dragActive?'Upuść pliki tutaj':busy?status:'Przeciągnij pliki lub folder do programu'}</strong><p>STEP / STP · PDF · DXF / DWG · obrazy · Excel</p></div>
     <button class="subtle" onclick={()=>showFiles=!showFiles} aria-expanded={showFiles}>{files.length} plików <ChevronRight size={15}/></button>
    </div>
    {#if !busy}<details class="manual-path"><summary>Otwórz plik przez ścieżkę</summary><div class="input-action"><input aria-label="Ścieżka modelu STEP" bind:value={inputPath} placeholder="C:\modele\zlozenie.step"/><button disabled={!inputPath.trim()} onclick={()=>openInputs([inputPath.trim()])}>Analizuj ścieżkę</button></div></details>{/if}
    {#if busy}<div class="analysis-progress" role="status"><span class="spinner"></span>{status}<span>Nie zamykaj programu.</span></div>{/if}
    {#if files.length&&showFiles}
     <section class="panel files-panel" aria-label="Pliki projektu">
      <div class="panel-title"><h2>Pliki projektu</h2><span class="muted">Jeden wybrany STEP stanowi zakres wyceny.</span></div>
      <ul class="file-list">
       {#each files as file}<li class:chosen={file===selectedStep}>
        <span class="file-type">{file.split('.').pop()?.toUpperCase()}</span><div class="file-name"><strong title={file}>{filename(file)}</strong><small>{file===selectedStep?'Model wyceniany':isStep(file)?'Dodatkowy model — nie doliczany do masy':isPdf(file)?'Dokumentacja PDF — odczyt warstwy tekstowej':'Załącznik — bez automatycznej analizy'}</small></div>
        {#if isStep(file)&&file!==selectedStep}<button class="tiny" disabled={busy} onclick={()=>{selectedStep=file;void analyzeSelected();}}>Wyceń ten model</button>{/if}
        {#if file===selectedStep}<span class="pill ok">Model główny</span>{/if}
        <button class="icon-button" title="Usuń z projektu" aria-label={'Usuń '+filename(file)} disabled={busy} onclick={()=>removeFile(file)}><X size={14}/></button>
       </li>{/each}
      </ul>
      <details class="manual-path"><summary>Wklej ścieżkę ręcznie</summary><div class="input-action"><input aria-label="Ścieżka pliku lub folderu" bind:value={inputPath} placeholder="C:\modele\zlozenie.step" onkeydown={e=>{if(e.key==='Enter'&&inputPath.trim())void openInputs([inputPath.trim()]);}}/><button disabled={busy||!inputPath.trim()} onclick={()=>openInputs([inputPath.trim()])}>Dodaj</button></div></details>
     </section>
    {/if}
   {/if}

   {#if busy}
    <section class="panel padded" role="status"><h2>Trwa analiza modelu</h2><p>{status}</p><p>Etapy wyceny pojawią się po analizie części i połączeń.</p></section>
   {:else if showSettings}
    <div class="settings-grid">
     <section class="panel"><h2>Materiał i stanowiska</h2><p>Wartości startowe są przykładowe. Zmiany nie uruchamiają ponownie silnika CAD.</p><div class="form-grid">

      {#each MODULES.filter(x=>x.rateKey) as m}<label>{m.title} [zł/h]<input type="number" min="0" value={rates[m.rateKey]??''} onchange={e=>changeRate(m.rateKey,e.currentTarget.value)}/></label>{/each}
     </div></section>
     <section class="panel"><h2>Geometria i zapis</h2><p>STEP jest odczytywany przez lokalny silnik OCCT. Przeliczenie kosztów korzysta z zapisanego wyniku analizy.</p><dl><dt>Gęstość domyślna</dt><dd>7850 kg/m³</dd><dt>Gatunek bez danych</dt><dd>Puste pole</dd><dt>Ustawienia części i korekty</dt><dd>Zapis lokalny dla wybranego modelu i jego wersji</dd><dt>Dokumentacja</dt><dd>PDF: warstwa tekstowa; DXF, DWG, obrazy i Excel: lista załączników</dd></dl><button onclick={toggleTheme}>{theme==='dark'?'Włącz jasny motyw':'Włącz ciemny motyw'}</button><p class="hint">Zmiana pliku STEP unieważnia jego poprzedni przedmiar. Żaden moduł nie traktuje brakujących czasów jak potwierdzonych zer.</p></section>
    </div>

    <section class="panel"><div class="panel-title"><div><h2>Maszyny i reguły cięcia</h2><p>Wartości startowe są przykładowe, wymagają kalibracji w Twoim zakładzie. Posuw zależy od grubości.</p></div></div>
     <label class="stacked">Granica preferowanego lasera [mm]<input aria-label="Granica lasera" type="number" min=".1" max="50" value={laserLimit} onchange={e=>{if(e.currentTarget.reportValidity()){laserLimit=Number(e.currentTarget.value);saveAutomation();}}}/></label>
     {#each Object.entries(machines) as [key,m]}<details class="machine-editor"><summary>{METHOD_LABELS[key]}</summary><div class="form-grid">
      <label>Przezbrojenie [min]<input type="number" min="0" value={m.setupMin} onchange={e=>changeMachine(key,'setupMin',Number(e.currentTarget.value))}/></label><label>Obsługa cięcia / detalu [min]<input type="number" min="0" step=".1" value={m.handlingMin} onchange={e=>changeMachine(key,'handlingMin',Number(e.currentTarget.value))}/></label>
      <label>Zakres grubości [mm]<input type="number" min=".1" value={m.maxThickness} onchange={e=>changeMachine(key,'maxThickness',Number(e.currentTarget.value))}/></label>
      {#if key==='saw'}<label>Wydajność [mm²/min]<input type="number" min=".1" value={m.areaRate} onchange={e=>changeMachine(key,'areaRate',Number(e.currentTarget.value))}/></label>{:else}<label>Przebicie [s]<input type="number" min="0" value={m.pierceSec} onchange={e=>changeMachine(key,'pierceSec',Number(e.currentTarget.value))}/></label>{/if}
     </div>{#if m.curve}<div class="feed-curve">{#each m.curve as pair,i}<label>{pair[0]} mm<input aria-label={METHOD_LABELS[key]+' posuw '+pair[0]+' mm'} type="number" min="1" value={pair[1]} onchange={e=>{if(e.currentTarget.reportValidity()){const curve=machines[key].curve.map((p,j)=>j===i?[p[0],Number(e.currentTarget.value)]:p);machines={...machines,[key]:{...machines[key],curve}};saveAutomation();}}}/><small>mm/min</small></label>{/each}</div>{/if}</details>{/each}
    </section>
    <section class="panel"><h2>Automatyczne normy operacji</h2><div class="form-grid"><label>Limit analizy połączeń [s]<input type="number" min="1" max="600" step="1" bind:value={jointSeconds} onchange={e=>{if(e.currentTarget.reportValidity())saveAutomation();}}/></label><button disabled={!inventory||busy||jointBusy} onclick={()=>void detectJoints(false,true)}>Ponów analizę połączeń</button></div><p>Geometria jest mierzona; poniższe normy czasu są założeniami do wyceny. Wyniki możesz nadpisać przy operacjach.</p>
     {#each Object.entries(norms) as [key,n]}<details class="machine-editor"><summary>{MODULES.find(m=>m.id===key)?.title||key}</summary><label class="check"><input type="checkbox" checked={n.enabled} onchange={e=>changeNorm(key,'enabled',e.currentTarget.checked)}/>Używaj automatycznego oszacowania</label><div class="form-grid">{#each Object.entries(n).filter(([field])=>field!=='enabled') as [field,v]}<label>{({drillingMode:'Dodatkowe wiercenie',machiningMode:'Obróbka po spawaniu',ndtMode:'Zakres NDT',scopeMode:'Zakres powłok',minutesPerRepeat:'Kontrola kolejnej sztuki [min]',supplierSampleRatio:'Udział próbek dostaw [0–1]',supplierSampleMin:'Kontrola próbki dostawy [min]',ndtSetupMin:'Przygotowanie NDT [min]',ndtMinMeter:'Badanie NDT [min/m]',setupMin:'Przygotowanie [min]',minutesPerPart:'Czas na detal [min]',minutesPerJoint:'Czas na połączenie [min]',heavyKg:'Próg ciężkiego detalu [kg]',heavyFactor:'Mnożnik ciężkiego detalu',a:'Domyślne a spoiny [mm]',deposition:'Wydajność stapiania [kg/h]',arcFactor:'Wykorzystanie łuku [0–1]',density:'Gęstość stopiwa [kg/m³]',secondsPerBend:'Cykl gięcia [s]',handlingMin:'Manipulacja [min]',removalCm3Min:'Usuwanie materiału [cm³/min]',layers:'Liczba warstw',m2Hour:'Wydajność powłoki [m²/h]',grindMinMeter:'Szlifowanie [min/m]',straightenMin:'Przygotowanie prostowania [min]',turnMinPart:'Manipulacja [min/podzespół]',longMm:'Próg długości podzespołu [mm]',profileFactor:'Mnożnik montażu profilu',bentFactor:'Mnożnik montażu blachy giętej',unknownFactor:'Mnożnik detalu nierozpoznanego',referenceLengthMm:'Długość odniesienia gięcia [mm]',referenceThicknessMm:'Grubość odniesienia gięcia [mm]',bevelSetupMin:'Przygotowanie fazowania [min]',bevelCm3Min:'Usuwanie materiału faz [cm³/min]',filletGrindFactor:'Mnożnik szlifowania pachwin',straightenDepositKgMeter:'Próg stopiwa dla prostowania [kg/m]',straightenLengthMeter:'Próg długości dla prostowania [m]',tackSpacingMm:'Rozstaw sczepów [mm]',tackSeconds:'Czas sczepu [s]',cleanMinMeter:'Czyszczenie spoin [min/m]',buttGrindFactor:'Mnożnik szlifowania spoin czołowych',straightenMinMeter:'Prostowanie [min/m spoiny]',vtMinMeter:'Kontrola VT [min/m]',packingMinPart:'Pakowanie [min/produkt STEP]',distanceKm:'Dystans [km]',costKm:'Transport [zł/km]',minutes:'Przygotowanie technologii [min]'} as any)[field]||field}{#if NORM_CHOICES[field]}<select value={v} onchange={e=>changeNorm(key,field,Number(e.currentTarget.value))}>{#each NORM_CHOICES[field] as option}<option value={option[0]}>{option[1]}</option>{/each}</select>{:else}<input type="number" min="0" step="any" value={v} onchange={e=>{if(e.currentTarget.reportValidity())changeNorm(key,field,Number(e.currentTarget.value));}}/>{/if}</label>{/each}</div></details>{/each}
     <p class="hint">Powłoki domyślnie dotyczą detali produkowanych; ustawienie pozwala włączyć zakupowe. Wykorzystują powierzchnie z B-Rep (z powierzchniami stykowymi); zweryfikuj powierzchnię faktycznie malowaną. CNC z naddatków jest oszacowaniem objętości usuwanej, nie czasem CAM.</p>
    </section>
       <section class="panel results-panel"><div class="panel-title"><div><h2>Ceny materiałów [zł/kg]</h2><p>Stawki zakładowe do wyceny — wartości początkowe są przykładowe. Pusty gatunek korzysta z pierwszej pozycji.</p></div></div><div class="form-grid padded">{#each MATERIALS as m}<label>{m.grade?m.label:'Stal — gatunek nieokreślony'}<input aria-label={'Cena kg '+(m.grade||'stal')} type="number" min="0" step=".01" value={materialPrices[m.grade]??''} onchange={e=>materialPrice(m.grade,e.currentTarget.value)}/></label>{/each}</div></section>
{:else if showReport}
    <section class="panel results-panel"><div class="panel-title"><h2>Gotowość wyceny</h2><span class="pill">{report.completedModules} / {report.totalModules} etapów</span></div>
     <div class="table-scroll"><table><thead><tr><th>Moduł</th><th>Stan</th><th>Brakujące pozycje</th><th>Znany koszt</th><th></th></tr></thead><tbody>{#each report.modules as mod}<tr><td><strong>{mod.title}</strong></td><td><span class={'pill '+severity(mod.status)}>{statusName(mod.status)}</span></td><td>{mod.missing}</td><td>{money(mod.knownCostPln)} zł</td><td><button class="tiny" onclick={()=>{showReport=false;active=mod.id;}}>Otwórz</button></td></tr>{/each}</tbody></table></div>
     <div class="panel-actions"><button disabled={!inventory||busy} onclick={()=>exportStatus('json')}><Download size={15}/>Zapisz raport JSON</button><button disabled={!inventory||busy} onclick={()=>exportStatus('csv')}><Download size={15}/>Zapisz raport CSV</button></div>
    </section><div class="banner info">Potwierdzenie etapu oznacza sprawdzenie danych przez operatora. Nie jest potwierdzeniem pełnej automatyzacji rozpoznawania technologii.</div>
   {:else if inventory&&active!=='project'}
    <div class="metrics"><article><Scale size={17}/><div><small>Masa konstrukcji</small><strong>{number(totalMass)} <em>kg</em></strong></div></article><article><Layers3 size={17}/><div><small>Materiał do przygotowania</small><strong>{number(stockMass)} <em>kg</em></strong></div></article><article><Files size={17}/><div><small>Bryły / produkty STEP</small><strong>{inventory.count} <em>/ {inventory.productCount??inventory.count}</em></strong></div></article><article><Check size={17}/><div><small>Potwierdzone etapy</small><strong>{report.completedModules} <em>/ {report.totalModules}</em></strong></div></article></div>

    {#if active==='material'}
     <section class="panel results-panel"><div class="panel-title"><div><h2>Części i materiały</h2><p>Każde wystąpienie ma własny materiał, wymiary, naddatki i realizację. Dopasowanie katalogowe sprawdź z dokumentacją.</p></div><label class="search"><Search size={15}/><input aria-label="Szukaj grupy części" bind:value={materialQuery} placeholder="Szukaj części…"/></label></div>
      <div class="table-scroll"><table><thead><tr><th>Detal / przekrój</th><th>Wymiary [mm]</th><th>Realizacja</th><th>Gatunek</th><th>Gęstość kg/m³</th><th>Masa [kg]</th><th>Materiał [zł]</th><th>Naddatki / półfabrykat</th></tr></thead><tbody>
       {#each visibleParts as p (p.id)}
        <tr><td><strong>{p.name}</strong><small class="cell-note">{partDescription(p)}</small>{#if p.solid.bodyCount>1}<small class="cell-note">Bryła {p.solid.bodyIndex+1} z {p.solid.bodyCount} tego produktu STEP</small>{/if}{#if p.solid.nameSource==='missing'}<small class="cell-note">STEP nie udostępnił nazwy</small>{/if}<button class="tiny text" onclick={()=>editPart(p.id)}>Parametry / biblioteka</button></td>
         <td>{p.dims.map(number).join(' × ')}<small class="cell-note">{p.solid.stockHint?.catalogStatus==='multiple-fits'?'Kilka pasujących przekrojów — wybierz':p.solid.bendHint?.count?'Gięcia: '+p.solid.bendHint.count+' (kandydat)':''}</small></td>
         <td><select aria-label={'Realizacja '+p.id} value={p.route} onchange={e=>changeMaterial(p.id,'route',e.currentTarget.value)}>{#each Object.entries(ROUTES) as [id,label]}<option value={id}>{label}</option>{/each}</select></td>
         <td><select aria-label={'Gatunek '+p.id} value={p.grade} onchange={e=>chooseGrade(p.id,e.currentTarget.value)}>{#each MATERIALS as mat}<option value={mat.grade}>{mat.label}</option>{/each}</select></td>
         <td><input class="number-input" aria-label={'Gęstość '+p.id} type="number" min="1" value={p.density} onchange={e=>{if(e.currentTarget.reportValidity())changeMaterial(p.id,'density',Number(e.currentTarget.value));}}/></td>
         <td>{number(p.massKg)}</td>
         <td>{p.materialCost===null?'—':money(p.materialCost)}<small class="cell-note">{p.route==='purchase'||(p.route==='cooperate'&&p.includesMaterial)?'W cenie dostawcy':'cały materiał detalu'}</small></td>
         <td><button class="tiny" aria-label={'Naddatki '+p.id} onclick={()=>editPart(p.id)}>{p.allowances.some(v=>v>0)?'Ustawione':'+ Dodaj'}</button><small class="cell-note">{number(p.stockMassKg)} kg</small><small class="cell-note">{p.stockSource}</small></td>
        </tr>
       {/each}
      </tbody></table></div>
      <div class="panel-actions"><strong>Policzony materiał: {money(detailRows.reduce((sum,p)=>sum+(p.materialCost??0),0))} zł</strong><span class="muted">{detailRows.filter(p=>p.materialCost===null).length} pozycji bez ustalonego kosztu. Ceny za kg zmienisz w ustawieniach.</span></div>
     </section>
     <p class="hint">Naddatki ustawiasz na sześciu stronach każdego detalu. Masa półfabrykatu z powiększonych gabarytów jest szacunkiem; dla profili preferuj naddatek długości, dla nietypowych części podaj znaną masę. Zakup i kooperacja są rozliczane osobno.</p>
    {/if}


    {#if active==='cutting'}
     <section class="panel results-panel"><div class="panel-title"><div><h2>Plan cięcia detali</h2><p>Blacha ≤ {laserLimit} mm: laser. Profile: piła. Przezbrojenie raz na partię.</p></div><span class="pill">{cutPlan.batches.length} partii</span></div>
      {#if cutPlan.error}<div class="banner danger">{cutPlan.error}</div>{/if}
      <div class="table-scroll"><table><thead><tr><th>Detal / partia</th><th>Technologia</th><th>Podstawa geometryczna</th><th>Praca [min]</th><th>Przezbrojenie [min]</th><th>Razem [min]</th><th></th></tr></thead><tbody>
       {#each cutPlan.rows as row}<tr><td><strong>{row.name}</strong><small class="cell-note">{row.batchKey}</small></td><td>{METHOD_LABELS[row.method]||'Do ustalenia'}</td><td>{row.method==='saw'?(row.sectionArea===null?'Brak pola przekroju':number(row.sectionArea)+' mm²'):(row.contour===null?'Brak konturu':number(row.contour)+' mm · '+row.pierces+' przebić')}<small class="cell-note">{row.notes.join(' ')}</small></td><td>{row.runMin===null?'—':number(row.runMin)}</td><td>{number(row.setupMin)}</td><td>{row.minutes===null?'—':number(row.minutes)}</td><td><button class="tiny" onclick={()=>editPart(row.id)}>Parametry</button></td></tr>{/each}
      </tbody></table></div>
      {#if cuttingAudit}<div class="panel-actions"><strong>Policzone: {cuttingAudit.knownTimeOccurrences} / {cuttingAudit.ownCutOccurrences} wystąpień własnych · {number(cuttingAudit.knownTimeMin)} min znanego czasu</strong><span class="muted">{cuttingAudit.unresolvedOwnOccurrences} bez czasu · {cuttingAudit.statusCounts.PURCHASED_NO_INTERNAL_CUT??0} zakup · {cuttingAudit.statusCounts.SUBCONTRACTED??0} kooperacja. To nie jest potwierdzenie pełnej wyceny.</span></div>
       {#if cuttingAudit.unresolvedOwnOccurrences>0}<details class="machine-editor"><summary>Przyczyny brakujących czasów ({cuttingAudit.unresolvedOwnOccurrences})</summary><div class="table-scroll"><table><thead><tr><th>Detal STEP</th><th>Półfabrykat</th><th>Przyczyna</th><th></th></tr></thead><tbody>{#each cuttingAudit.rows.filter(x=>x.status==='PENDING') as x (x.occurrenceId)}<tr><td>{x.name}<small class="cell-note">{x.occurrenceId}</small></td><td>{stockLabels[x.stockKind]||x.stockKind}</td><td>{x.reasonText}</td><td><button class="tiny" onclick={()=>editPart(x.occurrenceId)}>Parametry</button></td></tr>{/each}</tbody></table></div></details>{/if}
      {/if}
      <div class="panel-actions"><span class="muted">Posortowano według maszyny, materiału i przekroju / grubości. Zakup i kooperacja pominięte. Eksport CSV/JSON zawiera pełny audyt wystąpień.</span></div>
     </section>
    {/if}
    {#if active==='bending'}
     <section class="panel results-panel"><div class="panel-title"><div><h2>Gięcia detali</h2><p>Gięcia z geometrii; czas z długości linii, grubości, masy i norm prasy. Przezbrojenie na grupę materiał / grubość / promień. Naroża profili pomijane.</p></div></div><div class="table-scroll"><table><thead><tr><th>Detal</th><th>Wyrób / grubość</th><th>Liczba gięć</th><th>Czas pracy [min]</th><th></th></tr></thead><tbody>{#each detailRows.filter(p=>p.route==='make') as p}<tr><td>{p.name}</td><td>{partDescription(p)}</td><td>{partBends(p)??'Nierozpoznane'}</td><td>{partBends(p)===null?'—':number(bendEstimate(p,norms.bending).minutes)}</td><td><button class="tiny" onclick={()=>editPart(p.id)}>Parametry</button></td></tr>{/each}</tbody></table></div></section>
    {/if}
    {#if active==='welding'}
     <section class="panel results-panel"><div class="panel-title"><div><h2>Styki i proponowane spoiny</h2><p>Geometria wyznacza styk i długość. Potwierdź zamiar spawania, przekrój i dostęp.</p></div><button disabled={busy||jointBusy||!!contacts} onclick={()=>void detectJoints()}>{jointBusy?'Analiza…':contacts?'Przeanalizowano STEP':'Wykryj styki STEP'}</button></div>
      {#if contacts&&automatic.welds}
       <div class="table-scroll"><table><thead><tr><th>Detale</th><th>Uwzględnij</th><th>Typ</th><th>Długość [mm]</th><th>a [mm] / pole [mm²]</th><th>Stopiwo kg/m³</th><th>Czas [min]</th></tr></thead><tbody>{#each automatic.welds.rows as row}<tr><td><strong>{jointName(row.partA)} / {jointName(row.partB)}</strong><small class="cell-note">{row.groove?'Przygotowanie '+row.preparation+' · '+number(row.groove.includedAngleDeg??0)+'° · '+number(row.groove.sectionMm2??0)+' mm² rowka':'Brak potwierdzonego rowka · założenie spoiny pachwinowej'}</small></td><td><input aria-label={'Uwzględnij '+row.id} type="checkbox" checked={row.enabled} onchange={e=>changeJoint(row.id,'enabled',e.currentTarget.checked)}/></td><td><select aria-label={'Typ spoiny '+row.id} value={row.type} onchange={e=>changeJoint(row.id,'type',e.currentTarget.value)}><option value="fillet">Pachwinowa</option><option value="butt">Czołowa / rowek</option></select></td><td><input class="number-input" aria-label={'Długość spoiny '+row.id} type="number" min="0" step="any" value={row.lengthMm} onchange={e=>{if(e.currentTarget.reportValidity())changeJoint(row.id,'lengthMm',Number(e.currentTarget.value));}}/></td><td><input class="number-input" aria-label={'Przekrój spoiny '+row.id} type="number" min=".1" step=".1" value={row.type==='fillet'?row.a:row.sectionMm2} onchange={e=>{if(e.currentTarget.reportValidity())changeJoint(row.id,row.type==='fillet'?'a':'sectionMm2',Number(e.currentTarget.value));}}/></td><td><input class="number-input" aria-label={'Gęstość stopiwa '+row.id} type="number" min="1" value={row.density??row.defaultDensity??norms.welding.density} onchange={e=>{if(e.currentTarget.reportValidity())changeJoint(row.id,'density',Number(e.currentTarget.value));}}/></td><td>{number(row.minutes)}</td></tr>{/each}</tbody></table></div>
       <div class="panel-actions"><strong>{number(automatic.welds.totalLengthMm/1000)} m proponowanych spoin · {number(automatic.welds.minutes)} min</strong><span class="pill">{!contacts.complete?'Wynik częściowy':contacts.geometryValid===false?'Nierozwiązane przenikania / błędy':'Analiza styków zakończona'}</span></div>
       {#if automatic.welds.groups.length}<div class="weld-groups">{#each automatic.welds.groups as g}<span class="pill">{g.type==='fillet'?'Pachwinowa a'+g.a:'Czołowa '+g.sectionMm2+' mm²'} · {number(g.lengthMm/1000)} m · {number(g.minutes)} min</span>{/each}</div>{/if}
       <p class="hint padded">Sprawdzone pary: {contacts.completedPairs??contacts.testedPairs} / {contacts.eligiblePairs??'—'} · pozostało: {contacts.pendingPairs??'—'}. Limit: {contacts.analysisBudgetSeconds??jointSeconds} s.</p>
       {#each contacts.issues??[] as issue}<p class="hint padded">{issue}</p>{/each}
       <p class="hint padded">Obwód ścian styku jest propozycją spawania dookoła. Początkowe a pochodzi z 0,7 × mniejsza grubość (do limitu z norm); to założenie kosztowe, nie dobór wytrzymałości spoiny. Ściany podzielone, mocowania, śruby i połączenia niespawane wymagają wyłączenia lub korekty. Rowki I/V/X i przygotowanie stopy połączeń T/K są mierzone z przekrojów geometrii. Wynik nie obejmuje nadlewu i wymaga sprawdzenia zamiaru spawania.</p>
      {:else}<div class="padded"><p>Silnik analizuje rzeczywiste ściany B-Rep. Brak wyniku nie oznacza zerowej długości spoin.</p></div>{/if}
     </section>
    {/if}
    {#if automatic.error}<div class="banner danger">{automatic.error}</div>{/if}
    {#if active!=='material'}<section class="panel results-panel">
     <div class="panel-title"><div><h2>{active==='material'?'Koszt materiału':'Operacje — '+selected.title}</h2><p>Automat i wartość przyjęta są rozdzielone. Korekta pozostaje po zmianie stawek.</p></div><span class={'pill '+severity(selected.status)}>{statusName(selected.status)}</span></div>
     {#if selected.status==='error'}<div class="banner danger" role="alert">{selected.error}</div>{/if}
     <div class="table-scroll"><table><thead><tr><th>Operacja</th><th>Podstawa</th><th>Automat</th><th>Przyjęto</th><th>Koszt [zł]</th><th></th></tr></thead><tbody>
      {#each selected.rows as row (row.key)}<tr><td>{#if row.key.startsWith('custom-')}<input class="edit-label" aria-label="Nazwa operacji" value={row.name} onchange={e=>renameOperation(row.key,e.currentTarget.value)}/>{:else}<strong>{row.name}</strong>{/if}<small class="cell-note">{row.kind==='time'?'godziny [h]':'kwota [zł]'}</small>{#if row.manuallyEdited}<small class="cell-note accent">Korekta ręczna</small>{/if}</td><td class="basis">{row.detail}</td><td>{autoText(row)}</td><td><input class:overridden={row.manuallyEdited} class="number-input" type="number" min="0" step=".01" aria-label={'Przyjęto '+row.name} placeholder="—" value={row.value??''} disabled={selected.omitted} onchange={e=>editValue(active,row.key,e.currentTarget.value)}/></td><td class="cost">{row.costPln===null?'—':money(row.costPln)}</td><td>{#if row.manuallyEdited}<button class="icon-button" aria-label={'Przywróć automat '+row.name} title="Przywróć obliczenie automatyczne" onclick={()=>resetValue(active,row.key)}><RotateCcw size={14}/></button>{/if}</td></tr>{/each}
     </tbody></table></div>
     <div class="panel-actions"><button class="subtle" onclick={addOperation} disabled={selected.omitted}><Plus size={15}/>Dodaj operację</button><div class="checks"><label class="check"><input type="checkbox" checked={selected.omitted} onchange={e=>toggleExcluded(e.currentTarget.checked)}/>Nie dotyczy</label><label class="check"><input type="checkbox" checked={confirmed[active]===true} disabled={selected.missing>0||selected.omitted||selected.status==='error'} onchange={e=>toggleConfirmed(e.currentTarget.checked)}/>Potwierdź etap</label></div></div>
    </section>
    {/if}
    {#if active!=='material'&&selected.missing>0&&!selected.omitted}<div class="banner warning">Do uzupełnienia: {selected.missing} pozycji. Brak danych nie oznacza zerowego kosztu.</div>{/if}

   {:else if !files.length}
    <div class="intro-grid"><section class="panel"><Scale size={21}/><h2>Materiał i masa</h2><p>Puste pole gatunku, gęstość 7850 kg/m³. Zmieniaj materiał, gęstość i naddatki przy częściach.</p></section><section class="panel"><Settings2 size={21}/><h2>Etapy produkcji</h2><p>Cięcie, gięcie, montaż i spawanie w jednym interfejsie. W każdym etapie możesz poprawić czas.</p></section><section class="panel"><ClipboardList size={21}/><h2>Stan wyceny</h2><p>Widzisz policzone pozycje i brakujące dane. Zapiszesz zestawienie wszystkich modułów.</p></section></div>
   {/if}
   {#if notes.length}<details class="panel detail-panel"><summary>Uwagi do dokumentacji ({notes.length})</summary>{#each notes as n}<p>{n}</p>{/each}</details>{/if}
  </main>
  {#if inventory&&!busy}<footer><div><small>Koszt znanych pozycji</small><strong>{money(knownCost)} zł</strong></div><div><small>Czas przyjęty do wyceny</small><strong>{number(knownHours)} h</strong></div><span class:ok={report.complete} class="pill">{report.complete?'Etapy potwierdzone':'Wycena niekompletna'}</span><button class="subtle" onclick={()=>{showReport=true;showSettings=false;}}>Stan modułów <ChevronRight size={15}/></button></footer>{/if}
 </div>
</div>
