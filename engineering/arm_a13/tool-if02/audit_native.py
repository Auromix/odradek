# SPDX-License-Identifier: CC-BY-NC-4.0
from pathlib import Path
import bpy,json,hashlib,sys,math
from mathutils import Matrix
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=HERE/'build';ACTUAL='--actual' in sys.argv
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
native=ROOT/'work/arm-a13/tool-if02/actual-RS00-recessed-interface.blend' if ACTUAL else OUT/'A13-TOOL-IF02.blend'
bpy.ops.wm.open_mainfile(filepath=str(native));D=json.loads((OUT/'manifest.json').read_text())
assert bpy.context.scene['Tool interface manifest SHA256']==sha(OUT/'manifest.json')
assert bpy.data.texts['TOOL_IF02_READ_FIRST'].as_string()==(HERE/'README.md').read_text()
assert not any(o.name.startswith(('A13-IF-201','A13-IF-202','A13-IF-203','A13-IF-204','IF-')) for o in bpy.context.scene.objects)
errors=[]
for p in D['parts']+D['hardware']+D['allocations']:
 o=bpy.data.objects[p['id']];assert o.parent.name=='J7.rotor'
 assert len(o.data.vertices)==len(p['vertices_mm']) and len(o.data.polygons)==len(p['triangles'])
 e=max(abs(float(o.data.vertices[k].co[a])*1000-v[a]) for k,v in enumerate(p['vertices_mm']) for a in range(3));assert e<.001;errors.append(e)
 assert all(list(f.vertices)==p['triangles'][i] for i,f in enumerate(o.data.polygons))
 assert not any(m.type=='BOOLEAN' for m in o.modifiers),o.name
suppliers=[]
if ACTUAL:
 for p in json.loads((ROOT/'work/arm-a10/vendor/meshes.json').read_text()):
  if not p['id'].startswith('J7-supplier-'):continue
  o=bpy.data.objects[p['id']];assert len(o.data.vertices)==len(p['vertices_mm'])
  e=max(abs(float(o.data.vertices[k].co[a])*1000-v[a]) for k,v in enumerate(p['vertices_mm']) for a in range(3));assert e<.001
  assert all(list(f.vertices)==p['triangles'][i] for i,f in enumerate(o.data.polygons));suppliers.append(dict(id=p['id'],maximum_error_mm=e))
 assert len(suppliers)==2
else:assert not any('supplier-' in o.name for o in bpy.context.scene.objects)
angles=[]
for q in [-90,-45,0,45,90]:
 o=bpy.data.objects['J7.rotor'];o['angle_deg']=q;o.update_tag();bpy.context.view_layer.update();M=Matrix.Rotation(math.radians(q),4,'X')
 e=max(abs(o.matrix_world[a][b]-M[a][b]) for a in range(4) for b in range(4));assert e<2e-6;angles.append(dict(q=q,error=e))
r=dict(native_sha256=sha(native),manifest_sha256=sha(OUT/'manifest.json'),new_print_parts=len(D['parts']),connector_boxes=len(D['allocations']),
 maximum_owned_mesh_error_mm=max(errors),supplier_checks=suppliers,roll_checks=angles,section_modifiers_saved=False,scope='Native/CAD agreement; no whole arm or real connector qualification')
(OUT/('native-actual-audit.json' if ACTUAL else 'native-public-audit.json')).write_text(json.dumps(r,indent=2)+'\n');print('NATIVE_PASS',ACTUAL,flush=True)
