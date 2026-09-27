# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Native 7+4 hierarchy; P16 endpoint linkages use persistent expression drivers.

Run Blender --background --factory-startup --python this_file -- --mesh-json PATH
All angles are geometric controls, not qualified hardware trajectories.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--mesh-json',type=Path,required=True)
parser.add_argument('--out',type=Path)
parser.add_argument('--home-scale',type=float,default=1.27)
parser.add_argument('--home-target-z',type=float,default=.44)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
ROOT=Path(__file__).resolve().parents[1]
GENERATOR_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
OUT=args.out or ROOT/'engineering/generated/integrated-arm-preview'
OUT.mkdir(parents=True,exist_ok=True)
data=json.loads(args.mesh_json.read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
scene.name='ODRADEK_7_PLUS_4_REVIEW'
scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='MILLIMETERS'
scene.render.engine='CYCLES';scene.cycles.samples=32
scene.render.resolution_x=1600;scene.render.resolution_y=1300;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.52,.59,.64,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.32
scene['status']=data['scope'];scene['manufacturing_release']=False
scene['controls']='J1..J7 and FINGER_UR/UL/LL/LR have q_deg custom properties. P16 follows its two pins with algebraic drivers.'
scene['motion_warning']='No torque, cable, collision, velocity or duty qualification. Do not use as an executable trajectory.'
scene['omissions']='; '.join(data['omissions'])
collection=bpy.data.collections.new('Product geometry');scene.collection.children.link(collection)
controls=bpy.data.collections.new('11 geometric controls');scene.collection.children.link(controls)
display=bpy.data.collections.new('Presentation only');scene.collection.children.link(display)


def material(name,colour,metallic=.0,roughness=.45,emission=0,alpha=1):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*colour,alpha)
    p.inputs['Metallic'].default_value=metallic;p.inputs['Roughness'].default_value=roughness
    if emission:p.inputs['Emission Color'].default_value=(*colour,1);p.inputs['Emission Strength'].default_value=emission
    if alpha<1:
        p.inputs['Alpha'].default_value=alpha
        m.surface_render_method='DITHERED'
    return m


materials={
 'structure':material('Graphite structural metal',(.026,.040,.052),.30,.44),
 'base':material('Anchored base',(.022,.032,.042),.30,.46),
 'joint_envelope':material('Catalog housing envelope',(.035,.045,.059),.30,.40),
 'aluminum':material('Head aluminum',(.055,.078,.095),.35,.40),
 'steel':material('Steel',(.25,.28,.32),.8,.28),
 'LED':material('Amber LED',(.98,.43,.025),.03,.4,3.),
 'PCB':material('PCB',(.018,.065,.055),.05,.5),
 'rubber':material('Contact elastomer',(.055,.14,.13),0,.8),
 'dark':material('Dark electrical',(.012,.019,.028),.02,.45),
 'optics':material('Light diffuser',(.69,.57,.27),0,.6,.14,.24),
 'reserve':material('Unbuilt reservation',(.18,.14,.24),0,.5,0,.08),
 'ground':material('Ground',(.26,.31,.35),0,.7)}


def pick(part):
    name=part['id'];mat=part['material']
    if '_LED_' in name:return materials['LED']
    if 'PCB_outline' in name:return materials['PCB']
    if 'optical_sheet' in name:return materials['optics']
    if mat=='space_reservation':return materials['reserve']
    if mat.startswith('silicone'):return materials['rubber']
    if mat in ['P16_envelope','catalog_camera','electronic_mass_TBD']:return materials['dark']
    return materials.get(mat,materials['steel'])


def attach_keep_world(ob,parent,world):
    ob.parent=parent
    ob.matrix_parent_inverse=parent.matrix_world.inverted() if parent else Matrix.Identity(4)
    ob.matrix_world=world
    bpy.context.view_layer.update()


def empty(name,point,parent=None,axis=None,limits=None):
    ob=bpy.data.objects.new(name,None);controls.objects.link(ob)
    ob.empty_display_type='ARROWS';ob.empty_display_size=.025
    attach_keep_world(ob,parent,Matrix.Translation(point))
    if axis is not None:
        ob.rotation_mode='AXIS_ANGLE';ob.rotation_axis_angle=(0,*axis)
    if limits:
        ob['q_deg']=0.;ob['lower_study_deg']=limits[0];ob['upper_study_deg']=limits[1]
        ob.id_properties_ui('q_deg').update(min=limits[0],max=limits[1],soft_min=limits[0],soft_max=limits[1],description='Geometry study angle; not a hardware limit')
        driver(ob,'rotation_axis_angle',0,ob,'q*pi/180')
    return ob


