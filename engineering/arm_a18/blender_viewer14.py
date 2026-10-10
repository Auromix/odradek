# SPDX-License-Identifier: CC-BY-NC-4.0
"""Local-only actual-motor export from the exact current Blender assembly."""
from pathlib import Path
import json,hashlib,struct
import bpy
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];CACHE=ROOT/'work/arm-a18';CACHE.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=json.loads((HERE/'build/assembly12.json').read_text())
n=json.loads((HERE/'build/front-cowls10/native-audit.json').read_text())
native=ROOT/n['native_path'];assert sha(native)==n['native_sha256']
for path,h in a['source_sha256'].items():assert sha(ROOT/path)==h
bpy.ops.wm.open_mainfile(filepath=str(native),use_scripts=False)
def fingerprint(o):
    h=hashlib.sha256()
    for v in o.data.vertices:h.update(struct.pack('<3d',*(o.matrix_world@v.co)))
    for f in o.data.polygons:h.update(struct.pack('<'+str(len(f.vertices))+'I',*f.vertices))
    return h.hexdigest()
canonical=json.loads((ROOT/'engineering/arm_a16/build/native-modules-audit.json').read_text())['canonical_base_object_fingerprints']
assert all(fingerprint(bpy.data.objects[name])==h for name,h in canonical.items())
def mesh(o,world=False):
    o.data.calc_loop_triangles()
    color=list(o.data.materials[0].diffuse_color) if o.data.materials else [.08,.1,.12,1]
    return dict(id=o.name,role=o.get('role','canonical_base_reference'),
       vertices=[list((o.matrix_world@v.co if world else v.co)*1000) for v in o.data.vertices],
       faces=[list(t.vertices) for t in o.data.loop_triangles],color=color)
parts=[]
for row in a['parts']:
    o=bpy.data.objects[row['id']];expected='A16.root' if row['frame']=='world' else row['frame']
    assert o.parent.name==expected and tuple(o.scale)==(1,1,1),(row['id'],o.parent.name,expected,tuple(o.scale))
    p=mesh(o);p['frame']=row['frame'];p['role']=row['role'];parts.append(p)
motors=[o for o in bpy.data.objects if o.get('role')=='supplier_reference'];assert len(motors)==14
for o in motors:
    assert tuple(o.scale)==(1,1,1);p=mesh(o);p['frame']=o.parent.name;parts.append(p)
assert len(parts)==570
context=a['base_context'];base_manifest=ROOT.parent/'odradek'/context['base_sources']['manifest']['path']
base_ids={p['id'] for p in json.loads(base_manifest.read_text())['parts'] if p['category']!='environment'}
assert len(base_ids)==216 and base_ids.issubset(canonical)
data=dict(long=dict(layout=a['layout'],parts=parts,sha256=sha(native),flange_from_J7_mm=[110,0,0],
    shoulder_torque=a['physics']['sampled_abs_max_Nm'][1],known_conflicts=[]),base=[mesh(bpy.data.objects[name],True) for name in sorted(base_ids)])
path=CACHE/'actual-viewer14.json';path.write_text(json.dumps(data,separators=(',',':'))+'\n')
audit=dict(revision='A18-VIEWER14',data_path=str(path.relative_to(ROOT)),data_sha256=sha(path),
    native_sha256=sha(native),assembly_sha256=sha(HERE/'build/assembly12.json'),own_parts=556,supplier_partitions=14,
    base_product_meshes=216,canonical_world_meshes_unchanged=221,local_only_supplier_geometry=True,production_release=False)
(HERE/'build/viewer14-source-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print('A18_VIEWER_EXPORT_DONE',flush=True)
