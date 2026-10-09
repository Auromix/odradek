# SPDX-License-Identifier: CC-BY-NC-4.0
"""Reopen native assembly, compare actual motor meshes and all owned parts."""
from pathlib import Path
import bpy,json,sys,hashlib,math
from mathutils import Matrix

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=HERE/'build'
ACTUAL='--actual' in sys.argv
native=ROOT/'work/arm-a13/j7-fit01/actual-RS00-fit.blend' if ACTUAL else OUT/'A13-J7-plastic-fit.blend'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(native))
D=json.loads((OUT/'manifest.json').read_text())
assert bpy.context.scene['Owned manifest SHA256']==sha(OUT/'manifest.json')
assert not bpy.context.scene['Print release']
max_error=0
for p in D['parts']:
 o=bpy.data.objects[p['id']]
 assert len(o.data.vertices)==len(p['vertices_mm'])
 assert len(o.data.polygons)==len(p['triangles'])
 e=max(abs(float(o.data.vertices[k].co[a])*1000-v[a]) for k,v in enumerate(p['vertices_mm']) for a in range(3))
 assert e<.001;(max_error:=max(max_error,e))
 if p['frame']!='coupon':assert o.parent.name==p['frame']
suppliers=[]
if ACTUAL:
 source=ROOT/'work/arm-a10/vendor/meshes.json'
 assert bpy.context.scene['Supplier mesh cache SHA256']==sha(source)
 for p in json.loads(source.read_text()):
  if not p['id'].startswith('J7-supplier-'):continue
  o=bpy.data.objects[p['id']];assert o['Supplier source SHA256']==p['source_sha256']
  assert len(o.data.vertices)==len(p['vertices_mm'])
  e=max(abs(float(o.data.vertices[k].co[a])*1000-v[a]) for k,v in enumerate(p['vertices_mm']) for a in range(3))
  assert e<.001
  assert all(list(face.vertices)==p['triangles'][i] for i,face in enumerate(o.data.polygons))
  suppliers.append(dict(id=p['id'],max_vertex_error_mm=e,source_sha256=p['source_sha256']))
 assert len(suppliers)==2
else:
 assert not any('supplier-' in o.name for o in bpy.context.scene.objects)
 assert 'J7-motor-envelope' in bpy.data.objects
checks=[]
for q in [-90,-45,0,45,90]:
 rotor=bpy.data.objects['J7.rotor'];rotor['angle_deg']=q;rotor.update_tag();bpy.context.view_layer.update()
 expected=Matrix.Rotation(math.radians(q),4,'X')
 e=max(abs(rotor.matrix_world[a][b]-expected[a][b]) for a in range(4) for b in range(4));assert e<2e-6
 checks.append(dict(angle_deg=q,max_transform_error=e))
report=dict(native_sha256=sha(native),manifest_sha256=sha(OUT/'manifest.json'),
 owned_parts=12,max_owned_mesh_vertex_error_mm=max_error,supplier_groups=suppliers,
 roll_driver_checks=checks,scope='Native source agreement and local roll driver only; no manufacturing qualification')
(OUT/('native-actual-audit.json' if ACTUAL else 'native-public-audit.json')).write_text(json.dumps(report,indent=2)+'\n')
print('PASS NATIVE',ACTUAL,len(checks),'roll positions',len(suppliers),'exact supplier groups')
