/**
 * DS Estimate – deterministic cutting route proposal.
 *
 * Geometry is sourced from STEP B-Rep measurements where available.
 * A bounding box alone is NOT a verified plate outline, profile section,
 * or an ISO-tolerance requirement. No missing time is interpreted as zero.
 *
 * Values below are editable *example* shop settings; never machine-certified
 * feeds or a substitute for a cutting chart for the exact machine/material.
 */
export const CUTTING_METHODS = Object.freeze({
 laser: 'Laser', plasma: 'Plazma', oxy: 'Tlen', saw: 'Piła taśmowa',
 waterjet: 'Waterjet', wedm: 'WEDM'
});

export const SAMPLE_MACHINE_SETTINGS = Object.freeze({
 laser: {enabled:true,maxThicknessMm:15,feedMmMin:1400,pierceSec:3,setupMin:15,ratePlnHour:388},
 plasma:{enabled:true,maxThicknessMm:35,feedMmMin:900,pierceSec:5,setupMin:18,ratePlnHour:388},
 oxy:{enabled:true,maxThicknessMm:150,feedMmMin:350,pierceSec:35,setupMin:25,ratePlnHour:388},
 saw:{enabled:true,maxThicknessMm:300,cutAreaMm2Min:450,setupMin:12,ratePlnHour:388},
 waterjet:{enabled:false,maxThicknessMm:100,feedMmMin:130,pierceSec:35,setupMin:20,ratePlnHour:388},
 wedm:{enabled:false,maxThicknessMm:300,feedMmMin:8,pierceSec:120,setupMin:45,ratePlnHour:388}
});

const positive=(x,name)=>{if(typeof x!=='number'||!Number.isFinite(x)||x<=0)throw new RangeError(name);return x;};
const nonnegative=(x,name)=>{if(typeof x!=='number'||!Number.isFinite(x)||x<0)throw new RangeError(name);return x;};
const oneOf=(v,options)=>options.includes(v);

export function partCuttingHint(solid){
 if(!solid || !Array.isArray(solid.bboxMm) || solid.bboxMm.length!==3 ||
    !solid.bboxMm.every(x=>typeof x==='number'&&Number.isFinite(x)&&x>0))
   return {kind:'unclassified',reason:'Brak poprawnych wymiarów B-Rep'};
 const [small,mid,long]=[...solid.bboxMm].sort((a,b)=>a-b);
 const ratio=mid/small;
 // Elongated stock is a *candidate*, not proof that the part is cut from bar/pipe.
 if(long/mid>=4 && ratio<3)
  return {kind:'possible-profile',lengthMm:long,crossSectionAreaMm2:solid.volumeMm3/long,
   confidence:'low',source:'STEP bounding-box and net cross-section only'};
 if(ratio>=5){
  const exact=solid.cuttingHint;
  if(exact && exact.kind==='plate-outline' && exact.contourMm>0 &&
     Number.isInteger(exact.pierces)&&exact.pierces>=1 &&
     Math.abs(exact.thicknessMm-small)<=Math.max(0.2,small*0.03)){
   return {kind:'possible-plate',thicknessMm:small,contourMm:exact.contourMm,
    pierces:exact.pierces,confidence:'medium',source:'Measured STEP planar face wires; verify stock outline'};
  }
  return {kind:'possible-plate',thicknessMm:small,confidence:'low',
   source:'STEP bounding-box: plate thickness candidate only; no verified cut contour'};
 }
 return {kind:'unclassified',reason:'Geometria nie pozwala wiarygodnie rozpoznać materiału wyjściowego'};
}

