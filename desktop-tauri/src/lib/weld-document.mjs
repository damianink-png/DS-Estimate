// ISO 2553-oriented weld callout normalization. Only explicit dimensions
// are costed; unverified symbol-to-STEP mapping never becomes a quotation.
const num=x=>typeof x==='number'&&Number.isFinite(x)&&x>0;
export function normalizeWeldCallout(raw){
 if(!raw||typeof raw!=='object')throw new TypeError('weld callout');
 const {id,kind,throatMm,lengthMm,count=1,side='unspecified',allAround=false,source='unknown',verified=false}=raw;
 if(!['fillet','butt','other'].includes(kind))throw new RangeError('weld kind');
 if(!Number.isInteger(count)||count<1)throw new RangeError('count');
 if(throatMm!=null&&!num(throatMm))throw new RangeError('throatMm');
 if(lengthMm!=null&&!num(lengthMm))throw new RangeError('lengthMm');
 if(!['arrow','other','both','unspecified'].includes(side))throw new RangeError('side');
 const reasons=[];
 if(kind!=='fillet')reasons.push('cross-section model not implemented');
 if(!num(throatMm))reasons.push('missing throat a');
 if(!num(lengthMm))reasons.push('missing verified weld length');
 if(!verified)reasons.push('symbol-to-joint association unverified');
 return {id:id??null,kind,throatMm:throatMm??null,lengthMm:lengthMm??null,count,side,allAround:Boolean(allAround),source,verified:Boolean(verified),quotationReady:reasons.length===0,reasons};
}
export function createWeldTakeoff(callouts){
 if(!Array.isArray(callouts))throw new TypeError('callouts');
 const rows=callouts.map(normalizeWeldCallout);
 return {rows,ready:rows.filter(r=>r.quotationReady).map(r=>({count:r.count,lengthMm:r.lengthMm,throatMm:r.throatMm})),pending:rows.filter(r=>!r.quotationReady),allVerified:rows.every(r=>r.quotationReady)};
}
// Parses explicit, structured annotation text (not arbitrary raster OCR).
// Examples: "a5 120", "a 5 L=120", "a5 120 x2".
export function parseExplicitFilletNotes(text,{source='PDF text',verified=false}={}){
 if(typeof text!=='string')throw new TypeError('text');
 const notes=[];
 for(const [i,line] of text.split(/\r?\n/).entries()){
  const m=line.match(/\ba\s*(\d+(?:[.,]\d+)?)\s*(?:L\s*=\s*)?(\d+(?:[.,]\d+)?)(?:\s*[x×]\s*(\d+))?\b/i);
  if(!m)continue;
  notes.push(normalizeWeldCallout({id:`line-${i+1}`,kind:'fillet',throatMm:Number(m[1].replace(',','.')),lengthMm:Number(m[2].replace(',','.')),count:m[3]?Number(m[3]):1,source,verified}));
 }
 return notes;
}
