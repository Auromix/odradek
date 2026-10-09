# SPDX-License-Identifier: CC-BY-NC-4.0
"""Source-linked plastic-fit package; exclude all supplier CAD."""
from pathlib import Path
import json,hashlib,zipfile
import numpy as np
import trimesh

HERE=Path(__file__).resolve().parent;OUT=HERE/'build';ROOT=HERE.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda name:json.loads((OUT/name).read_text())
D=read('manifest.json');digest=sha(OUT/'manifest.json');fit=read('fit-audit.json')
assert fit['manifest_sha256']==digest
assert len(D['parts'])==12 and not fit['overlaps']
assert len(fit['exact_checks'])==100 and len(fit['bearing_insertion_samples'])==8
assert fit['detachable_flange_overlap_mm3']<.05
for relative,expected in D['sources'].items():assert sha(ROOT/relative)==expected,relative
bed_checks=[]
for p in D['parts']:
 for folder,key,ext in [('step','step_sha256','.step'),('stl-object','object_stl_sha256','.stl'),('print-bed','print_stl_sha256','.stl')]:
  path=OUT/folder/(p['id']+ext);assert sha(path)==p[key]
 m=trimesh.load(OUT/'print-bed'/(p['id']+'.stl'),force='mesh')
 assert m.is_watertight and m.is_winding_consistent and m.volume>0 and len(m.split())==1
 assert np.min(m.bounds[0])>=-.0001 and np.max(m.extents)<240
 bed_checks.append(dict(id=p['id'],bed_mm=m.extents.tolist(),closed=True,components=1))
drawing=read('drawings/sources.json');assert drawing['manifest_sha256']==digest
for p in drawing['parts']:assert sha(OUT/'drawings'/(p['id']+'.svg'))==p['svg_sha256']
assert sha(OUT/'drawings/J7-axial-stack.svg')==drawing['stack_svg_sha256']
for name,native in [('native-public-audit.json',OUT/'A13-J7-plastic-fit.blend'),('native-actual-audit.json',ROOT/'work/arm-a13/j7-fit01/actual-RS00-fit.blend')]:
 r=read(name);assert r['native_sha256']==sha(native) and r['manifest_sha256']==digest
render=read('render-source.json');assert render['manifest_sha256']==digest
assert render['native_sha256']==read('native-actual-audit.json')['native_sha256']
package=OUT/'J7-FIT01-plastic-fit.zip'
files=[HERE/'README.md',OUT/'interface.json',OUT/'parts.csv',OUT/'fit-audit.json',OUT/'drawings/sources.json',
       OUT/'j7-assembled.png',OUT/'j7-exploded.png',OUT/'A13-J7-plastic-fit.blend']
for folder,glob in [('step','*.step'),('print-bed','*.stl'),('drawings','*.svg')]:files.extend(sorted((OUT/folder).glob(glob)))
# Explicit per-file ledger, included inside the package; manifest vertices
# are intentionally not needed by slicers and are omitted to keep it small.
ledger=OUT/'package-files.json';ledger.write_text(json.dumps(dict(manifest_sha256=digest,
 files=[dict(path=str(p.relative_to(HERE)),sha256=sha(p)) for p in files],
 status='supported unpowered plastic fit, measure coupons and inspect slicer before assembly'),indent=2)+'\n')
files.append(ledger)
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'J7-FIT01-plastic-fit/'+p.relative_to(HERE).as_posix())
with zipfile.ZipFile(package) as z:
 assert z.testzip() is None
 assert len(z.namelist())==40
 assert not any('vendor' in name or 'supplier' in name for name in z.namelist())
report=dict(package_sha256=sha(package),package_files=40,manifest_sha256=digest,
 print_mesh_checks=bed_checks,exact_local_checks=100,bearing_insertion_samples=8,
 actual_native_sha256=read('native-actual-audit.json')['native_sha256'],
 public_native_sha256=read('native-public-audit.json')['native_sha256'],
 complete_arm_print_release=False,physical_assembly_pass=False,load_3kg_qualified=False)
(OUT/'package-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print('PACKAGE',len(files),'files',package.stat().st_size,'bytes')