export function recommendCutting({
 solid,quantity=1,material='unknown',machines=SAMPLE_MACHINE_SETTINGS,
 overrideMethod=null,overrideMinutes=null
}={}){
 if(!Number.isSafeInteger(quantity)||quantity<1)throw new RangeError('quantity');
 if(overrideMinutes!==null)nonnegative(overrideMinutes,'overrideMinutes');
 const hint=partCuttingHint(solid);
 const isCarbonSteel=oneOf(material,['S235','S355','S690QL','S960QL','carbon-steel']);
 const isMetal=oneOf(material,['S235','S355','S690QL','S960QL','carbon-steel','stainless','aluminium']);
 let candidates=[];
 if(hint.kind==='possible-profile')candidates=['saw'];
 if(hint.kind==='possible-plate'){
  // Rough primary manufacturing preference, NOT guaranteed cost optimum.
  const t=hint.thicknessMm;
  candidates=t<=12?['laser','plasma','waterjet','oxy']:
             t<=35?['plasma','laser','oxy','waterjet']:
                   ['oxy','plasma','waterjet','laser'];
  if(!isCarbonSteel)candidates=candidates.filter(x=>x!=='oxy');
  if(!isMetal)candidates=candidates.filter(x=>x==='waterjet');
 }
 // WEDM is never auto-selected from a generic STEP bbox; needs high precision requirements.
 const alternatives=candidates.filter(method=>{
  const m=machines?.[method];
  return m?.enabled===true && (method==='saw'||(typeof m.maxThicknessMm==='number'&&
   hint.thicknessMm<=m.maxThicknessMm));
 });
 let selected=alternatives[0]??null;
 if(overrideMethod!==null){
  if(!oneOf(overrideMethod,Object.keys(CUTTING_METHODS)))throw new RangeError('overrideMethod');
  const cfg=machines?.[overrideMethod];
  if(!cfg?.enabled)throw new RangeError('Selected machine unavailable');
  if(hint.kind==='possible-plate'&&hint.thicknessMm>cfg.maxThicknessMm)throw new RangeError('Selected machine thickness exceeds limit');
  selected=overrideMethod;
 }
 let setupMin=null,perPieceMin=null,calcMin=null;
 const warnings=[];
 if(hint.confidence==='low')warnings.push('Typ półfabrykatu jest hipotezą z wymiarów STEP');
 if(material==='unknown')warnings.push('Brak potwierdzonego gatunku materiału');
 if(!selected)warnings.push('Nie można automatycznie dobrać dostępnej technologii');
 if(selected){
  const m=machines[selected];
  setupMin=nonnegative(m.setupMin,'setupMin');
  positive(m.ratePlnHour,'ratePlnHour');
  if(selected==='saw' && hint.kind==='possible-profile'){
   // Saw time uses net material cross-section; kerf/section clamping and
   // number of actual stock cuts are unknown. Report as unresolved.
   warnings.push('Nieznany przekrój cięcia piłą, liczba cięć i sposób mocowania');
  }else if(hint.kind==='possible-plate' && hint.contourMm && hint.pierces!=null){
   positive(m.feedMmMin,'feedMmMin');nonnegative(m.pierceSec,'pierceSec');
   perPieceMin=hint.contourMm/m.feedMmMin+hint.pierces*m.pierceSec/60;
   calcMin=setupMin+perPieceMin*quantity;
   warnings.push('Prędkość cięcia z edytowalnego profilu maszyny; wymaga kalibracji dla grubości i gatunku');
  }else{
   warnings.push('Brak zmierzonego konturu/parametrów do obliczenia czasu');
  }
 }
 const acceptedMin=overrideMinutes??calcMin;
 const rate=selected?machines[selected].ratePlnHour:null;
 return {hint,method:selected,alternatives,quantity,setupMin,perPieceMin,
  calculatedMin:calcMin,acceptedMin,
  costPln:acceptedMin==null||rate==null?null:acceptedMin*rate/60,
  ratePlnHour:rate,
  confidence:overrideMinutes!==null?'manual':(calcMin===null?'requires-review':'estimated'),
  warnings,calculationSource:calcMin===null?null:'measured contour and editable machine assumptions'};
}
