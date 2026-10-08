# SPDX-License-Identifier: CC-BY-NC-4.0
"""Render reopened actual B06 solids; no geometry changes."""
import bpy,json
from pathlib import Path
from mathutils import Vector
OUT=Path(bpy.data.filepath).parent
D=json.loads((OUT/'manifest.json').read_text())
scene=bpy.context.scene;camera=scene.camera
scene.cycles.samples=8
scene.render.resolution_x=1200;scene.render.resolution_y=900
def view(name,position,target,scale):
    camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True);print('RENDERED',name,flush=True)
def modes(showcover,showcontext):
    for p in D['parts']:
        o=bpy.data.objects[p['id']]
        if p['assembly_role']=='routing':o.hide_render=True
        elif p['assembly_role'] in ('structure','electronics'):o.hide_render=not showcontext
        elif p['assembly_role'] in ('cover','rear_lid'):o.hide_render=not showcover
modes(True,False)
view('front-three-quarter',(.30,.43,.29),(0,.075,.037),.32)
view('top',(0,.075,.85),(0,.075,.037),.32)
view('rear',(-.30,-.35,.24),(0,.075,.037),.32)
modes(False,True)
view('internal-fit',(.30,.43,.34),(0,.065,.085),.34)
modes(True,True)
view('root-integrated',(.30,.43,.34),(0,.075,.080),.34)
