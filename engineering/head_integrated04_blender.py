# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Native head-only J7+4 rig, persistent P16 expression drivers, CAD checks.
Blender --background --factory-startup --python this.py -- --mesh-json PATH
Reopen with --disable-autoexec FILE --python this.py -- --mesh-json PATH --review.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix,Vector

ap=argparse.ArgumentParser();ap.add_argument('--mesh-json',required=True,type=Path);ap.add_argument('--out',type=Path);ap.add_argument('--review',action='store_true');ap.add_argument('--no-render',action='store_true');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
ROOT=Path(__file__).resolve().parents[1];OUT=args.out or ROOT/'engineering/generated/head-integrated04/blender';OUT.mkdir(parents=True,exist_ok=True)
d=json.loads(args.mesh_json.read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def attach(ob,parent):
 world=ob.matrix_world.copy();ob.parent=parent;ob.matrix_parent_inverse=parent.matrix_world.inverted();ob.matrix_world=world;bpy.context.view_layer.update()
def drv(ob,path,index,control,expr):
 fc=ob.driver_add(path,index);driver=fc.driver;driver.type='SCRIPTED';v=driver.variables.new();v.name='q';v.type='SINGLE_PROP';v.targets[0].id=control;v.targets[0].data_path='["q_deg"]';driver.expression=expr
def empty(name,point,parent=None,axis=None,limits=None):
 ob=bpy.data.objects.new(name,None);controls.objects.link(ob);ob.empty_display_type='ARROWS';ob.empty_display_size=.015;ob.location=point;bpy.context.view_layer.update()
 if parent:attach(ob,parent)
 if axis is not None:ob.rotation_mode='AXIS_ANGLE';ob.rotation_axis_angle=(0,*axis)
 if limits:
  ob['q_deg']=0.;ob.id_properties_ui('q_deg').update(min=limits[0],max=limits[1],description='Nominal geometry only; not hardware-qualified motion');drv(ob,'rotation_axis_angle',0,ob,'q*pi/180')
 return ob
def mat(name,rgb,metallic=0,alpha=1,emission=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*rgb,alpha);p.inputs['Metallic'].default_value=metallic;p.inputs['Roughness'].default_value=.48
 if emission:p.inputs['Emission Color'].default_value=(*rgb,1);p.inputs['Emission Strength'].default_value=emission
 if alpha<1:p.inputs['Alpha'].default_value=alpha;m.surface_render_method='DITHERED'
 return m
def pick(p):
 n=p['id'];m=p['material']
 if n.startswith('CD01-LED-'):
  xyz=np.array(p['vertices_m']);x,y=1000*(xyz.min(0)+xyz.max(0))[:2]/2;r=math.hypot(x,y)
  lit=23.5<=r<=27.5 or (abs(x)<=8.5 and abs(y-(11.2-abs(x)))<.2) or (abs(x)<.2 and -8.5<=y<=8.5)
  return materials['led'] if lit else materials['pixel_off']
 if '_LED_' in n or n.startswith('CD01-LED-'):return materials['led']
 if 'optical_sheet' in n or n=='CD01-window':return materials['optics']
 if 'PCB' in n and 'PCBA' not in n:return materials['pcb']
 if m.startswith('aluminum'):return materials['metal']
 if m.startswith('silicone'):return materials['rubber']
 if m in ['P16_envelope','electronic_mass_TBD','catalog_camera']:return materials['dark']
 return materials['steel']
def pose(angles,roll=0):
 bpy.data.objects['J7_ROLL']['q_deg']=roll;bpy.data.objects['J7_ROLL'].update_tag()
 for f,a in angles.items():ob=bpy.data.objects['FINGER_'+f];ob['q_deg']=float(a);ob.update_tag()
 bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
def aim(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()

if not args.review:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;scene=bpy.context.scene;scene.name='HEAD04_GEOMETRY_REVIEW';scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='MILLIMETERS'
 controls=bpy.data.collections.new('J7 and four independent fingers');scene.collection.children.link(controls)
 product=bpy.data.collections.new('1027 CAD objects and declared envelopes');scene.collection.children.link(product)
 materials={'metal':mat('Graphite aluminum',(.065,.093,.12),.45),'steel':mat('Steel',(.3,.35,.39),.7),'rubber':mat('Contact pad',(.035,.14,.12)),'pcb':mat('PCB',(.025,.1,.065)),'dark':mat('Electronic and actuator envelopes',(.014,.025,.033)),'led':mat('Amber pixels',(.98,.44,.025),0,1,1.2),'pixel_off':mat('Unlit physical pixel',(.015,.009,.004)),'optics':mat('Window',(.71,.75,.77),0,.20)}
 roll=empty('J7_ROLL',(0,0,-.164),axis=(0,0,1),limits=(-90,90));head=empty('DETACHABLE_HEAD_FACE',(0,0,0),roll)
 fingers={};bodies={};sliders={}
 for f in d['finger_joints']:
  key=f['id'];root=Vector(f['pivot_head_mm'])*.001;axis=Vector(f['closing_axis_head']);tangent=-axis;radial=Vector((tangent.y,-tangent.x,0));sign=f['mechanical_mirror_sign']
  ctrl=empty('FINGER_'+key,root,head,axis,f['range_deg']);fingers[key]=ctrl;A=root+tangent*(-.018*sign)+Vector((0,0,-.123))
  t0=math.atan2(26*math.cos(math.radians(-68)),123+26*math.sin(math.radians(-68)));L0=math.sqrt(123**2+26**2+2*123*26*math.sin(math.radians(-68)))
  body=empty('P16_'+key+'_body',A,head,tangent);drv(body,'rotation_axis_angle',0,ctrl,f'atan2(26*cos(q*pi/180-68*pi/180),123+26*sin(q*pi/180-68*pi/180))-({t0:.17g})');slider=empty('P16_'+key+'_slider',(0,0,0),body);w0=radial*math.sin(t0)+Vector((0,0,math.cos(t0)))
  for i in range(3):drv(slider,'location',i,ctrl,f'({w0[i]:.17g})*(sqrt(123*123+26*26+2*123*26*sin(q*pi/180-68*pi/180))-({L0:.17g}))*0.001')
  bodies[key]=body;sliders[key]=slider
 for p in d['parts']:
  mesh=bpy.data.meshes.new(p['id']+'_mesh');mesh.from_pydata(p['vertices_m'],[],p['triangles']);mesh.update();ob=bpy.data.objects.new(p['id'],mesh);product.objects.link(ob);ob.data.materials.append(pick(p));ob['source']=p['source'];ob['geometry_group']=p['group'];ob['manufacturing_release']=False
  if p['group']=='head_fixed':parent=head
  elif p['group'].endswith('_rotor'):parent=fingers[p['finger']]
  else:assert p['group'].endswith('_P16_kinematic');parent=sliders[p['finger']] if p['id'].endswith(('_slider','_tip')) else bodies[p['finger']]
  attach(ob,parent)
  if p['material']=='space_reservation':ob.hide_render=True;ob.hide_set(True)
 scene['scope']=d['scope'];scene['unknown_electronic_masses_not_zero']=True;scene['hardware_qualified']=False;scene['route_status']='ARCHIVED P16 branch, cannot meet confirmed <=1s empty cycle';scene['P16_duty_warning']='20 percent catalogue duty; geometry controls are not executable cycles';scene['generator_sha256']=sha(__file__);scene['pixel_pattern']='Presentation assignment on actual 285 LED meshes, no added floating screen or implemented UI firmware'

# Endpoint checks compare all evaluated meshes against independent closed STEP.
closed={f['id']:f['range_deg'][1] for f in d['finger_joints']};pose(closed);errors=[]
for p in d['parts']:
 ob=bpy.data.objects[p['id']];T=np.array(ob.matrix_world);v=np.array([tuple(x.co) for x in ob.data.vertices]);v=np.einsum('ij,nj->ni',T[:3,:3],v)+T[:3,3];actual=np.array([v.min(0),v.max(0)])*1000;err=float(np.max(abs(actual-np.array(d['closed_bounds_head_mm'][p['id']]))));assert err<.20,(p['id'],err);errors.append(err)
drivers=[]
for ob in bpy.data.objects:
 if ob.animation_data:
  for fc in ob.animation_data.drivers:
   q=fc.driver;assert q.is_valid and q.is_simple_expression,(ob.name,q.expression);drivers.append({'object':ob.name,'expression':q.expression,'simple':q.is_simple_expression,'valid':q.is_valid})
assert len(drivers)==21,len(drivers)
pose({f:0 for f in closed})
report=dict(revision='HEAD-INTEGRATED04',mesh_count=len(d['parts']),drivers=drivers,independent_closed_CAD_bbox_checks=len(errors),maximum_bound_error_mm=max(errors),input_GLB_sha256=d['GLB_sha256'],script_sha256=sha(__file__),hardware_qualified=False)
if args.review:
 assert not bpy.app.autoexec_fail and not bpy.context.preferences.filepaths.use_scripts_auto_execute
 report.update(reopened_blend_sha256=sha(bpy.data.filepath),python_autoexec_enabled=False,handlers_required=False,file_resaved=False);(OUT/'reopen-review.json').write_text(json.dumps(report,indent=2)+'\n');print('Reopened head rig:',len(errors),'CAD comparisons passed');raise SystemExit

scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.render.resolution_x=1500;scene.render.resolution_y=1250;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.16,.20,.24,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.45
for name,loc,energy,size in [('Key',(.3,.3,.45),35,.45),('Fill',(-.35,-.1,.25),20,.4),('Back',(.1,.2,-.45),25,.3)]:
 l=bpy.data.lights.new(name,'AREA');l.energy=energy;l.size=size;ob=bpy.data.objects.new(name,l);scene.collection.objects.link(ob);ob.location=loc;aim(ob,(0,0,-.04))
c=bpy.data.cameras.new('Review');camera=bpy.data.objects.new('Review',c);scene.collection.objects.link(camera);scene.camera=camera;c.type='ORTHO';c.ortho_scale=.49
views=[('head-open',(.27,.16,.7),(0,0,-.02),False),('head-closed',(.40,.24,.7),(0,0,.01),True),('head-back',(.24,.12,-.7),(0,0,-.075),False)]
if not args.no_render:
 for name,pos,target,isclosed in views:
  pose(closed if isclosed else {f:0 for f in closed});camera.location=pos;aim(camera,target);scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
pose({f:0 for f in closed});camera.location=views[0][1];aim(camera,views[0][2]);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'odradek-head04.blend'));report['blend_sha256']=sha(OUT/'odradek-head04.blend');(OUT/'build-review.json').write_text(json.dumps(report,indent=2)+'\n');print('Saved head rig:',len(errors),'CAD comparisons passed')
