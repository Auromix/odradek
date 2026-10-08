# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Render the currently open native exterior scene without rebuilding it."""
import bpy,json
from pathlib import Path
from mathutils import Vector
out=Path(bpy.data.filepath).parent
manifest=json.loads((out/'exterior-manifest.json').read_text())
for text in list(bpy.data.texts):
 if text.name.startswith(('B05 exterior parameters.json','B05 read me.txt')): bpy.data.texts.remove(text)
bpy.data.texts.new('B05 exterior parameters.json').write(json.dumps(manifest['parameters'],ensure_ascii=False,indent=2))
bpy.data.texts.new('B05 read me.txt').write('SHAPE-08: eight printable parts, integrated two-piece support frame and shallow shoulder grooves. Purchased hardware is not printable. Unpowered assembly candidate; no arm load/PCB integration qualification.')
scene=bpy.context.scene
camera=scene.camera
target=Vector((0,.080,.034))
views=[('front-three-quarter',(.39,.53,.34),.43),('top',(0,.080,.85),.43),('rear',(-.36,-.47,.26),.43)]
for name,position,scale in views:
 camera.location=position
 camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
 camera.data.ortho_scale=scale
 scene.render.filepath=str(out/(name+'.png'))
 bpy.ops.render.render(write_still=True)
 print('B05_RENDER_COMPLETE',name,flush=True)
hidden=[]
for part in manifest['parts']:
 if part['viewer_group']!='cover_support':
  obj=bpy.data.objects[part['id']];hidden.append((obj,obj.hide_render));obj.hide_render=True
camera.location=(.30,.42,.38)
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.ortho_scale=.37
scene.render.filepath=str(out/'frame.png')
bpy.ops.render.render(write_still=True)
for obj,state in hidden: obj.hide_render=state
camera.location=views[0][1]
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.ortho_scale=views[0][2]
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('B05_FOUR_VIEWS_COMPLETE')
