# SPDX-License-Identifier: CC-BY-NC-4.0
"""Publish only own body/base meshes, never exact supplier actuator geometry."""
from pathlib import Path
import hashlib,json,struct
import bpy

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'engineering/arm_a16/build';DEST=ROOT/'manufacturing/selected/arm-body-a16-fit'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
n=json.loads((OUT/'native-modules-audit.json').read_text());source=ROOT/n['native_path'];assert sha(source)==n['native_sha256']
bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
def fingerprint(o):
    h=hashlib.sha256()
    for v in o.data.vertices:h.update(struct.pack('<3d',*((o.matrix_world@v.co))))
    for f in o.data.polygons:h.update(struct.pack('<'+str(len(f.vertices))+'I',*f.vertices))
    return h.hexdigest()
removed=[]
for o in list(bpy.data.objects):
    if o.get('role')=='supplier_reference':
        me=o.data;removed.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
        if me.users==0:bpy.data.meshes.remove(me)
assert len(removed)==14
assert not any('supplier-' in m.name for m in bpy.data.meshes)
assert not any(o.get('role')=='supplier_reference' for o in bpy.data.objects)
for name,digest in n['canonical_base_object_fingerprints'].items():assert fingerprint(bpy.data.objects[name])==digest
own=[o for o in bpy.data.objects if o.type=='MESH' and o.name not in n['canonical_base_object_fingerprints']]
assert len(own)==n['own_part_count']==541
bpy.context.scene['Supplier geometry']='Excluded from public native. Rebuild private native from pinned source files for actual motor fit review.'
bpy.context.scene['Manufacturing scope']='Own CAD print/fit only; no production, payload, metal or dynamic harness release.'
DEST.mkdir(parents=True,exist_ok=True);path=DEST/'A16-body-own-parts.blend';bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
report=dict(layout=n['layout'],source_private_native_sha256=n['native_sha256'],own_meshes=len(own),canonical_base_meshes=len(n['canonical_base_object_fingerprints']),canonical_world_geometry_unchanged=True,
    removed_supplier_mesh_groups=removed,supplier_mesh_data_present=False,public_native_path=str(path.relative_to(ROOT)),public_native_sha256=sha(path),scope='Source-preserving public own CAD/native export; exact actuator meshes removed from objects and mesh datablocks. Physical/production qualification absent.',production_release=False)
(OUT/'public-native07-audit.json').write_text(json.dumps(report,indent=2)+'\n');print('PUBLIC_NATIVE',len(own),'own meshes;14 supplier groups removed',flush=True)
