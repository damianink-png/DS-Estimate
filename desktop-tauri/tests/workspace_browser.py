"""UI interaction regression. Native commands are mocked; CAD is tested separately."""
import json, subprocess, time, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
fixture={"engineVersion":"0.7.0","count":2,"totalMassKg":15.7,"solids":[{"id":"solid-1","name":"Plate P-101","verifiedShapeKey":"A","volumeMm3":1000000,"massKg":7.85,"bboxMm":[1000,100,10],"verificationMethod":"native-brep","stockHint":{"kind":"rectangular-bar","lengthMm":1000}},{"id":"solid-2","name":"Plate P-102","verifiedShapeKey":"A","volumeMm3":1000000,"massKg":7.85,"bboxMm":[1000,100,10]}],"groups":[{"geometryId":"A","quantity":2,"massKg":7.85}]}
fixture['previews']={'A':{'triangles':[[[0,0,0],[.5,0,0],[0,.5,0]]],'partial':False}}
for solid in fixture['solids']:solid['previewKey']='A'
shim=r"""
window.isTauri=true;window.__mockFiles=['C:\\job\\main.step'];window.__calls=[];window.__callbacks={};window.__listeners={};let next=0;
window.__TAURI_INTERNALS__={metadata:{currentWindow:{label:'main'},currentWebview:{label:'main'}},
 transformCallback(fn){let id=++next;window.__callbacks[id]=fn;return id;},
 unregisterCallback(id){delete window.__callbacks[id]},
 async invoke(cmd,args={}){window.__calls.push({cmd,args});
 if(cmd==='plugin:dialog|open')return window.__mockFiles;
 if(cmd==='plugin:dialog|save')return args.options.defaultPath;
 if(cmd==='write_report'){window.__savedReport=args.content;return;}
 if(cmd==='plugin:event|listen'){window.__listeners[args.event]=args.handler;return ++next;}
 if(cmd==='plugin:event|unlisten')return;
 if(cmd==='scan_project')return [args.path];
 if(cmd==='step_fingerprint')return 'unchanged-v1';
 if(cmd==='preview_part')return JSON.stringify({triangles:[[[0,0,0],[.5,0,0],[0,.5,0]]],partial:false});
 if(cmd==='analyze_joints'){await new Promise(r=>setTimeout(r,500));return JSON.stringify({engineVersion:'0.7.0',solidCount:2,complete:true,issues:[],candidates:[{id:'solid-1|solid-2',partA:'solid-1',partB:'solid-2',lengthMm:90,contactAreaMm2:200}]});}
 if(cmd==='analyze_step')return JSON.stringify(FIXTURE);
 if(cmd==='extract_pdf_text')return 'a4 100 x2';
 throw Error('Unmocked command: '+cmd);
 }};
window.__drop=paths=>{let id=window.__listeners['tauri://drag-drop'];if(!id)throw Error('Native drop listener missing');window.__callbacks[id]({event:'tauri://drag-drop',id:1,payload:{paths,position:{x:300,y:200}}});};
""".replace('FIXTURE',json.dumps(fixture))
log=open('/tmp/ds-estimate-vite.log','w');server=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','8769'],cwd=root,stdout=log,stderr=log)
try:
 for i in range(120):
  try:urllib.request.urlopen('http://127.0.0.1:8769',timeout=1);break
  except Exception:time.sleep(.25)
 with sync_playwright() as p:
  chrome=next((str(p) for p in [Path('/usr/bin/google-chrome'),Path('/usr/bin/chromium')] if p.exists()),None)
  browser=p.chromium.launch(**({'executable_path':chrome} if chrome else {}),headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
  page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.add_init_script(shim);page.goto('http://127.0.0.1:8769');page.get_by_role('heading',name='Wczytaj konstrukcję',exact=True).wait_for()
  assert page.get_by_role('button',name='Narzędzia',exact=True).count()==0
  assert page.get_by_role('button',name='Detale / materiał',exact=True).count()==0
  page.get_by_role('button',name='Dodaj pliki',exact=True).click()
  page.get_by_role('heading',name='Trwa analiza modelu',exact=True).wait_for()
  assert page.get_by_role('button',name='Spawanie',exact=True).count()==0
  try:page.get_by_role('heading',name='Części i materiały',exact=True).wait_for(timeout=15000)
  except Exception:
   print('BODY',page.locator('body').inner_text());print('CALLS',page.evaluate('window.__calls'));print('ERRORS',errors);raise
  assert page.get_by_label('Gatunek solid-1',exact=True).input_value()==''
  assert page.get_by_label('Gęstość solid-1',exact=True).input_value()=='7850'
  page.get_by_label('Gęstość solid-1',exact=True).fill('2700');page.get_by_label('Gęstość solid-1',exact=True).press('Tab')
  assert '10,55' in page.locator('.metrics').inner_text()
  assert page.get_by_label('Gęstość solid-2',exact=True).input_value()=='7850'
  assert page.get_by_role('heading',name='Koszt materiału',exact=True).count()==0
  assert page.get_by_label('Cena materiału solid-1',exact=True).count()==0
  assert page.get_by_role('heading',name='Pliki projektu',exact=True).count()==0
  assert page.get_by_text('Plate P-101',exact=True).count()==1
  assert page.evaluate("window.__calls.filter(x=>x.cmd==='analyze_joints').length")==1
  page.get_by_label('Realizacja solid-1',exact=True).select_option('purchase')
  page.get_by_role('button',name='Naddatki solid-2',exact=True).click()
  page.get_by_role('img',name='Podgląd 3D: Plate P-102').wait_for()
  assert page.evaluate("window.__calls.filter(x=>x.cmd==='preview_part').length")==0
  page.get_by_label('Długość — początek',exact=True).fill('3');page.get_by_role('button',name='Zapisz detal',exact=True).click()
  assert page.get_by_role('dialog').is_visible() is False
  page.evaluate("window.__mockFiles=['C:\\\\job\\\\drawing.pdf']")
  page.get_by_role('button',name='Dodaj pliki',exact=True).click()
  page.get_by_role('heading',name='Części i materiały',exact=True).wait_for()
  page.get_by_role('button',name='Pliki projektu',exact=False).first.click()
  page.get_by_role('button',name='2 plików',exact=False).click()
  page.get_by_text('drawing.pdf',exact=True).wait_for()
  assert page.locator('.file-list li').count()==2
  page.evaluate("window.__drop(['C:\\\\job\\\\detail.step'])")
  page.get_by_role('heading',name='Części i materiały',exact=True).wait_for()
  page.get_by_role('button',name='Pliki projektu',exact=False).first.click()
  page.get_by_text('detail.step',exact=True).wait_for()
  assert page.locator('.file-list li').count()==3
  # All three file additions use the unchanged main model's single cached CAD result.
  assert page.evaluate("window.__calls.filter(x=>x.cmd==='analyze_step').length")==1
  page.get_by_role('button',name='Spawanie',exact=True).click()
  page.get_by_role('button',name='Przeanalizowano STEP',exact=True).wait_for()
  before=page.get_by_label('Przyjęto Wykonanie spoin',exact=True).input_value()
  page.get_by_label('Typ spoiny solid-1|solid-2',exact=True).select_option('butt')
  assert page.get_by_label('Przyjęto Wykonanie spoin',exact=True).input_value()!=before
  assert page.get_by_text('Kalkulator czasu',exact=False).count()==0
  assert page.get_by_text('Dane geometrii i rozpoznanie wyrobu',exact=True).count()==0
  control=page.get_by_label('Przyjęto Wykonanie spoin',exact=True);control.fill('2.5');control.press('Tab')
  page.get_by_role('button',name='Stawki i ustawienia',exact=True).click()
  price=page.get_by_label('Cena kg stal',exact=True);price.fill('6');price.press('Tab')
  rate=page.get_by_label('Spawanie [zł/h]',exact=True);rate.fill('200');rate.press('Tab')
  page.get_by_role('button',name='Spawanie',exact=True).click()
  assert page.get_by_label('Przyjęto Wykonanie spoin',exact=True).input_value()=='2.5'
  assert '500,00' in page.locator('main').inner_text()
  page.get_by_role('button',name='Przywróć automat Wykonanie spoin',exact=True).click()
  assert 'overridden' not in page.get_by_label('Przyjęto Wykonanie spoin',exact=True).get_attribute('class')
  page.get_by_role('button',name='Stan modułów',exact=True).first.click()
  assert page.locator('tbody tr').count()==12
  page.get_by_role('button',name='Zapisz raport JSON',exact=True).click()
  page.wait_for_function('window.__savedReport')
  data=json.loads(page.evaluate('window.__savedReport'));assert len(data['modules'])==12;assert data['complete'] is False
  page.get_by_role('button',name='Detale / materiał',exact=True).click()
  out=root/'evidence';out.mkdir(exist_ok=True);page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(out/'modules-dark.png'),full_page=True)
  page.get_by_role('button',name='Zmień motyw',exact=True).click()
  assert page.locator('.app').get_attribute('data-theme')=='light'
  page.set_viewport_size({'width':800,'height':650});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  page.screenshot(path=str(out/'modules-light-800.png'),full_page=True)
  page.get_by_role('button',name='Pliki projektu',exact=False).first.click();page.get_by_role('button',name='Wyceń ten model',exact=True).click()
  page.get_by_role('heading',name='Części i materiały',exact=True).wait_for()
  assert page.evaluate("window.__calls.filter(x=>x.cmd==='analyze_step').length")==2
  page.get_by_role('button',name='Detale / materiał',exact=True).click();assert page.get_by_label('Gęstość solid-1',exact=True).input_value()=='7850'
  assert not errors,errors
  print('UI_WORKSPACE_PASS: native picker and drop mocks, file append, CAD cache, materials, corrections, status export, theme, responsive layout. No native Windows claim.')
  browser.close()
finally:
 server.terminate();server.wait(timeout=10);log.close()
