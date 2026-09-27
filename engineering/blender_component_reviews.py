# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Blender --background --factory-startup --python this_file -- --mesh-json PATH."""
import argparse,json,sys,math,hashlib
from pathlib import Path
import bpy
from mathutils import Matrix,Vector

parser=argparse.ArgumentParser();parser.add_argument('--mesh-json',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);data=json.loads(args.mesh_json.read_text())
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'engineering/generated/component-reviews';OUT.mkdir(parents=True,exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.read_factory_settings(use_empty=True)
colors={'metal':(.16,.22,.26),'amber':(1.,.52,.07),'rubber':(.035,.10,.11),'black':(.008,.016,.022),'object':(.68,.72,.75)}
materials={}
for name,color in colors.items():
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes.get('Principled BSDF')
    n.inputs['Base Color'].default_value=(*color,1);n.inputs['Metallic'].default_value=.6 if name=='metal' else .03
    n.inputs['Roughness'].default_value=.32 if name=='metal' else .65
    if name=='amber':n.inputs['Emission Color'].default_value=(*color,1);n.inputs['Emission Strength'].default_value=.6
    materials[name]=m
checks=[];made=[]
def aim(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
for spec in data['scenes']:
    scene=bpy.data.scenes.new(spec['name']);bpy.context.window.scene=scene;made.append(scene)
    scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='MILLIMETERS';scene.render.engine='CYCLES';scene.cycles.samples=24
    scene.render.resolution_x=1200;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
    scene.world=bpy.data.worlds.new(scene.name+'_world');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.70,.74,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
    scene['status']=spec['note'];scene['manufacturing_release']=False;scene['input_revision']=data['revision']
    pivots={}
    for key,p in spec.get('pivots',{}).items():
        ob=bpy.data.objects.new('FINGER_'+key,None);scene.collection.objects.link(ob);ob.location=Vector(p['root_mm'])*.001
        ob.empty_display_type='ARROWS';ob.empty_display_size=.02;ob.rotation_mode='AXIS_ANGLE';ob.rotation_axis_angle=(0,*p['axis'])
        ob['lower_deg']=0.;ob['upper_deg']=p['closed_deg'];pivots[key]=ob
    objects={}
    for part in spec['parts']:
        mesh=bpy.data.meshes.new(part['name']+'_mesh');mesh.from_pydata([[c*.001 for c in v] for v in part['vertices_mm']],[],part['triangles']);mesh.update()
        ob=bpy.data.objects.new(part['name'],mesh);scene.collection.objects.link(ob);ob.data.materials.append(materials[part['material']])
        ob['source']=part['source'];ob['CAD_volume_mm3']=part['solid_volume_mm3'];objects[part['name']]=ob
        if part.get('finger'):
            ob.parent=pivots[part['finger']];ob.matrix_parent_inverse=Matrix.Translation(-Vector(spec['pivots'][part['finger']]['root_mm'])*.001)
    if pivots:
        # Read an actual mesh vertex after native hierarchy evaluation and
        # compare with an independent closed-form radial rotation.
        for key,p in spec['pivots'].items():
            ob=objects[key+'_structure'];point=ob.data.vertices[0].co.copy();root=Vector(p['root_mm'])*.001
            axis=Vector(p['axis']);pivot=pivots[key]
            for angle in [0,p['grasp_deg'],p['closed_deg']]:
                pivot.rotation_axis_angle=(math.radians(angle),*axis);bpy.context.view_layer.update()
                v=point-root;c=math.cos(math.radians(angle));ss=math.sin(math.radians(angle))
                expected=root+v*c+axis.cross(v)*ss+axis*(axis.dot(v))*(1-c)
                error=(ob.matrix_world@point-expected).length*1000;assert error<.001
                checks.append({'finger':key,'q_deg':angle,'vertex_error_mm':error})
            for frame,angle in [(1,0),(120,p['grasp_deg']),(220,p['closed_deg']),(360,0)]:
                pivot.rotation_axis_angle=(math.radians(angle),*axis);pivot.keyframe_insert(data_path='rotation_axis_angle',frame=frame)
            if pivot.animation_data and hasattr(pivot.animation_data.action,'fcurves'):
                for fc in pivot.animation_data.action.fcurves:
                    for k in fc.keyframe_points:k.interpolation='LINEAR'
        obj=objects['STUDY_OBJECT_80x40']
        for frame,hidden in [(1,True),(100,False),(120,False),(121,True)]:
            obj.hide_render=hidden;obj.hide_viewport=hidden;obj.keyframe_insert(data_path='hide_render',frame=frame);obj.keyframe_insert(data_path='hide_viewport',frame=frame)
        scene.frame_end=360;scene.render.fps=24;scene['animation']='Geometry interpolation only; no actuator speed/duty or contact trajectory qualification.'
    else:scene.frame_end=1
    scene.frame_set(1)
    # Ground and camera are presentation objects, not product geometry.
    mesh=bpy.data.meshes.new(scene.name+'_ground');z=spec['floor_mm']*.001
    mesh.from_pydata([(-2,-2,z),(2,-2,z),(2,2,z),(-2,2,z)],[],[(0,1,2,3)]);mesh.update()
    ob=bpy.data.objects.new('PRESENTATION_GROUND',mesh);scene.collection.objects.link(ob);ob.data.materials.append(materials['object'])
    target=Vector(spec['target_mm'])*.001
    for name,delta,power,size in [('key',(1,-1,1.5),30,1.),('fill',(-1,-.3,.8),12,1.),('rim',(0,1,1.1),25,.8)]:
        light=bpy.data.lights.new(scene.name+'_'+name,'AREA');light.energy=power;light.size=size
        ob=bpy.data.objects.new(light.name,light);scene.collection.objects.link(ob);ob.location=target+Vector(delta);aim(ob,target)
    camdata=bpy.data.cameras.new(scene.name+'_camera');camera=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(camera)
    camera.location=target+Vector(spec['camera_offset_mm'])*.001;aim(camera,target);camdata.type='ORTHO';camdata.ortho_scale=spec['ortho_mm']*.001;scene.camera=camera
    for frame,label in ([(1,'open'),(120,'grasp'),(220,'closed')] if pivots else [(1,'assembly')]):
        scene.frame_set(frame);scene.render.filepath=str(OUT/(scene.name+'_'+label+'.png'));bpy.ops.render.render(write_still=True)
    scene.frame_set(1)
bpy.context.window.scene=made[0]
# Remove the unused default scene so every saved scene is intentional.
for scene in list(bpy.data.scenes):
    if scene not in made:bpy.data.scenes.remove(scene)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'odradek-r4-subassemblies.blend'))
report={'revision':data['revision'],'scene_names':[s.name for s in made],
    'product_meshes_per_scene':{s['name']:len(s['parts']) for s in data['scenes']},
    'finger_pivot_checks':checks,'source_hashes':data['source_hashes'],'export_generator_sha256':data['generator_sha256'],
    'blender_generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'units':'mesh m; display mm','manufacturing_release':False,'integration_status':'Independent review scenes, not a mechanically integrated new arm assembly'}
(OUT/'evidence.json').write_text(json.dumps(report,indent=2)+'\n')
print('Saved three native scenes and five renders; pivot checks:',len(checks))
