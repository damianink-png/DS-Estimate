<script lang="ts">
 import { onMount } from 'svelte';
 import { getCurrentWebview } from '@tauri-apps/api/webview';
 import { invoke } from '@tauri-apps/api/core';
 import { partCuttingHint, CUTTING_METHODS, SAMPLE_MACHINE_SETTINGS } from './lib/cutting-plan.mjs';
 import { planCuttingBatches } from './lib/cutting-batch.mjs';
 import { extractManufacturingRequirements } from './lib/document-requirements.mjs';
 import { validateStepBom } from './lib/inventory-validate.mjs';

 type Inventory={source:string;count:number;totalMassKg:number;groups:Array<{geometryId:string;quantity:number;massKg:number}>;solids:Array<{id:string;verifiedShapeKey:string;volumeMm3:number;bboxMm:number[];cuttingHint?:unknown}>;limitations?:string[]};
 type Override={method?:string;minutes?:number|null};
 const fmt=(n:number)=>n.toLocaleString('pl-PL',{maximumFractionDigits:2,minimumFractionDigits:2});
 let inputPath=$state('');
 let files=$state<string[]>([]);
 let candidateSteps=$state<string[]>([]);
 let selectedStep=$state('');
 let inventory=$state<Inventory|null>(null);
 let projectText=$state('');
 let technicalNotes=$state<string[]>([]);
 let status=$state('Przeciągnij dokumentację lub wpisz ścieżkę.');
 let busy=$state(false);
 let error=$state('');
 let material=$state('S355');
 let materialEvidence=$state('Domyślne założenie — zweryfikuj z rysunkiem');
 let machines=$state<any>(Object.fromEntries(Object.entries(SAMPLE_MACHINE_SETTINGS).map(([k,v])=>[k,{...v}])));
 let overrides=$state<Record<string,Override>>({});
 let extraTimes=$state<Array<{key:string;label:string;hours:number|null;rate:number}>>([
  {key:'cnc',label:'Obróbka CNC',hours:null,rate:388},
  {key:'welding',label:'Spawanie',hours:null,rate:145},
  {key:'assembly',label:'Montaż / sczepianie',hours:null,rate:120},
  {key:'surface',label:'Obróbka powierzchni',hours:null,rate:150},
  {key:'quality',label:'Kontrola jakości',hours:null,rate:140}
 ]);

 const basename=(p:string)=>p.split(/[\\/]/).pop()||p;
 const ext=(p:string)=>basename(p).split('.').pop()?.toLowerCase()||'';
 const isStep=(p:string)=>['stp','step'].includes(ext(p));
 const isPdf=(p:string)=>ext(p)==='pdf';
 const modelScore=(p:string)=>/assembly|assembl|z[lł]o[żz]en|monta[żz]|komplet|main/i.test(basename(p))?0:1;

 async function importPaths(paths:string[]) {
  if(busy||!paths.length)return;
  busy=true;error='';inventory=null;projectText='';technicalNotes=[];overrides={};material='S355';materialEvidence='Domyślne założenie — zweryfikuj z rysunkiem';
  status='Wyszukiwanie dokumentacji…';
  try {
   const found:string[]=[];
   for(const path of paths)found.push(...await invoke<string[]>('scan_project',{path}));
   files=[...new Set(found)];
   candidateSteps=files.filter(isStep).sort((a,b)=>modelScore(a)-modelScore(b)||a.localeCompare(b));
   selectedStep=candidateSteps[0]||'';
   if(!selectedStep)throw new Error('Nie znaleziono złożenia STEP; wczytano tylko dokumentację. Dodaj plik STEP, aby wyznaczyć masy.');
   await analyzeSelected();
  }catch(e){error=String(e);status='Wymaga poprawy danych wejściowych';}
  finally{busy=false;}
 }
 async function analyzeSelected(){
  if(!selectedStep)return;
  status='Analizuję geometrię STEP i masy detali…';inventory=null;
  try{
   const data=validateStepBom(JSON.parse(await invoke<string>('analyze_step',{path:selectedStep}))) as Inventory;
   inventory=data;
   projectText='';
   const pdfs=files.filter(isPdf);
   const lines:string[]=[];
   for(const pdf of pdfs.slice(0,15)){
    try{const txt=await invoke<string>('extract_pdf_text',{path:pdf});if(txt.trim())lines.push(txt.slice(0,30000));}
    catch{technicalNotes=[...technicalNotes,'Nie udało się odczytać warstwy tekstowej: '+basename(pdf)];}
   }
   projectText=lines.join('\n');
   const found=projectText.match(/\b(?:S355(?:J2(?:\+N)?|J0|JR)?|S235(?:JR)?|S690QL|S960QL)\b/i);
   if(found){material=found[0].toUpperCase().startsWith('S355')?'S355':found[0].toUpperCase().startsWith('S235')?'S235':found[0].toUpperCase();materialEvidence='Odczytany z tekstu PDF (wymaga potwierdzenia)';}
   const unsupported=files.filter(x=>!isStep(x)&&!isPdf(x));
   if(unsupported.length)technicalNotes=[...technicalNotes,`${unsupported.length} plików DXF/DWG/JPG/PNG/Excel jest w zestawie, ale ich analiza geometrii/OCR nie jest jeszcze połączona z tym ekranem.`];
   if(pdfs.length>15)technicalNotes=[...technicalNotes,'Odczytano pierwszych 15 PDF; pozostałe wymagają oddzielnej analizy.'];
   if(candidateSteps.length>1)technicalNotes=[...technicalNotes,'Znaleziono kilka STEP: wybrano kandydat na złożenie główne. Wybór potwierdź, aby uniknąć podwójnego liczenia.'];
   status='Wynik wstępny — uzupełnij lub popraw nieustalone czasy.';
  }catch(e){error=String(e);status='Błąd analizy STEP';}
 }
 async function changeStep(path:string){
  selectedStep=path;
  busy=true;error='';technicalNotes=[];overrides={};
  try{await analyzeSelected();}finally{busy=false;}
 }
 onMount(()=>{
  let unlisten:(()=>void)|null=null;
  getCurrentWebview().onDragDropEvent((event)=>{
   if(event.payload.type==='drop')void importPaths(event.payload.paths);
  }).then(fn=>unlisten=fn).catch(e=>{technicalNotes=[...technicalNotes,'Przeciąganie systemowe niedostępne: '+String(e)]});
  return ()=>{unlisten?.()};
 });

 let requirements=$derived(extractManufacturingRequirements(projectText).requirements);
 let cuttingPlan=$derived.by(()=>{
  if(!inventory)return {rows:[],batchCount:0,knownTimeOccurrences:0,pendingOccurrences:0};
  const solids=new Map(inventory.solids.map(s=>[s.verifiedShapeKey,s]));
  const groups=inventory.groups.map(g=>{
   const solid=solids.get(g.geometryId)??null;
   const hint=partCuttingHint(solid);
   const label=hint.kind==='possible-plate'?'Blacha, t≈'+fmt(hint.thicknessMm)+' mm':
    hint.kind==='possible-profile'?'Profil / rura, L≈'+fmt(hint.lengthMm)+' mm':'Detal nieokreślony';
   return {key:g.geometryId,solid,label,quantity:g.quantity,massKg:g.massKg,
    totalMassKg:g.massKg*g.quantity,origin:solid?.id??g.geometryId};
  });
  return planCuttingBatches({groups,material,machines,overrides});
 });
 let rows=$derived(cuttingPlan.rows);
 let cutHours=$derived(rows.reduce((sum,r)=>sum+(r.cut.acceptedMin??0)/60,0));
 let cutCost=$derived(rows.reduce((sum,r)=>sum+(r.cut.costPln??0),0));
 let additionalHours=$derived(extraTimes.reduce((sum,r)=>sum+(r.hours??0),0));
 let additionalCost=$derived(extraTimes.reduce((sum,r)=>sum+(r.hours??0)*r.rate,0));
 let unresolved=$derived(rows.filter(r=>r.cut.acceptedMin==null).length+extraTimes.filter(r=>r.hours==null).length);
 const changedTime=(key:string,v:string)=>{
  const min=v.trim()===''?null:Number(v.replace(',','.'));
  if(min!==null&&(!Number.isFinite(min)||min<0))return;
  overrides={...overrides,[key]:{...(overrides[key]??{}),minutes:min}};
 };
 const changedMethod=(key:string,v:string)=>{
  overrides={...overrides,[key]:{...(overrides[key]??{}),method:v||undefined,minutes:null}};
 };
 const changedExtra=(key:string,prop:'hours'|'rate',v:string)=>{
  const value=v.trim()===''&&prop==='hours'?null:Number(v.replace(',','.'));
  if(value!==null&&(!Number.isFinite(value)||value<0))return;
  extraTimes=extraTimes.map(x=>x.key===key?{...x,[prop]:value}:x);
 };
