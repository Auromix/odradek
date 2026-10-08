# SPDX-License-Identifier: CC-BY-NC-4.0
"""Reopen native, prove new original meshes and retained motor/rig sources."""
from pathlib import Path
import json,hashlib,bpy,numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent/'build'
D=json.loads((OUT/'manifest.json').read_text());sha=hashlib.sha256((OUT/'manifest.json').read_bytes()).hexdigest()
scene=bpy.context.scene;assert scene['A12 source manifest SHA256']==sha
errors=[]
for p in D['parts']:
 o=bpy.data.objects[p['id']];assert o.parent.name==p['frame'];assert o['Source STEP SHA256']==p['step_sha256']
 vertices=np.array([list(v.co) for v in o.data.vertices])*1000;expected=np.array(p['vertices_mm']);assert vertices.shape==expected.shape
 errors.append(float(np.max(abs(vertices-expected))))
assert max(errors)<.00005
for id in D['replaced_parts']:assert id not in bpy.data.objects
drivers=[]
for i in range(1,8):
 o=bpy.data.objects[f'J{i}.rotor'];assert o.animation_data and len(o.animation_data.drivers)==1;drivers.append(o.name)
actual=bool(scene['Official motor CAD imported'])
suppliers=[o for o in bpy.data.objects if o.name.endswith(('supplier-stator','supplier-external-output'))]
assert len(suppliers)==(14 if actual else 0)
if actual:
 data=json.loads((ROOT/'work/arm-a10/vendor/meshes.json').read_text())
 for p in data:
  o=bpy.data.objects[p['id']];assert o['Source SHA256']==p['source_sha256'] and o.parent.name==p['frame']
  errors.append(float(np.max(abs(np.array([list(v.co) for v in o.data.vertices])*1000-np.array(p['vertices_mm'])))))
 assert max(errors)<.00005
report=dict(manifest_sha256=sha,reopened_file=bpy.data.filepath.split('/')[-1],new_shields=2,driven_axes=len(drivers),official_supplier_groups=len(suppliers),max_local_mesh_error_mm=max(errors),base_native_sha256=scene['A12 canonical base native SHA256'],scope='Reopened new mesh/source/parent checks. No new full-domain or load proof.')
(OUT/('native-actual-audit.json' if actual else 'native-public-audit.json')).write_text(json.dumps(report,indent=2)+'\n')
print('A12_NATIVE_AUDIT',report,flush=True)
