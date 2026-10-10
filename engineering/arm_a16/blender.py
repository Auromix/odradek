# SPDX-License-Identifier: CC-BY-NC-4.0
"""Actual supplier assembly over the byte-pinned canonical B06 native base."""
from pathlib import Path
import json,hashlib,math,struct,sys
import bpy
from mathutils import Matrix,Vector

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent;OUT=HERE/'build';CACHE=ROOT/'work/arm-a16'
MODULED='--modules' in sys.argv
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
context=json.loads((OUT/'base-context.json').read_text());base=ROOT.parent/'odradek';native=base/context['base_sources']['native']['path']
for s in context['base_sources'].values():assert sha(base/s['path'])==s['sha256']
L=json.loads((OUT/'vendor-audit.json').read_text())['layout']
bpy.ops.wm.open_mainfile(filepath=str(native));scene=bpy.context.scene
for layer in scene.view_layers:layer.material_override=None
def fingerprint(o):
    h=hashlib.sha256()
    for v in o.data.vertices:h.update(struct.pack('<3d',*((o.matrix_world@v.co))))
    for f in o.data.polygons:h.update(struct.pack('<'+str(len(f.vertices))+'I',*f.vertices))
    return h.hexdigest()
canonical={o.name:fingerprint(o) for o in scene.objects if o.type=='MESH'}
col=bpy.data.collections.new('A16_BODY_Native_Trial');scene.collection.children.link(col)
def empty(name,parent=None):
    o=bpy.data.objects.new(name,None);col.objects.link(o)
    if parent:o.parent=parent;o.matrix_parent_inverse=Matrix.Identity(4)
    o.empty_display_size=.015;return o
root=empty('A16.root');T=Matrix(L['root_transform_mm']);T.translation*=.001;root.matrix_world=T
parents={'world':root};up=root
for j in L['joints']:
    f=empty(j['id']+'.fixed',up);f.location=Vector(j['offset'])*.001
    r=empty(j['id']+'.rotor',f);r.rotation_mode='AXIS_ANGLE';r.rotation_axis_angle=(0,*j['axis']);r['angle_deg']=0
    d=r.driver_add('rotation_axis_angle',0).driver;v=d.variables.new();v.name='q';v.type='SINGLE_PROP';v.targets[0].id=r;v.targets[0].data_path='["angle_deg"]';d.expression=f'(q+{j["zero_deg"]})*{math.pi/180}'
    parents[f.name]=f;parents[r.name]=r;up=r
def material(name,color,metal=.25,rough=.35):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1);n=m.node_tree.nodes.get('Principled BSDF');n.inputs['Base Color'].default_value=(*color,1);n.inputs['Metallic'].default_value=metal;n.inputs['Roughness'].default_value=rough;return m
M=material('A16 graphite continuous carapace',(.028,.043,.052),.4,.32)
S=material('A16 internal graphite finish',(.024,.032,.036),.08,.55)
V=material('A16 exact RobStride casing',(.018,.024,.029),.25,.55)
parts=[];sources=[];byid={}
names=['root01','skeleton01','covers02','hardware01']+(['root-cover03','cowls04','wrist05','skins06'] if MODULED else [])
for name in names:
    manifest=OUT/name/'manifest.json'
    document=json.loads(manifest.read_text());assert document['layout']==L,name+' has stale datums'
    if MODULED and name not in ['root01','skeleton01','covers02','hardware01']:
        reviewpath=OUT/name/'review.json'
        review=json.loads(reviewpath.read_text()) if reviewpath.exists() else document
        assert review['scoped_clear'] and review['tool_access']['scoped_clear'],name+' failed review'
        for relative,digest in review.get('source_sha256',{}).items():assert sha(ROOT/relative)==digest
        for old in document['replaces_only']:
            assert old in byid,(name,'unmatched replacement',old)
            del byid[old]
    sources.append(dict(path=str(manifest.relative_to(ROOT)),sha256=sha(manifest)))
    p=OUT/name/'meshes.json';sources.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p)))
    for row in json.loads(p.read_text()):
        assert row['id'] not in byid
        byid[row['id']]=row
parts=list(byid.values())
motorpath=CACHE/'vendor/meshes.json';motors=json.loads(motorpath.read_text());sources.append(dict(path=str(motorpath.relative_to(ROOT)),sha256=sha(motorpath)))
for p in parts+motors:
    me=bpy.data.meshes.new(p['id']);me.from_pydata([[x*.001 for x in v] for v in p['vertices_mm']],[],p['triangles']);me.update()
    me.materials.append(M if p['role']=='printed_cover' else V if p in motors else S);me.set_sharp_from_angle(angle=math.radians(28))
    for f in me.polygons:f.use_smooth=True
    o=bpy.data.objects.new(p['id'],me);col.objects.link(o);o.parent=parents[p['frame']];o.matrix_parent_inverse=Matrix.Identity(4)
    o['Frame']=p['frame'];o['role']=p['role'];o['Production qualified']=False;o['Supplier scaled']=False
