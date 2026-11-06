// Editable shop examples, not manufacturer-certified feeds. No proprietary charts copied.
export const MACHINES=Object.freeze({
 laser:{enabled:true,maxThickness:20,setupMin:15,handlingMin:.3,pierceSec:3,rate:388,curve:[[1,9000],[2,6500],[4,3500],[6,2400],[8,1700],[10,1300],[15,650],[20,350]]},
 plasma:{enabled:true,maxThickness:50,setupMin:18,handlingMin:.5,pierceSec:5,rate:388,curve:[[2,6000],[6,3000],[10,1800],[15,1300],[20,900],[35,500],[50,280]]},
 oxy:{enabled:true,maxThickness:200,setupMin:25,handlingMin:1,pierceSec:35,rate:388,curve:[[10,600],[20,450],[35,350],[60,250],[100,180],[200,100]]},
 saw:{enabled:true,maxThickness:500,setupMin:12,handlingMin:.8,areaRate:450,rate:388}
});
export const METHOD_LABELS={laser:'Laser',plasma:'Plazma',oxy:'Palnik tlenowy',saw:'Piła'};
const valid=(n,label,positive=false)=>{if(typeof n!=='number'||!Number.isFinite(n)||n<(positive?Number.MIN_VALUE:0))throw new RangeError(label);return n;};
export function metalFamily(p){const grade=p.grade||'';return /^S\d|carbon/.test(grade)?'steel':/^1\.|stainless/.test(grade)?'stainless':/^EN AW|aluminium/.test(grade)?'aluminium':grade===''&&p.density===7850?'assumed-steel':'unknown';}
export function curveFeed(curve,t){valid(t,'Grubość',true);if(!Array.isArray(curve)||!curve.length)throw new RangeError('Krzywa maszyny');
 const sorted=curve.map(([x,y])=>[valid(x,'Grubość w tabeli',true),valid(y,'Posuw w tabeli',true)]).sort((a,b)=>a[0]-b[0]);
 if(t<=sorted[0][0])return sorted[0][1];for(let i=1;i<sorted.length;i++){const [x,y]=sorted[i],[px,py]=sorted[i-1];if(t<=x)return py+(y-py)*(t-px)/(x-px);}return sorted.at(-1)[1];}
const profiles=new Set(['square-hollow','rectangular-hollow','round-tube','round-bar','square-bar','rectangular-bar','flat-section','angle','channel','tee','i-section']);
export function planAutomaticCutting(parts,{machines=MACHINES,laserLimit=10,rate=null,catalog=[]}={}){
 const rows=[];for(const p of parts){if(p.route!=='make')continue;
  const s=p.solid,h=s.stockHint??{},kind=p.stockKind||h.kind,selected=catalog.find(x=>x.id===p.catalogId);const notes=[];if(s.cuttingHint?.estimated)notes.push('Szacunek konturu blachy giętej z powierzchni środkowej; przyjęto 1 przebicie.');
  const family=metalFamily(p);if(family==='assumed-steel')notes.push('Przyjęto stal do doboru cięcia; gatunek pozostaje pusty.');
  const thickness=h.thicknessMm??s.bendHint?.bends?.[0]?.thicknessMm??s.cuttingHint?.thicknessMm??Math.min(...p.dims);
  const isProfile=profiles.has(kind)||(selected&&selected.shape!=='FLAT');
  const plate=kind==='plate-candidate'||kind==='plate'||kind==='bent-plate'||s.cuttingHint?.kind==='plate-outline';
  let method=p.cutMethod!=='auto'?p.cutMethod:isProfile?'saw':plate?(thickness<=laserLimit?'laser':thickness<=35?'plasma':['steel','assumed-steel'].includes(family)?'oxy':'plasma'):null;
  if(family==='unknown'&&p.cutMethod==='auto'&&method!=='saw'){method=null;notes.push('Nieznany materiał: wybierz technologię.');}
  let m=machines[method],minutes=null,runMin=null,setupMin=0,feed=null;
  let contour=p.contourMm??s.cuttingHint?.contourMm??null,pierces=p.pierces??s.cuttingHint?.pierces??null;
  let sectionArea=p.cutAreaMm2??selected?.areaMm2??h.sectionAreaMm2??null;
  if(method&&(!m?.enabled)){notes.push('Maszyna wyłączona');method=null;m=null;}
  if(method==='oxy'&&!['steel','assumed-steel'].includes(family)){notes.push('Palnik tlenowy nie jest automatyczną technologią dla tego materiału.');method=null;m=null;}
  if(m){
   setupMin=valid(m.setupMin,'Przezbrojenie');valid(m.handlingMin,'Obsługa');
   if(method==='saw'){
    valid(p.cutCount,'Liczba cięć');valid(p.sawAngle,'Kąt');if(!Number.isInteger(p.cutCount)||p.sawAngle>75)throw new RangeError('Cięcia: całkowita liczba, kąt 0–75°');
    if(sectionArea!==null){valid(sectionArea,'Pole cięcia',true);const speed=valid(m.areaRate,'Wydajność piły',true)*(family==='stainless'?.65:family==='aluminium'?1.5:1);
     runMin=p.cutCount*(sectionArea/Math.cos(p.sawAngle*Math.PI/180)/speed+m.handlingMin);
     notes.push('Założono '+p.cutCount+' cięcia/szt.; zweryfikuj mocowanie i wspólne cięcia sztangi.');
    }else notes.push('Brak zmierzonego pola przekroju — wpisz je lub wybierz przekrój katalogowy.');
   }else if(thickness>m.maxThickness)notes.push('Grubość przekracza zakres maszyny.');
   else if(contour!==null&&pierces!==null){valid(contour,'Kontur');valid(pierces,'Przebicia');if(!Number.isInteger(pierces))throw new RangeError('Liczba przebić');
    feed=curveFeed(m.curve,thickness)*(family==='stainless'?.7:family==='aluminium'?1.1:1);
    runMin=contour/feed+pierces*valid(m.pierceSec,'Przebicie')/60+m.handlingMin;
   }else notes.push('Brak konturu rozwinięcia lub liczby przebić. Nie używamy obwodu bbox jako konturu.');
  }
  const profile=p.catalogId||kind||'unknown';const batchKey=[method||'unknown',family==='assumed-steel'?'steel':family,p.grade||'—',method==='saw'?profile+':'+p.dims.slice(1).map(x=>x.toFixed(1)).join('x')+':'+p.sawAngle:thickness.toFixed(1)].join(' | ');
  rows.push({id:p.id,name:p.name,method,family,thickness,profile,batchKey,contour,pierces,sectionArea,feed,runMin,setupMin,minutes,rate:rate??m?.rate??null,notes});
 }
 rows.sort((a,b)=>a.batchKey.localeCompare(b.batchKey,'pl',{numeric:true})||a.name.localeCompare(b.name,'pl',{numeric:true}));
 const batches=new Map();for(const row of rows){if(row.runMin===null)continue;let batch=batches.get(row.batchKey);if(!batch){batch={key:row.batchKey,method:row.method,count:0,setupMin:row.setupMin,runMin:0};batches.set(row.batchKey,batch);row.minutes=row.setupMin+row.runMin;}else{row.minutes=row.runMin;row.setupMin=0;}valid(row.minutes,'Czas cięcia');batch.count++;batch.runMin+=row.runMin;}
 return {rows,batches:[...batches.values()],missing:rows.filter(r=>r.minutes===null).length};
}
