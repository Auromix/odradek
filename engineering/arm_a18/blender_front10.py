# SPDX-License-Identifier: CC-BY-NC-4.0
"""Import exact four front-cowl STEP derivatives into actual-motor arm native."""
from pathlib import Path
import json,hashlib,struct,math
import bpy
from mathutils import Vector,Matrix
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/front-cowls10'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((OUT/'manifest.json').read_text());assert d['changed_pair_sampled_clear']
oldaudit=json.loads((HERE/'build/contacts09/native-audit.json').read_text());old=ROOT/oldaudit['native_path'];assert sha(old)==oldaudit['native_sha256']
for p in d['parts']:assert sha(ROOT/p['step_path'])==p['step_sha256']
bpy.ops.wm.open_mainfile(filepath=str(old),use_scripts=False);scene=bpy.context.scene
canonical=json.loads((ROOT/'engineering/arm_a16/build/native-modules-audit.json').read_text())['canonical_base_object_fingerprints']
def fingerprint(o,world=False):
    h=hashlib.sha256()
    for v in o.data.vertices:h.update(struct.pack('<3d',*(o.matrix_world@v.co if world else v.co)))
    for f in o.data.polygons:h.update(struct.pack('<'+str(len(f.vertices))+'I',*f.vertices))
    return h.hexdigest()
motors={o.name:fingerprint(o) for o in scene.objects if o.get('role')=='supplier_reference'};assert len(motors)==14
assert all(fingerprint(bpy.data.objects[n],True)==h for n,h in canonical.items())
for id in d['replaces_only']:
    o=bpy.data.objects[id];me=o.data;bpy.data.objects.remove(o,do_unlink=True)
    if me.users==0:bpy.data.meshes.remove(me)
col=bpy.data.collections.new('A18 front cowl refinement');scene.collection.children.link(col)
mat=bpy.data.materials.get('A17 swept graphite alloy');assert mat
rows=json.loads((OUT/'meshes.json').read_text());assert len(rows)==4
for p in rows:
    me=bpy.data.meshes.new(p['id']);me.from_pydata([[x*.001 for x in v] for v in p['vertices_mm']],[],p['triangles']);me.update();me.materials.append(mat)
    me.set_sharp_from_angle(angle=math.radians(35))
    for face in me.polygons:face.use_smooth=True
    o=bpy.data.objects.new(p['id'],me);col.objects.link(o);o.parent=bpy.data.objects[p['frame']];o.matrix_parent_inverse=Matrix.Identity(4)
    o['role']='printed_cover';o['Frame']=p['frame'];o['production_release']=False
def pose(q):
    for j,x in zip(d['layout']['joints'],q):
        o=bpy.data.objects[j['id']+'.rotor'];o['angle_deg']=x;o.update_tag()
    bpy.context.view_layer.update()
scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100;scene.cycles.samples=20
cam=scene.camera;cam.data.type='ORTHO';images={}
for name,q,eye,target,scale in [('whole-attention',d['layout']['poses']['attention'],(-1.05,1.10,.95),(0,.34,.33),1.13),
                             ('whole-idle',d['layout']['poses']['idle'],(-1.2,.50,.60),(0,.27,.24),.88)]:
    pose(q);cam.location=eye;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True);images[name]=sha(OUT/(name+'.png'))
pose(d['layout']['poses']['attention']);T=bpy.data.objects['J4.fixed'].matrix_world.copy()
cam.location=T@Vector((.20,.24,.18));target=T@Vector((0,.04,0));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.30
scene.render.filepath=str(OUT/'elbow-front-detail.png');bpy.ops.render.render(write_still=True);images['elbow-front-detail']=sha(OUT/'elbow-front-detail.png')
assert all(fingerprint(bpy.data.objects[n],True)==h for n,h in canonical.items())
assert all(fingerprint(bpy.data.objects[n])==h and tuple(bpy.data.objects[n].scale)==(1,1,1) for n,h in motors.items())
scene['Revision']='A18-FRONT10-CONTACT09';scene['Production qualified']=False
scene['Appearance scope']='Own printed front lips on J3/J4 only. J2 unchanged; no hidden collision parts, no scaled motors. IF09 contact face installed, test gauge hidden.'
native=ROOT/'work/arm-a18/actual-front10-contact09.blend';bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
report=dict(revision=d['revision'],native_path=str(native.relative_to(ROOT)),native_sha256=sha(native),source_IF09_native_sha256=sha(old),
 manifest_sha256=sha(OUT/'manifest.json'),meshes_sha256=sha(OUT/'meshes.json'),canonical_base_count=len(canonical),base_world_geometry_unchanged=True,
 actual_supplier_partitions=len(motors),supplier_geometry_unchanged_and_unscaled=True,changed_cover_count=4,J2_cover_unchanged=True,images=images,production_release=False)
for name in motors:
    o=bpy.data.objects[name];me=o.data;bpy.data.objects.remove(o,do_unlink=True)
    if me.users==0:bpy.data.meshes.remove(me)
assert not any(o.get('role')=='supplier_reference' for o in bpy.data.objects)
assert not any('supplier-' in m.name for m in bpy.data.meshes)
assert all(fingerprint(bpy.data.objects[n],True)==h for n,h in canonical.items())
public=OUT/'A18-ownparts-fit.blend';bpy.ops.wm.save_as_mainfile(filepath=str(public),compress=True)
report['public_own_native_path']=str(public.relative_to(ROOT));report['public_own_native_sha256']=sha(public)
report['supplier_mesh_present_in_public_native']=False
(OUT/'native-audit.json').write_text(json.dumps(report,indent=2)+'\n');print('A18_FRONT_NATIVE_DONE',flush=True)
