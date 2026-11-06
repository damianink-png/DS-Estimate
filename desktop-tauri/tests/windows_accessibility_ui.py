"""Native release-app regression through Windows UI Automation (no DevTools needed)."""
import json,time
from PIL import ImageGrab,ImageChops
from pywinauto import Application,mouse

def run_accessibility_test(pid,exe,step,out):
 app=Application(backend='uia').connect(process=pid,timeout=30);win=app.window(title='DS Estimate 0.6.0');win.wait('exists visible',timeout=60);win.set_focus()
 def find(name,timeout=30):
  deadline=time.monotonic()+timeout
  while time.monotonic()<deadline:
   candidates=[c for c in win.descendants() if c.element_info.name==name]
   if candidates:return candidates[0]
   time.sleep(.3)
  raise AssertionError('Native control missing: '+name)
 def press(name):
  control=find(name)
  try:control.invoke()
  except Exception:control.click_input()
 def enter(name,value):
  control=find(name);control.set_focus();control.type_keys('^a'+value+'{TAB}',with_spaces=True,pause=.02)
 def value(name):
  control=find(name)
  try:return str(control.iface_value.CurrentValue)
  except Exception:return str(control.iface_range_value.CurrentValue)
 def screenshot(name):
  r=win.rectangle();ImageGrab.grab(bbox=(r.left,r.top,r.right,r.bottom)).save(out/name)
 try:
  press('Otwórz plik przez ścieżkę');enter('Ścieżka modelu STEP',str(step));press('Analizuj ścieżkę')
  find('Części i materiały',timeout=300)
  names=['Blacha lewa V','Blacha prawa V','Płyta P-015','Płyta P-015 druga','Profil SHS z wycięciem','Blacha gięta BG-003']
  for name in names:find(name)
  find('Płyta 15 mm')
  part=find('Płyta P-015');parent=part
  for _ in range(6):
   parent=parent.parent();buttons=[c for c in parent.descendants() if c.element_info.name=='Parametry / biblioteka']
   if len(buttons)==1:break
  else:raise AssertionError('Cannot locate parameters for the named native part')
  try:buttons[0].invoke()
  except Exception:buttons[0].click_input()
  image=find('Podgląd 3D: Płyta P-015');r=image.rectangle();assert r.height()>=240
  before=ImageGrab.grab(bbox=(r.left,r.top,r.right,r.bottom)).convert('RGB')
  assert sum(1 for red,green,blue in before.getdata() if red>45 and green>65 and blue>65)>500,'Native preview has no visible faces'
  cx,cy=(r.left+r.right)//2,(r.top+r.bottom)//2
  mouse.press(coords=(cx,cy))
  for i in range(1,7):mouse.move(coords=(cx+i*10,cy+round(i*20/6)));time.sleep(.05)
  mouse.release(coords=(cx+60,cy+20));mouse.move(coords=(r.right+10,r.bottom+10));time.sleep(.4)
  after=ImageGrab.grab(bbox=(r.left,r.top,r.right,r.bottom)).convert('RGB');diff=ImageChops.difference(before,after)
  assert sum(1 for pixel in diff.getdata() if max(pixel)>10)>1000,'Native preview did not rotate'
  screenshot('installed-part-preview.png');press('Zamknij parametry');press('Spawanie')
  deadline=time.monotonic()+30
  while time.monotonic()<deadline and not any('Przygotowanie V' in c.element_info.name for c in win.descendants()):time.sleep(.3)
  assert any('Przygotowanie V' in c.element_info.name for c in win.descendants())
  area='Przekrój spoiny solid-1|solid-2';assert abs(float(value(area).replace(',','.'))-64)<.01
  before_time=value('Przyjęto Wykonanie spoin');enter(area,'80');time.sleep(.3);assert value('Przyjęto Wykonanie spoin')!=before_time
  screenshot('installed-weld-preparation.png');press('Gięcie');find('Blacha gięta 3 mm');screenshot('installed-bending.png')
  (out/'result.json').write_text(json.dumps({'status':'PASS','driver':'Windows UI Automation','installedExecutable':str(exe),'version':'0.6.0','nativeBridgeMocked':False,'checks':['nested names','15mm rotated plate','actual preview pixels','preview rotation','V groove 64mm2','automatic weld time edit','3mm bent sheet']},indent=2),encoding='utf8')
  print('INSTALLED_WINDOWS_UI_PASS: Windows UI Automation, actual NSIS app and native CAD, no mocks')
 except Exception:
  try:screenshot('failure.png')
  except Exception:pass
  try:(out/'failure-controls.json').write_text(json.dumps([{'name':c.element_info.name,'type':c.element_info.control_type} for c in win.descendants()],ensure_ascii=False,indent=2),encoding='utf8')
  except Exception:pass
  raise
