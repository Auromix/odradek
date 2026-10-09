# SPDX-License-Identifier: CC-BY-NC-4.0
"""Tool interface prototype on the pinned native RS00 local assembly."""
from pathlib import Path
import bpy,json,math,hashlib,sys
from mathutils import Vector,Matrix
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=HERE/'build'
ACTUAL='--actual' in sys.argv;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
D=json.loads((OUT/'manifest.json').read_text())
source=ROOT/D['previous_native_actual' if ACTUAL else 'previous_native_public']
assert sha(source)==D['previous_native_actual_sha256' if ACTUAL else 'previous_native_public_sha256']
bpy.ops.wm.open_mainfile(filepath=str(source));scene=bpy.context.scene
old=bpy.data.objects[D['replaces']];bpy.data.objects.remove(old,do_unlink=True)
for o in list(scene.objects):
 if o.name.startswith('FLANGE-'):bpy.data.objects.remove(o,do_unlink=True)
col=bpy.data.collections.new('05_Tool_Interface_Original_CAD');scene.collection.children.link(col)
budgets=bpy.data.collections.new('06_Connector_SPACE_ALLOCATIONS_NOT_VENDOR');scene.collection.children.link(budgets)
shell=bpy.data.materials['Graphite blue plastic prototype'];metal=bpy.data.materials['Purchased steel'];gauge=bpy.data.materials['Amber fit coupons']
def mesh(p,target,mat):
 me=bpy.data.meshes.new(p['id']);me.from_pydata([[v*.001 for v in xyz] for xyz in p['vertices_mm']],[],p['triangles']);me.update();me.materials.append(mat)
 me.set_sharp_from_angle(angle=math.radians(28))
 for face in me.polygons:face.use_smooth=True
 o=bpy.data.objects.new(p['id'],me);target.objects.link(o);o.parent=bpy.data.objects[p['frame']];o.matrix_parent_inverse=Matrix.Identity(4)
 o['Source role']=p['role'];o['Interface source manifest SHA256']=sha(OUT/'manifest.json');o['Load qualified']=False
 if 'step_sha256' in p:o['Owned STEP SHA256']=p['step_sha256']
 return o
for p in D['parts']:
 o=mesh(p,col,gauge if p['role']=='fit_coupon' else shell)
 if p['role']=='fit_coupon':o.hide_render=True;o.hide_set(True)
for p in D['hardware']:mesh(p,col,metal)
for p in D['allocations']:
 o=mesh(p,budgets,gauge);o['Exact vendor connector']=False;o['Geometry meaning']='Space budget only; connector retention and final PN pending'
 o.hide_render=True;o.hide_set(True)
scene['Revision']='A13-TOOL-IF01';scene['Tool interface manifest SHA256']=sha(OUT/'manifest.json')
scene['Scope']='Tool mechanical fit + four connector space allocations; no energized wiring or dynamic coax qualification'
scene['Print release']=False
text=bpy.data.texts.new('TOOL_IF01_READ_FIRST');text.write('Original CAD: new piloted output flange, tool-side receiver, replaceable four-slot panel, open-top service tray and removable cover.\nPWR / CTRL / CAM_UP / CAM_DOWN have independent planning blocks. These are not vendor CAD.\nControl may use CAN or a different EtherCAT/RJ45 insert. Do not wire arbitrary RJ45 pins.\nPoC conditional on camera/source; supply voltage/current and exact connectors pending.\nNo hollow RS00 or tight coax bend assumed.\nRead README and interface.json. Unpowered supported trial only.\n')
cam=bpy.data.objects['Review_camera'];cam.location=(.28,-.25,.19);cam.rotation_euler=(Vector((.075,0,.012))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.29
scene.cycles.samples=24;scene.render.resolution_x=1500;scene.render.resolution_y=1000
bpy.context.preferences.filepaths.save_version=0;bpy.context.view_layer.update()
native=ROOT/'work/arm-a13/tool-if01/actual-RS00-tool-interface.blend' if ACTUAL else OUT/'A13-TOOL-IF01.blend'
native.parent.mkdir(parents=True,exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
if ACTUAL:
 scene.render.filepath=str(OUT/'interface-closed.png');bpy.ops.render.render(write_still=True)
 bpy.data.objects['A13-IF-204-service-cover'].hide_render=True
 for o in budgets.objects:o.hide_render=False
 for o in col.objects:
  if o.name.startswith('IF-cover-'):o.hide_render=True
 scene.render.filepath=str(OUT/'interface-open-reservations.png');bpy.ops.render.render(write_still=True)
 # Show the tool receiver and separable mechanical locator without the pod.
 for o in col.objects:
  if o.name.startswith(('A13-IF-202','A13-IF-203','A13-IF-204','IF-tray-','IF-cover-','IF-tool-')):o.hide_render=True
 for o in budgets.objects:o.hide_render=True
 bpy.data.objects['A13-IF-201-tool-receiver'].location.x=.045
 cam.location=(.23,-.20,.14);cam.rotation_euler=(Vector((.04,0,0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.24
 scene.render.filepath=str(OUT/'mechanical-interface-exploded.png');bpy.ops.render.render(write_still=True)
 (OUT/'render-source.json').write_text(json.dumps(dict(native_sha256=sha(native),manifest_sha256=sha(OUT/'manifest.json'),
  source_native_sha256=sha(source),supplier_geometry=True,connector_geometry='Space allocation blocks, no PN/retention qualification'),indent=2)+'\n')
print('NATIVE',native,flush=True)
