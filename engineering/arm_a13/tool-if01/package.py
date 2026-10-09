# SPDX-License-Identifier: CC-BY-NC-4.0
from pathlib import Path
import json,hashlib,shutil,zipfile,xml.etree.ElementTree as ET
import trimesh
HERE=Path(__file__).resolve().parent;OUT=HERE/'build';ROOT=HERE.parents[2];PREV=HERE.parent/'j7-fit01/build'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
D=json.loads((OUT/'manifest.json').read_text());digest=sha(OUT/'manifest.json');audit=json.loads((OUT/'fit-audit.json').read_text())
assert not audit['overlaps'] and audit['manifest_sha256']==digest
assert len(audit['checks'])==359
for rel,h in D['source_hashes'].items():assert sha(ROOT/rel)==h
for p in D['parts']:
 for folder,ext,key in [('step','.step','step_sha256'),('stl-object','.stl','object_stl_sha256'),('print-bed','.stl','print_stl_sha256')]:assert sha(OUT/folder/(p['id']+ext))==p[key]
 m=trimesh.load(OUT/'print-bed'/(p['id']+'.stl'),force='mesh');assert m.is_watertight and m.is_winding_consistent and m.volume>0 and len(m.split())==1
 assert min(m.bounds[0])>=-.0001 and max(m.extents)<230
for path in (OUT/'drawings').glob('*.svg'):ET.parse(path)
drawing=json.loads((OUT/'drawings/sources.json').read_text());assert drawing['manifest_sha256']==digest
for p in drawing['parts']:assert sha(OUT/'drawings'/(p['id']+'.svg'))==p['svg_sha256']
assert sha(OUT/'drawings/port-map.svg')==drawing['port_map_svg_sha256']
for name,native in [('native-public-audit.json',OUT/'A13-TOOL-IF01.blend'),('native-actual-audit.json',ROOT/'work/arm-a13/tool-if01/actual-RS00-tool-interface.blend')]:
 r=json.loads((OUT/name).read_text());assert r['manifest_sha256']==digest and r['native_sha256']==sha(native)
render=json.loads((OUT/'render-source.json').read_text());assert render['manifest_sha256']==digest
assert render['native_sha256']==sha(ROOT/'work/arm-a13/tool-if01/actual-RS00-tool-interface.blend')
files=[HERE/'README.md',OUT/'interface.json',OUT/'parts.csv',OUT/'manifest.json',OUT/'fit-audit.json',OUT/'drawings/sources.json',OUT/'A13-TOOL-IF01.blend',OUT/'native-public-audit.json',OUT/'native-actual-audit.json',OUT/'render-source.json']
for folder,glob in [('step','*.step'),('print-bed','*.stl'),('drawings','*.svg')]:files.extend(sorted((OUT/folder).glob(glob)))
files.extend(sorted(OUT.glob('*.png')))
inherited=[]
old=json.loads((PREV/'manifest.json').read_text())
for p in old['parts']:
 if p['role']=='fit_coupon' or p['id']=='A13-J7-106-detachable-flange':continue
 for source_folder,new_folder,ext,key in [('step','inherited-step','.step','step_sha256'),('print-bed','inherited-print-bed','.stl','print_stl_sha256')]:
  src=PREV/source_folder/(p['id']+ext);assert sha(src)==p[key]
  dst=OUT/new_folder/src.name;dst.parent.mkdir(exist_ok=True);shutil.copyfile(src,dst);files.append(dst)
  inherited.append(dict(path=str(dst.relative_to(HERE)),sha256=sha(dst),source=str(src.relative_to(ROOT))))
assert len(inherited)==10
ledger=OUT/'package-files.json';ledger.write_text(json.dumps(dict(manifest_sha256=digest,files=[dict(path=str(p.relative_to(HERE)),sha256=sha(p)) for p in files],
 inherited=inherited,connector_space_only=True,electrical_release=False),indent=2)+'\n');files.append(ledger)
package=OUT/'TOOL-IF01-plastic-fit.zip'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'TOOL-IF01-plastic-fit/'+p.relative_to(HERE).as_posix())
with zipfile.ZipFile(package) as z:
 assert z.testzip() is None
 assert not any('vendor' in n or 'actual-RS00' in n for n in z.namelist())
report=dict(manifest_sha256=digest,package_sha256=sha(package),package_files=len(files),new_print_files=8,inherited_print_files=5,
 exact_local_checks=len(audit['checks']),physical_trial_pass=False,exact_connector_retention=False,dynamic_harness_pass=False,
 complete_arm_print_release=False,load_3kg_pass=False)
(OUT/'package-audit.json').write_text(json.dumps(report,indent=2)+'\n');print('PACKAGE',len(files),package.stat().st_size,'bytes')