def driver(ob,path,index,control,expression):
    fc=ob.driver_add(path,index);d=fc.driver;d.type='SCRIPTED'
    var=d.variables.new();var.name='q';var.type='SINGLE_PROP'
    var.targets[0].id=control;var.targets[0].data_path='["q_deg"]'
    d.expression=expression


joints=[]
for j in data['joints']:
    ob=empty(j['id'],Vector(j['origin_mm'])*.001,joints[-1] if joints else None,j['axis'],j['limit_deg'])
    ob['candidate_model']=j['model'];joints.append(ob)
face=Vector(data['head_face_world_mm'])*.001
head=empty('HEAD_DETACHABLE',face,joints[-1])
finger_controls={};actuator_controls={};slider_controls={};finger_specs={}
for f in data['finger_joints']:
    key=f['id'];root=face+Vector(f['pivot_head_mm'])*.001
    finger=empty('FINGER_'+key,root,head,f['closing_axis_head'],f['range_deg'])
    finger_controls[key]=finger;finger_specs[key]=f
    closing=Vector(f['closing_axis_head']);tangent=-closing
    radial=Vector((tangent.y,-tangent.x,0))
    sign=f['mechanical_mirror_sign']
    A=root+tangent*(-.018*sign)+Vector((0,0,-.123))
    theta0=math.atan2(26*math.cos(math.radians(-68)),123+26*math.sin(math.radians(-68)))
    L0=math.sqrt(123**2+26**2+2*123*26*math.sin(math.radians(-68)))
    actuator=empty('P16_'+key+'_body_pivot',A,head,tangent)
    driver(actuator,'rotation_axis_angle',0,finger,f'atan2(26*cos(q*pi/180-68*pi/180),123+26*sin(q*pi/180-68*pi/180))-({theta0:.17g})')
    slider=empty('P16_'+key+'_slider',Vector((0,0,0)),actuator)
    w0=radial*math.sin(theta0)+Vector((0,0,math.cos(theta0)))
    for k in range(3):
        driver(slider,'location',k,finger,f'({w0[k]:.17g})*(sqrt(123*123+26*26+2*123*26*sin(q*pi/180-68*pi/180))-({L0:.17g}))*0.001')
    actuator_controls[key]=actuator;slider_controls[key]=slider

objects={}
for part in data['parts']:
    mesh=bpy.data.meshes.new(part['id']+'_mesh')
    mesh.from_pydata(part['vertices_m'],[],part['triangles']);mesh.update()
    ob=bpy.data.objects.new(part['id'],mesh);collection.objects.link(ob)
    ob.data.materials.append(pick(part));ob['source']=part['source'];ob['volume_mm3']=part['volume_mm3']
    ob['geometry_group']=part['group'];ob['manufacturing_release']=False
    if part['group']=='head_fixed':parent=head
    elif part['group'].endswith('_rotor'):parent=finger_controls[part['finger']]
    elif part['group'].endswith('_P16_kinematic'):
        parent=slider_controls[part['finger']] if part['id'].endswith(('_slider','_tip')) else actuator_controls[part['finger']]
    else:parent=joints[part['attachment']-1] if part['attachment'] else None
    attach_keep_world(ob,parent,Matrix.Identity(4));objects[part['id']]=ob
    if part['material']=='space_reservation':ob.hide_render=True

# Presentation-only central display. There is no PCB, power, mounting or
# thermal qualification behind these pixels. Product mass/part count excludes
# this isolated collection, which can be hidden without changing the CAD.
ui=bpy.data.collections.new('UI preview only - unbuilt central display')
scene.collection.children.link(ui)
ui['status']='Visual pixel map only; not a selected or manufactured display assembly'
off_material=material('Unlit display pixels',(.006,.004,.002),0,.9)
off_material.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=0.


def ui_disks(name,disks,mat):
    vertices=[];faces=[]
    for x,y,z,r,n in disks:
        start=len(vertices)
        vertices += [(face.x+x+r*math.cos(2*math.pi*k/n),face.y+y+r*math.sin(2*math.pi*k/n),face.z+z) for k in range(n)]
        faces.append(tuple(range(start,start+n)))
    mesh=bpy.data.meshes.new(name+'_mesh');mesh.from_pydata(vertices,[],faces);mesh.update()
    ob=bpy.data.objects.new(name,mesh);ui.objects.link(ob);ob.data.materials.append(mat)
    ob['status']='Presentation only; no physical BOM or mass';attach_keep_world(ob,head,Matrix.Identity(4))


