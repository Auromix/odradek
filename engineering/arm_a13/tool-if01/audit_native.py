# SPDX-License-Identifier: CC-BY-NC-4.0
from pathlib import Path
import bpy,json,hashlib,sys,math
from mathutils import Matrix
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=HERE/'build';ACTUAL='--actual' in sys.argv
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
native=ROOT/'work/arm-a13/tool-if01/actual-RS00-tool-interface.blend' if ACTUAL else OUT/'A13-TOOL-IF01.blend'
bpy.ops.wm.open_mainfile(filepath=str(native));D=json.loads((OUT/'manifest.json').read_text())
assert bpy.context.scene['Tool interface manifest SHA256']==sha(OUT/'manifest.json')
assert D['replaces'] not in bpy.data.objects
errors=[]
for p in D['parts']+D['allocations']+D['hardware']:
 o=bpy.data.objects[p['id']];assert o.parent.name=='J7.rotor'
 assert len(o.data.vertices)==len(p['vertices_mm']) and len(o.data.polygons)==len(p['triangles'])
 e=max(abs(float(o.data.vertices[k].co[a])*1000-v[a]) for k,v in enumerate(p['vertices_mm']) for a in range(3));assert e<.001;errors.append(e)
source=ROOT/'work/arm-a10/vendor/meshes.json';suppliers=[]
if ACTUAL:
 for p in json.loads(source.read_text()):
  if not p['id'].startswith('J7-supplier-'):continue
  o=bpy.data.objects[p['id']];assert len(o.data.vertices)==len(p['vertices_mm'])
  e=max(abs(float(o.data.vertices[k].co[a])*1000-v[a]) for k,v in enumerate(p['vertices_mm']) for a in range(3));assert e<.001
  assert all(list(face.vertices)==p['triangles'][i] for i,face in enumerate(o.data.polygons))
  suppliers.append(dict(id=p['id'],vertex_error_mm=e))
 assert len(suppliers)==2
else:assert not any('supplier-' in o.name for o in bpy.context.scene.objects)
angles=[]
for q in [-90,-45,0,45,90]:
 o=bpy.data.objects['J7.rotor'];o['angle_deg']=q;o.update_tag();bpy.context.view_layer.update();target=Matrix.Rotation(math.radians(q),4,'X')
 e=max(abs(o.matrix_world[a][b]-target[a][b]) for a in range(4) for b in range(4));assert e<2e-6;angles.append(dict(q=q,error=e))
r=dict(native_sha256=sha(native),manifest_sha256=sha(OUT/'manifest.json'),supplier_mesh_checks=suppliers,new_owned_print_parts=8,
 connector_allocation_blocks=4,maximum_owned_mesh_error_mm=max(errors),roll_checks=angles,scope='Native agreement and local roll; no actual connector or wiring qualification')
(OUT/('native-actual-audit.json' if ACTUAL else 'native-public-audit.json')).write_text(json.dumps(r,indent=2)+'\n')
print('NATIVE_PASS',ACTUAL,len(suppliers),len(angles))
