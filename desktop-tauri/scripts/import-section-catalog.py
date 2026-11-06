"""Import the pinned MIT steel-section data. No network or runtime dependency."""
import csv,json,sys,tomllib,subprocess
from pathlib import Path
source=Path(sys.argv[1]);output=Path(__file__).parents[1]/'src/lib/data/steel-sections.json'
rows=[]
for path in sorted((source/'data').glob('*/*.csv')):
 meta=tomllib.loads(path.with_suffix('.toml').read_text())
 computed={r['designation']:r for r in csv.DictReader((source/'generated/properties'/path.name).open())}
 for row in csv.DictReader(path.open()):
  dims={k:float(v) for k,v in row.items() if k!='designation' and v}
  props=computed.get(row['designation'],{})
  rows.append({'id':meta['id']+':'+row['designation'],'name':row['designation'],
   'series':meta['id'],'shape':meta['shape'],'standard':meta.get('standard',''),
   'process':meta.get('process',''),'dims':dims,
   'areaMm2':float(props['A_cm2'])*100 if props.get('A_cm2') else None})
sha=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
output.write_text(json.dumps({'source':'https://github.com/ulmewix/Steel_Section_Database','commit':sha,'license':'MIT','sections':rows},ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print('CATALOG_IMPORTED',len(rows),sha)
