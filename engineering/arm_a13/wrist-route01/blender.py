# SPDX-License-Identifier: CC-BY-NC-4.0
"""Install reviewed J7 module on selected-A whole arm, preserving motors/base."""
from pathlib import Path
import bpy,json,sys,hashlib,math
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=HERE/'build';ACTUAL='--actual' in sys.argv
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
B=ROOT/'engineering/arm_a12/wrist02/build';source=ROOT/'work/arm-a12/wrist02/actual-motors.blend' if ACTUAL else B/'A12-A-wrist02.blend'
prior=json.loads((B/('native-actual-audit.json' if ACTUAL else 'native-public-audit.json')).read_text());assert sha(source)==prior['native_sha256']
D=json.loads((OUT/'integration-parts.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(source));scene=bpy.context.scene
remove=['P06-yaw-to-roll','B7-output-flange','J7-bearing-cage','J7-bearing-retainer','J7-inner-spacer','J7-inner-centre-spacer']+[f'J7-tool-M4-nut-{i}' for i in range(1,4)]
for name in remove:
 if name in bpy.data.objects:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
col=bpy.data.collections.new('A13_WRIST_ROUTE01_Integrated_Trial');scene.collection.children.link(col)
mat=bpy.data.materials['A12 Graphite blue carapace'];metal=bpy.data.materials.new('A13 nominal steel');metal.use_nodes=True;metal.diffuse_color=(.4,.45,.50,1);bs=metal.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=metal.diffuse_color;bs.inputs['Metallic'].default_value=.8
amber=metal.copy();amber.name='Allocation only';amber.diffuse_color=(.8,.35,.055,1);amber.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=amber.diffuse_color;amber.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value=0
for p in D['new_parts']+D['hardware']+D['allocations']:
 me=bpy.data.meshes.new(p['id']);me.from_pydata([[v*.001 for v in xyz] for xyz in p['vertices_mm']],[],p['triangles']);me.update();me.materials.append(metal if p in D['hardware'] else amber if p in D['allocations'] else mat)
 me.set_sharp_from_angle(angle=math.radians(28))
 for face in me.polygons:face.use_smooth=True
 o=bpy.data.objects.new(p['id'],me);col.objects.link(o);o.parent=bpy.data.objects[p['frame']];o.matrix_parent_inverse=Matrix.Identity(4);o['Frame']=p['frame'];o['role']='allocation_reference' if p in D['allocations'] else p['role'];o['Print trial only']=True
 if p in D['allocations']:o.hide_render=True;o.hide_set(True)
scene['Revision']='A13-WRIST-ROUTE01';scene['Integrated source SHA256']=sha(OUT/'integration-parts.json');scene['Original native SHA256']=sha(source);scene['New nominal tool plane J7 mm']=[110,0,0];scene['Dynamic harness released']=False
# Old head form reference is detached: it has not been redesigned for the new tool pocket.
head=bpy.data.collections['81_Petal_Form_Reference_HIDDEN'];head.hide_render=True;head.hide_viewport=True
scene['Head rear pocket integrated']=False;scene['3kg qualified']=False
if 'WRIST_ROUTE01_README' in bpy.data.texts:bpy.data.texts.remove(bpy.data.texts['WRIST_ROUTE01_README'])
t=bpy.data.texts.new('WRIST_ROUTE01_README');t.write((HERE/'README.md').read_text())
for j,q in zip(D['layout']['joints'],D['layout']['poses']['attention']):o=bpy.data.objects[j['id']+'.rotor'];o['angle_deg']=q;o.update_tag()
bpy.context.view_layer.update()
cam=bpy.data.objects['Review_camera']
def camera(pos,target,scale):
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=scale;scene.camera=cam
camera((-.7,1.28,.67),(0,.33,.27),1.19);scene.render.resolution_x=1500;scene.render.resolution_y=1050;scene.cycles.samples=20;bpy.context.preferences.filepaths.save_version=0
native=ROOT/'work/arm-a13/wrist-route01/actual-motors.blend' if ACTUAL else OUT/'A13-WRIST-ROUTE01.blend';native.parent.mkdir(parents=True,exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
if ACTUAL:
 scene.render.filepath=str(OUT/'whole-integrated.png');bpy.ops.render.render(write_still=True)
 # Wrist in its unpowered fit context; omitted components are only distant body/base.
 origin=bpy.data.objects['J7.fixed'].matrix_world.translation
 frame=bpy.data.objects['J7.fixed'].matrix_world.to_3x3();target=origin+frame@Vector((.03,0,0))
 camera(target+frame@Vector((.25,-.3,.22)),target,.40)
 for o in scene.objects:
  if o.type=='MESH' and o not in col.objects[:] and o.parent is not None and o.parent.name in ['Arm_mount_B05','J1.fixed','J1.rotor','J2.fixed','J2.rotor','J3.fixed','J3.rotor','J4.fixed','J4.rotor']:o.hide_render=True
 for o in bpy.data.collections['80_Base_Context'].objects:o.hide_render=True
 scene.render.filepath=str(OUT/'wrist-integrated.png');bpy.ops.render.render(write_still=True)
 (OUT/'render-source.json').write_text(json.dumps(dict(native_sha256=sha(native),source_native_sha256=sha(source),integration_parts_sha256=sha(OUT/'integration-parts.json'),images={n:sha(OUT/n) for n in ['whole-integrated.png','wrist-integrated.png']},supplier_geometry=True,dynamic_cables_drawn=False),indent=2)+'\n')
print('INTEGRATED_NATIVE',native,flush=True)
