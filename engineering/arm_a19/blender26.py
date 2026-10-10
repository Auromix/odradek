# SPDX-License-Identifier: CC-BY-NC-4.0
"""Native actual-size wrist/root integration over unchanged canonical base."""
from pathlib import Path
import json,hashlib,struct,math
import bpy
from mathutils import Vector,Matrix
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/assembly25'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
path=OUT/'manifest.json';d=json.loads(path.read_text());prep=json.loads((ROOT/'work/arm-a19/changed-native26.json').read_text());assert prep['assembly_sha256']==sha(path)
old=json.loads((ROOT/'engineering/arm_a18/build/front-cowls10/native-audit.json').read_text());native=ROOT/old['native_path'];assert sha(native)==old['native_sha256']
bpy.ops.wm.open_mainfile(filepath=str(native),use_scripts=False);scene=bpy.context.scene
canonical=json.loads((ROOT/'engineering/arm_a16/build/native-modules-audit.json').read_text())['canonical_base_object_fingerprints']
def fingerprint(o,world=False):
    h=hashlib.sha256()
    for v in o.data.vertices:h.update(struct.pack('<3d',*(o.matrix_world@v.co if world else v.co)))
    for f in o.data.polygons:h.update(struct.pack('<'+str(len(f.vertices))+'I',*f.vertices))
    return h.hexdigest()
assert all(fingerprint(bpy.data.objects[n],True)==h for n,h in canonical.items())
unchanged={o.name:fingerprint(o) for o in scene.objects if o.get('role')=='supplier_reference' and not o.name.startswith('J5-supplier-')};assert len(unchanged)==12
covermat=bpy.data.materials.get('A17 swept graphite alloy');assert covermat
structuremat=bpy.data.materials.get('A16 internal graphite finish');vendormat=bpy.data.materials.get('A16 exact RobStride casing');assert structuremat and vendormat
for name in d['removed_part_ids']+['J5-supplier-stator','J5-supplier-external-output']:
    assert name in bpy.data.objects,name
    o=bpy.data.objects[name];me=o.data;bpy.data.objects.remove(o,do_unlink=True)
    if me.users==0:bpy.data.meshes.remove(me)
bpy.data.objects['J6.fixed'].location=Vector(d['layout']['joints'][5]['offset'])*.001
col=bpy.data.collections.new('A19 conventional native root and wrist');scene.collection.children.link(col)
for p in prep['own']+prep['supplier']:
    me=bpy.data.meshes.new(p['id']);me.from_pydata([[x*.001 for x in v] for v in p['vertices_mm']],[],p['triangles']);me.update()
    me.materials.append(covermat if p['role']=='printed_cover' else vendormat if p['role']=='supplier_reference' else structuremat)
    me.set_sharp_from_angle(angle=math.radians(35))
    for face in me.polygons:face.use_smooth=True
    o=bpy.data.objects.new(p['id'],me);col.objects.link(o);o.parent=bpy.data.objects[p['frame']];o.matrix_parent_inverse=Matrix.Identity(4);o['role']=p['role'];o['Frame']=p['frame'];o['production_release']=False
def pose(q):
    for j,x in zip(d['layout']['joints'],q):
        o=bpy.data.objects[j['id']+'.rotor'];o['angle_deg']=x;o.update_tag()
    bpy.context.view_layer.update()
pose(d['layout']['poses']['attention'])
# Direct independent frame matrix comparison includes changed J6 offset.
def rot(axis,angle):
    return Matrix.Rotation(angle,4,Vector(axis))
fkerrors=[]
for q in [d['layout']['poses'][name] for name in ['attention','idle','reference']]:
    pose(q);T=Matrix(d['layout']['root_transform_mm']);T.translation*=.001
    for j,x in zip(d['layout']['joints'],q):
        T=T@Matrix.Translation(Vector(j['offset'])*.001)
        fkerrors.append(max(abs(T[i][k]-bpy.data.objects[j['id']+'.fixed'].matrix_world[i][k]) for i in range(4) for k in range(4)))
        T=T@rot(j['axis'],math.radians(x+j['zero_deg']))
        fkerrors.append(max(abs(T[i][k]-bpy.data.objects[j['id']+'.rotor'].matrix_world[i][k]) for i in range(4) for k in range(4)))
assert max(fkerrors)<1e-6,max(fkerrors)
scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100;scene.cycles.samples=24;cam=scene.camera;cam.data.type='ORTHO';images={}
for name,q,eye,target,scale in [('whole-attention',d['layout']['poses']['attention'],(-1.05,1.10,.95),(0,.34,.33),1.16),('whole-idle',d['layout']['poses']['idle'],(-1.2,.50,.60),(0,.27,.24),.95)]:
    pose(q);cam.location=eye;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True);images[name]=sha(OUT/(name+'.png'))
pose(d['layout']['poses']['attention']);T=bpy.data.objects['J5.fixed'].matrix_world.copy();target=T@Vector((0,.06,0));cam.location=T@Vector((-.18,.30,.18));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.35
scene.render.filepath=str(OUT/'wrist-native-detail.png');bpy.ops.render.render(write_still=True);images['wrist-native-detail']=sha(OUT/'wrist-native-detail.png')
assert all(fingerprint(bpy.data.objects[n],True)==h for n,h in canonical.items())
assert all(fingerprint(bpy.data.objects[n])==h and tuple(bpy.data.objects[n].scale)==(1,1,1) for n,h in unchanged.items())
assert all(tuple(o.scale)==(1,1,1) for o in scene.objects if o.get('role')=='supplier_reference')
pose(d['layout']['poses']['attention']);scene['Revision']='A19-INTEGRATED25';scene['Production qualified']=False;scene['Harness']='Unmodelled allowances; no dynamic harness or electrical qualification.'
native=ROOT/'work/arm-a19/actual-integrated26.blend';bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
report=dict(revision='A19-NATIVE26',assembly_sha256=sha(path),native_path=str(native.relative_to(ROOT)),native_sha256=sha(native),canonical_base_count=len(canonical),canonical_base_world_geometry_unchanged=True,unchanged_supplier_partitions=12,unchanged_supplier_fingerprints=unchanged,changed_J5_model='RS03',supplier_mesh_scale=1,native_frame_matrix_max_error=max(fkerrors),images=images,production_release=False)
for o in list(bpy.data.objects):
    if o.get('role')=='supplier_reference':
        me=o.data;bpy.data.objects.remove(o,do_unlink=True)
        if me.users==0:bpy.data.meshes.remove(me)
assert not any('supplier-' in m.name for m in bpy.data.meshes)
public=OUT/'A19-ownparts-fit.blend';bpy.ops.wm.save_as_mainfile(filepath=str(public),compress=True);report.update(public_native_path=str(public.relative_to(ROOT)),public_native_sha256=sha(public),supplier_mesh_present_in_public=False)
(OUT/'native-audit26.json').write_text(json.dumps(report,indent=2)+'\n');print('NATIVE26_DONE',flush=True)