ui_disks('UI_PREVIEW_dark_face',[(0,0,.0002,.031,96)],materials['dark'])
lit=[];unlit=[]
for x,y in data['central_pixel_preview_mm']:
    r=math.hypot(x,y)
    ring=24<=r<=28.5
    arrow=(abs(x)<=9 and abs(y-(12-abs(x)))<=.2) or (abs(x)<.2 and -9<=y<=9)
    (lit if ring or arrow else unlit).append((x*.001,y*.001,.0006,.0007,8))
ui_disks('UI_PREVIEW_lit_pixels',lit,materials['LED'])
ui_disks('UI_PREVIEW_unlit_pixels',unlit,off_material)


def set_pose(q,angles=None):
    for ob,a in zip(joints,q):ob['q_deg']=float(a);ob.update_tag()
    if angles is not None:
        for k,angle in angles.items():finger_controls[k]['q_deg']=float(angle);finger_controls[k].update_tag()
    scene.frame_set(scene.frame_current);bpy.context.view_layer.update()


checks=[]
for name,q in data['poses_deg'].items():
    set_pose(q,{k:0 for k in finger_controls})
    for row in [r for r in data['arm_vertex_checks'] if r['pose']==name]:
        ob=objects[row['part']];actual=ob.matrix_world@ob.data.vertices[0].co
        error=(actual-Vector(row['expected_vertex_world_m'])).length*1000
        assert error<.005,(row,error)
        checks.append({'pose':name,'part':row['part'],'vertex_error_mm':error})

# Independent home-head point transforms check all rotor and actuator objects.
set_pose([0]*7,{k:0 for k in finger_controls})
head_checks=[]
for angles in [{k:45. for k in finger_controls},{k:finger_specs[k]['range_deg'][1] for k in finger_controls},dict(UR=17.,UL=65.,LL=31.,LR=112.)]:
    set_pose([0]*7,angles)
    for part in data['parts']:
        if part['group']=='head_fixed' or not part.get('finger'):continue
        f=finger_specs[part['finger']];q=math.radians(angles[f['id']]);point=Vector(part['vertices_m'][0])
        root=face+Vector(f['pivot_head_mm'])*.001;closing=Vector(f['closing_axis_head'])
        if part['group'].endswith('_rotor'):
            expected=root+Matrix.Rotation(q,3,closing)@(point-root)
        else:
            tangent=-closing;radial=Vector((tangent.y,-tangent.x,0));sign=f['mechanical_mirror_sign']
            A=root+tangent*(-.018*sign)+Vector((0,0,-.123))
            theta0=math.atan2(26*math.cos(math.radians(-68)),123+26*math.sin(math.radians(-68)))
            theta=math.atan2(26*math.cos(q-math.radians(68)),123+26*math.sin(q-math.radians(68)))
            delta=0.
            if part['id'].endswith(('_slider','_tip')):
                delta=(math.sqrt(123**2+26**2+2*123*26*math.sin(q-math.radians(68)))-math.sqrt(123**2+26**2+2*123*26*math.sin(math.radians(-68))))*.001
            w0=radial*math.sin(theta0)+Vector((0,0,math.cos(theta0)))
            expected=A+Matrix.Rotation(theta-theta0,3,tangent)@(point-A+w0*delta)
        ob=objects[part['id']];actual=ob.matrix_world@ob.data.vertices[0].co
        error=(actual-expected).length*1000
        assert error<.005,(part['id'],angles,error)
        head_checks.append({'part':part['id'],'q_deg':angles[f['id']],'vertex_error_mm':error})

# Independent CAD endpoint cross-check: the closed meshes were regenerated
# from the BREP assembly, not from the Blender formula used above. Tessellated
# bounds may lie inside curved exact surfaces, so allow 0.20mm mesh tolerance.
set_pose([0]*7,{k:finger_specs[k]['range_deg'][1] for k in finger_controls})
closed_checks=[]
for name,wanted in data['independent_closed_CAD_bounds_head_mm'].items():
    ob=objects[name];v=np.array([tuple(x.co) for x in ob.data.vertices]);T=np.array(ob.matrix_world)
    assert np.all(np.isfinite(v)) and np.all(np.isfinite(T))
    v=np.einsum('ij,nj->ni',T[:3,:3],v)+T[:3,3]
    assert np.all(np.isfinite(v))
    actual=np.array([v.min(axis=0),v.max(axis=0)])*1000-np.array(data['head_face_world_mm'])
    error=float(np.max(abs(actual-np.array(wanted))))
    assert error<.20,(name,'independent closed BREP bounds error mm',error)
    closed_checks.append({'part':name,'max_bound_error_mm':error})


