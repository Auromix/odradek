# SPDX-License-Identifier: CC-BY-NC-4.0
"""Refresh all original part meshes from current manifest in an existing native rig.
Preserves actual supplier meshes and independent seven-axis controls.
"""
import bpy,json,hashlib,sys,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'engineering/arm_a10/build';FILE=OUT/'manifest.json';d=json.loads(FILE.read_text());scene=bpy.context.scene
for p in d['parts']:
 o=bpy.data.objects[p['id']];old=o.data;materials=list(old.materials);me=bpy.data.meshes.new(p['id']+'_current');me.from_pydata([tuple(v*.001 for v in point) for point in p['vertices_mm']],[],p['triangles']);me.update()
 for m in materials:me.materials.append(m)
 for q in me.polygons:q.use_smooth=True
 me.set_sharp_from_angle(angle=math.radians(35));o.data=me
 if not old.users:bpy.data.meshes.remove(old)
 for k in ['role','material','note','mass_kg','frame','solid_count']:o[k]=p[k]
sha=hashlib.sha256(FILE.read_bytes()).hexdigest();scene['Source manifest SHA256']=sha
for text in bpy.data.texts:
 if text.name=='READ_ME_3KG_TARGET':
  content=text.as_string();content=content[:content.index('CAD manifest SHA256: ')]+'CAD manifest SHA256: '+sha;text.clear();text.write(content)
def pose(name):
 for j,q in zip(d['layout']['joints'],d['layout']['poses'][name]):bpy.data.objects[j['id']+'.rotor']['angle_deg']=q;bpy.data.objects[j['id']+'.rotor'].update_tag()
 bpy.context.view_layer.update()
pose('attention');bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
if '--render' in sys.argv:
 scene.cycles.samples=24
 for name in ['attention','idle','reference']:
  pose(name);scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
print('REFRESH_NATIVE',bpy.data.filepath,len(d['parts']),sha,flush=True)
