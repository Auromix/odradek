# SPDX-License-Identifier: CC-BY-NC-4.0
"""CAD link skins on pinned full-size motors and canonical B06 base."""
from pathlib import Path
import bpy,json,sys,hashlib,math
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=HERE/'build';ACTUAL='--actual' in sys.argv
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
P=ROOT/'engineering/arm_a13/wrist-route01/build';native=ROOT/'work/arm-a13/wrist-route01/actual-motors.blend' if ACTUAL else P/'A13-WRIST-ROUTE01.blend'
prior=json.loads((P/('native-actual-audit.json' if ACTUAL else 'native-public-audit.json')).read_text());assert sha(native)==prior['native_sha256']
D=json.loads((OUT/'parts.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(native));scene=bpy.context.scene
remove=D['replaces']+['A12-W13-J3-rotor-lip','A12-W14-J4-rotor-lip']
for name in remove:
 if name in bpy.data.objects:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
col=bpy.data.collections.new('A14_CAD_LINK_SHELL01');scene.collection.children.link(col)
mat=bpy.data.materials['A12 Graphite blue carapace']
for p in D['parts']:
 me=bpy.data.meshes.new(p['id']);me.from_pydata([[v*.001 for v in xyz] for xyz in p['vertices_mm']],[],p['triangles']);me.update();me.materials.append(mat)
 me.set_sharp_from_angle(angle=math.radians(28))
 for f in me.polygons:f.use_smooth=True
 o=bpy.data.objects.new(p['id'],me);col.objects.link(o);o.parent=bpy.data.objects[p['frame']];o.matrix_parent_inverse=Matrix.Identity(4)
 o['Frame']=p['frame'];o['role']=p['role'];o['Production released']=False;o['Source STEP SHA256']=p['step_sha256']
scene['Revision']='A14-LINK-SHELL01';scene['A14 parts SHA256']=sha(OUT/'parts.json');scene['Original native SHA256']=sha(native);scene['3kg qualified']=False;scene['Dynamic harness released']=False
scene['A14 motor selection frozen']=False
text=bpy.data.texts.new('A14_LINK_SHELL01_README');text.write('Four detachable CAD covers; selected-A long-arm style and unscaled motors retained. Supported unpowered fit study only. Current actuator layout NOT 3kg continuous-load qualified. Full assembly, harness, thermal and physical manufacturing validation remain open. See engineering/arm_a14/link-shell01/README.md and the version-matched source reports.\n')
cam=bpy.data.objects['Review_camera']
def camera(pos,target,scale):
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=scale;scene.camera=cam
def pose(name):
 for j,q in zip(D['layout']['joints'],D['layout']['poses'][name]):
  o=bpy.data.objects[j['id']+'.rotor'];o['angle_deg']=q;o.update_tag()
 bpy.context.view_layer.update()
pose('attention');camera((-.7,1.28,.67),(0,.33,.27),1.19)
scene.render.resolution_x=1500;scene.render.resolution_y=1050;scene.cycles.samples=16;bpy.context.preferences.filepaths.save_version=0
dest=ROOT/'work/arm-a14/link-shell01/actual-motors.blend' if ACTUAL else OUT/'A14-LINK-SHELL01.blend';dest.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(dest),compress=True)
if ACTUAL:
 images={}
 for name in ['attention','idle','reference']:
  pose(name)
  if name=='idle':camera((-.5,.9,.45),(0,.20,.19),.91)
  elif name=='reference':camera((-.9,1.48,.65),(0,.4,.29),1.42)
  else:camera((-.7,1.28,.67),(0,.33,.27),1.19)
  path=OUT/(name+'.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True);images[name]=sha(path)
 (OUT/'render-source.json').write_text(json.dumps(dict(native_sha256=sha(dest),source_native_sha256=sha(native),parts_source_sha256=sha(OUT/'parts.json'),images=images,supplier_geometry=True,harness_drawn=False),indent=2)+'\n')
print('NATIVE_COMPLETE',dest,flush=True)
