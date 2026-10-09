# SPDX-License-Identifier: CC-BY-NC-4.0
"""Compare every packaged viewer mesh to its evaluated native geometry."""
from pathlib import Path
import bpy,json,sys,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;ACTUAL='--actual' in sys.argv
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
data=json.loads((ROOT/('work/arm-a14/wrist-tail01/viewer-data-actual.json' if ACTUAL else 'work/arm-a14/wrist-tail01/viewer-data-public.json')).read_text())
native=ROOT/'work/arm-a14/wrist-tail01/actual-motors.blend' if ACTUAL else HERE/'build/A14-WRIST-TAIL01.blend'
assert data['long']['sha256']==sha(native)
bpy.ops.wm.open_mainfile(filepath=str(native));bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();checks=[]
for group,parts in [('long',data['long']['parts']),('base',data['base'])]:
 for p in parts:
  o=bpy.data.objects[p['id']];e=o.evaluated_get(dg);me=e.to_mesh();me.calc_loop_triangles();M=e.matrix_world
  if group=='long':M=bpy.data.objects['Arm_mount_B05' if p['frame']=='world' else p['frame']].matrix_world.inverted()@M
  v=np.array([list(M@x.co) for x in me.vertices])*1000
  assert len(v)==len(p['vertices']),(p['id'],len(v),len(p['vertices']))
  err=float(np.max(np.abs(v-np.array(p['vertices']))));assert err<.003,(p['id'],err)
  assert [list(x.vertices) for x in me.loop_triangles]==p['faces'],p['id']
  e.to_mesh_clear();checks.append(dict(id=p['id'],group=group,max_error_mm=err))
report=dict(native_sha256=sha(native),part_count=len(data['long']['parts']),base_mesh_count=len(data['base']),max_error_mm=max(x['max_error_mm'] for x in checks),checks=checks,production_release=False)
(HERE/'build'/('viewer-native-actual-audit.json' if ACTUAL else 'viewer-native-public-audit.json')).write_text(json.dumps(report,indent=2)+'\n')
print('VIEWER_NATIVE_MATCH',ACTUAL,report['part_count'],report['base_mesh_count'],report['max_error_mm'],flush=True)
