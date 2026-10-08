# SPDX-License-Identifier: CC-BY-NC-4.0
"""Render integrated frame with a wider camera; preserve assembled visibility."""
import bpy,json
from pathlib import Path
from mathutils import Vector
out=Path(bpy.data.filepath).parent
manifest=json.loads((out/'exterior-manifest.json').read_text())
scene=bpy.context.scene; camera=scene.camera
original=(camera.location.copy(),camera.rotation_euler.copy(),camera.data.ortho_scale)
hidden=[]
try:
 for part in manifest['parts']:
  if part['viewer_group']!='cover_support':
   obj=bpy.data.objects[part['id']];hidden.append((obj,obj.hide_render));obj.hide_render=True
 camera.location=(.30,.42,.38)
 camera.rotation_euler=(Vector((0,.0695,.030))-camera.location).to_track_quat('-Z','Y').to_euler()
 camera.data.ortho_scale=.37
 scene.render.filepath=str(out/'frame.png')
 bpy.ops.render.render(write_still=True)
finally:
 for obj,state in hidden: obj.hide_render=state
 camera.location,camera.rotation_euler,camera.data.ortho_scale=original
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('B05_FRAME_REVIEW_COMPLETE')
