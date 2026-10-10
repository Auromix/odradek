# SPDX-License-Identifier: CC-BY-NC-4.0
"""Local-only viewer export from current actual native assembly."""
from pathlib import Path
import json,hashlib,struct
import bpy
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/assembly25';CACHE=ROOT/'work/arm-a19'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=json.loads((OUT/'manifest.json').read_text());n=json.loads((OUT/'native-audit26.json').read_text());native=ROOT/n['native_path'];assert sha(native)==n['native_sha256'] and n['assembly_sha256']==sha(OUT/'manifest.json')
for path,h in a['source_manifests_sha256'].items():assert sha(ROOT/path)==h
for p in a['parts']:assert sha(ROOT/p['step_path'])==p['step_sha256']
bpy.ops.wm.open_mainfile(filepath=str(native),use_scripts=False)
def fingerprint(o):
    h=hashlib.sha256()
    for v in o.data.vertices:h.update(struct.pack('<3d',*(o.matrix_world@v.co)))
    for f in o.data.polygons:h.update(struct.pack('<'+str(len(f.vertices))+'I',*f.vertices))
    return h.hexdigest()
canonical=json.loads((ROOT/'engineering/arm_a16/build/native-modules-audit.json').read_text())['canonical_base_object_fingerprints'];assert all(fingerprint(bpy.data.objects[name])==h for name,h in canonical.items())
def mesh(o,world=False):
    o.data.calc_loop_triangles();color=list(o.data.materials[0].diffuse_color) if o.data.materials else [.08,.1,.12,1]
    return dict(id=o.name,role=o.get('role','canonical_base_reference'),vertices=[list((o.matrix_world@v.co if world else v.co)*1000) for v in o.data.vertices],faces=[list(t.vertices) for t in o.data.loop_triangles],color=color)
parts=[]
for row in a['parts']:
    o=bpy.data.objects[row['id']];expected='A16.root' if row['frame']=='world' else row['frame'];assert o.parent.name==expected and tuple(o.scale)==(1,1,1)
    p=mesh(o);p['frame']=row['frame'];p['role']=row['role'];parts.append(p)
motors=[o for o in bpy.data.objects if o.get('role')=='supplier_reference'];assert len(motors)==14
for o in motors:
    assert tuple(o.scale)==(1,1,1);p=mesh(o);p['frame']=o.parent.name;parts.append(p)
context=a['base_context'];base_manifest=ROOT.parent/'odradek'/context['base_sources']['manifest']['path'];base_ids={p['id'] for p in json.loads(base_manifest.read_text())['parts'] if p['category']!='environment'};assert len(base_ids)==216 and base_ids.issubset(canonical)
data=dict(long=dict(layout=a['layout'],parts=parts,sha256=sha(native),flange_from_J7_mm=[110,0,0],shoulder_torque=a['sampled_max_abs_Nm'][1],known_conflicts=[]),base=[mesh(bpy.data.objects[name],True) for name in sorted(base_ids)])
path=CACHE/'actual-viewer30.json';path.write_text(json.dumps(data,separators=(',',':'))+'\n')
audit=dict(revision='A19-VIEWER30',data_path=str(path.relative_to(ROOT)),data_sha256=sha(path),native_sha256=sha(native),assembly_sha256=sha(OUT/'manifest.json'),own_parts=len(a['parts']),supplier_partitions=14,base_product_meshes=216,canonical_world_meshes_unchanged=221,local_only_supplier_geometry=True,production_release=False)
(OUT/'viewer30-source-audit.json').write_text(json.dumps(audit,indent=2)+'\n');print('VIEWER30_EXPORT_DONE',flush=True)
