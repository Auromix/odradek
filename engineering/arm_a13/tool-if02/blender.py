# SPDX-License-Identifier: CC-BY-NC-4.0
from pathlib import Path
import bpy,json,hashlib,sys,math
from mathutils import Vector,Matrix
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=HERE/'build';ACTUAL='--actual' in sys.argv
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();D=json.loads((OUT/'manifest.json').read_text())
kind='actual' if ACTUAL else 'public';source=ROOT/D['source_native_'+kind]
assert sha(source)==D['source_native_'+kind+'_sha256'];bpy.ops.wm.open_mainfile(filepath=str(source));scene=bpy.context.scene
for o in list(scene.objects):
 if o.name.startswith(('A13-IF-201','A13-IF-202','A13-IF-203','A13-IF-204','IF-','PWR-space','CTRL-space','CAM_UP-space','CAM_DOWN-space','A13-IF-G','A13-J7-G')):
  bpy.data.objects.remove(o,do_unlink=True)
col=bpy.data.collections.new('07_Recessed_Interface_Original_CAD');scene.collection.children.link(col)
alloc=bpy.data.collections.new('08_DATASHEET_BOXES_AND_ALLOCATIONS');scene.collection.children.link(alloc)
shell=bpy.data.materials['Graphite blue plastic prototype'];steel=bpy.data.materials['Purchased steel'];amber=bpy.data.materials['Amber fit coupons']
blue=amber.copy();blue.name='HFM dimensions only';blue.diffuse_color=(.08,.35,.52,1)
if blue.use_nodes:blue.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.08,.35,.52,1)
def mesh(p,collection,mat):
 me=bpy.data.meshes.new(p['id']);me.from_pydata([[v*.001 for v in t] for t in p['vertices_mm']],[],p['triangles']);me.update();me.materials.append(mat)
 me.set_sharp_from_angle(angle=math.radians(28))
 for f in me.polygons:f.use_smooth=True
 o=bpy.data.objects.new(p['id'],me);collection.objects.link(o);o.parent=bpy.data.objects[p['frame']];o.matrix_parent_inverse=Matrix.Identity(4)
 o['Source role']=p['role'];o['TOOL-IF02 manifest SHA256']=sha(OUT/'manifest.json');o['Load qualified']=False
 if p['role']=='fit_coupon':o.hide_render=True;o.hide_set(True)
 return o
for p in D['parts']:mesh(p,col,shell if p['role']!='fit_coupon' else amber)
for p in D['hardware']:mesh(p,col,steel)
for p in D['allocations']:
 o=mesh(p,alloc,blue if p['role'].startswith('datasheet') else amber)
 o['Geometry meaning']=p['role'];o.hide_render=True;o.hide_set(True)
scene['Revision']='A13-TOOL-IF02';scene['Tool interface manifest SHA256']=sha(OUT/'manifest.json')
scene['Scope']='Recessed manual interface trial. Supplier RS00 preserved; HFM full-body nominal boxes, PWR/CTRL allocations. Not a powered/load release.'
read=bpy.data.texts.new('TOOL_IF02_READ_FIRST');read.write((HERE/'README.md').read_text())
cam=bpy.data.objects['Review_camera'];cam.location=(.28,-.25,.19);cam.rotation_euler=(Vector((.065,0,.005))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.29
scene.cycles.samples=24;scene.render.resolution_x=1500;scene.render.resolution_y=1000
bpy.context.preferences.filepaths.save_version=0
native=ROOT/'work/arm-a13/tool-if02/actual-RS00-recessed-interface.blend' if ACTUAL else OUT/'A13-TOOL-IF02.blend'
native.parent.mkdir(parents=True,exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
if ACTUAL:
 scene.render.filepath=str(OUT/'recessed-closed.png');bpy.ops.render.render(write_still=True)
 # Open the dorsal shell and remove the tool-side verification cup for service.
 for name in ['A13-IF-302-dorsal-cover','A13-IF-304-tool-pocket','A13-IF-305-tool-pocket-cover']:bpy.data.objects[name].hide_render=True
 for o in col.objects:
  if o.name.startswith(('IF02-tool-M4','IF02-roof-')):o.hide_render=True
 for o in alloc.objects:o.hide_render=False
 cam.location=(.27,-.20,.24);cam.rotation_euler=(Vector((.065,0,0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.29
 scene.render.filepath=str(OUT/'recessed-service.png');bpy.ops.render.render(write_still=True)
 # Section is an illustration derived from native geometry, not a modified release.
 for o in alloc.objects:o.hide_render=False
 cutter=bpy.data.objects.new('SECTION_CUTTER',None)
 bpy.ops.mesh.primitive_cube_add(size=1,location=(.055,-.1045,0));cutter=bpy.context.object;cutter.name='SECTION_CUTTER';cutter.dimensions=(.4,.191,.3);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 cutter.hide_render=True
 for o in list(scene.objects):
  if o.type!='MESH' or o==cutter or 'Coupon' in o.name:continue
  if o in alloc.objects[:]:continue
  if o.name.startswith(('A13-','J7-supplier','IF02-')):
   mod=o.modifiers.new('SECTION Y=-9mm for illustration','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
 for name in ['A13-IF-302-dorsal-cover','A13-IF-304-tool-pocket','A13-IF-305-tool-pocket-cover']:bpy.data.objects[name].hide_render=False
 for o in col.objects:
  if o.name.startswith('IF02-tool-M4'):o.hide_render=False
 cam.location=(.08,-.37,.05);cam.rotation_euler=(Vector((.065,0,0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.25
 scene.render.filepath=str(OUT/'recessed-section.png');bpy.ops.render.render(write_still=True)
 (OUT/'render-source.json').write_text(json.dumps(dict(native_sha256=sha(native),manifest_sha256=sha(OUT/'manifest.json'),source_native_sha256=sha(source),
  supplier_geometry=True,connector_geometry='Two sourced housing boxes per coax; PWR/CTRL allocations; no qualified mating or retention',section='Y=-9 mm render-only Boolean after assembled native saved',images={name:sha(OUT/name) for name in ['recessed-closed.png','recessed-service.png','recessed-section.png']}),indent=2)+'\n')
print('NATIVE',native,flush=True)
