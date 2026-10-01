# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Import exact tessellated manufacturing solids; save editable .blend and renders."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent/'build'
data=json.loads((ROOT/'manifest.json').read_text())
NAME='ODR-BASE-'+data['revision']
cadmesh=json.loads((ROOT/'cad-surface-meshes.json').read_text()) if (ROOT/'cad-surface-meshes.json').exists() else {}
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='MILLIMETERS'
scene.render.engine='CYCLES';scene.cycles.samples=48
scene.cycles.use_denoising=True
scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.world.color=(.27,.29,.32)
scene.view_settings.view_transform='AgX'
collections={}
for name in ['01_Frame','02_Covers','03_Cradle','04_PCB','05_Fasteners','06_Cable_allocations','07_Desk_and_wall','08_Operation_guide']:
    c=bpy.data.collections.new(name);scene.collection.children.link(c);collections[name]=c
for p in data['parts']:
    id=p['id'];cat=p['category']
    if cat=='environment':group='07_Desk_and_wall'
    elif cat=='guide':group='08_Operation_guide'
    elif cat=='routing':group='06_Cable_allocations'
    elif cat=='component' or 'PCB' in id:group='04_PCB'
    elif cat in ['fastener','hardware']:group='05_Fasteners'
    elif id.startswith('B04-30'):group='02_Covers'
    elif id.startswith('B04-20') or id=='ENV-CONTROLLER':group='03_Cradle'
    else:group='01_Frame'
    if id in cadmesh:
        m=cadmesh[id];mesh=bpy.data.meshes.new(id);mesh.from_pydata(m['vertices'],[],m['faces']);mesh.update()
        obj=bpy.data.objects.new(id,mesh);scene.collection.objects.link(obj)
        for poly in mesh.polygons:poly.use_smooth=True
        mesh.normals_split_custom_set_from_vertices(m['normals'])
    else:
        bpy.ops.wm.stl_import(filepath=str(ROOT/p['stl']));obj=bpy.context.object;obj.name=id
    obj.scale=(.001,.001,.001)
    for col in list(obj.users_collection):col.objects.unlink(obj)
    collections[group].objects.link(obj)
    mat=bpy.data.materials.new(id);mat.diffuse_color=p['color'];mat.use_nodes=True
    bsdf=mat.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=p['color']
    bsdf.inputs['Metallic'].default_value=.72 if p['material'] in ['steel','S355','6061-T651','brass'] else .02
    bsdf.inputs['Roughness'].default_value=.34 if p['material'] in ['steel','6061-T651','brass'] else .5
    obj.data.materials.clear();obj.data.materials.append(mat)
    if id not in cadmesh:
        obj.data.set_sharp_from_angle(angle=math.radians(28))
        for poly in obj.data.polygons:poly.use_smooth=True
    obj['Part number']=id;obj['Process']=p['process'];obj['Material']=p['material'];obj['Status']=cat
    obj['Dimensions mm']=str(p['bbox']['size']);obj['Notes']=' | '.join(p['notes'])
    if cat in ['environment','guide']:obj.hide_render=True;obj.hide_set(True)
    if id=='B04-302-LIGHT-LENS':
        bsdf.inputs['Emission Color'].default_value=(1,.28,.015,1);bsdf.inputs['Emission Strength'].default_value=.4
    if id=='ENV-CONTROLLER':obj['Mass allocation kg']=3
    if cat=='custom' and id not in cadmesh:
        bevel=obj.modifiers.new('Render edge highlights only','BEVEL');bevel.width=.00025;bevel.segments=2
        bevel.show_viewport=False
target=Vector((0,.105,-.045))
def camera_at(pos,look=target,scale=.56):
    cam=bpy.data.objects.get('Review_camera')
    if not cam:
        bpy.ops.object.camera_add();cam=bpy.context.object;cam.name='Review_camera'
    cam.location=pos;cam.rotation_euler=(look-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.type='ORTHO';cam.data.ortho_scale=scale;scene.camera=cam
    return cam
camera_at((.55,.72,.37))
for name,loc,energy,size in [('Key',(.2,.1,.8),7,.55),('Fill',(-.5,.2,.3),4.5,.5),('Rim',(.1,-.5,.4),5.5,.4)]:
    bpy.ops.object.light_add(type='AREA',location=loc);obj=bpy.context.object;obj.name=name;obj.data.energy=energy;obj.data.shape='DISK';obj.data.size=size
    obj.rotation_euler=(target-obj.location).to_track_quat('-Z','Y').to_euler()
# Compact ground plane separate from actual desk geometry.
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.201));floor=bpy.context.object;floor.name='Render_floor'
mat=bpy.data.materials.new('Backdrop');mat.diffuse_color=(.64,.69,.74,1);floor.data.materials.append(mat);floor.hide_set(True)
# Viewport opens with a useful noncamera view, CAD axes preserved.
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_distance=.62
            area.spaces.active.region_3d.view_location=target
            area.spaces.active.region_3d.view_rotation=scene.camera.rotation_euler.to_quaternion()
            area.spaces.active.clip_start=.001;area.spaces.active.clip_end=100
scene['Review scope']='Base prototype only; not physically load-qualified.'
scene['CAD source']=NAME+'.step; Blender meshes imported from the same CAD tessellation.'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/(NAME+'.blend')))
views=['shield-closeup'] if '--closeup-only' in sys.argv else ['shield-closeup','assembled','open','exploded','rear']
for view in views:
    for obj in collections['02_Covers'].objects:obj.hide_render=view=='open'
    floor.hide_render=False
    for obj in bpy.data.objects:
        if 'Part number' not in obj:continue
        base=Vector((0,0,0));id=obj['Part number']
        if view=='exploded':
            if id.startswith('B04-301'):base.z=.12
            elif 'FLANGE' in id:base.z=.07
            elif id.startswith('B04-20') or 'ENV-CONTROLLER'==id:base.z=-.06
            elif 'PCB' in id:base.z=.045
        obj.location=base
    floor.location.z=-.265 if view=='exploded' else -.201
    camera_at((-.45,-.60,.28) if view=='rear' else (.55,.72,.37),scale=.69 if view=='exploded' else .56)
    desk=bpy.data.objects.get('ENV-DESK');desk.hide_render=view!='shield-closeup'
    if view=='shield-closeup':camera_at((.38,.57,.30),Vector((0,.12,.024)),scale=.38)
    scene.render.filepath=str(ROOT/f'{view}.png');bpy.ops.render.render(write_still=True)
print('BLENDER_RENDER_COMPLETE',flush=True)
