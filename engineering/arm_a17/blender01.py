# SPDX-License-Identifier: CC-BY-NC-4.0
"""Native exact-motor A17 appearance review; canonical base left intact."""
from pathlib import Path
import json,hashlib,struct,math
import bpy
from mathutils import Vector,Matrix

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
OUT=HERE/'build/style01';CACHE=ROOT/'work/arm-a17';CACHE.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
mf=OUT/'manifest.json';d=json.loads(mf.read_text());L=d['layout']
old=ROOT/'work/arm-a16/actual-motors-modules.blend'
old_audit=json.loads((ROOT/'engineering/arm_a16/build/native-modules-audit.json').read_text())
assert sha(old)==old_audit['native_sha256']
bpy.ops.wm.open_mainfile(filepath=str(old),use_scripts=False)
scene=bpy.context.scene
def fingerprint(o):
    h=hashlib.sha256()
    for v in o.data.vertices:h.update(struct.pack('<3d',*((o.matrix_world@v.co))))
    for f in o.data.polygons:h.update(struct.pack('<'+str(len(f.vertices))+'I',*f.vertices))
    return h.hexdigest()
canonical=old_audit['canonical_base_object_fingerprints']
assert all(fingerprint(bpy.data.objects[n])==h for n,h in canonical.items())
def mat(name,color,metal,rough):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    n=m.node_tree.nodes.get('Principled BSDF');n.inputs['Base Color'].default_value=(*color,1)
    n.inputs['Metallic'].default_value=metal;n.inputs['Roughness'].default_value=rough
    return m
carapace=mat('A17 swept graphite alloy',(.065,.090,.104),.38,.29)
bone=mat('A17 quiet subframe',(.025,.033,.039),.15,.44)
hardware=mat('A17 recessed dark hardware',(.035,.04,.045),.35,.38)
for id in d['replaces_only']:
    assert id in bpy.data.objects,id
    o=bpy.data.objects[id];mesh=o.data;bpy.data.objects.remove(o,do_unlink=True)
    if mesh.users==0:bpy.data.meshes.remove(mesh)
for o in list(scene.objects):
    if o.type=='MESH' and o.name not in canonical and o.get('role') in ['printed_structure','hardware']:
        o.data.materials.clear();o.data.materials.append(hardware if o.get('role')=='hardware' else bone)
collection=bpy.data.collections.new('A17 development carapace');scene.collection.children.link(collection)
rows=json.loads((OUT/'meshes.json').read_text())
for p in rows:
    mesh=bpy.data.meshes.new(p['id']);mesh.from_pydata([[x*.001 for x in v] for v in p['vertices_mm']],[],p['triangles']);mesh.update()
    mesh.materials.append(carapace);mesh.set_sharp_from_angle(angle=math.radians(35))
    for face in mesh.polygons:face.use_smooth=True
    o=bpy.data.objects.new(p['id'],mesh);collection.objects.link(o)
    o.parent=bpy.data.objects[p['frame']];o.matrix_parent_inverse=Matrix.Identity(4)
    o['role']='printed_cover';o['Frame']=p['frame'];o['production_release']=False
def pose(q):
    for j,x in zip(L['joints'],q):
        o=bpy.data.objects[j['id']+'.rotor'];o['angle_deg']=x;o.update_tag()
    bpy.context.view_layer.update()
scene['Revision']='A17-MANTA-CARAPACE01';scene['Production qualified']=False
scene['Interface']='IF08 contact+dual coax proposal; not installed in native arm.'
scene['Appearance']='Physical corner blends in STEP, inherited real mounting features. No smaller motors, hidden geometry or base replacement.'
scene.render.engine='CYCLES';scene.cycles.samples=32
scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
cam=scene.camera;cam.data.type='ORTHO'
views=[('attention-side',L['poses']['attention'],(-1.2,.50,.70),(0,.34,.34),1.08),
       ('attention-three-quarter',L['poses']['attention'],(-1.05,1.10,.95),(0,.34,.33),1.13),
       ('idle-side',L['poses']['idle'],(-1.2,.50,.60),(0,.27,.24),.88)]
images={}
for name,q,location,target,scale in views:
    pose(q);cam.location=location;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True);images[name]=sha(OUT/(name+'.png'))
pose(L['poses']['attention'])
assert all(fingerprint(bpy.data.objects[n])==h for n,h in canonical.items())
bpy.context.preferences.filepaths.save_version=0
native=CACHE/'actual-style01.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
report=dict(revision=d['revision'],native_path=str(native.relative_to(ROOT)),native_sha256=sha(native),source_native_sha256=sha(old),manifest_sha256=sha(mf),
  current_supplier_partitions=14,supplier_scaled=False,canonical_base_count=len(canonical),canonical_base_world_geometry_unchanged=True,
  replacement_count=len(rows),images=images,IF08_installed=False,production_release=False)
(OUT/'native-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print('A17_NATIVE_DONE',flush=True)
