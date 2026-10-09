# SPDX-License-Identifier: CC-BY-NC-4.0
from pathlib import Path
import bpy,json,hashlib,sys,math
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=HERE/'build';ACTUAL='--actual' in sys.argv
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();native=ROOT/'work/arm-a13/wrist-route01/actual-motors.blend' if ACTUAL else OUT/'A13-WRIST-ROUTE01.blend'
bpy.ops.wm.open_mainfile(filepath=str(native));D=json.loads((OUT/'integration-parts.json').read_text());assert bpy.context.scene['Integrated source SHA256']==sha(OUT/'integration-parts.json')
assert bpy.data.texts['WRIST_ROUTE01_README'].as_string()==(HERE/'README.md').read_text()
for id in ['P06-yaw-to-roll','B7-output-flange','J7-bearing-cage','J7-bearing-retainer','J7-inner-spacer','J7-inner-centre-spacer']:
 assert id not in bpy.data.objects
errs=[]
for p in D['new_parts']+D['hardware']+D['allocations']:
 o=bpy.data.objects[p['id']];assert o.parent.name==p['frame'];assert len(o.data.vertices)==len(p['vertices_mm'])
 e=max(abs(o.data.vertices[i].co[a]*1000-v[a]) for i,v in enumerate(p['vertices_mm']) for a in range(3));assert e<.001;errs.append(e)
 assert len(o.data.polygons)==len(p['triangles']);assert all(list(f.vertices)==p['triangles'][i] for i,f in enumerate(o.data.polygons));assert not o.modifiers
sup=[]
if ACTUAL:
 for p in json.loads((ROOT/'work/arm-a10/vendor/meshes.json').read_text()):
  o=bpy.data.objects[p['id']];assert o.parent.name==p['frame'];assert len(o.data.vertices)==len(p['vertices_mm'])
  e=max(abs(o.data.vertices[i].co[a]*1000-v[a]) for i,v in enumerate(p['vertices_mm']) for a in range(3));assert e<.001
  assert all(list(f.vertices)==p['triangles'][i] for i,f in enumerate(o.data.polygons));sup.append(dict(id=p['id'],max_error_mm=e))
 assert len(sup)==14
else:assert not any('supplier-' in o.name for o in bpy.context.scene.objects)
poses={n:c['q_deg'] for n,c in json.loads((OUT/'integration-review.json').read_text())['checks'].items()};checks=[]
for name,qs in poses.items():
 for j,q in zip(D['layout']['joints'],qs):o=bpy.data.objects[j['id']+'.rotor'];o['angle_deg']=q;o.update_tag()
 bpy.context.view_layer.update();T=Matrix.Translation((0,.075,.0346))@Matrix.Rotation(math.pi/2,4,'Z');errors=[]
 for j,q in zip(D['layout']['joints'],qs):
  T=T@Matrix.Translation(Vector(j['offset'])*.001);fixed=bpy.data.objects[j['id']+'.fixed'].matrix_world;errors.append(max(abs(fixed[a][b]-T[a][b]) for a in range(4) for b in range(4)))
  T=T@Matrix.Rotation(math.radians(q+j['zero_deg']),4,'XYZ'[j['axis'].index(1)]);rotor=bpy.data.objects[j['id']+'.rotor'].matrix_world;errors.append(max(abs(rotor[a][b]-T[a][b]) for a in range(4) for b in range(4)))
 assert max(errors)<2e-6;checks.append(dict(pose=name,max_frame_error=max(errors)))
assert not bpy.context.scene['3kg qualified'] and not bpy.context.scene['Dynamic harness released']
base=json.loads((ROOT/'engineering/arm_a12/wrist02/build/base-context.json').read_text());assert bpy.context.scene['A12 canonical base native SHA256']==base['base_native_sha256']
report=dict(native_sha256=sha(native),source_parts_sha256=sha(OUT/'integration-parts.json'),mesh_max_error_mm=max(errs),supplier_mesh_checks=sup,pose_fk_checks=checks,base_source_sha256=base['base_native_sha256'],source_readme_sha256=sha(HERE/'README.md'),qualified=False)
(OUT/('native-actual-audit.json' if ACTUAL else 'native-public-audit.json')).write_text(json.dumps(report,indent=2)+'\n');print('INTEGRATED_NATIVE_PASS',ACTUAL,len(sup),len(checks),flush=True)
