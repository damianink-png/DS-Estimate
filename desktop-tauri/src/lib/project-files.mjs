const allowed=/\.(step|stp|pdf|dxf|dwg|png|jpe?g|csv|xlsx?)$/i;
export const fileName=path=>path.split(/[\\/]/).pop()||path;
export const isStep=path=>/\.(step|stp)$/i.test(path);
export const isPdf=path=>/\.pdf$/i.test(path);
export function mergeProjectFiles(existing,added){
 const result=[],seen=new Set();
 for(const path of [...existing,...added]){
  if(typeof path!=='string'||!path.trim()||!allowed.test(path))continue;
  const normalized=path.replaceAll('\\','/').toLowerCase();
  if(seen.has(normalized))continue;
  seen.add(normalized);result.push(path);
 }
 return result;
}
export function preferredStep(files,current=''){
 const candidates=files.filter(isStep);
 if(candidates.includes(current))return current;
 return candidates.slice().sort((a,b)=>{
  const score=p=>/assembly|assembl|z[lł]o[żz]en|monta[żz]|komplet|main/i.test(fileName(p))?0:1;
  return score(a)-score(b)||a.localeCompare(b);
 })[0]||'';
}
export function csvCell(value){
 let s=String(value??'');
 if(/^[=+@\-\t\r]/.test(s))s="'"+s;
 return '"'+s.replaceAll('"','""')+'"';
}
export function moduleReport(report,source){return {
 schema:'ds-estimate.module-status.v1',createdAt:new Date().toISOString(),source,
 complete:report.complete,automatedQuoteVerified:false,knownCostPln:report.knownCostPln,
 modules:report.modules.map(m=>({id:m.id,name:m.title,status:m.status,missing:m.missing,
  costPln:m.knownCostPln,detail:m.detail,error:m.error??null,
  rows:m.rows.map(r=>({name:r.name,kind:r.kind,automatic:r.kind==='time'?r.autoHours??null:r.autoAmount??null,
   value:r.value,costPln:r.costPln,manuallyEdited:r.manuallyEdited,source:r.detail}))}))
};}
