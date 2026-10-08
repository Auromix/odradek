# SPDX-License-Identifier: CC-BY-NC-4.0
"""Selected-A J2 exterior module on untouched A11 exact motor rig.
Public native uses owned envelopes; local native retains supplier geometry.
"""
from pathlib import Path
import bpy,json,sys,math,hashlib
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent/'build'
ACTUAL='--actual' in sys.argv
D=json.loads((OUT/'manifest.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
INPUTS=json.loads((OUT/'inputs.json').read_text())
assert sha(OUT/'manifest.json')==INPUTS['shoulder_manifest_sha256']
assert sha(ROOT/'engineering/arm_a11/build/manifest.json')==D['baseline_manifest_sha256']
BASELINE=ROOT/'work/arm-a11/odradek-a11-long-actual-motors.blend' if ACTUAL else ROOT/'engineering/arm_a11/build/odradek-a11-long-validation.blend'
assert sha(BASELINE)==INPUTS['baseline_actual_native_sha256' if ACTUAL else 'baseline_public_native_sha256']
bpy.ops.wm.open_mainfile(filepath=str(BASELINE))
scene=bpy.context.scene
for id in D['replaced_parts']:
 o=bpy.data.objects.get(id);assert o is not None;bpy.data.objects.remove(o,do_unlink=True)
col=bpy.data.collections.new('A12_01_J2_Selected_A_Shields');scene.collection.children.link(col)
def material(name,color,metal=0):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=.3;p.inputs['Metallic'].default_value=metal;return m
shellmat=material('A12_Continuous_Carapace',(.055,.083,.11),.2)
for p in D['parts']:
 m=bpy.data.meshes.new(p['id']);m.from_pydata([tuple(.001*x for x in v) for v in p['vertices_mm']],[],p['triangles']);m.update()
 m.materials.append(shellmat);m.set_sharp_from_angle(angle=math.radians(30))
 for f in m.polygons:f.use_smooth=True
 o=bpy.data.objects.new(p['id'],m);col.objects.link(o);o.parent=bpy.data.objects['J2.fixed'];o.matrix_parent_inverse=Matrix.Identity(4)
 o['Source STEP SHA256']=p['step_sha256'];o['Source STL SHA256']=p['stl_sha256'];o['A12 prototype']=True;o['Printable release']=False;o['Frame']='J2.fixed'
# B06 remains read-only canonical context. No changes or assembly pass inherited.
basefile=ROOT/INPUTS['read_only_cache_relative_path'];base_sha=sha(basefile);assert base_sha==INPUTS['base_native_sha256']
for obj in list(bpy.data.collections['80_Base_Context'].objects):bpy.data.objects.remove(obj,do_unlink=True)
with bpy.data.libraries.load(str(basefile),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.startswith('B06-')]
for o in dst.objects:
 assert o is not None;bpy.data.collections['80_Base_Context'].objects.link(o);o['A12 context only']='Current canonical B06 geometry; root/base integration not checked here'
assert sha(basefile)==base_sha,'Canonical base changed while read; rerun instead of mixing revisions'
scene['A12 canonical base native SHA256']=base_sha
scene['A12 canonical base path']=INPUTS['base_canonical_relative_path']
for k in ['Canonical base manifest SHA256','Canonical base revision','Canonical base repository']:
 if k in scene:del scene[k]
scene['Canonical base revision']='B06 native pinned by A12 inputs.json; no root integration proof'
wirecol=bpy.data.collections.new('A12_02_Unconnected_Wire_Space_HIDDEN');scene.collection.children.link(wirecol)
wiremat=material('Reserved_space_only_amber',(1,.43,.06))
curve=bpy.data.curves.new('D10_unconnected_static_U_reservation','CURVE');curve.dimensions='3D';curve.resolution_u=1;curve.bevel_depth=.005;curve.bevel_resolution=3;curve.use_fill_caps=True
s=curve.splines.new('POLY');s.points.add(len(D['wire_reservation']['centreline_mm'])-1)
for p,co in zip(s.points,D['wire_reservation']['centreline_mm']):p.co=(*[x*.001 for x in co],1)
o=bpy.data.objects.new('RESERVATION_NOT_HARNESS',curve);wirecol.objects.link(o);o.parent=bpy.data.objects['J2.fixed'];o.matrix_parent_inverse=Matrix.Identity(4);curve.materials.append(wiremat)
o['Scope']='Stationary unconnected U-shaped D10 space; R36 target, no cable chosen or motion simulation';wirecol.hide_render=True;wirecol.hide_viewport=True
scene['A12 design status']='Module01 J2 cover geometry prototype; all other A11 armour awaits A12 reconstruction'
scene['A12 source manifest SHA256']=sha(OUT/'manifest.json')
scene['Official motor CAD imported']=ACTUAL
scene['3kg qualified']=False
text=bpy.data.texts.new('A12_SCOPE');text.write('Selected A, shoulder01 only.\nTwo new J2 shields; untouched original-sized motors and upstream/downstream mechanics.\nB06 canonical context only; base integration is not validated here.\nUnconnected D10/R36 static U-space is a reservation, not a real harness.\nNo print, thermal, motor clamp, cable-motion or 3kg release.\nOther A11 exposed parts remain pending A12 design.\nSupplier solids local only; public native has original owned envelopes.\nSelect J1.rotor ... J7.rotor and change angle_deg.\nA12 source: '+sha(OUT/'manifest.json'))
def camera(pos,target,scale):
 o=bpy.data.objects['Review_camera'];o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();o.data.type='ORTHO';o.data.ortho_scale=scale;scene.camera=o
def pose(name):
 L=json.loads((ROOT/'engineering/arm_a11/build/manifest.json').read_text())['layout']
 for j,q in zip(L['joints'],L['poses'][name]):bpy.data.objects[j['id']+'.rotor']['angle_deg']=q
 bpy.context.view_layer.update()
pose('attention');camera((-.55,.55,.54),(-.065,.075,.255),.47)
scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.cycles.samples=24
bpy.context.preferences.filepaths.save_version=0
bpy.ops.object.select_all(action='DESELECT');o=bpy.data.objects[D['parts'][0]['id']];o.select_set(True);bpy.context.view_layer.objects.active=o
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.region_3d.view_distance=.65;area.spaces.active.region_3d.view_location=Vector((-.065,.075,.255));area.spaces.active.region_3d.view_rotation=scene.camera.rotation_euler.to_quaternion()
file=ROOT/'work/arm-a12/shoulder01-actual-motors.blend' if ACTUAL else OUT/'A12-A-shoulder01.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(file),compress=True)
if '--no-render' not in sys.argv:
 scene.render.filepath=str(OUT/'shoulder-assembled.png');bpy.ops.render.render(write_still=True)
 for idx,p in enumerate(D['parts']):bpy.data.objects[p['id']].location.x=(-1 if idx==0 else 1)*.11
 wirecol.hide_render=False
 camera((-.54,.58,.56),(-.065,.075,.255),.53)
 scene.render.filepath=str(OUT/'shoulder-exploded-space.png');bpy.ops.render.render(write_still=True)
 for p in D['parts']:bpy.data.objects[p['id']].location.x=0
 wirecol.hide_render=True
 camera((-.9,.85,.72),(0,.30,.26),1.10)
 scene.render.filepath=str(OUT/'module-context.png');bpy.ops.render.render(write_still=True)
 (OUT/'render-source.json').write_text(json.dumps(dict(manifest_sha256=sha(OUT/'manifest.json'),baseline_native_sha256=sha(BASELINE),base_native_sha256=base_sha,supplier_geometry=ACTUAL,scope='J2 module only; remainder is unchanged A11. Static reservation not connected harness.'),indent=2)+'\n')
print('A12_BLENDER_MODULE_COMPLETE',ACTUAL,len(D['parts']),flush=True)
