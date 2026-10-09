# SPDX-License-Identifier: CC-BY-NC-4.0
from pathlib import Path
import bpy,json,hashlib,sys,math
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=HERE/'build';ACTUAL='--actual' in sys.argv
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
native=ROOT/'work/arm-a14/link-shell01/actual-motors.blend' if ACTUAL else OUT/'A14-LINK-SHELL01.blend'
bpy.ops.wm.open_mainfile(filepath=str(native));D=json.loads((OUT/'parts.json').read_text());scene=bpy.context.scene
assert scene['A14 parts SHA256']==sha(OUT/'parts.json')
errs=[]
for p in D['parts']:
 o=bpy.data.objects[p['id']];assert o.parent.name==p['frame'] and not o.modifiers
 assert len(o.data.vertices)==len(p['vertices_mm']) and len(o.data.polygons)==len(p['triangles'])
 e=max(abs(o.data.vertices[i].co[a]*1000-v[a]) for i,v in enumerate(p['vertices_mm']) for a in range(3));assert e<.001;errs.append(e)
 assert all(list(f.vertices)==p['triangles'][i] for i,f in enumerate(o.data.polygons))
for n in D['replaces']+['A12-W13-J3-rotor-lip','A12-W14-J4-rotor-lip']:assert n not in bpy.data.objects
sup=[]
if ACTUAL:
 for p in json.loads((ROOT/'work/arm-a10/vendor/meshes.json').read_text()):
  o=bpy.data.objects[p['id']];assert o.parent.name==p['frame'];assert len(o.data.vertices)==len(p['vertices_mm'])
  e=max(abs(o.data.vertices[i].co[a]*1000-v[a]) for i,v in enumerate(p['vertices_mm']) for a in range(3));assert e<.001
  assert all(list(f.vertices)==p['triangles'][i] for i,f in enumerate(o.data.polygons));sup.append(dict(id=p['id'],max_error_mm=e))
 assert len(sup)==14
else:assert not any('supplier-' in o.name for o in scene.objects)
checks=[]
for name,q in D['layout']['poses'].items():
 for j,angle in zip(D['layout']['joints'],q):o=bpy.data.objects[j['id']+'.rotor'];o['angle_deg']=angle;o.update_tag()
 bpy.context.view_layer.update();T=Matrix.Translation((0,.075,.0346))@Matrix.Rotation(math.pi/2,4,'Z');errors=[]
 for j,angle in zip(D['layout']['joints'],q):
  T=T@Matrix.Translation(Vector(j['offset'])*.001);o=bpy.data.objects[j['id']+'.fixed'];errors.append(max(abs(o.matrix_world[a][b]-T[a][b]) for a in range(4) for b in range(4)))
  T=T@Matrix.Rotation(math.radians(angle+j['zero_deg']),4,'XYZ'[j['axis'].index(1)]);o=bpy.data.objects[j['id']+'.rotor'];errors.append(max(abs(o.matrix_world[a][b]-T[a][b]) for a in range(4) for b in range(4)))
 assert max(errors)<2e-6;checks.append(dict(name=name,max_frame_error=max(errors)))
assert not scene['3kg qualified'] and not scene['Dynamic harness released'] and not scene['A14 motor selection frozen']
base=json.loads((ROOT/'engineering/arm_a12/wrist02/build/base-context.json').read_text());assert scene['A12 canonical base native SHA256']==base['base_native_sha256']
report=dict(native_sha256=sha(native),parts_source_sha256=sha(OUT/'parts.json'),mesh_max_error_mm=max(errs),supplier_mesh_checks=sup,pose_checks=checks,base_source_sha256=base['base_native_sha256'],qualified=False)
(OUT/('native-actual-audit.json' if ACTUAL else 'native-public-audit.json')).write_text(json.dumps(report,indent=2)+'\n');print('NATIVE_PASS',ACTUAL,len(sup),len(checks),flush=True)
