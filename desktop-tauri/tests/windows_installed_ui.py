"""Exercise the installed NSIS app and its actual WebView/native CAD bridge.
No command mocks, no dev server, no injected inventory. CDP is enabled only on
this CI-launched WebView through a temporary environment variable.
"""
import json,os,subprocess,sys,time,urllib.request,io
from PIL import Image
from pathlib import Path
from playwright.sync_api import sync_playwright
exe=Path(sys.argv[1]).resolve();step=Path(sys.argv[2]).resolve();out=Path('evidence/windows-native');out.mkdir(parents=True,exist_ok=True)
env=dict(os.environ)
# Match a normal user launch: the installed app must not rely on conda DLLs.
env['PATH']=';'.join(p for p in env.get('PATH','').split(';') if not any(word in p.lower() for word in ['miniconda','miniforge','\\envs\\ds-cad']))
for key in ['CONDA_PREFIX','CONDA_DEFAULT_ENV','CONDA_PROMPT_MODIFIER','PYTHONPATH','PYTHONHOME','QT_PLUGIN_PATH']:env.pop(key,None)
env['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS']='--remote-debugging-port=9223 --force-renderer-accessibility';env['WEBVIEW2_USER_DATA_FOLDER']=str(out.resolve()/'webview-profile')
log=open(out/'app.log','w');app=subprocess.Popen([str(exe)],env=env,stdout=log,stderr=log)
try:
 ready=False
 for _ in range(30):
  if app.poll() is not None:raise RuntimeError('Installed app exited: '+str(app.returncode))
  try:
   urllib.request.urlopen('http://127.0.0.1:9223/json/version',timeout=1);ready=True;break
  except Exception:time.sleep(1)
 if not ready:
  from windows_accessibility_ui import run_accessibility_test
  run_accessibility_test(app.pid,exe,step,out);sys.exit(0)
 with sync_playwright() as p:
  browser=p.chromium.connect_over_cdp('http://127.0.0.1:9223');context=browser.contexts[0]
  for _ in range(60):
   pages=context.pages
   if pages:break
   time.sleep(1)
  page=pages[0];page.set_default_timeout(30000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.get_by_text('DS Estimate 0.6.0 · zapis lokalny',exact=True).wait_for(timeout=60000)
  page.get_by_text('Otwórz plik przez ścieżkę',exact=True).click()
  page.get_by_label('Ścieżka modelu STEP',exact=True).fill(str(step));page.get_by_role('button',name='Analizuj ścieżkę',exact=True).click()
  page.get_by_role('heading',name='Części i materiały',exact=True).wait_for(timeout=300000)
  for name in ['Blacha lewa V','Blacha prawa V','Płyta P-015','Płyta P-015 druga','Profil SHS z wycięciem','Blacha gięta BG-003']:
   page.get_by_text(name,exact=True).wait_for()
  row=page.locator('tr').filter(has=page.get_by_text('Płyta P-015',exact=True))
  assert 'Płyta 15 mm' in row.inner_text(),row.inner_text()
  row.get_by_role('button',name='Parametry / biblioteka',exact=True).click()
  preview=page.get_by_role('img',name='Podgląd 3D: Płyta P-015',exact=True);preview.wait_for()
  assert preview.locator('polygon').count()>=12
  assert preview.bounding_box()['height']>=240
  pixels=Image.open(io.BytesIO(preview.screenshot())).convert('RGB')
  assert sum(1 for r,g,b in pixels.getdata() if r>45 and g>65 and b>65)>500,'Preview contains no visible CAD faces'
  before=preview.locator('polygon').first.get_attribute('points');box=preview.bounding_box()
  page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2);page.mouse.down();page.mouse.move(box['x']+box['width']/2+60,box['y']+box['height']/2+20,steps=5);page.mouse.up()
  assert preview.locator('polygon').first.get_attribute('points')!=before
  page.screenshot(path=str(out/'installed-part-preview.png'))
  page.get_by_role('button',name='Zamknij parametry',exact=True).click()
  page.get_by_role('button',name='Spawanie',exact=True).click()
  assert 'Przygotowanie V' in page.locator('main').inner_text()
  assert page.get_by_label('Typ spoiny solid-1|solid-2',exact=True).input_value()=='butt'
  assert abs(float(page.get_by_label('Przekrój spoiny solid-1|solid-2',exact=True).input_value())-64)<.01
  before=page.get_by_label('Przyjęto Wykonanie spoin',exact=True).input_value()
  page.get_by_label('Przekrój spoiny solid-1|solid-2',exact=True).fill('80');page.get_by_label('Przekrój spoiny solid-1|solid-2',exact=True).press('Tab')
  assert page.get_by_label('Przyjęto Wykonanie spoin',exact=True).input_value()!=before
  page.screenshot(path=str(out/'installed-weld-preparation.png'))
  page.get_by_role('button',name='Gięcie',exact=True).click()
  row=page.locator('tr').filter(has=page.get_by_text('Blacha gięta BG-003',exact=True));assert 'Blacha gięta 3 mm' in row.inner_text()
  page.screenshot(path=str(out/'installed-bending.png'))
  assert not errors,errors
  (out/'result.json').write_text(json.dumps({'status':'PASS','installedExecutable':str(exe),'version':'0.6.0','nativeBridgeMocked':False,'checks':['nested names','15mm rotated plate','embedded actual mesh','preview rotation','V groove 64mm2','automatic weld time edits','3mm bent sheet']},indent=2),encoding='utf8')
  print('INSTALLED_WINDOWS_UI_PASS: actual NSIS application, WebView2 and bundled CAD, no command mocks')
except Exception:
 try:
  if 'page' in locals():
   page.screenshot(path=str(out/'failure.png'));(out/'failure-body.log').write_text(page.locator('body').inner_text(),encoding='utf8')
 except Exception:pass
 raise
finally:
 app.terminate()
 try:app.wait(timeout=10)
 except subprocess.TimeoutExpired:app.kill()
 log.close()