def aim(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()


ground=bpy.data.meshes.new('Floor_mesh')
ground.from_pydata([(-4,-4,-.042),(4,-4,-.042),(4,4,-.042),(-4,4,-.042)],[],[(0,1,2,3)])
g=bpy.data.objects.new('PRESENTATION_FLOOR',ground);display.objects.link(g);g.data.materials.append(materials['ground'])
target=Vector((.12,0,.4))
for name,delta,power,size in [('key',(1,-1,1.5),125,1.2),('fill',(-1,-.4,.7),65,1.0),('rim',(0,1.2,1.2),145,1.)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.size=size
    ob=bpy.data.objects.new(name,light);display.objects.link(ob);ob.location=target+Vector(delta);aim(ob,target)
camera_data=bpy.data.cameras.new('Review_camera');camera=bpy.data.objects.new('Review_camera',camera_data)
display.objects.link(camera);scene.camera=camera;camera_data.type='ORTHO'


def render(name,position,target,scale,up=None):
    camera.location=position;aim(camera,target);camera_data.ortho_scale=scale
    if up is not None:
        forward=(Vector(target)-position).normalized()
        right=forward.cross(Vector(up)).normalized();vertical=right.cross(forward).normalized()
        camera.rotation_euler=Matrix((right,vertical,-forward)).transposed().to_euler()
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)


set_pose(data['poses_deg']['inspect'],{k:0 for k in finger_controls})
render('arm-open-oblique',Vector((1.65,-2.1,1.45)),Vector((.19,0,.39)),1.13)
set_pose([0]*7,{k:0 for k in finger_controls})
render('arm-home-structure',Vector((1.6,-2.2,1.75)),Vector((0,0,args.home_target_z)),args.home_scale)
render('head-open',face+Vector((.15,-.18,.85)),face+Vector((0,0,-.035)),.52,up=(0,1,0))
set_pose([0]*7,{k:finger_specs[k]['range_deg'][1] for k in finger_controls})
render('head-closed',face+Vector((.22,-.26,.72)),face+Vector((0,0,.015)),.42,up=(0,1,0))
set_pose(data['poses_deg']['inspect'],{k:0 for k in finger_controls})
camera.location=Vector((1.65,-2.1,1.45));aim(camera,Vector((.19,0,.39)));camera_data.ortho_scale=1.13
for ob in bpy.context.selected_objects:ob.select_set(False)
joints[0].select_set(True);bpy.context.view_layer.objects.active=joints[0]
text=bpy.data.texts.new('READ_ME')
text.write('Odradek integrated candidate geometry.\nEdit q_deg on the 11 controls. P16 moves through algebraic drivers saved in this file; no frame handlers or external runtime needed.\nSeven OEM housings are original catalog envelopes, not precise purchased-part surfaces.\nNo full-arm collision, cables, stiffness, thermal or payload qualification. No manufacture release.\nCC BY-NC 4.0; Auromix contributors.\n')
text.write('The separate UI preview collection shows a central 285-pixel ring/arrow only. It is not physical CAD or a released display and is excluded from all mass/part counts.\n')
assert GENERATOR_SHA256==hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'Generator changed while running; rerun before publishing evidence'
path=OUT/'odradek-integrated-7-plus-4.blend';bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
report={'revision':data['revision'],'parts':len(objects),'arm_vertex_checks':checks,'finger_and_P16_vertex_checks':head_checks,
        'independent_closed_CAD_bounds_checks':closed_checks,'mesh_bound_tolerance_mm':.20,
        'source_hashes':data['source_hashes'],'mesh_export_generator_sha256':data['generator_sha256'],
        'blender_generator_sha256':GENERATOR_SHA256,
        'blend_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'manufacturing_release':False,'scope':data['scope'],
        'home_view':{'ortho_scale_m':args.home_scale,'target_z_m':args.home_target_z},
        'native_controls':7+len(finger_controls),'P16_drivers':'Body aim plus extension; not a rigid finger child',
        'omissions':data['omissions'],
        'central_display_preview':{'pixels':len(data['central_pixel_preview_mm']),'lit_pixels':len(lit),'physical_design':False,'included_in_mass_or_parts':False},
        'render_names':['arm-open-oblique.png','arm-home-structure.png','head-open.png','head-closed.png']}
(OUT/'evidence.json').write_text(json.dumps(report,indent=2)+'\n')
print('Saved integrated native model. Parts:',len(objects),'arm checks:',len(checks),'head checks:',len(head_checks))
