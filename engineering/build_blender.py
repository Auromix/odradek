# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Run with Blender --background --factory-startup --python this_file.

Articulated dimensioned layout, NOT manufacturing CAD. Generated STL is mm;
Blender uses metre geometry and actual pivot hierarchy. No implicit IK motion.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[1]
bpy.context.preferences.filepaths.save_version=0
OUT=ROOT/'engineering/generated/layout'
p=json.loads((ROOT/'engineering/parameters/r4-layout.json').read_text())
manifest=json.loads((OUT/'manifest.json').read_text())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='MILLIMETERS'
scene.render.engine='CYCLES';scene.cycles.samples=32
scene.render.resolution_x=1600;scene.render.resolution_y=1400;scene.render.resolution_percentage=100
scene.world.color=(.05,.05,.05)
scene.view_settings.view_transform='AgX'
scene.render.image_settings.file_format='PNG'


def material(name,color,metallic=.0,roughness=.45,emission=0):
    m=bpy.data.materials.new(name);m.use_nodes=True
    bsdf=m.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=(*color,1)
    bsdf.inputs['Metallic'].default_value=metallic;bsdf.inputs['Roughness'].default_value=roughness
    if emission:
        bsdf.inputs['Emission Color'].default_value=(*color,1);bsdf.inputs['Emission Strength'].default_value=emission
    return m


def empty(name,location,parent=None):
    ob=bpy.data.objects.new(name,None);scene.collection.objects.link(ob)
    ob.empty_display_type='ARROWS';ob.empty_display_size=.035;ob.parent=parent;ob.location=location
    return ob


joint_objects=[]
previous=Vector((0,0,0))
for i,j in enumerate(p['joints']):
    origin=Vector(j['origin_mm'])*.001
    ob=empty(j['id']+'_'+j['model'],origin-previous,joint_objects[-1] if i else None)
    ob.rotation_mode='AXIS_ANGLE';ob.rotation_axis_angle=(0,*j['axis'])
    ob['joint_lower_deg'],ob['joint_upper_deg']=j['limit_deg'];ob['status']='Study limits; not qualified'
    joint_objects.append(ob);previous=origin

face=Vector(p['head']['face_center_mm'])*.001;finger_objects={};finger_roots={}
for f in p['head']['fingers']:
    phi=math.radians(f['phi_deg']);er=Vector((math.cos(phi),math.sin(phi),0))
    root=face+er*f['root_radius_mm']*.001+Vector((0,0,f['root_z_mm']*.001))
    ob=empty('FINGER_'+f['id'],root,joint_objects[-1])
    ob.matrix_parent_inverse=Matrix.Translation(-previous)
    ob.rotation_mode='AXIS_ANGLE';ob.rotation_axis_angle=(0,math.sin(phi),-math.cos(phi),0)
    ob['positive_axis']='minus local tangent: forward curling';ob['dof']=1
    finger_objects[f['id']]=ob;finger_roots[f['id']]=root

for entry in manifest['parts']:
    bpy.ops.wm.stl_import(filepath=str(OUT/entry['mesh']))
    ob=bpy.context.object;ob.name=entry['name']
    for v in ob.data.vertices:v.co*=.001
    color=entry['material_color'];category=entry['category']
    metallic=.45 if category in ['output_visual','beam_study','trim'] else .05
    mat=material(ob.name+'_mat',color,metallic=metallic,
                 roughness=.48 if category!='contact_candidate' else .85,emission=.8 if category=='finger_light' else 0)
    ob.data.materials.clear();ob.data.materials.append(mat)
    if entry['finger']:
        ob.parent=finger_objects[entry['finger']];ob.matrix_parent_inverse=Matrix.Translation(-finger_roots[entry['finger']])
    elif entry['attachment']:
        n=entry['attachment'];ob.parent=joint_objects[n-1]
        ob.matrix_parent_inverse=Matrix.Translation(-Vector(p['joints'][n-1]['origin_mm'])*.001)
    ob['engineering_status']=category
    bevel=ob.modifiers.new('Display edge bevel only','BEVEL');bevel.width=.00045;bevel.segments=2
    if category in ['envelope','trim','camera_envelope']:
        for poly in ob.data.polygons:poly.use_smooth=True

amber=material('Amber LED pixels',(1.,.48,.065),roughness=.5,emission=3.)
for ix in range(-8,9):
    for iy in range(-8,9):
        r=math.hypot(ix,iy)
        ring=7.3<r<8.2
        arrow=(abs(ix)<=1 and -3<=iy<=3) or (iy==3-abs(ix) and abs(ix)<=3)
        if not (ring or arrow):continue
        bpy.ops.mesh.primitive_uv_sphere_add(segments=8,ring_count=4,radius=.0008,
                location=face+Vector((ix*.003,iy*.003,.0026)))
        pixel=bpy.context.object;pixel.name=f'PIXEL_{ix}_{iy}';pixel.data.materials.append(amber)
        pixel.parent=joint_objects[-1];pixel.matrix_parent_inverse=Matrix.Translation(-previous)

