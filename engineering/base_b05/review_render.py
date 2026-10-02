# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Render the currently open native exterior scene without rebuilding it."""
import bpy
from pathlib import Path
from mathutils import Vector
out=Path(bpy.data.filepath).parent
scene=bpy.context.scene
camera=scene.camera
target=Vector((0,.080,.034))
views=[('front-three-quarter',(.39,.53,.34),.43),('top',(0,.080,.85),.40),('rear',(-.36,-.47,.26),.43)]
for name,position,scale in views:
    camera.location=position
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=scale
    scene.render.filepath=str(out/(name+'.png'))
    bpy.ops.render.render(write_still=True)
camera.location=views[0][1]
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.ortho_scale=views[0][2]
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('B05_THREE_VIEWS_COMPLETE')
