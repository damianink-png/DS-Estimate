// File selection and native drops follow DS Compare 0.6.4's Tauri adapter.
import {invoke,isTauri} from '@tauri-apps/api/core';
import {open,save} from '@tauri-apps/plugin-dialog';
export const native=isTauri();
export function call<T>(command:string,args:Record<string,unknown>={}):Promise<T>{
 if(!native)return Promise.reject(new Error('Wybór plików i analiza CAD działają w aplikacji Windows.'));
 return invoke<T>(command,args);
}
export async function pickInputs(directory=false):Promise<string[]>{
 if(!native)throw new Error('Uruchom aplikację Windows, aby dodać pliki.');
 const result=await open({directory,multiple:!directory,title:directory?'Dodaj folder projektu':'Dodaj modele i dokumentację',
  filters:directory?undefined:[{name:'Dokumentacja konstrukcji',extensions:['step','stp','pdf','dxf','dwg','png','jpg','jpeg','csv','xlsx','xls']}]});
 return result?Array.isArray(result)?result:[result]:[];
}
export async function watchDrops(handler:(paths:string[]|null,hover:boolean)=>void){
 if(!native)return ()=>{};
 const {getCurrentWebview}=await import('@tauri-apps/api/webview');
 return getCurrentWebview().onDragDropEvent(e=>{
  if(e.payload.type==='drop')handler(e.payload.paths,false);
  else handler(null,e.payload.type==='enter'||e.payload.type==='over');
 });
}
export async function saveReport(text:string,extension:'json'|'csv'){
 if(!native)throw new Error('Zapis raportu jest dostępny w aplikacji Windows.');
 const path=await save({title:'Zapisz zestawienie wyceny',defaultPath:'DS-Estimate-raport.'+extension,
  filters:[{name:extension.toUpperCase(),extensions:[extension]}]});
 if(!path)return false;
 await call('write_report',{path,content:text});return true;
}
