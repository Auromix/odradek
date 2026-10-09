# SPDX-License-Identifier: CC-BY-NC-4.0
"""Package five cover candidates only, with hashes and units, no load release."""
from pathlib import Path
import json,hashlib,zipfile,csv,io
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=HERE/'build'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
D=json.loads((OUT/'parts.json').read_text());G=json.loads((OUT/'geometry-review.json').read_text());assert G['sampled_geometry_clear'] and not G['production_release']
files={};rows=[]
for p in D['parts']:
 step=ROOT/p['source_step_path'];folder=step.parent.parent
 for kind,source,expected in [('step',step,p['step_sha256']),('stl-object',folder/'stl-object'/(p['id']+'.stl'),p['stl_sha256']),('print-bed',folder/'print-bed'/(p['id']+'.stl'),p['print_bed_sha256'])]:
  assert sha(source)==expected;files[kind+'/'+source.name]=source
 rows.append([p['id'],1,p['frame'],p['role'],p['mass_kg_uniform_PETG'],p['solid_count']])
buf=io.StringIO();w=csv.writer(buf);w.writerow(['part_id','quantity','assembly_frame','role','mass_kg_uniform_PETG_assumption','solid_count']);w.writerows(rows)
note='A14 five cover candidates / supported, unpowered, no-load fit study only.\nAll STEP/STL dimensions are millimetres. STL has no embedded unit metadata.\nprint-bed files are transformed for placement; never use their coordinates as assembly datums.\nThis is an incremental cover package, not an entire arm or a production release.\nCurrent motors are NOT qualified for3kg continuous holding. No dynamic harness, material, slicer, tolerances or metal frame release.\nRead MODULE-README.md and LINK-SHELL-README.md before printing or assembly.\n'
for name,source in [('MODULE-README.md',HERE/'README.md'),('LINK-SHELL-README.md',ROOT/'engineering/arm_a14/link-shell01/README.md'),('parts.json',OUT/'parts.json'),('geometry-review.json',OUT/'geometry-review.json')]:files[name]=source
for name in ['attention','idle','reference']:files['build/'+name+'.png']=OUT/(name+'.png')
old=json.loads((ROOT/'engineering/arm_a11/build/manifest.json').read_text());wrist=json.loads((ROOT/'engineering/arm_a12/wrist02/build/manifest.json').read_text())
ids=set(D['retained_hardware'])|{x for x in wrist['retained_hardware'] if x.startswith('J6-armour-')}
hardware=io.StringIO();hw=csv.writer(hardware);hw.writerow(['part_id','quantity','assembly_frame','nominal_material_description','fit_note_not_production_release'])
for p in old['parts']:
 if p['id'] in ids:hw.writerow([p['id'],1,p['frame'],p['material'],p['note']])
assert len(ids)==32
path=OUT/'A14-five-covers-supported-fit.zip'
with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
 for name,source in files.items():z.write(source,name)
 z.writestr('START-HERE.txt',note);z.writestr('parts.csv',buf.getvalue());z.writestr('retained-hardware.csv',hardware.getvalue());z.writestr('SHA256SUMS.txt',''.join(f'{sha(source)}  {name}\n' for name,source in sorted(files.items())))
with zipfile.ZipFile(path) as z:
 assert z.testzip() is None
 for name,source in files.items():assert hashlib.sha256(z.read(name)).hexdigest()==sha(source)
report=dict(archive_sha256=sha(path),file_count=len(files)+4,cover_count=5,retained_nominal_hardware_entries=32,units='mm;STL unit assumption explicit',production_release=False)
(OUT/'package-audit.json').write_text(json.dumps(report,indent=2)+'\n');print('PACKAGE_PASS',report)
