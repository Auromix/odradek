# SPDX-License-Identifier: CC-BY-NC-4.0
from pathlib import Path
import bpy,json,sys,hashlib,math
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=HERE/'build';ACTUAL='--actual' in sys.argv
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
P=ROOT/'engineering/arm_a14/link-shell01/build';source=ROOT/'work/arm-a14/link-shell01/actual-motors.blend' if ACTUAL else P/'A14-LINK-SHELL01.blend'
prior=json.loads((P/('native-actual-audit.json' if ACTUAL else 'native-public-audit.json')).read_text());assert prior['native_sha256']==sha(source)
D=json.loads((OUT/'parts.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(source));scene=bpy.context.scene;assert scene['A14 parts SHA256']==D['parent_parts_sha256']
bpy.data.objects.remove(bpy.data.objects[D['tail_change']['old_id']],do_unlink=True)
p=D['parts'][-1];me=bpy.data.meshes.new(p['id']);me.from_pydata([[v*.001 for v in xyz] for xyz in p['vertices_mm']],[],p['triangles']);me.update();me.materials.append(bpy.data.materials['A12 Graphite blue carapace']);me.set_sharp_from_angle(angle=math.radians(28))
for f in me.polygons:f.use_smooth=True
o=bpy.data.objects.new(p['id'],me);bpy.data.collections['A14_CAD_LINK_SHELL01'].objects.link(o);o.parent=bpy.data.objects[p['frame']];o.matrix_parent_inverse=Matrix.Identity(4);o['Frame']=p['frame'];o['role']=p['role'];o['Production released']=False
scene['Revision']='A14-WRIST-TAIL01';scene['A14 parts SHA256']=sha(OUT/'parts.json');scene['Original native SHA256']=sha(source)
native=ROOT/'work/arm-a14/wrist-tail01/actual-motors.blend' if ACTUAL else OUT/'A14-WRIST-TAIL01.blend';native.parent.mkdir(parents=True,exist_ok=True);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
if ACTUAL:
 cam=bpy.data.objects['Review_camera'];images={}
 for name in ['attention','idle','reference']:
  for j,q in zip(D['layout']['joints'],D['layout']['poses'][name]):o=bpy.data.objects[j['id']+'.rotor'];o['angle_deg']=q;o.update_tag()
  bpy.context.view_layer.update();pos,target,scale={'attention':((-.7,1.28,.67),(0,.33,.27),1.19),'idle':((-.5,.9,.45),(0,.2,.19),.91),'reference':((-.9,1.48,.65),(0,.4,.29),1.42)}[name]
  cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True);images[name]=sha(OUT/(name+'.png'))
 (OUT/'render-source.json').write_text(json.dumps(dict(native_sha256=sha(native),parts_source_sha256=sha(OUT/'parts.json'),images=images,full_size_supplier_motors=True,harness_drawn=False),indent=2)+'\n')
print('TAIL_NATIVE_COMPLETE',ACTUAL,flush=True)
