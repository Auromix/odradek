# SPDX-License-Identifier: CC-BY-NC-4.0
"""Install exact own IF09 CAD in private actual-motor A17 Blender assembly."""
from pathlib import Path
import json, hashlib, struct, math
import bpy
from mathutils import Matrix,Vector

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/contacts09'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((OUT/'manifest.json').read_text());assert d['review']['sampled_clear']
oldreport=json.loads((ROOT/'engineering/arm_a17/build/style01/native-audit.json').read_text())
old=ROOT/oldreport['native_path'];assert sha(old)==oldreport['native_sha256']
for p in d['parts']:assert sha(ROOT/p['step_path'])==p['step_sha256']
bpy.ops.wm.open_mainfile(filepath=str(old),use_scripts=False);scene=bpy.context.scene
canonical=json.loads((ROOT/'engineering/arm_a16/build/native-modules-audit.json').read_text())['canonical_base_object_fingerprints']
def world_fingerprint(o):
    h=hashlib.sha256()
    for v in o.data.vertices:h.update(struct.pack('<3d',*(o.matrix_world@v.co)))
    for f in o.data.polygons:h.update(struct.pack('<'+str(len(f.vertices))+'I',*f.vertices))
    return h.hexdigest()
def local_fingerprint(o):
    h=hashlib.sha256()
    for v in o.data.vertices:h.update(struct.pack('<3d',*v.co))
    for f in o.data.polygons:h.update(struct.pack('<'+str(len(f.vertices))+'I',*f.vertices))
    return h.hexdigest()
assert all(world_fingerprint(bpy.data.objects[n])==h for n,h in canonical.items())
motors={o.name:local_fingerprint(o) for o in scene.objects if o.get('role')=='supplier_reference'};assert len(motors)==14
for id in d['replaces_only']:
    assert id in bpy.data.objects;obj=bpy.data.objects[id];me=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
    if me.users==0:bpy.data.meshes.remove(me)
def material(name,col,metal=.1,rough=.35):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*col,1)
    n=m.node_tree.nodes.get('Principled BSDF');n.inputs['Base Color'].default_value=(*col,1);n.inputs['Metallic'].default_value=metal;n.inputs['Roughness'].default_value=rough;return m
materials={'printed_structure':material('IF09 quiet graphite insert',(.027,.037,.044)),
           'fit_fixture':material('IF09 separate test gauge',(.18,.25,.26)),
           'PCB_geometry_only':material('IF09 provisional PCB',(.02,.063,.048),.05),
           'contact_pad_envelope':material('IF09 contact gold',(.55,.34,.08),.75),
           'working_pin_envelope':material('IF09 nominal test pins',(.55,.34,.08),.75),
           'hardware':material('IF09 standard fasteners',(.09,.1,.11),.65)}
col=bpy.data.collections.new('IF09 contact fit module');scene.collection.children.link(col)
fixture=[];ours=[];rows=json.loads((OUT/'meshes.json').read_text())
for p in rows:
    mesh=bpy.data.meshes.new(p['id']);mesh.from_pydata([[x*.001 for x in v] for v in p['vertices_mm']],[],p['triangles']);mesh.update()
    mesh.materials.append(materials[p['role']]);mesh.set_sharp_from_angle(angle=math.radians(30))
    for face in mesh.polygons:face.use_smooth=True
    o=bpy.data.objects.new(p['id'],mesh);col.objects.link(o);o.parent=bpy.data.objects['J7.rotor'];o.matrix_parent_inverse=Matrix.Identity(4)
    o['role']=p['role'];o['Frame']=p['frame'];o['production_release']=False;ours.append(o)
    if p['role'] in ['fit_fixture','working_pin_envelope'] or '-tool-' in p['id']:fixture.append(o)
def hide_fixture(state,shift=0):
    for o in fixture:o.hide_render=state;o.hide_set(state);o.location.x=shift
def pose(q):
    for j,x in zip(d['layout']['joints'],q):
        o=bpy.data.objects[j['id']+'.rotor'];o['angle_deg']=x;o.update_tag()
    bpy.context.view_layer.update()
scene.render.engine='CYCLES';scene.cycles.samples=20;scene.cycles.use_denoising=True
scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
camera=scene.camera;camera.data.type='ORTHO';images={}
def render(name,eye,target,scale):
    camera.location=eye;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True);images[name]=sha(OUT/(name+'.png'))
pose(d['layout']['poses']['attention']);hide_fixture(True)
render('whole-attention',(-1.05,1.10,.95),(0,.34,.33),1.13)
T=bpy.data.objects['J7.rotor'].matrix_world.copy()
render('contact-face',T@Vector((.285,-.145,.110)),T@Vector((.104,0,0)),.18)
hide_fixture(False,.05);bpy.context.view_layer.update()
render('contact-gauge-exploded',T@Vector((.30,-.20,.15)),T@Vector((.128,0,0)),.20)
hide_fixture(True);pose(d['layout']['poses']['attention'])
scene['Revision']='A18-IF09-CONTACT-FIT';scene['Production qualified']=False
scene['Interface']='IF09 own nominal CAD installed. Arm PCB/pad geometry, not fabricated PCB. Tool gauge hidden; manual dual coax, no automatic blind mating.'
assert all(world_fingerprint(bpy.data.objects[n])==h for n,h in canonical.items())
assert all(local_fingerprint(bpy.data.objects[n])==h for n,h in motors.items())
assert all(tuple(bpy.data.objects[n].scale)==(1,1,1) for n in motors)
cache=ROOT/'work/arm-a18';cache.mkdir(parents=True,exist_ok=True);native=cache/'actual-contact09.blend'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
report=dict(revision=d['revision'],native_path=str(native.relative_to(ROOT)),native_sha256=sha(native),source_A17_native_sha256=sha(old),
  manifest_sha256=sha(OUT/'manifest.json'),meshes_sha256=sha(OUT/'meshes.json'),canonical_base_mesh_count=len(canonical),base_world_geometry_preserved=True,
  exact_motor_partition_count=len(motors),supplier_geometry_unscaled_and_unchanged=True,own_IF09_mesh_count=len(ours),test_gauge_hidden_in_saved_arm=True,
  images=images,production_release=False)
(OUT/'native-audit.json').write_text(json.dumps(report,indent=2)+'\n');print('IF09_NATIVE_DONE',flush=True)
