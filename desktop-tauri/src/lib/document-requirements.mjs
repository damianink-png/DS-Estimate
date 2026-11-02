/**
 * Conservative evidence-backed checklist. Text clues are NOT interpreted as
 * measured geometry or verified drawing symbols. Never auto-add charges.
 */
export function extractManufacturingRequirements(text){
 if(typeof text!=='string')throw new TypeError('document text');
 const lines=text.split(/\r?\n/).map((x,i)=>({line:i+1,text:x.trim()})).filter(x=>x.text);
 const rules=[
  {id:'steel-grade',category:'material',label:'Gatunek stali / materiał',pattern:/\b(?:S(?:235|275|355|420|460|500|690|700|890|960)(?:J0|JR|J2|J2\+N|QL|M|ML)?|C45|42CrMo4|1[.,]4301)\b/ig,review:'Zweryfikuj cenę, atest i gęstość materiału'},
  {id:'welding-quality',category:'welding-quality',label:'Klasa jakości spoin ISO 5817',pattern:/\b(?:EN\s*)?ISO\s*5817(?:\s*[-:]?\s*[BCD])?\b/ig,review:'Sprawdź klasę spoin i koszt kontroli VT / NDT'},
  {id:'welding-process',category:'welding',label:'Proces spawania',pattern:/\b(?:MAG\s*135|MIG\s*131|proces\s*135|ISO\s*4063|spawanie\s*135)\b/ig,review:'Wymagane są rzeczywista długość, typ i a spoiny'},
  {id:'ultrasonic-test',category:'inspection',label:'Kontrola ultradźwiękowa',pattern:/\b(?:UT\s*(?:100\s*%|[ABC]\b)?|ISO\s*17640)\b/ig,review:'Dodaj odrębną operację NDT, zakres i koszt badania'},
  {id:'surface-prep',category:'surface-preparation',label:'Przygotowanie powierzchni',pattern:/\b(?:ISO\s*8501(?:\s*[-–]\s*1)?|Sa\s*2[.,]5|śrutowani[ea]|piaskowani[ea])\b/ig,review:'Zweryfikuj powierzchnię m² i normę przygotowania'},
  {id:'painting',category:'painting',label:'Powłoka malarska / grubość',pattern:/\b(?:RAL\s*\d{4}|DFT\s*\d+(?:[.,]\d+)?\s*(?:µm|um)?|malowani[ea])\b/ig,review:'Potrzebna powierzchnia, liczba warstw, DFT i czas schnięcia'},
  {id:'roughness',category:'machining',label:'Chropowatość powierzchni',pattern:/\bRa\s*\d+(?:[.,]\d+)?\b/ig,review:'Weryfikuj operacje wykańczające i pomiar chropowatości'},
  {id:'fits',category:'machining',label:'Pasowania / tolerancje otworów',pattern:/\b(?:H[6-9]|h[6-9])\b/g,review:'Weryfikuj rozwiercanie, wytaczanie, obróbkę i pomiary'},
  {id:'general-tolerances',category:'inspection',label:'Tolerancje ogólne',pattern:/\bISO\s*2768\s*[-–]?\s*[fmcv](?:[HKL])?\b/ig,review:'Dodaj kontrolę wymiarową odpowiednią do klasy'},
 ];
 const matches=[];
 for(const rule of rules){
  const hits=[];
  for(const entry of lines) for(const match of entry.text.matchAll(rule.pattern)){
   hits.push({line:entry.line,value:match[0],excerpt:entry.text.slice(Math.max(0,match.index-35),Math.min(entry.text.length,match.index+match[0].length+35))});
   if(hits.length>=20)break;
  }
  if(hits.length)matches.push({id:rule.id,category:rule.category,label:rule.label,hits,review:rule.review,source:'text evidence; not verified against drawing',quotationReady:false});
 }
 return {requirements:matches,needsReview:matches.length>0,recognizedCategories:[...new Set(matches.map(x=>x.category))],
  disclaimer:'OCR/text evidence does not establish geometry, inspection extent, weld length or cost; verify drawing before quotation.'};
}
