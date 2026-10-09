# SPDX-License-Identifier: CC-BY-NC-4.0
"""Editable local J7 assembly; supplier geometry is local-only."""
from pathlib import Path
import bpy, math, json, sys, hashlib
from mathutils import Vector, Matrix

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=HERE/'build'
ACTUAL='--actual' in sys.argv
D=json.loads((OUT/'manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='MILLIMETERS'
scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.resolution_x=1400;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.80,.83,.87,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
bpy.context.preferences.filepaths.save_version=0

def material(name,color,metal=0,rough=.4):
 m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
 bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough;return m
shell=material('Graphite blue plastic prototype',(.065,.11,.16),.05,.33)
rotating=material('Grey plastic journal',(.25,.31,.36),.05,.38)
steel=material('Purchased steel',(.4,.45,.50),.8,.24)
motor=material('Purchased RS00 dark finish',(.035,.045,.055),.6,.28)
gauge=material('Amber fit coupons',(.8,.36,.065),0,.4)
ground=material('Studio ground',(.82,.85,.88),0,.8)

def collection(name):
 col=bpy.data.collections.new(name);scene.collection.children.link(col);return col
structures=collection('01_Owned_plastic_fit_parts');purchased=collection('02_Purchased_nominal_hardware')
suppliers=collection('03_Supplier_CAD_LOCAL_ONLY' if ACTUAL else '03_Owned_motor_envelope')
coupons=collection('04_Fit_coupons_print_first');studio=collection('90_Studio')
def empty(name):
 o=bpy.data.objects.new(name,None);structures.objects.link(o);o.empty_display_type='ARROWS';o.empty_display_size=.012;return o
fixed=empty('J7.fixed');rotor=empty('J7.rotor');rotor.parent=fixed
rotor['angle_deg']=0.;rotor.rotation_mode='XYZ'
driver=rotor.driver_add('rotation_euler',0).driver;driver.expression='q*pi/180'
v=driver.variables.new();v.name='q';v.targets[0].id=rotor;v.targets[0].data_path='["angle_deg"]'
def mesh(p,col,mat):
 me=bpy.data.meshes.new(p['id']);me.from_pydata([[x*.001 for x in co] for co in p['vertices_mm']],[],p['triangles']);me.update()
 me.materials.append(mat);me.set_sharp_from_angle(angle=math.radians(28))
 for face in me.polygons:face.use_smooth=True
 o=bpy.data.objects.new(p['id'],me);col.objects.link(o)
 if p['frame'] in ['J7.fixed','J7.rotor']:o.parent=fixed if p['frame']=='J7.fixed' else rotor;o.matrix_parent_inverse=Matrix.Identity(4)
 o['Source role']=p['role'];o['Load qualified']=False
 if 'step_sha256' in p:o['Owned STEP SHA256']=p['step_sha256']
 return o
for p in D['parts']:
 o=mesh(p,coupons if p['role']=='fit_coupon' else structures,gauge if p['role']=='fit_coupon' else rotating if p['frame']=='J7.rotor' else shell)
 if p['role']=='fit_coupon':o.hide_render=True;o.hide_set(True)
for p in D['owned_context']:
 if p['role']=='owned_motor_envelope_reference':
  if not ACTUAL:mesh(p,suppliers,motor)
 else:mesh(p,purchased,steel)
if ACTUAL:
 source=ROOT/'work/arm-a10/vendor/meshes.json'
 for p in json.loads(source.read_text()):
  if p['id'].startswith('J7-supplier-'):
   o=mesh(p,suppliers,motor);o['Supplier geometry local only']=True;o['Supplier source SHA256']=p['source_sha256']
 scene['Supplier mesh cache SHA256']=sha(source)
scene['Revision']='A13-J7-FIT01';scene['Owned manifest SHA256']=sha(OUT/'manifest.json')
scene['Scope']='Supported unpowered local plastic fit; not whole arm or 3kg qualification'
scene['Print release']=False
text=bpy.data.texts.new('READ_FIRST');text.write('J7 plastic-first local assembly. Six owned assembly pieces + six coupons.\nFront flange is detachable so the bearings can pass onto the journal.\nRotate J7.rotor[angle_deg] for the output. Actual supplier CAD is local-only.\nMotor installation holes, axis and flange stack unchanged from pinned A11.\nUse README, interface.json, feature drawings and exact fit audit.\nSupported unpowered fit only. Measure actual thread depths and bearing fits.\nWire route, rigid cosmetic mount and full arm motion are not released.\n')

def camera(pos,target,scale):
 if 'Review_camera' not in bpy.data.objects:
  data=bpy.data.cameras.new('Review_camera');obj=bpy.data.objects.new('Review_camera',data);studio.objects.link(obj)
 obj=bpy.data.objects['Review_camera'];obj.location=pos;obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler();obj.data.type='ORTHO';obj.data.ortho_scale=scale;scene.camera=obj
for name,pos,energy,size in [('Key',(.14,-.18,.24),.6,.20),('Rim',(-.1,.12,.15),.4,.16),('Fill',(.18,.12,.06),.23,.14)]:
 data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
 o=bpy.data.objects.new(name,data);studio.objects.link(o);o.location=pos;o.rotation_euler=(Vector((.025,0,0))-o.location).to_track_quat('-Z','Y').to_euler()
camera((.21,-.23,.16),(.025,0,0),.20)
bpy.context.view_layer.update()
# Reopenable native stores assembled state with all five structural pieces.
native=ROOT/'work/arm-a13/j7-fit01/actual-RS00-fit.blend' if ACTUAL else OUT/'A13-J7-plastic-fit.blend'
native.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
if ACTUAL:
 scene.render.filepath=str(OUT/'j7-assembled.png');bpy.ops.render.render(write_still=True)
 # Separate by assembly stations, not arbitrary rotation, to explain order.
 positions={
  'A13-J7-105-carrier':-.06,'A13-J7-101-bearing-housing':.020,
  'J7-6807-1':.047,'J7-6807-2':.054,
  'A13-J7-102-bearing-retainer':.066,'A13-J7-104-inner-spacer':.077,
  'A13-J7-103-output-journal':.124,'A13-J7-106-detachable-flange':.143}
 for o in purchased.objects:
  if not o.name.startswith('J7-6807-'):o.hide_render=True
 for id,offset in positions.items():bpy.data.objects[id].location.x=offset
 camera((.31,-.31,.22),(.063,0,0),.40)
 scene.render.filepath=str(OUT/'j7-exploded.png');bpy.ops.render.render(write_still=True)
 for id in positions:bpy.data.objects[id].location.x=0
 for o in purchased.objects:o.hide_render=False
 report=dict(manifest_sha256=sha(OUT/'manifest.json'),native_sha256=sha(native),supplier_groups=2,
             scope='Local J7 supported plastic fit assembly; no whole-arm design qualification')
 (OUT/'render-source.json').write_text(json.dumps(report,indent=2)+'\n')
print('NATIVE',native,flush=True)