</script>

<section class="quick">
 <div class="import">
  <div class="drop-title">Wycena projektu</div>
  <p class="muted">Wrzuć folder z dokumentacją lub pojedynczy STEP. Program policzy części, masy i zaproponuje technologie cięcia.</p>
  <div class="drop-area" role="region" aria-label="Upuść folder lub pliki">
   <div class="drop-symbol">⇩</div>
   <strong>Przeciągnij tutaj folder lub pliki</strong>
   <span>STEP · STP · PDF · DXF · DWG · JPG · PNG · Excel</span>
  </div>
  <div class="path-line">
   <input type="text" bind:value={inputPath} placeholder="Lub wklej pełną ścieżkę folderu / pliku" aria-label="Ścieżka projektu" onkeydown={e=>{if(e.key==='Enter'&&inputPath.trim())void importPaths([inputPath.trim()])}}/>
   <button disabled={busy||!inputPath.trim()} onclick={()=>void importPaths([inputPath.trim()])}>{busy?'Analizuję…':'Analizuj'}</button>
  </div>
  <p class="status" aria-live="polite">{status}</p>
  {#if error}<p class="problem" role="alert">{error}</p>{/if}
 </div>
 {#if inventory}
  <div class="topline">
   <div><h2>Wynik analizy</h2><p class="muted">{files.length} plików · {inventory.count} brył · {inventory.groups.length} grup detali</p></div>
  </div>
  {#if candidateSteps.length>1}
   <label class="field">Model STEP głównego złożenia
    <select value={selectedStep} disabled={busy} onchange={e=>void changeStep(e.currentTarget.value)}>
     {#each candidateSteps as step}<option value={step}>{basename(step)}</option>{/each}
    </select>
   </label>
  {/if}
  <div class="figures">
   <div><small>Łączna masa gotowa</small><strong>{fmt(inventory.totalMassKg)} kg</strong></div>
   <div><small>Czas przyjęty (niepełny)</small><strong>{fmt(cutHours+additionalHours)} h</strong></div>
   <div><small>Koszt z określonych czasów</small><strong>{fmt(cutCost+additionalCost)} zł</strong></div>
  </div>
  {#if unresolved>0}<p class="problem">To nie jest kompletna wycena: {unresolved} pozycji ma nieustalony czas. Nie zaliczono ich jako 0 h.</p>{:else}<p class="good">Wszystkie czasy wpisane. Zweryfikuj technologię i stawki przed ofertą.</p>{/if}

  <details class="panel">
   <summary>Założenia i dostępne metody cięcia</summary>
   <div class="settings">
    <label>Materiał (przyjęty do doboru)
     <select bind:value={material}>
      <option value="unknown">Nieznany</option><option value="S235">S235</option><option value="S355">S355</option>
      <option value="S690QL">S690QL</option><option value="S960QL">S960QL</option>
      <option value="stainless">Nierdzewna</option><option value="aluminium">Aluminium</option>
     </select>
    </label>
    <p class="muted">{materialEvidence}. Parametry prędkości i stawki są przykładowe — dopasuj do swoich maszyn.</p>
    {#each Object.entries(CUTTING_METHODS) as [id,name]}
     <div class="machine">
      <label><input type="checkbox" checked={machines[id].enabled} onchange={e=>machines[id].enabled=e.currentTarget.checked}/> {name}</label>
      <label>Stawka zł/h <input type="number" min="0.01" value={machines[id].ratePlnHour} oninput={e=>{const v=Number(e.currentTarget.value);if(v>0)machines[id].ratePlnHour=v}}/></label>
      {#if id!=='saw'}
       <label>Posuw mm/min <input type="number" min="0.01" value={machines[id].feedMmMin} oninput={e=>{const v=Number(e.currentTarget.value);if(v>0)machines[id].feedMmMin=v}}/></label>
      {/if}
     </div>
    {/each}
   </div>
  </details>

  <h3>Cięcie — automatyczny wybór i edycja czasów</h3>
  <p class="muted">Przezbrojenia naliczane wspólnie według metody, materiału i grubości. Partie z wyliczonym konturem: {cuttingPlan.batchCount}; liczba detali bez obliczonego czasu: {cuttingPlan.pendingOccurrences}. Ręczne zmiany czasu mają pierwszeństwo.</p>
  <div class="table-wrap"><table>
   <thead><tr><th>Detal</th><th>Il.</th><th>Masa/szt.</th><th>Metoda</th><th>Obliczono [h]</th><th>Przyjęto [h]</th><th>Koszt</th></tr></thead>
   <tbody>
    {#each rows as r}
     <tr>
      <td><strong>{r.label}</strong><small>{r.origin} · {r.cut.hint.confidence==='medium'?'kontur zmierzony':'do weryfikacji'}</small></td>
      <td>{r.quantity}</td><td>{fmt(r.massKg)} kg</td>
      <td><select aria-label={'Metoda cięcia '+r.key} value={r.cut.method??''} onchange={e=>changedMethod(r.key,e.currentTarget.value)}>
        <option value="">Nieustalona</option>
        {#each Object.entries(CUTTING_METHODS) as [id,name]}
         {#if machines[id].enabled}<option value={id}>{name}</option>{/if}
        {/each}
       </select></td>
      <td>{r.cut.calculatedMin!=null?fmt(r.cut.calculatedMin/60):'—'}</td>
      <td><input type="number" min="0" step=".01" aria-label={'Przyjęty czas '+r.key}
       value={r.cut.acceptedMin!=null?String(Number((r.cut.acceptedMin/60).toFixed(4))):''}
       placeholder="Nieustalony"
       oninput={e=>changedTime(r.key,e.currentTarget.value.trim()===''?'':String(Number(e.currentTarget.value)*60))}/></td>
      <td>{r.cut.costPln!=null?fmt(r.cut.costPln)+' zł':'—'}</td>
     </tr>
    {/each}
   </tbody>
  </table></div>

  <h3>Pozostałe operacje — czas i stawka do edycji</h3>
  <div class="table-wrap"><table>
   <thead><tr><th>Operacja</th><th>Czas przyjęty [h]</th><th>Stawka [zł/h]</th><th>Koszt</th></tr></thead>
   <tbody>{#each extraTimes as r}
    <tr><td>{r.label}</td>
    <td><input type="number" step=".1" min="0" placeholder="Nieustalony" aria-label={'Czas '+r.label} value={r.hours??''} oninput={e=>changedExtra(r.key,'hours',e.currentTarget.value)}/></td>
    <td><input type="number" step="1" min="0" aria-label={'Stawka '+r.label} value={r.rate} oninput={e=>changedExtra(r.key,'rate',e.currentTarget.value)}/></td>
    <td>{r.hours==null?'—':fmt(r.hours*r.rate)+' zł'}</td>
    </tr>{/each}</tbody>
  </table></div>

  <details class="panel">
   <summary>Zestawienie mas — wszystkie grupy STEP</summary>
   <div class="table-wrap"><table>
    <thead><tr><th>Grupa</th><th>Szt.</th><th>Masa/szt.</th><th>Razem</th></tr></thead>
    <tbody>{#each rows as r}<tr><td>{r.origin} · {r.label}</td><td>{r.quantity}</td><td>{fmt(r.massKg)} kg</td><td>{fmt(r.totalMassKg)} kg</td></tr>{/each}</tbody>
    <tfoot><tr><th colspan="3">Masa złożenia</th><th>{fmt(inventory.totalMassKg)} kg</th></tr></tfoot>
   </table></div>
  </details>
  {#if requirements.length||technicalNotes.length}
   <details class="panel"><summary>Wymagania i ograniczenia dokumentacji ({requirements.length+technicalNotes.length})</summary>
    {#each requirements as r}<p class="muted"><b>{r.label}:</b> {r.hits.map((h:any)=>h.value).join(', ')}. {r.review}</p>{/each}
    {#each technicalNotes as note}<p class="muted">{note}</p>{/each}
   </details>
  {/if}
  <div class="footnote">Propozycje metod wynikają z reguł i geometrii B-Rep; nie są wynikiem pełnej technologii CAM. Bez potwierdzonego konturu, parametrów lub dokumentacji czas pozostaje nieustalony. Masa STEP to masa gotowych części, nie masa materiału zakupionego.</div>
 {/if}
</section>

<style>
 .quick{max-width:1150px;display:grid;gap:18px}
 h2{font-size:21px;margin:0}h3{font-size:16px;margin:10px 0 0}
 .import,.panel{border:1px solid #2a3544;background:#161e28;border-radius:13px;padding:22px}
 .drop-title{font-size:23px;font-weight:650}.muted{color:#9aa9ba;font-size:13px;line-height:1.6}
 .drop-area{border:1.5px dashed #637991;border-radius:14px;display:flex;flex-direction:column;align-items:center;gap:10px;padding:33px;margin-top:18px;background:#111923;text-align:center}
 .drop-area span{color:#8996a9;font-size:12px}.drop-symbol{font-size:34px;color:#a1b7d0}
 .path-line{display:flex;gap:10px;margin-top:18px}.path-line input{flex:1;min-width:0}
 input,select{background:#111923;border:1px solid #3b4a5d;border-radius:8px;padding:9px;color:#ecf1f7;font:inherit;min-width:0}
 input[type=number]{width:112px}input[type=checkbox]{width:auto}
 button{background:#d5dfeb;color:#101721;border:0;border-radius:8px;padding:10px 20px;font-weight:650;cursor:pointer}
 button:disabled{opacity:.55;cursor:default}.status{font-size:12px;color:#9cabbc;margin:14px 0 0}
 .problem{color:#ffbe94;font-size:13px;padding:10px 0}.good{color:#9ccdad}
 .topline{display:flex;justify-content:space-between}.topline p{margin:5px 0}
 .figures{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
 .figures div{border:1px solid #2a3544;background:#161e28;padding:17px;border-radius:12px;display:grid;gap:9px}
 .figures small{color:#9ca9b9}.figures strong{font-size:22px}
 summary{cursor:pointer;font-weight:600}.settings{display:grid;gap:10px;margin-top:16px}.field{display:grid;gap:8px;font-size:13px}
 .machine{display:flex;align-items:center;gap:18px;flex-wrap:wrap}.machine label{font-size:12px;display:flex;align-items:center;gap:8px}.machine input[type=number]{width:90px}
 .table-wrap{overflow-x:auto;border:1px solid #2a3544;border-radius:10px}
 table{border-collapse:collapse;width:100%;font-size:12px;min-width:680px}
 th{background:#202a37;color:#b5c2d1;text-align:left;font-weight:500}th,td{padding:11px 9px;border-bottom:1px solid #2a3544}
 td small{display:block;color:#8495a8;margin-top:5px}td input[type=number]{width:106px}td select{max-width:136px}
 .footnote{color:#8292a6;font-size:12px;line-height:1.7}
 @media(max-width:760px){.figures{grid-template-columns:1fr}.path-line{flex-direction:column}}
</style>
