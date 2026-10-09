# SPDX-License-Identifier: CC-BY-NC-4.0
"""Mechanical prototype BOM from current CAD; explicit incomplete whole-base scope."""
import csv,json,hashlib
from pathlib import Path
from collections import defaultdict
HERE=Path(__file__).resolve().parent;OUT=HERE/'build';F=OUT/'load-frame'
D=json.loads((F/'manifest.json').read_text());groups=defaultdict(list)
for p in D['parts']:
 if p['category']=='environment':continue
 if p['category']=='hardware':key=(p['category'],p['process'],tuple(p['notes']),round(p['volume_mm3'],3))
 elif p['id'].startswith('B06-105-POST-'):key=('custom','B06-105-POST')
 elif p['id'].startswith(('B06-107-SPREADER','B06-108-PRESS-PAD')):key=('custom',p['id'].rsplit('-',1)[0].rstrip('-'))
 else:key=('custom',p['id'])
 groups[key].append(p)
rows=[]
for ps in groups.values():
 p=ps[0];rows.append({'id':p['id'],'quantity':len(ps),'category':p['category'],'material':p['material'],'specification':p['process'],
 'cad_files':';'.join('load-frame/'+a['step'] for a in ps),'notes':' | '.join(p['notes']),'status':'Mechanical DFM / no powered or load release'})
M=json.loads((OUT/'exterior/manifest.json').read_text())
for p in M['parts']:
 if not p.get('print_stl') or p['id'].startswith('B06-307'):continue
 rows.append({'id':p['id'],'quantity':1,'category':'printed','material':'Translucent PETG' if p['id'].startswith('B06-306') else 'PETG',
 'specification':'FDM; 0.4 nozzle target; final slicing/fit coupon required','cad_files':'exterior/'+p['print_stl'],
 'notes':'Printed locating/cosmetic component, no arm load','status':'Mesh and bed checked; slicing/physical fit not qualified'})
extra=[('HW-COVER-PCB-REAR-M3',10,'ISO7380-1 M3x10, AF2, head D5.7x1.65'),('HW-COVER-PCB-REAR-NUT',10,'DIN934 M3 nut AF5.5 x2.4'),
 ('SHELF-STRAP',1,'20mm hook/loop strap, minimum600mm; trim to box after installation')]
for id,q,s in extra:rows.append({'id':id,'quantity':q,'category':'purchase','material':'steel' if id.startswith('HW') else 'textile','specification':s,'cad_files':'','notes':'Current model / confirmed box budget','status':'Supplier selection and first article fit required'})
rows.append({'id':'PCB-B06-IO', 'quantity':1,'category':'electronics','material':'FR4 1.6mm 4-layer','specification':'Native JLCEDA project + B06-IO-PROTOTYPE-Gerber.zip','cad_files':'../electronics/base-io-b05/manufacturing/b06-io-prototype/', 'notes':'Refer original BRI01 component list; BOM not automatically migrated by this script','status':'Board candidate; complete electrical assembly release pending'})
with (OUT/'B06-mechanical-bom.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
meta={'revision':M['revision'],'cad_manifest_sha256':hashlib.sha256((F/'manifest.json').read_bytes()).hexdigest(),
 'exterior_manifest_sha256':hashlib.sha256((OUT/'exterior/manifest.json').read_bytes()).hexdigest(),'line_count':len(rows),
 'not_included':['LED PCB, LED mounting hardware and light control wiring','Final external/internal Ethernet/GMSL/power/ground harness','Final external box electronics','Root motor and arm-root mating parts themselves'],
 'release':'Mechanical procurement planning only; NOT complete base BOM or order approval'}
(OUT/'B06-bom-provenance.json').write_text(json.dumps(meta,indent=2)+'\n');print('BOM',len(rows),'lines')
