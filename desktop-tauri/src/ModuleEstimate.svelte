<script lang="ts">
 import {onMount} from 'svelte';
 import {invoke} from '@tauri-apps/api/core';
 import {getCurrentWebview} from '@tauri-apps/api/webview';
 import {createCadSession} from './lib/cad-session.mjs';
 import {validateStepBom} from './lib/inventory-validate.mjs';
 import {evaluateModules} from './lib/modular-quote.mjs';
 import {MODULES,DEFAULT_RATES} from './lib/quote-modules/index.mjs';
 import {parseExplicitFilletNotes} from './lib/weld-document.mjs';

 let {onTools=()=>{}}:{onTools?:()=>void}=$props();
 type Inv={count:number;totalMassKg:number;solids:Array<{id:string;verifiedShapeKey:string;volumeMm3:number;massKg:number;bboxMm:number[];verificationMethod?:string}>;groups:Array<{geometryId:string;quantity:number;massKg:number}>;limitations?:string[]};
 type Edit={value:number|null};
 type CustomRow={key:string;name:string;kind:'time'|'amount'};
 const money=(x:number)=>x.toLocaleString('pl-PL',{minimumFractionDigits:2,maximumFractionDigits:2});
 const number=(x:number)=>x.toLocaleString('pl-PL',{maximumFractionDigits:2});
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
 let materialApproved=$state(false);
 let selectedSolid=$state(0);
 let projectKey=$state('');
 let added=$state(0);
 let report=$derived(evaluateModules({inventory,pdfText,rates,edits,confirmed,excluded,custom,grade,materialApproved}));
 let selected=$derived(report.modules.find(m=>m.id===active)??report.modules[0]);
 let part=$derived(inventory?.solids[selectedSolid]??null);
 let weldNotes=$derived(pdfText?parseExplicitFilletNotes(pdfText):[]);
 let knownHours=$derived(report.modules.flatMap(m=>m.rows||[]).reduce((sum,r)=>sum+(r.kind==='time'?(r.value??0):0),0));

 const projectStorage=()=>projectKey?'ds-estimate-project-v1:'+projectKey:'';
 function saveSettings(){
  try{localStorage.setItem(storageSettings,JSON.stringify(rates));}catch{}
 }
 function saveProject(){
  if(!projectKey)return;
  try{localStorage.setItem(projectStorage(),JSON.stringify({edits,confirmed,excluded,custom,grade,materialApproved}));}catch{}
 }
 function restoreProject(){
  edits={};confirmed={};excluded={};custom={};grade='unknown';materialApproved=false;
  try{
   const saved=JSON.parse(localStorage.getItem(projectStorage())||'null');
   if(saved && typeof saved==='object'){
    edits=saved.edits||{};confirmed=saved.confirmed||{};
    excluded=saved.excluded||{};custom=saved.custom||{};
    grade=saved.grade||'unknown';materialApproved=saved.materialApproved===true;
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
  custom={...custom,[active]:[...list,{key:'custom-'+Date.now()+'-'+added,name:'Nowa operacja',kind:'time'}]};
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
   const lists=await Promise.all(paths.map(path=>invoke<string[]>('scan_project',{path})));
   files=[...new Set(lists.flat())];
   candidateSteps=files.filter(isStep).sort((a,b)=>modelScore(a)-modelScore(b)||a.localeCompare(b));
   if(!candidateSteps.length)throw new Error('Brak pliku STEP. Dokumentacja bez modelu wymaga ręcznego przedmiaru.');
   selectedStep=candidateSteps[0];
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
  let unlisten:(()=>void)|null=null;
  getCurrentWebview().onDragDropEvent(e=>{
   if(e.payload.type==='drop')void openInputs(e.payload.paths);
  }).then(cb=>unlisten=cb).catch(()=>{});
  return ()=>{unlisten?.();};
 });
 const severity=(s:string)=>s==='verified'?'ok':s==='excluded'?'idle':
  s==='review'||s==='partial'?'warn':s==='idle'?'idle':'bad';
 const statusName=(s:string)=>({
  verified:'OK',excluded:'Nie dotyczy',review:'Do potwierdzenia',
  partial:'Niepełne',missing:'Brak danych',idle:'Nieanalizowane',error:'Błąd modułu'
 } as Record<string,string>)[s]||'Weryfikacja';
</script>

<div class="module-app">
 <div class="top">
  <div class="brand"><span class="logo">DS</span><strong>DS Estimate</strong><span class="small">moduły wyceny</span></div>
  <div class="project-name">{selectedStep?filename(selectedStep):'Nowy projekt'}</div>
  <div class="top-actions">
   <button class:chosen={showSettings} onclick={()=>showSettings=!showSettings} title="Stawki godzinowe i cena materiału">⚙ Ustawienia</button>
   <button onclick={onTools} title="Poprzednie narzędzia">Narzędzia</button>
  </div>
 </div>
 <div class="project-bar">
  <input aria-label="Folder lub plik projektu" placeholder="Ścieżka folderu lub STEP…" bind:value={inputPath}
   onkeydown={e=>{if(e.key==='Enter'&&inputPath.trim())void openInputs([inputPath.trim()]);}}/>
  <button class="primary" disabled={busy||!inputPath.trim()} onclick={()=>void openInputs([inputPath.trim()])}>
   {busy?'Analizuję…':'Analizuj'}
  </button>
  {#if candidateSteps.length>1}
   <select aria-label="Wybierz model główny" value={selectedStep} disabled={busy}
    onchange={e=>{selectedStep=e.currentTarget.value;void analyzeSelected();}}>
    {#each candidateSteps as step}<option value={step}>{filename(step)}</option>{/each}
   </select>
  {/if}
  <span class="muted">{status}</span>
 </div>
 {#if error}<p class="error" role="alert">{error}</p>{/if}

 {#if showSettings}
  <section class="rate-panel">
   <div><h2>Stawki i ustawienia</h2><p>Wspólne dla projektu. Zmiana stawki przelicza zł bez ponownego uruchomienia CAD. Wartości początkowe są przykładowe.</p></div>
   <div class="rate-grid">
    <label>Cena materiału [zł/kg]
     <input type="number" min="0" step=".1" value={rates.materialPriceKg??''}
      oninput={e=>changeRate('materialPriceKg',e.currentTarget.value)}/>
    </label>
    {#each MODULES.filter(x=>x.rateKey) as m}
     <label>{m.title} [zł/h]
      <input type="number" min="0" step="1" value={rates[m.rateKey]??''}
       oninput={e=>changeRate(m.rateKey,e.currentTarget.value)}/>
     </label>
    {/each}
   </div>
  </section>
 {:else}
  <div class="layout">
   <aside class="modules">
    <div class="side-head"><strong>Etapy wyceny</strong><span>{report.completedModules}/{report.totalModules}</span></div>
    <div class="progress"><div style:width={(report.completedModules/report.totalModules*100)+'%'}></div></div>
    {#each report.modules as mod}
     <button class:active={mod.id===active} class="module-entry" onclick={()=>active=mod.id}>
      <span class:ok={severity(mod.status)==='ok'} class:warn={severity(mod.status)==='warn'}
       class:bad={severity(mod.status)==='bad'} class:idle={severity(mod.status)==='idle'}
       class="indicator">{severity(mod.status)==='ok'?'✓':severity(mod.status)==='bad'?'!':
        severity(mod.status)==='warn'?'•':'–'}</span>
      <span class="mod-text"><strong>{mod.title}</strong><small>{statusName(mod.status)}</small></span>
      <span class="chevron">›</span>
     </button>
    {/each}
    <div class="side-foot"><span>Import STEP</span><strong>{inventory?inventory.count+' brył · '+inventory.groups.length+' grup':'brak danych'}</strong></div>
   </aside>

   <main class="content">
    <div class="section-title">
     <div><small>MODUŁ WYCENY</small><h1>{selected.title}</h1>
      <p>{selected.detail}</p>
     </div>
     <span class:ok={severity(selected.status)==='ok'} class:warn={severity(selected.status)==='warn'}
      class:bad={severity(selected.status)==='bad'} class:idle={severity(selected.status)==='idle'}
      class="pill">{statusName(selected.status)}</span>
    </div>

    {#if inventory}
     <div class="section-metrics">
      <div><small>Koszt policzonych pozycji</small><strong>{money(selected.knownCostPln)} zł</strong></div>
      <div><small>Do uzupełnienia</small><strong>{selected.missing} pozycji</strong></div>
     </div>
     {#if active==='material'}
      <div class="material-options">
       <label>Gatunek materiału
        <select bind:value={grade} onchange={()=>{confirmed={...confirmed,material:false};saveProject();}}>
         <option value="unknown">Nieustalony</option><option value="S235">S235</option>
         <option value="S355">S355</option><option value="S690QL">S690QL</option>
         <option value="S960QL">S960QL</option><option value="stainless">Nierdzewna</option>
         <option value="aluminium">Aluminium</option>
        </select>
       </label>
       <label class="inline"><input type="checkbox" bind:checked={materialApproved}
        onchange={()=>{confirmed={...confirmed,material:false};saveProject();}}/>
        Potwierdzam gatunek, zakres i masę do wyceny</label>
      </div>
     {/if}
     <div class="table-box">
      <table><thead><tr><th>Operacja</th><th>Podstawa</th><th>{active==='material'||active==='purchased'?'Kwota [zł]':'Czas [h]'}</th><th>Koszt [zł]</th></tr></thead>
      <tbody>
       {#each selected.rows as row (row.key)}
        <tr>
         <td>
          {#if row.key.startsWith('custom-')}
           <input class="edit-label" aria-label="Nazwa operacji" value={row.name}
            oninput={e=>renameOperation(row.key,e.currentTarget.value)}/>
          {:else}<strong>{row.name}</strong>{/if}
          {#if active==='cutting'}<button class="tiny" title="Pokaż detale B-Rep" onclick={()=>{
           const idx=inventory?.solids.findIndex(x=>x.verifiedShapeKey===row.key)??-1;
           if(idx>=0)selectedSolid=idx;
          }}>Detal</button>{/if}
         </td>
         <td class="basis">{row.detail}</td>
         <td><input type="number" min="0" step=".01" aria-label={'Wartość '+row.name}
          placeholder="—" value={row.value??''} disabled={selected.omitted}
          oninput={e=>editValue(active,row.key,e.currentTarget.value)}/></td>
         <td class="cost">{row.costPln===null?'—':money(row.costPln)}</td>
        </tr>
       {/each}
      </tbody></table>
     </div>
     <div class="control-row">
      <button class="quiet" onclick={addOperation} disabled={selected.omitted}>+ Operacja</button>
      <div class="checks">
       <label><input type="checkbox" checked={selected.omitted}
        onchange={e=>toggleExcluded(e.currentTarget.checked)}/> Nie dotyczy</label>
       <label><input type="checkbox" checked={confirmed[active]===true}
        disabled={selected.missing>0||selected.omitted||selected.status==='error'}
        onchange={e=>toggleConfirmed(e.currentTarget.checked)}/> Potwierdź etap</label>
      </div>
     </div>
     {#if selected.missing>0&&!selected.omitted}
      <div class="notice">Brak danych dla {selected.missing} pozycji. Nie są naliczane jako 0 zł.</div>
     {/if}
     {#if active==='welding'}
      <div class="notice">Odczyt tekstu PDF: {weldNotes.length} możliwych oznaczeń spoin.
       Nie są automatycznie mapowane do połączeń 3D. Potwierdź długości, metodę i czas ręcznie.</div>
     {/if}
     {#if active==='cutting'}
      <p class="hint">Czasy automatyczne pochodzą z konturów OCCT i przykładowych parametrów maszyn; ustawienia stawek są centralne. Brak konturu oznacza brak czasu.</p>
     {/if}
    {:else}
     <div class="empty">Dodaj folder z dokumentacją lub plik STEP, aby rozpocząć. Analizę B-Rep wykonujemy tylko raz na niezmieniony plik.</div>
    {/if}
   </main>

   <aside class="details">
    <h2>Dane modelu</h2>
    {#if inventory}
     <div class="mini-stats"><span>Bryły <strong>{inventory.count}</strong></span><span>Grupy <strong>{inventory.groups.length}</strong></span></div>
     <label class="part-select">Wystąpienie STEP
      <select value={selectedSolid} onchange={e=>selectedSolid=Number(e.currentTarget.value)}>
       {#each inventory.solids as s,i}<option value={i}>{s.id} · {s.verifiedShapeKey}</option>{/each}
      </select>
     </label>
     {#if part}
      <div class="bbox">
       <svg viewBox="0 0 220 140" role="img" aria-label="Schemat gabarytów wybranej bryły, nie geometria B-Rep">
        <path d="M35 53 L128 23 L191 55 L99 87 Z M35 53 L35 105 L99 137 L99 87 M99 137 L191 107 L191 55 M35 105 L128 75 L191 107 M128 23 L128 75"
         fill="none" stroke="#73849a" stroke-width="2" stroke-linejoin="round"/>
       </svg>
       <small>Schemat bbox · nie podgląd powierzchni 3D</small>
      </div>
      <dl>
       <dt>Wymiary bbox</dt><dd>{part.bboxMm.map(number).join(' × ')} mm</dd>
       <dt>Objętość</dt><dd>{number(part.volumeMm3)} mm³</dd>
       <dt>Masa przy 7850 kg/m³</dt><dd>{number(part.massKg)} kg</dd>
       <dt>Metoda grupowania</dt><dd>{part.verificationMethod||'brak danych'}</dd>
      </dl>
     {/if}
     <p class="hint">Pełny model 3D B-Rep wymaga osobnej wizualizacji; ten panel wykorzystuje jedynie istniejące wyniki analizy.</p>
    {:else}
     <p class="hint">Wyniki analizy pojawią się po imporcie.</p>
    {/if}
    {#if notes.length}
     <h3>Dokumentacja</h3>
     {#each notes as n}<p class="hint">{n}</p>{/each}
    {/if}
   </aside>
  </div>
  <div class="bottom-bar">
   <div><small>Koszt znanych operacji · niepełna oferta</small>
    <strong>{money(report.knownCostPln)} zł</strong></div>
   <div><small>Ręcznie określony / oszacowany czas</small><strong>{number(knownHours)} h</strong></div>
   <div><small>Etapy wymagające sprawdzenia</small>
    <strong>{report.openModules}</strong></div>
   <span class="summary-tag">{report.complete?'Etapy potwierdzone ręcznie':'Wycena niekompletna'}</span>
  </div>
 {/if}
</div>
<style>
 .module-app{min-height:100vh;background:#0d1117;color:#e7edf5;font:13px system-ui,'Segoe UI',sans-serif;display:flex;flex-direction:column}
 .module-app *{box-sizing:border-box}
 .top{height:63px;border-bottom:1px solid #27303d;display:flex;align-items:center;gap:24px;padding:0 26px}
 .brand{display:flex;align-items:center;gap:10px;min-width:230px;font-size:17px}.brand .small{color:#8493a5;font-size:11px;font-weight:400}
 .logo{font-weight:900;font-size:15px;background:#785cc8;color:white;border-radius:7px;padding:7px}
 .project-name{flex:1;font-weight:600;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
 .top-actions{display:flex;gap:8px}
 button{font:inherit;cursor:pointer;border:1px solid #374357;background:#1b2431;color:#e7edf5;border-radius:8px;padding:10px 13px}
 button:hover{border-color:#6984a0}button:disabled{opacity:.45;cursor:default}
 .primary{background:#a58cfc;color:#130c24;border:0;font-weight:700}
 .project-bar{min-height:64px;display:flex;align-items:center;gap:10px;padding:11px 24px;border-bottom:1px solid #27303d;flex-wrap:wrap}
 input,select{background:#141c27;border:1px solid #354256;border-radius:7px;padding:9px;color:#e7edf5;font:inherit;min-width:0}
 .project-bar>input{width:min(410px,35vw)}.project-bar select{max-width:235px}.muted{color:#8f9eb1;font-size:12px}
 .error{color:#ffb4b6;padding:5px 26px}
 .layout{display:grid;grid-template-columns:248px minmax(460px,1fr) 260px;gap:16px;padding:18px;flex:1;min-height:0}
 .modules,.content,.details{background:#151d28;border:1px solid #293445;border-radius:12px}
 .modules{padding:12px;display:flex;flex-direction:column;min-height:560px}
 .side-head{display:flex;justify-content:space-between;padding:9px 8px 12px}.side-head span{color:#a0adbd}
 .progress{height:4px;border-radius:10px;background:#303e4d;margin:0 8px 12px;overflow:hidden}
 .progress>div{height:100%;background:#3eae72;transition:width .2s}
 .module-entry{border:0;background:transparent;display:flex;align-items:center;gap:9px;text-align:left;width:100%;padding:10px 9px;border-radius:7px;margin-bottom:2px}
 .module-entry.active{background:#31304b}.module-entry .mod-text{display:grid;gap:2px;flex:1}
 .mod-text strong{font-size:12px;font-weight:600}.mod-text small{font-size:10px;color:#97a5b5}.chevron{font-size:18px;color:#718396}
 .indicator{border-radius:50%;width:19px;height:19px;flex:none;display:grid;place-items:center;font-size:12px;font-weight:800}
 .indicator.ok{background:#174c36;color:#58d48d}.indicator.bad{background:#55262d;color:#ff8790}
 .indicator.warn{background:#51431e;color:#f6cd72}.indicator.idle{background:#293544;color:#8798ac}
 .side-foot{margin-top:auto;border-top:1px solid #293445;padding:15px 8px 5px;display:grid;gap:4px;color:#8293a6;font-size:11px}.side-foot strong{color:#dae2ed;font-size:12px}
 .content{padding:20px;min-width:0}.section-title{display:flex;align-items:flex-start;justify-content:space-between;gap:15px;margin-bottom:19px}
 .section-title small{color:#9d8be6;letter-spacing:1px;font-size:10px}.section-title h1{font-size:24px;margin:7px 0 5px}.section-title p{margin:0;color:#90a0b2;font-size:12px;line-height:1.5}
 .pill{font-size:11px;white-space:nowrap;border-radius:7px;padding:8px 9px}.pill.ok{background:#163d30;color:#67d99a}
 .pill.warn{background:#463c28;color:#e8c070}.pill.bad{background:#512b35;color:#ffa2a5}.pill.idle{background:#26303c;color:#96a5b5}
 .section-metrics{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:17px}
 .section-metrics>div{padding:17px;border:1px solid #2d3849;border-radius:9px;display:grid;gap:8px}
 .section-metrics small{color:#8b9aae}.section-metrics strong{font-size:20px}
 .table-box{overflow:auto;border:1px solid #303a49;border-radius:9px}table{width:100%;border-collapse:collapse;font-size:12px}
 th{text-align:left;background:#222b39;color:#aeb9c6;font-weight:500}td,th{padding:12px 10px;border-bottom:1px solid #2b3545}
 td strong{font-weight:550}.basis{color:#8799ac;font-size:11px;max-width:210px}.cost{font-variant-numeric:tabular-nums;font-weight:600}
 td input[type=number]{width:100px;text-align:right}td input.edit-label{width:160px}.tiny{margin-left:6px;padding:3px 6px;font-size:10px}
 .control-row{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:17px;flex-wrap:wrap}
 .checks{display:flex;gap:20px}.checks label,.inline{display:flex;align-items:center;gap:8px;font-size:12px;cursor:pointer}
 .checks input,.inline input{accent-color:#a58cfc}.quiet{background:transparent;border-style:dashed}
 .notice{border:1px solid #574b31;color:#dfc792;background:#30291b;border-radius:8px;padding:12px;margin-top:16px;font-size:12px}
 .hint{font-size:11px;color:#8e9db1;line-height:1.7}
 .material-options{display:flex;align-items:center;flex-wrap:wrap;gap:18px;margin-bottom:15px}
 .material-options label:not(.inline){display:grid;gap:6px;font-size:12px;color:#afbdcb}
 .empty{padding:90px 10px;text-align:center;color:#8696a7;line-height:1.7}
 .details{padding:17px;min-width:0}.details h2{font-size:15px;margin:0 0 15px}
 .mini-stats{display:flex;justify-content:space-between;gap:8px;color:#8c9cac;font-size:12px}
 .mini-stats strong{color:#d9e3ef}.part-select{display:grid;gap:7px;margin:17px 0;font-size:11px;color:#90a2b6}
 .part-select select{width:100%}.bbox{background:#101720;border:1px solid #2c3644;border-radius:9px;padding:10px;text-align:center}
 .bbox svg{width:100%;height:130px}.bbox small{color:#8a9aad;font-size:10px}
 dl{display:grid;grid-template-columns:1fr 1.1fr;gap:11px 7px;border-top:1px solid #293445;margin:16px 0;padding-top:15px;font-size:11px}
 dt{color:#8798ab}dd{margin:0;overflow-wrap:anywhere}
 .details h3{font-size:13px;margin-top:20px}
 .bottom-bar{margin:0 18px 16px;display:flex;align-items:center;gap:24px;padding:15px 20px;background:#192231;border:1px solid #303b4c;border-radius:11px;flex-wrap:wrap}
 .bottom-bar>div{display:grid;gap:4px;flex:1}.bottom-bar small{color:#8d9caf;font-size:11px}
 .bottom-bar strong{font-size:20px}.summary-tag{color:#e6c282;font-size:12px;margin-left:auto}
 .rate-panel{margin:18px 24px;padding:22px;border:1px solid #293445;border-radius:12px;background:#151d28}
 .rate-panel h2{margin:0 0 8px}.rate-panel p{color:#90a0b2;margin-bottom:20px}
 .rate-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(195px,1fr));gap:16px}
 .rate-grid label{display:grid;gap:7px;color:#a8b8c8;font-size:12px}
 @media(max-width:1250px){.layout{grid-template-columns:215px minmax(410px,1fr)}.details{grid-column:2}}
 @media(max-width:750px){.layout{display:block;padding:10px}.modules{min-height:0;margin-bottom:12px}.content{padding:13px}.details{margin-top:12px}
  .module-entry{display:inline-flex;width:calc(50% - 6px)}.top{padding:0 12px;gap:12px}.brand .small{display:none}
  .project-bar>input{width:100%}.bottom-bar{margin:10px}.top-actions button{padding:7px}.section-metrics strong{font-size:16px}}
</style>
