# SPDX-License-Identifier: CC-BY-NC-4.0
"""Export native whole-arm geometry to the offline viewer; suppliers local only."""
from pathlib import Path
import bpy,json,sys,hashlib
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent/'build';ACTUAL='--actual' in sys.argv
native=ROOT/'work/arm-a12/whole-style01/actual-motors.blend' if ACTUAL else OUT/'A12-A-whole-style.blend'
bpy.ops.wm.open_mainfile(filepath=str(native))
head=bpy.data.collections['81_Petal_Form_Reference_HIDDEN'];head.hide_viewport=False;head.hide_render=False
for obj in head.objects:obj.hide_set(False)
bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
D=json.loads((ROOT/'engineering/arm_a11/build/manifest.json').read_text())
metadata={p['id']:p for p in D['parts'] if p['role'] not in ['fit_coupon','printed_cover'] and (not ACTUAL or p['role']!='motor_envelope')}
if ACTUAL:
 for p in json.loads((ROOT/'work/arm-a10/vendor/meshes.json').read_text()):metadata[p['id']]=dict(p,role='supplier_visual_reference')
for p in json.loads((ROOT/'engineering/arm_a12/shoulder01/build/manifest.json').read_text())['parts']:metadata[p['id']]=dict(p,role='style_surface')
for p in json.loads((OUT/'style-surfaces.json').read_text())['style_surfaces']:metadata[p['id']]=p
for o in bpy.data.collections['81_Petal_Form_Reference_HIDDEN'].objects:
 if o.type=='MESH':metadata[o.name]=dict(id=o.name,frame='J7.rotor',role='head_reference')
def geometry(o,frame=None):
 e=o.evaluated_get(dg);me=e.to_mesh();me.calc_loop_triangles();matrix=e.matrix_world
 if frame:matrix=bpy.data.objects['Arm_mount_B05' if frame=='world' else frame].matrix_world.inverted() @ matrix
 vertices=[[round(v*1000,3) for v in matrix @ p.co] for p in me.vertices];faces=[list(t.vertices) for t in me.loop_triangles];e.to_mesh_clear()
 return dict(vertices=vertices,faces=faces)
parts=[]
for name,p in metadata.items():
 o=bpy.data.objects[name];color=list(o.data.materials[0].diffuse_color) if o.data.materials else [.06,.08,.10,1]
 parts.append(dict(id=name,frame=p['frame'],role=p['role'],color=color,**geometry(o,p['frame'])))
base=[dict(id=o.name,color=list(o.data.materials[0].diffuse_color) if o.data.materials else [.08,.10,.12,1],**geometry(o)) for o in bpy.data.collections['80_Base_Context'].objects if o.type=='MESH']
data=dict(long=dict(layout=D['layout'],parts=parts,flange_from_J7_mm=D['flange_from_J7_mm'],shoulder_torque=37.13,sha256=hashlib.sha256(native.read_bytes()).hexdigest(),known_conflicts=[]),base=base)
target=ROOT/'work/arm-a12/whole-style01/actual-viewer.json' if ACTUAL else ROOT/'work/arm-a12/whole-style01/public-viewer.json';target.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')))
print('EXPORTED',ACTUAL,len(parts),len(base),target.stat().st_size,flush=True)
