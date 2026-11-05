<script lang="ts">
 import {onMount} from 'svelte';
 import {call as invoke,native,pickInputs,watchDrops,saveReport} from './lib/desktop-api';
 import {Layers3,FolderOpen,FilePlus2,Plus,Upload,Scale,Settings2,Sun,Moon,Download,Check,ChevronRight,X,Files,RotateCcw,ClipboardList,Search} from 'lucide-svelte';
 import {mergeProjectFiles,preferredStep,moduleReport,csvCell} from './lib/project-files.mjs';
 import {MATERIALS,defaultMaterial,groupMaterial} from './lib/part-materials.mjs';
 import {calculateWeld} from './lib/welding.mjs';
 import {estimateBending,estimateCnc} from './lib/estimate.mjs';
 import {createCadSession} from './lib/cad-session.mjs';
 import {validateStepBom} from './lib/inventory-validate.mjs';
 import {evaluateModules} from './lib/modular-quote.mjs';
 import {MODULES,DEFAULT_RATES} from './lib/quote-modules/index.mjs';
 import {parseExplicitFilletNotes} from './lib/weld-document.mjs';
 import {kwantflowKnownCost} from './lib/modular-kwantflow.js';

 type StockHint={kind:string;confidence?:string;reason?:string;source?:string;limitations?:string;lengthMm?:number;widthMm?:number;heightMm?:number;diameterMm?:number;thicknessMm?:number;wallMm?:number;sectionAreaMm2?:number};
 type Inv={count:number;totalMassKg:number;solids:Array<{id:string;verifiedShapeKey:string;volumeMm3:number;massKg:number;bboxMm:number[];verificationMethod?:string;stockHint?:StockHint}>;groups:Array<{geometryId:string;quantity:number;massKg:number}>;limitations?:string[]};
 type Edit={value:number|null};
 type CustomRow={key:string;name:string;kind:'time'|'amount'};
 const money=(x:number)=>x.toLocaleString('pl-PL',{minimumFractionDigits:2,maximumFractionDigits:2});
 const number=(x:number)=>x.toLocaleString('pl-PL',{maximumFractionDigits:2});
 const stockLabels:Record<string,string>={
  'plate-candidate':'Blacha / płyta — kandydat',
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
  async(path:string)=>validateStepBom(JSON.parse(await invoke<string>('analyze_step',{path}))) as Inv,
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
 let showFiles=$state(true);
 let showReport=$state(false);
 let materialQuery=$state('');
 let notice=$state('');
 let showCalculator=$state(false);
 let weldLength=$state(0),weldA=$state(4),deposition=$state(2.5),arcPercent=$state(35),weldSetup=$state(20);
 let bendCount=$state(0),bendSeconds=$state(30),bendSetup=$state(20);
 let cncRemoved=$state(0),cncQ=$state(10),cncSetup=$state(20);
 let assemblyPerPart=$state(2.5),assemblyJoints=$state(0),assemblyPerJoint=$state(1.5),assemblySetup=$state(20);
 let weldResult=$derived.by(()=>{try{return calculateWeld({lengthM:weldLength,throatMm:weldA,depositionKgH:deposition,arcFactor:arcPercent/100,setupMin:weldSetup})}catch{return null}});
 let bendResult=$derived.by(()=>{try{return estimateBending({bends:bendCount,secondsPerBend:bendSeconds,setupMin:bendSetup,ratePerHour:rates.bending??0})}catch{return null}});
 let cncResult=$derived.by(()=>{try{return estimateCnc({removedCm3:cncRemoved,removalCm3Min:cncQ,setupMin:cncSetup,ratePerHour:rates.cnc??0})}catch{return null}});
 let materialApproved=$state(false);
 let selectedSolid=$state(0);
 let projectKey=$state('');
 let added=$state(0);
 let report=$derived(evaluateModules({inventory,pdfText,rates,edits,confirmed,excluded,custom,grade,materialApproved,partMaterials}));
 let selected=$derived(report.modules.find(m=>m.id===active)??report.modules[0]);
 let part=$derived(inventory?.solids[selectedSolid]??null);
 let weldNotes=$derived(pdfText?parseExplicitFilletNotes(pdfText):[]);
 let knownHours=$derived(report.modules.filter(m=>!m.omitted).flatMap(m=>m.rows||[])
  .reduce((sum,r)=>sum+(r.kind==='time'?(r.value??0):0),0));
 let knownCost=$derived(kwantflowKnownCost(report));

 const projectStorage=()=>projectKey?'ds-estimate-project-v1:'+projectKey:'';
 function saveSettings(){
  try{localStorage.setItem(storageSettings,JSON.stringify(rates));}catch{}
 }
 function saveProject(){
  if(!projectKey)return;
  try{localStorage.setItem(projectStorage(),JSON.stringify({edits,confirmed,excluded,custom,grade,materialApproved,partMaterials}));}catch{}
 }
 function restoreProject(){
  edits={};confirmed={};excluded={};custom={};grade='unknown';materialApproved=false;partMaterials={};
  try{
   const saved=JSON.parse(localStorage.getItem(projectStorage())||'null');
   if(saved && typeof saved==='object'){
    edits=saved.edits||{};confirmed=saved.confirmed||{};
    excluded=saved.excluded||{};custom=saved.custom||{};
    grade=saved.grade||'unknown';materialApproved=saved.materialApproved===true;partMaterials=saved.partMaterials||{};
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
   partMaterials=Object.fromEntries(data.groups.map(g=>[g.geometryId,{...defaultMaterial(),...(partMaterials[g.geometryId]||{})}]));
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
   active='material';
   status='Analiza geometrii zakończona · uzupełnij dane wyceny';
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
  try{theme=localStorage.getItem('ds-estimate-theme')==='light'?'light':'dark';}catch{}
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

 let materialRows=$derived.by(()=>!inventory?[]:inventory.groups.map(g=>{
  try{return {group:g,material:groupMaterial(inventory,g,partMaterials[g.geometryId],rates.materialPriceKg),error:''};}
  catch(e){return {group:g,material:null,error:String(e)};}
 }));
 let totalMass=$derived(materialRows.reduce((sum,r)=>sum+(r.material?.totalMassKg??0),0));
 let stockMass=$derived(materialRows.reduce((sum,r)=>sum+(r.material?.totalStockMassKg??0),0));
 let visibleMaterialRows=$derived(materialRows.filter(r=>r.group.geometryId.toLowerCase().includes(materialQuery.toLowerCase())));
 async function chooseInputs(folder=false){try{const paths=await pickInputs(folder);if(paths.length)await openInputs(paths);}catch(e){error=String(e);}}
 function changeMaterial(key:string,field:string,value:any){
  partMaterials={...partMaterials,[key]:{...defaultMaterial(),...partMaterials[key],[field]:value}};
  confirmed={...confirmed,material:false,cutting:false};materialApproved=false;saveProject();
 }
 function chooseGrade(key:string,value:string){const m=MATERIALS.find(x=>x.grade===value);if(!m)return;
  partMaterials={...partMaterials,[key]:{...defaultMaterial(),...partMaterials[key],grade:m.grade,density:m.density}};
  materialApproved=false;confirmed={...confirmed,material:false,cutting:false};saveProject();
 }
 function resetValue(moduleId:string,key:string){const own={...edits[moduleId]};delete own[key];
  edits={...edits,[moduleId]:own};confirmed={...confirmed,[moduleId]:false};saveProject();}
 function removeFile(path:string){if(busy)return;files=files.filter(f=>f!==path);candidateSteps=files.filter(isStep);
  if(path===selectedStep){selectedStep=preferredStep(files);inventory=null;projectKey='';restoreProject();if(selectedStep)void analyzeSelected();}}
 function newProject(){if(busy)return;files=[];candidateSteps=[];selectedStep='';inventory=null;projectKey='';pdfText='';notes=[];error='';notice='';restoreProject();status='Dodaj pliki projektu';showReport=false;showSettings=false;active='material';}
 function toggleTheme(){theme=theme==='dark'?'light':'dark';try{localStorage.setItem('ds-estimate-theme',theme);}catch{}}
 function autoText(row:any){const value=row.kind==='time'?row.autoHours:row.autoAmount;return typeof value==='number'?number(value):'—';}
 async function exportStatus(format:'json'|'csv'){
  try{const data=moduleReport(report,{step:selectedStep,files,solidCount:inventory?.count??0,totalMassKg:totalMass,stockMassKg:stockMass});
   const text=format==='json'?JSON.stringify(data,null,2):'\uFEFF'+[
    ['Moduł','Stan','Brakujące pozycje','Znany koszt PLN'],
    ...data.modules.map(m=>[m.name,statusName(m.status),m.missing,m.costPln]),[],
    ['Moduł','Operacja','Rodzaj','Automat','Przyjęto','Koszt PLN','Korekta'],
    ...data.modules.flatMap(m=>m.rows.map(r=>[m.name,r.name,r.kind,r.automatic,r.value,r.costPln,r.manuallyEdited?'tak':'nie']))
   ].map(row=>row.map(csvCell).join(';')).join('\r\n');
   if(await saveReport(text,format))notice='Zapisano zestawienie '+format.toUpperCase()+'.';
  }catch(e){error=String(e);}
 }
 function revealPart(key:string){
  selectedSolid=inventory?.solids.findIndex(s=>s.verifiedShapeKey===key)??0;
  const panel=document.getElementById('geometry-details') as HTMLDetailsElement|null;
  if(panel){panel.open=true;panel.scrollIntoView({block:'nearest',behavior:'smooth'});}
 }
 function applyCalculator(){
  if(active==='assembly'&&(!inventory||![assemblySetup,assemblyPerPart,assemblyJoints,assemblyPerJoint].every(v=>Number.isFinite(v)&&v>=0)||!Number.isInteger(assemblyJoints))){error='Podaj nieujemne normy i całkowitą liczbę połączeń.';return;}

  if(active==='welding'&&weldResult){editValue(active,'setup',String(weldSetup/60));editValue(active,'weld',String((weldResult.totalMinutes-weldSetup)/60));}
  if(active==='bending'&&bendResult){editValue(active,'setup',String(bendSetup/60));editValue(active,'bends',String((bendResult.totalMin-bendSetup)/60));}
  if(active==='cnc'&&cncResult){editValue(active,'program',String(cncSetup/60));editValue(active,'milling',String(cncResult.millingMin/60));}
  if(active==='assembly'&&inventory&&[assemblySetup,assemblyPerPart,assemblyJoints,assemblyPerJoint].every(v=>Number.isFinite(v)&&v>=0)){
   editValue(active,'fixtures',String(assemblySetup/60));editValue(active,'fitup',String(inventory.count*assemblyPerPart/60));editValue(active,'tacks',String(assemblyJoints*assemblyPerJoint/60));
  }
  notice='Przyjęto oszacowanie do tabeli operacji. Możesz je dalej korygować.';
 }
</script>
<div class="app" data-theme={theme}>
 <aside class="rail">
  <div class="brand"><span class="brand-mark"><Layers3 size={23}/></span><strong>DS Estimate</strong></div>
  <nav aria-label="Moduły wyceny">
   <button class:active={!showSettings&&!showReport&&active==='project'} onclick={()=>{active='project';showSettings=false;showReport=false;}}><Files size={18}/><span>Pliki projektu</span><small class="nav-count">{files.length}</small></button>
   <div class="rail-caption">ETAPY WYCENY</div>
   {#each report.modules as mod}
    <button class:active={!showSettings&&!showReport&&active===mod.id} title={mod.title+' — '+statusName(mod.status)} onclick={()=>{active=mod.id;showSettings=false;showReport=false;showCalculator=false;}}>
     <span class={'stage-dot '+severity(mod.status)}>{mod.status==='verified'?'✓':mod.status==='excluded'?'–':''}</span>
     <span>{mod.title}</span>
    </button>
   {/each}
  </nav>
  <div class="rail-bottom">
   <button class:active={showReport} onclick={()=>{showReport=true;showSettings=false;}}><ClipboardList size={18}/><span>Stan modułów</span></button>
   <button class:active={showSettings} onclick={()=>{showSettings=true;showReport=false;}}><Settings2 size={18}/><span>Stawki i ustawienia</span></button>
   <small>DS Estimate 0.3 · zapis lokalny</small>
  </div>
 </aside>
 <div class="workspace">
  <header>
   <div class="breadcrumb"><strong>{showSettings?'Stawki i ustawienia':showReport?'Stan modułów':active==='project'?'Pliki projektu':selected.title}</strong><ChevronRight size={14}/><span>{selectedStep?filename(selectedStep):'Nowy projekt'}</span></div>
   <div class="header-actions">
    <button class="subtle" disabled={busy} onclick={newProject}><Plus size={16}/>Nowy projekt</button>
    <button class="subtle" onclick={()=>exportStatus('csv')} disabled={!inventory}><Download size={16}/>Eksport CSV</button>
    <button class="icon-button" onclick={toggleTheme} aria-label="Zmień motyw">{#if theme==='dark'}<Sun size={18}/>{:else}<Moon size={18}/>{/if}</button>
   </div>
  </header>
  <main>
   {#if !native}<div class="banner info">Podgląd interfejsu. Dodawanie lokalnych plików i analiza CAD działają w programie Windows.</div>{/if}
   {#if error}<div class="banner danger" role="alert"><div><strong>Nie udało się ukończyć operacji</strong><p>{error}</p></div><button aria-label="Zamknij błąd" onclick={()=>error=''}><X size={16}/></button></div>{/if}
   {#if notice}<div class="banner info" role="status"><span>{notice}</span><button aria-label="Zamknij informację" onclick={()=>notice=''}><X size={16}/></button></div>{/if}
   <div class="page-heading">
    <div><h1>{showSettings?'Stawki i ustawienia':showReport?'Stan poszczególnych modułów':!inventory?'Wycena konstrukcji':active==='project'?'Pliki projektu':selected.title}</h1>
     <p>{showSettings?'Jedno miejsce dla cen materiału i stawek stanowisk.':showReport?'Sprawdź, co jest policzone, a co wymaga uzupełnienia.':!inventory?'Dodaj modele STEP i dokumentację. Przejdź przez kolejne etapy wyceny.':active==='project'?'Wybierz model główny. Pozostałe pliki pozostają dokumentacją projektu.':selected.detail}</p>
    </div>
    <div class="heading-actions"><button class="primary" disabled={busy} onclick={()=>chooseInputs()}><FilePlus2 size={17}/>Dodaj pliki</button><button disabled={busy} onclick={()=>chooseInputs(true)}><FolderOpen size={17}/>Dodaj folder</button></div>
   </div>

   {#if !showSettings}
    <div class:drop-active={dragActive} class:compact={inventory&&active!=='project'} class="upload-panel panel" aria-label="Obszar dodawania plików">
     <Upload size={inventory?22:32}/><div><strong>{dragActive?'Upuść pliki tutaj':busy?status:'Przeciągnij pliki lub folder do programu'}</strong><p>STEP / STP · PDF · DXF / DWG · obrazy · Excel</p></div>
     <button class="subtle" onclick={()=>showFiles=!showFiles} aria-expanded={showFiles}>{files.length} plików <ChevronRight size={15}/></button>
    </div>
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

   {#if showSettings}
    <div class="settings-grid">
     <section class="panel"><h2>Materiał i stanowiska</h2><p>Wartości startowe są przykładowe. Zmiany nie uruchamiają ponownie silnika CAD.</p><div class="form-grid">
      <label>Domyślna cena materiału [zł/kg]<input type="number" min="0" step=".01" value={rates.materialPriceKg??''} placeholder="Brak ceny" onchange={e=>changeRate('materialPriceKg',e.currentTarget.value)}/></label>
      {#each MODULES.filter(x=>x.rateKey) as m}<label>{m.title} [zł/h]<input type="number" min="0" value={rates[m.rateKey]??''} onchange={e=>changeRate(m.rateKey,e.currentTarget.value)}/></label>{/each}
     </div></section>
     <section class="panel"><h2>Geometria i zapis</h2><p>STEP jest odczytywany przez lokalny silnik OCCT. Przeliczenie kosztów korzysta z zapisanego wyniku analizy.</p><dl><dt>Gęstość domyślna</dt><dd>7850 kg/m³</dd><dt>Gatunek bez danych</dt><dd>Puste pole</dd><dt>Ustawienia części i korekty</dt><dd>Zapis lokalny dla wybranego modelu i jego wersji</dd><dt>Dokumentacja</dt><dd>PDF: warstwa tekstowa; DXF, DWG, obrazy i Excel: lista załączników</dd></dl><button onclick={toggleTheme}>{theme==='dark'?'Włącz jasny motyw':'Włącz ciemny motyw'}</button><p class="hint">Zmiana pliku STEP unieważnia jego poprzedni przedmiar. Żaden moduł nie traktuje brakujących czasów jak potwierdzonych zer.</p></section>
    </div>
   {:else if showReport}
    <section class="panel results-panel"><div class="panel-title"><h2>Gotowość wyceny</h2><span class="pill">{report.completedModules} / {report.totalModules} etapów</span></div>
     <div class="table-scroll"><table><thead><tr><th>Moduł</th><th>Stan</th><th>Brakujące pozycje</th><th>Znany koszt</th><th></th></tr></thead><tbody>{#each report.modules as mod}<tr><td><strong>{mod.title}</strong></td><td><span class={'pill '+severity(mod.status)}>{statusName(mod.status)}</span></td><td>{mod.missing}</td><td>{money(mod.knownCostPln)} zł</td><td><button class="tiny" onclick={()=>{showReport=false;active=mod.id;}}>Otwórz</button></td></tr>{/each}</tbody></table></div>
     <div class="panel-actions"><button disabled={!inventory} onclick={()=>exportStatus('json')}><Download size={15}/>Zapisz raport JSON</button><button disabled={!inventory} onclick={()=>exportStatus('csv')}><Download size={15}/>Zapisz raport CSV</button></div>
    </section><div class="banner info">Potwierdzenie etapu oznacza sprawdzenie danych przez operatora. Nie jest potwierdzeniem pełnej automatyzacji rozpoznawania technologii.</div>
   {:else if inventory&&active!=='project'}
    <div class="metrics"><article><Scale size={17}/><div><small>Masa konstrukcji</small><strong>{number(totalMass)} <em>kg</em></strong></div></article><article><Layers3 size={17}/><div><small>Półfabrykaty z naddatkami</small><strong>{number(stockMass)} <em>kg</em></strong></div></article><article><Files size={17}/><div><small>Bryły / grupy geometrii</small><strong>{inventory.count} <em>/ {inventory.groups.length}</em></strong></div></article><article><Check size={17}/><div><small>Potwierdzone etapy</small><strong>{report.completedModules} <em>/ {report.totalModules}</em></strong></div></article></div>

    {#if active==='material'}
     <section class="panel results-panel"><div class="panel-title"><div><h2>Części i materiały</h2><p>Wiersz obejmuje wszystkie wystąpienia identycznej geometrii.</p></div><label class="search"><Search size={15}/><input aria-label="Szukaj grupy części" bind:value={materialQuery} placeholder="Szukaj części…"/></label></div>
      <div class="table-scroll"><table><thead><tr><th>Grupa części / wyrób</th><th>Szt.</th><th>Gatunek</th><th>Gęstość kg/m³</th><th>Masa / szt.</th><th>Cena zł/kg</th><th>Naddatek pocz. / kon. mm</th><th>Półfabrykat kg/szt.</th></tr></thead><tbody>
       {#each visibleMaterialRows as item (item.group.geometryId)}
        {@const g=item.group}{@const m=item.material}{@const solid=inventory.solids.find(s=>s.verifiedShapeKey===g.geometryId)}
        <tr><td><strong>{g.geometryId}</strong><small class="cell-note">{stockLabels[solid?.stockHint?.kind||'unknown']||'Nierozpoznany'}{solid?.stockHint?.confidence?' · '+solid.stockHint.confidence:''}</small><button class="tiny text" onclick={()=>revealPart(g.geometryId)}>Szczegóły</button></td><td>{g.quantity}</td>
         <td><select aria-label={'Gatunek '+g.geometryId} value={m?.grade??''} onchange={e=>chooseGrade(g.geometryId,e.currentTarget.value)}>{#each MATERIALS as mat}<option value={mat.grade}>{mat.label}</option>{/each}</select></td>
         <td><input class="number-input" aria-label={'Gęstość '+g.geometryId} type="number" min="1" value={m?.density??7850} onchange={e=>{if(e.currentTarget.reportValidity())changeMaterial(g.geometryId,'density',Number(e.currentTarget.value));}}/></td>
         <td>{m?number(m.massKg):'—'}<small class="cell-note">kg</small></td>
         <td><input class="number-input" aria-label={'Cena '+g.geometryId} type="number" min="0" step=".01" placeholder={rates.materialPriceKg===null?'—':String(rates.materialPriceKg)} value={partMaterials[g.geometryId]?.price??''} onchange={e=>{if(e.currentTarget.reportValidity())changeMaterial(g.geometryId,'price',e.currentTarget.value===''?null:Number(e.currentTarget.value));}}/></td>
         <td><div class="paired"><input aria-label={'Naddatek początek '+g.geometryId} type="number" min="0" step=".1" value={m?.allowStart??0} onchange={e=>{if(e.currentTarget.reportValidity())changeMaterial(g.geometryId,'allowStart',Number(e.currentTarget.value));}}/><span>/</span><input aria-label={'Naddatek koniec '+g.geometryId} type="number" min="0" step=".1" value={m?.allowEnd??0} onchange={e=>{if(e.currentTarget.reportValidity())changeMaterial(g.geometryId,'allowEnd',Number(e.currentTarget.value));}}/></div></td>
         <td><input class="number-input" aria-label={'Znana masa półfabrykatu '+g.geometryId} title="Puste = szacunek z naddatków. Wpisz znaną masę, aby ją przyjąć." type="number" min="0" step=".001" placeholder={m?number(m.stockMassKg):'—'} value={partMaterials[g.geometryId]?.stockMassKg??''} onchange={e=>{if(e.currentTarget.reportValidity())changeMaterial(g.geometryId,'stockMassKg',e.currentTarget.value===''?null:Number(e.currentTarget.value));}}/>{#if item.error}<small class="cell-note bad">{item.error}</small>{/if}</td>
        </tr>
       {/each}
      </tbody></table></div>
      <div class="panel-actions"><label class="check"><input type="checkbox" bind:checked={materialApproved} onchange={()=>{confirmed={...confirmed,material:false};saveProject();}}/>Potwierdzam gęstości, ceny i zakres materiału</label><span class="muted">Gatunek może pozostać pusty.</span></div>
     </section>
     <p class="hint">Naddatki są liczone na długości półfabrykatu według wymiaru rozpoznanego przekroju lub najdłuższego boku bbox. To szacunek; dla nietypowej części wpisz znaną masę półfabrykatu. Naddatek nie zmienia masy gotowej konstrukcji.</p>
    {/if}

    <section class="panel results-panel">
     <div class="panel-title"><div><h2>{active==='material'?'Koszt materiału':'Operacje — '+selected.title}</h2><p>Automat i wartość przyjęta są rozdzielone. Korekta pozostaje po zmianie stawek.</p></div><span class={'pill '+severity(selected.status)}>{statusName(selected.status)}</span></div>
     {#if selected.status==='error'}<div class="banner danger" role="alert">{selected.error}</div>{/if}
     <div class="table-scroll"><table><thead><tr><th>Operacja</th><th>Podstawa</th><th>Automat {active==='material'||active==='purchased'?'[zł]':'[h]'}</th><th>Przyjęto {active==='material'||active==='purchased'?'[zł]':'[h]'}</th><th>Koszt [zł]</th><th></th></tr></thead><tbody>
      {#each selected.rows as row (row.key)}<tr><td>{#if row.key.startsWith('custom-')}<input class="edit-label" aria-label="Nazwa operacji" value={row.name} onchange={e=>renameOperation(row.key,e.currentTarget.value)}/>{:else}<strong>{row.name}</strong>{/if}{#if row.manuallyEdited}<small class="cell-note accent">Korekta ręczna</small>{/if}</td><td class="basis">{row.detail}</td><td>{autoText(row)}</td><td><input class:overridden={row.manuallyEdited} class="number-input" type="number" min="0" step=".01" aria-label={'Przyjęto '+row.name} placeholder="—" value={row.value??''} disabled={selected.omitted} onchange={e=>editValue(active,row.key,e.currentTarget.value)}/></td><td class="cost">{row.costPln===null?'—':money(row.costPln)}</td><td>{#if row.manuallyEdited}<button class="icon-button" aria-label={'Przywróć automat '+row.name} title="Przywróć obliczenie automatyczne" onclick={()=>resetValue(active,row.key)}><RotateCcw size={14}/></button>{/if}</td></tr>{/each}
     </tbody></table></div>
     <div class="panel-actions"><button class="subtle" onclick={addOperation} disabled={selected.omitted}><Plus size={15}/>Dodaj operację</button><div class="checks"><label class="check"><input type="checkbox" checked={selected.omitted} onchange={e=>toggleExcluded(e.currentTarget.checked)}/>Nie dotyczy</label><label class="check"><input type="checkbox" checked={confirmed[active]===true} disabled={selected.missing>0||selected.omitted||selected.status==='error'} onchange={e=>toggleConfirmed(e.currentTarget.checked)}/>Potwierdź etap</label></div></div>
    </section>
    {#if selected.missing>0&&!selected.omitted}<div class="banner warning">Do uzupełnienia: {selected.missing} pozycji. Brak danych nie oznacza zerowego kosztu.</div>{/if}

    {#if ['welding','bending','cnc','assembly'].includes(active)}
     <section class="panel calculator"><button class="subtle" aria-expanded={showCalculator} onclick={()=>showCalculator=!showCalculator}><Settings2 size={16}/>Kalkulator czasu — {selected.title}<ChevronRight size={15}/></button>
      {#if showCalculator}<p>Podaj parametry całej wycenianej partii. Wynik zostanie wpisany do odpowiednich operacji.</p><div class="form-grid">
       {#if active==='welding'}<label>Długość spoin [m]<input type="number" min="0" bind:value={weldLength}/></label><label>Gardziel a [mm]<input type="number" min="0" bind:value={weldA}/></label><label>Wydajność stapiania [kg/h]<input type="number" min=".01" bind:value={deposition}/></label><label>Wykorzystanie łuku [%]<input type="number" min="1" max="100" bind:value={arcPercent}/></label><label>Przygotowanie [min]<input type="number" min="0" bind:value={weldSetup}/></label>
       {:else if active==='bending'}<label>Liczba gięć całej partii<input type="number" min="0" step="1" bind:value={bendCount}/></label><label>Czas gięcia [s]<input type="number" min="0" bind:value={bendSeconds}/></label><label>Przezbrojenie [min]<input type="number" min="0" bind:value={bendSetup}/></label>
       {:else if active==='cnc'}<label>Objętość do usunięcia [cm³]<input type="number" min="0" bind:value={cncRemoved}/></label><label>Wydajność usuwania [cm³/min]<input type="number" min=".01" bind:value={cncQ}/></label><label>Program i przezbrojenie [min]<input type="number" min="0" bind:value={cncSetup}/></label>
       {:else}<label>Przygotowanie stanowiska [min]<input type="number" min="0" bind:value={assemblySetup}/></label><label>Ustawienie jednej bryły [min]<input type="number" min="0" bind:value={assemblyPerPart}/></label><label>Liczba sczepianych połączeń<input type="number" min="0" step="1" bind:value={assemblyJoints}/></label><label>Sczepianie połączenia [min]<input type="number" min="0" bind:value={assemblyPerJoint}/></label>{/if}
      </div><div class="panel-actions"><span class="muted">{active==='welding'?(weldResult?number(weldResult.totalMinutes)+' min':'Nieprawidłowe parametry'):active==='bending'?(bendResult?number(bendResult.totalMin)+' min':'Nieprawidłowe parametry'):active==='cnc'?(cncResult?number(cncResult.totalMin)+' min':'Nieprawidłowe parametry'):number(assemblySetup+inventory.count*assemblyPerPart+assemblyJoints*assemblyPerJoint)+' min'}</span><button class="primary" disabled={selected.omitted||(active==='welding'&&!weldResult)||(active==='bending'&&!bendResult)||(active==='cnc'&&!cncResult)} onclick={applyCalculator}>Przyjmij czas do wyceny</button></div>
      {#if active==='welding'}<p class="hint">Spoiny pachwinowe stalowe (7850 kg/m³) o równych ramionach. Czas z masy stopiwa, wydajności i wykorzystania łuku. Nie wykrywamy automatycznie spoin ani faz.</p>{/if}{/if}
     </section>
    {/if}
    {#if active==='welding'}<p class="hint">PDF: {weldNotes.length} możliwych oznaczeń spoin. Długości i przypisanie do połączeń wymagają potwierdzenia.</p>{/if}

    <details id="geometry-details" class="panel detail-panel"><summary>Dane geometrii i rozpoznanie wyrobu</summary><div class="detail-layout"><label>Wystąpienie STEP<select value={selectedSolid} onchange={e=>selectedSolid=Number(e.currentTarget.value)}>{#each inventory.solids as s,i}<option value={i}>{s.id} · {s.verifiedShapeKey}</option>{/each}</select></label>{#if part}<dl><dt>Objętość B-Rep</dt><dd>{number(part.volumeMm3)} mm³</dd><dt>Gabaryty</dt><dd>{part.bboxMm.map(number).join(' × ')} mm</dd><dt>Półfabrykat</dt><dd>{stockLabels[part.stockHint?.kind||'unknown']||'Nierozpoznany'}</dd><dt>Wymiary przekroju</dt><dd>{stockText(part.stockHint)}</dd><dt>Dowód grupowania</dt><dd>{part.verificationMethod||'Brak danych'}</dd></dl>{/if}</div></details>
   {:else if !files.length}
    <div class="intro-grid"><section class="panel"><Scale size={21}/><h2>Materiał i masa</h2><p>Puste pole gatunku, gęstość 7850 kg/m³. Zmieniaj materiał, gęstość i naddatki przy częściach.</p></section><section class="panel"><Settings2 size={21}/><h2>Etapy produkcji</h2><p>Cięcie, gięcie, montaż i spawanie w jednym interfejsie. W każdym etapie możesz poprawić czas.</p></section><section class="panel"><ClipboardList size={21}/><h2>Stan wyceny</h2><p>Widzisz policzone pozycje i brakujące dane. Zapiszesz zestawienie wszystkich modułów.</p></section></div>
   {/if}
   {#if notes.length}<details class="panel detail-panel"><summary>Uwagi do dokumentacji ({notes.length})</summary>{#each notes as n}<p>{n}</p>{/each}</details>{/if}
  </main>
  <footer><div><small>Koszt znanych pozycji</small><strong>{money(knownCost)} zł</strong></div><div><small>Czas przyjęty do wyceny</small><strong>{number(knownHours)} h</strong></div><span class:ok={report.complete} class="pill">{report.complete?'Etapy potwierdzone':'Wycena niekompletna'}</span><button class="subtle" onclick={()=>{showReport=true;showSettings=false;}}>Stan modułów <ChevronRight size={15}/></button></footer>
 </div>
</div>
