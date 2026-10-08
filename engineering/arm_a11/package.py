# SPDX-License-Identifier: CC-BY-NC-4.0
"""Source-bound original print prototype archive; excludes all supplier CAD."""
from pathlib import Path
import json,hashlib,zipfile
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'engineering/arm_a11/build';sha=hashlib.sha256((OUT/'manifest.json').read_bytes()).hexdigest()
reports=['print-audit.json','feasibility.json','collision-supplier.json','motion-audit.json','tool-access-audit.json','blender-audit.json','blender-audit-actual.json','base-context-audit.json']
for filename in reports:assert json.loads((OUT/filename).read_text())['manifest_sha256']==sha,filename
P=json.loads((OUT/'print-audit.json').read_text());assert P['print_files']==51 and P['assembly_prints']==35
C=json.loads((OUT/'collision-supplier.json').read_text());assert all(not p['overlaps'] for p in C['checks'].values())
M=json.loads((OUT/'motion-audit.json').read_text());assert len(M['path_samples'])==22 and all(not p['overlaps'] for p in M['path_samples'])
T=json.loads((OUT/'tool-access-audit.json').read_text());assert len(T['checks'])==119 and all(not p['overlaps'] for p in T['checks'])
for p in P['parts']:assert hashlib.sha256((OUT/p['path']).read_bytes()).hexdigest()==p['sha256']
name='odradek-a11-long-supported-fit';archive=OUT/(name+'.zip');D=json.loads((OUT/'manifest.json').read_text())
files=[OUT/f for f in reports+['manifest.json','parts.json','metadata-correction.json','render-source.json','hardware-BOM.csv','assembly-guide.md','print-README.md','odradek-a11-long-validation.blend']]+list((OUT/'print-ready').glob('*.stl'))+list((OUT/'drawings').glob('*'))+[OUT/'step'/(p['id']+'.step') for p in D['parts'] if p['role'] in ['printed_structure','printed_cover','fit_coupon']]
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for f in files:z.write(f,name+'/'+f.relative_to(OUT).as_posix())
 z.write(ROOT/'docs/viewers/arm-body-a11/index.html',name+'/viewer/index.html')
 z.write(ROOT/'docs/viewers/arm-body-a11/THREE-LICENSE.txt',name+'/viewer/THREE-LICENSE.txt')
 z.write(ROOT/'docs/engineering/arm-body-a11-validation.md',name+'/VALIDATION.md')
 z.write(ROOT/'engineering/arm_a11/context-source.json',name+'/context-source.json')
 z.write(ROOT/'LICENSE',name+'/LICENSE')
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 assert len([p for p in z.namelist() if p.endswith('.stl')])==51
 assert all(p.startswith(name+'/') for p in z.namelist())
 (OUT/'archive-audit.json').write_text(json.dumps(dict(manifest_sha256=sha,archive=archive.name,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=len(z.namelist()),print_stls=51,crc_pass=True,supplier_cad_included=False),indent=2)+'\n')
print('A11_PACKAGE',archive.stat().st_size,flush=True)
