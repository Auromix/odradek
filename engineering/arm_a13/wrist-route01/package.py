# SPDX-License-Identifier: CC-BY-NC-4.0
"""Current J7/interface fit bundle; replacement carrier, not full-arm release."""
from pathlib import Path
import json,hashlib,shutil,zipfile,csv,xml.etree.ElementTree as ET
import trimesh,numpy as np
HERE=Path(__file__).parent;OUT=HERE/'build';ROOT=HERE.resolve().parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
review=json.loads((OUT/'integration-review.json').read_text());assert review['all_sampled_owned_geometry_clear'] and review['hardware_box_screen_clear'];assert len(review['checks'])==73
assert len(review['direct_chord_probes'])==7 and all(p['obstacle_hits'] for p in review['direct_chord_probes'])
for name,h in review['source_hashes'].items():assert sha(ROOT/name)==h
parts=json.loads((OUT/'integration-parts.json').read_text())['new_parts'];assert len(parts)==11
old=HERE.parent/'tool-if02/build';ifparts=json.loads((old/'manifest.json').read_text())['parts'];parts+= [p for p in ifparts if p['role']=='fit_coupon'];assert len(parts)==14
files=[HERE/'README.md']+[HERE/p for p in ['carrier.py','review.py','blender.py','audit_native.py','drawings.py','viewer.py','package.py']]
files+=[OUT/p for p in ['carrier-manifest.json','integration-parts.json','integration-before.json','integration-review.json','native-public-audit.json','native-actual-audit.json','render-source.json','viewer-audit.json','A13-WRIST-ROUTE01.blend','whole-integrated.png','wrist-integrated.png']]
# Current exported parts remain independent of supplier geometry.
rows=[]
for p in parts:
 id=p['id'];base=OUT if id.startswith('A13-J7-108') else (HERE.parent/'j7-fit01/build' if id.startswith('A13-J7-') else (HERE.parent/'tool-if01/build' if id.startswith('A13-IF-107') else old))
 for folder,ext,key in [('step','.step','step_sha256'),('print-bed','.stl','print_stl_sha256')]:
  src=base/folder/(id+ext);assert sha(src)==p[key]
  dst=OUT/folder/src.name
  if src!=dst:shutil.copyfile(src,dst)
  files.append(dst)
 mesh=trimesh.load(OUT/'print-bed'/(id+'.stl'),force='mesh');assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
 assert len(trimesh.graph.connected_components(mesh.face_adjacency,nodes=np.arange(len(mesh.faces)),engine='scipy'))==1
 assert min(mesh.bounds[0])>=-.0001 and max(mesh.extents)<230
 rows.append([id,p['frame'],p['role'],*mesh.extents,sha(OUT/'step'/(id+'.step')),sha(OUT/'print-bed'/(id+'.stl'))])
with (OUT/'parts.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['id','frame','role','bed_x_mm','bed_y_mm','bed_z_mm','step_sha256','print_stl_sha256']);w.writerows(rows)
files.append(OUT/'parts.csv')
# Current instructions + historic reference instructions explicitly subordinate to108 replacement.
contexts=[(HERE.parent/'j7-fit01/README.md','core-assembly.md'),(HERE.parent/'tool-if02/README.md','interface-assembly.md'),(old/'interface.json','interface.json'),(old/'interface-hardware.csv','interface-hardware.csv')]
for src,name in contexts:
 dst=OUT/'assembly'/name;dst.parent.mkdir(exist_ok=True);shutil.copyfile(src,dst);files.append(dst)
(OUT/'assembly/READ-FIRST.md').write_text('本包只发布J7核心与端面接口的受支撑、无载、不通电试配。108替换旧105，旧装配文字中所有105均按108理解。不得叠装。106与201—204不在本包；不要从历史包混装。整臂Blender是上下文，不是整臂打印发布。相机端接、供电/控制针脚和动态线束仍未冻结。\n')
files.append(OUT/'assembly/READ-FIRST.md')
for src in [OUT/'drawings/A13-J7-108-yaw-clearance-carrier.svg',OUT/'drawings/sources.json']:
 if src.suffix=='.svg':ET.parse(src)
 files.append(src)
# Include unchanged assembly-part CAD projections, excluding superseded105/106.
for p in parts:
 if p['role']=='fit_coupon' or p['id'].startswith('A13-J7-108'):continue
 base=HERE.parent/'j7-fit01/build' if p['id'].startswith('A13-J7-') else (HERE.parent/'tool-if01/build' if p['id'].startswith('A13-IF-107') else old)
 src=base/'drawings'/(p['id']+'.svg');assert src.exists();dst=OUT/'drawings'/src.name;shutil.copyfile(src,dst);dst.write_text('\n'.join(line.rstrip() for line in dst.read_text().splitlines())+'\n');files.append(dst)
# Render and native reports are bound to final native/source metadata.
for report,native in [('native-public-audit.json',OUT/'A13-WRIST-ROUTE01.blend'),('native-actual-audit.json',ROOT/'work/arm-a13/wrist-route01/actual-motors.blend')]:
 r=json.loads((OUT/report).read_text());assert r['native_sha256']==sha(native) and r['source_parts_sha256']==sha(OUT/'integration-parts.json')
r=json.loads((OUT/'render-source.json').read_text());assert r['native_sha256']==sha(ROOT/'work/arm-a13/wrist-route01/actual-motors.blend')
for name,h in r['images'].items():assert sha(OUT/name)==h
assert len(files)==len(set(files))
ledger=OUT/'package-files.json';ledger.write_text(json.dumps(dict(revision='WRIST-ROUTE01',files=[dict(path=p.relative_to(HERE).as_posix(),sha256=sha(p)) for p in files],full_arm_release=False,dynamic_harness_pass=False,physical_trial_pass=False),indent=2)+'\n');files.append(ledger)
package=OUT/'WRIST-ROUTE01-fit.zip'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'WRIST-ROUTE01-fit/'+p.relative_to(HERE).as_posix())
with zipfile.ZipFile(package) as z:
 assert z.testzip() is None
 assert sum(n.endswith('.step') for n in z.namelist())==14 and sum(n.endswith('.stl') for n in z.namelist())==14
 assert not any('105-carrier' in n or 'vendor/' in n or 'actual-motors' in n for n in z.namelist())
 for item in json.loads(z.read('WRIST-ROUTE01-fit/build/package-files.json'))['files']:
  assert hashlib.sha256(z.read('WRIST-ROUTE01-fit/'+item['path'])).hexdigest()==item['sha256']
(OUT/'package-audit.json').write_text(json.dumps(dict(package_sha256=sha(package),archive_crc_pass=True,ledger_pass=True,print_parts=14,assembly_parts=11,coupons=3,integrated_sampled_poses=73,dynamic_harness_pass=False,full_arm_release=False,load_3kg_pass=False),indent=2)+'\n')
print('PACKAGE_PASS',len(files),package.stat().st_size,'bytes')
