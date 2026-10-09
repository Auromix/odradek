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
        if p['assembly_role'] in ('routing','environment'):o.hide_render=True
        elif p['assembly_role'] in ('structure','electronics'):o.hide_render=not showcontext
        elif p['assembly_role'] in ('cover','rear_lid'):o.hide_render=not showcover
modes(True,False)
view('front-three-quarter',(.30,.43,.29),(0,.075,.037),.32)
view('top',(0,.075,.85),(0,.075,.037),.32)
view('rear',(-.30,-.35,.24),(0,.075,.037),.32)
for p in D['parts']:
    if p['assembly_role']=='electronics':bpy.data.objects[p['id']].hide_render=False
view('rear-interfaces',(-.13,-.35,.16),(0,.015,.028),.23)
modes(False,True)
view('internal-fit',(.30,.43,.34),(0,.065,.085),.34)
modes(True,True)
view('root-integrated',(.30,.43,.34),(0,.075,.080),.34)

# All review contexts are native budget solids; nothing is saved back to geometry.
for p in D['parts']:
    if p['assembly_role']=='environment':bpy.data.objects[p['id']].hide_render=False
bpy.data.objects['Render backdrop only'].hide_render=True
view('clamp-and-shelf',(.43,-.46,.10),(0,.11,-.060),.62)

# Detail view of the actual native lamp models and current fixing hardware.
for p in D['parts']:
    bpy.data.objects[p['id']].hide_render=not (p['id'].startswith(('LIGHT-NATIVE','HW-LIGHT')) or p['id']=='B06-308-LENS-RETAINER')
bpy.data.objects['Render backdrop only'].hide_render=False
pcb=bpy.data.objects['LIGHT-NATIVE-01']
mat=bpy.data.materials.new('Light PCB green / presentation only');mat.use_nodes=True
shader=mat.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(.01,.09,.04,1)
shader.inputs['Metallic'].default_value=0;shader.inputs['Roughness'].default_value=.6
pcb.data.materials.clear();pcb.data.materials.append(mat)
view('light-board-mount',(.055,.208,.090),(0,.162,.047),.085)
