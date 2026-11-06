<script lang="ts">
 import {onMount} from 'svelte';
 import {call as invoke} from './lib/desktop-api';
 let {path,index,name,mesh}=$props<{path:string,index:number,name:string,mesh?:any}>();
 let triangles=$state<number[][][]>([]),error=$state(''),loading=$state(true),partial=$state(false);
 let yaw=$state(.6),pitch=$state(-.45),zoom=$state(1),dragging=false,lastX=0,lastY=0;
 const cache=new Map<string,any>();
 let projected=$derived.by(()=>{
  const cy=Math.cos(yaw),sy=Math.sin(yaw),cx=Math.cos(pitch),sx=Math.sin(pitch);
  return triangles.map(tri=>{const p=tri.map(([x,y,z])=>{const u=cy*x+sy*z,v=-sy*x+cy*z;return [u,cx*y-sx*v,sx*y+cx*v];});
   const a=p[1].map((v,i)=>v-p[0][i]),b=p[2].map((v,i)=>v-p[0][i]);
   const normal=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
   const shade=Math.round(46+Math.abs((normal[0]*.3-normal[1]*.5+normal[2]*.8)/(Math.hypot(...normal)||1))*30);
   return {points:p.map(([x,y])=>`${200+x*260*zoom},${140-y*260*zoom}`).join(' '),depth:p.reduce((s,v)=>s+v[2],0),shade};}).sort((a,b)=>a.depth-b.depth);
 });
 onMount(()=>{let live=true;const key=path+':'+index;
  (async()=>{try{const data=(mesh?.triangles?.length?mesh:null)||cache.get(key)||JSON.parse(await invoke<string>('preview_part',{path,index}));if(!Array.isArray(data.triangles)||!data.triangles.length)throw Error(data.error||'Silnik nie zwrócił siatki detalu');cache.set(key,data);if(live){triangles=data.triangles;partial=data.partial;}}
   catch(e){if(live)error=String(e);}finally{if(live)loading=false;}})();return()=>{live=false;};});
</script>
<div class="part-preview">
 {#if loading}<p role="status">Przygotowywanie podglądu CAD…</p>{:else if error}<p role="alert">Podgląd niedostępny: {error}</p>{:else}
 <svg viewBox="0 0 400 280" role="img" aria-label={'Podgląd 3D: '+name} style="touch-action:none;cursor:grab;display:block;width:100%;height:320px;min-height:240px;background:var(--surface);border:1px solid var(--line);border-radius:8px"
 onpointerdown={e=>{dragging=true;lastX=e.clientX;lastY=e.clientY;e.currentTarget.setPointerCapture(e.pointerId);}}
 onpointerup={()=>dragging=false} onpointercancel={()=>dragging=false}
 onpointermove={e=>{if(dragging){yaw+=(e.clientX-lastX)*.01;pitch+=(e.clientY-lastY)*.01;lastX=e.clientX;lastY=e.clientY;}}}>
 <title>{name}</title>{#each projected as tri}<polygon points={tri.points} fill={'hsl(200 25% '+tri.shade+'%)'} stroke="rgba(20,40,55,.14)" stroke-width=".3"/>{/each}
 </svg>
 <div class="panel-actions"><small>Przeciągnij, aby obrócić{partial?' · podgląd uproszczony':''}</small><button type="button" aria-label="Obróć podgląd w lewo" onclick={()=>yaw-=.3}>↶</button><button type="button" aria-label="Obróć podgląd w prawo" onclick={()=>yaw+=.3}>↷</button><button type="button" onclick={()=>zoom=Math.max(.3,zoom-.2)}>−</button><button type="button" onclick={()=>zoom=Math.min(3,zoom+.2)}>+</button><button type="button" onclick={()=>{yaw=.6;pitch=-.45;zoom=1;}}>Reset</button></div>
 {/if}
</div>