for i,angle in enumerate(p['poses_deg']['inspect']):
    ob=joint_objects[i];ob.rotation_axis_angle=(math.radians(angle),*p['joints'][i]['axis'])
for f in p['head']['fingers']:
    ob=finger_objects[f['id']];axis=ob.rotation_axis_angle[1:];ob.rotation_axis_angle=(math.radians(6),*axis)
scene['release_status']='R4 PACKAGING STUDY — NOT FOR MANUFACTURE'
scene['omissions']='No finished link connections, confirmed motor/hub drawings, belt supports or qualified harness routes'
scene['payload_requirement_kg']=2.;scene['payload_validated']=False
scene['parameter_revision']=p['revision']
scene['animation_note']='Geometry demo only: no trajectory qualification; no grasped-load breathing.'

# Check the native pivot hierarchy against a separate matrix POE evaluation.
tcp=empty('TCP_reference',Vector(p['head']['tcp_home_mm'])*.001,joint_objects[-1])
tcp.matrix_parent_inverse=Matrix.Translation(-previous)
def pose_transform(q):
    T=Matrix.Identity(4)
    for j,a in zip(p['joints'],q):
        o=Vector(j['origin_mm'])*.001
        T=T@Matrix.Translation(o)@Matrix.Rotation(math.radians(a),4,Vector(j['axis']))@Matrix.Translation(-o)
    return T
errors=[]
for label,q in p['poses_deg'].items():
    for i,a in enumerate(q):joint_objects[i].rotation_axis_angle=(math.radians(a),*p['joints'][i]['axis'])
    bpy.context.view_layer.update()
    expected=pose_transform(q)@Vector((*[x*.001 for x in p['head']['tcp_home_mm']],1))
    errors.append({'pose':label,'TCP_difference_mm':(tcp.matrix_world.translation-expected.to_3d()).length*1000})
assert max(r['TCP_difference_mm'] for r in errors)<.001
(OUT/'blender-hierarchy-check.json').write_text(json.dumps({'revision':p['revision'],'TCP_checks':errors,'joint_count':7,'independent_finger_count':4},indent=2)+'\n')
for i,a in enumerate(p['poses_deg']['inspect']):joint_objects[i].rotation_axis_angle=(math.radians(a),*p['joints'][i]['axis'])
scene.render.fps=24;scene.frame_start=1;scene.frame_end=360
for frame_no,closed_fraction in [(1,0.),(24,0.),(180,1.),(204,1.),(360,0.)]:
    for f in p['head']['fingers']:
        ob=finger_objects[f['id']];axis=ob.rotation_axis_angle[1:]
        ob.rotation_axis_angle=(math.radians(f['closure_study_deg']*closed_fraction),*axis)
        ob.keyframe_insert(data_path='rotation_axis_angle',frame=frame_no)
for ob in finger_objects.values():
    action=ob.animation_data.action
    if hasattr(action,'fcurves'):
        for fc in action.fcurves:
            for key in fc.keyframe_points:key.interpolation='LINEAR'
scene.frame_set(1)

# Scene presentation: only the dimensioned CAD meshes supply product geometry.
floor=material('Backdrop',(.70,.73,.75),roughness=.8)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.001))
bpy.context.object.name='Backdrop';bpy.context.object.data.materials.append(floor)
target=Vector((.05,0,.42))
def aim(ob,point):ob.rotation_euler=(Vector(point)-ob.location).to_track_quat('-Z','Y').to_euler()
for name,loc,power,size in [('Key',(1.3,-1.6,2.3),55,2.2),('Fill',(-1.8,-.5,1.4),25,2.),('Rim',(.3,1.2,1.9),65,1.5)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=loc;aim(ob,target)
data=bpy.data.cameras.new('Engineering presentation');camera=bpy.data.objects.new('Camera',data)
scene.collection.objects.link(camera);camera.location=(1.5,-1.8,1.15);aim(camera,target)
data.type='ORTHO';data.ortho_scale=1.10;scene.camera=camera
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'odradek-r4-layout.blend'))
scene.render.filepath=str(OUT/'odradek-r4-inspect.png');bpy.ops.render.render(write_still=True)
# Full front view of the detachable head, with upper/lower asymmetry visible.
for i in range(7):joint_objects[i].rotation_axis_angle=(0,*p['joints'][i]['axis'])
for ob in scene.objects:
    if ob.type=='MESH' and not ob.name.startswith(('HEAD_','CAM_','F_','PIXEL_','Backdrop')):
        ob.hide_render=True
camera.location=face+Vector((0,0,1.));aim(camera,face);data.ortho_scale=.46
scene.render.resolution_x=1600;scene.render.resolution_y=1200
scene.render.filepath=str(OUT/'odradek-r4-head-front.png');bpy.ops.render.render(write_still=True)
# Oblique closed-state image makes the 50 mm root offset visible.
scene.frame_set(180)
camera.location=face+Vector((.55,-.70,.8));aim(camera,face+Vector((0,0,.035)));data.ortho_scale=.40
scene.render.filepath=str(OUT/'odradek-r4-head-closed.png');bpy.ops.render.render(write_still=True)
print('Saved native Blender hierarchy/animation and three parameter-derived renders.')