assert all(fingerprint(bpy.data.objects[n])==h for n,h in canonical.items())
scene['Revision']=L['id'];scene['Base revision']=context['base_revision'];scene['Base native SHA256']=context['base_native_sha256'];scene['Base priority']=True;scene['Full arm release']=False
scene['Harness']='Straight tube space reservation checked separately. No connected dynamic harness or delivered mating plugs.'
def pose(name):
    for j,q in zip(L['joints'],L['poses'][name]):o=parents[j['id']+'.rotor'];o['angle_deg']=q;o.update_tag()
    bpy.context.view_layer.update()
pose('attention');bpy.context.preferences.filepaths.save_version=0
actual=CACHE/('actual-motors-modules.blend' if MODULED else 'actual-motors.blend');bpy.ops.wm.save_as_mainfile(filepath=str(actual),compress=True)
# Extract current canonical base vertices without modifying the source model.
basemesh=[]
base_manifest=json.loads((base/context['base_sources']['manifest']['path']).read_text())
visible_base_ids={p['id'] for p in base_manifest['parts'] if p['category']!='environment'}
assert visible_base_ids.issubset(canonical),'Missing canonical product mesh'
for name in canonical:
    # Construction masters duplicate exterior surfaces and the base stage has
    # its own table/box. They remain untouched in Blender, but are not product
    # geometry in the arm browser; the viewer provides its own desk.
    if name not in visible_base_ids:continue
    o=bpy.data.objects[name];o.data.calc_loop_triangles();mat=o.data.materials[0] if o.data.materials else None
    basemesh.append(dict(id=name,role='canonical_base_reference',vertices=[list((o.matrix_world@v.co)*1000) for v in o.data.vertices],faces=[list(t.vertices) for t in o.data.loop_triangles],color=list(mat.diffuse_color) if mat else [.1,.15,.2,1]))
export=dict(long=dict(layout=L,parts=[dict(id=p['id'],frame=p['frame'],role=p['role'],vertices=p['vertices_mm'],faces=p['triangles'],color=[.075,.13,.17,1] if p['role']=='printed_cover' else [.055,.08,.095,1] if p['role']=='printed_structure' else [.08,.10,.12,1] if p['role']=='supplier_reference' else [.18,.22,.25,1]) for p in parts+motors],sha256=sha(actual),flange_from_J7_mm=[110,0,0]),base=basemesh)
datafile=CACHE/('viewer-modules-data.json' if MODULED else 'viewer-data.json');datafile.write_text(json.dumps(export,separators=(',',':'))+'\n')
# Dedicated review camera leaves all canonical base transforms unchanged.
camera=bpy.data.cameras.new('A16 review');cam=bpy.data.objects.new('A16 review camera',camera);col.objects.link(cam);scene.camera=cam;camera.type='ORTHO'
for k,(loc,energy,size) in enumerate([((-1,1.5,1.8),36.7,2),((1,0,1.2),26.7,1.5),((0,-1,1.5),30,1.5)]):
    light=bpy.data.lights.new('A16 area'+str(k),'AREA');light.energy=energy;light.shape='DISK';light.size=size;o=bpy.data.objects.new(light.name,light);col.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,.3,.3))-o.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.render.resolution_x=1500;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
images={}
for name in ['attention','idle','reference']:
    pose(name);target=Vector((0,.33,.32));cam.location=(-.9,1.4,.8);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camera.ortho_scale=1.28 if name!='reference' else 1.5
    image_name=('modules-' if MODULED else '')+name
    scene.render.filepath=str(OUT/(image_name+'.png'));bpy.ops.render.render(write_still=True);images[image_name]=sha(OUT/(image_name+'.png'))
pose('attention');bpy.ops.wm.save_as_mainfile(filepath=str(actual),compress=True)
# Save/export hashes after final camera/pose state; geometry data unchanged.
export['long']['sha256']=sha(actual);datafile.write_text(json.dumps(export,separators=(',',':'))+'\n')
sources.append(dict(path=str((OUT/'vendor-audit.json').relative_to(ROOT)),sha256=sha(OUT/'vendor-audit.json')))
report=dict(layout=L,installed_modules=names,native_path=str(actual.relative_to(ROOT)),native_sha256=sha(actual),base_context=context,canonical_base_mesh_count=len(canonical),canonical_base_world_geometry_unchanged=True,canonical_base_object_fingerprints=canonical,viewer_base_product_mesh_count=len(basemesh),viewer_base_ids=sorted(visible_base_ids),source_files=sources,own_part_count=len(parts),supplier_mesh_groups=len(motors),images=images,production_release=False,whole_assembly_qualified=False)
(OUT/('native-modules-audit.json' if MODULED else 'native-audit.json')).write_text(json.dumps(report,indent=2)+'\n');print('A16_NATIVE',len(parts),len(motors),len(canonical),flush=True)
