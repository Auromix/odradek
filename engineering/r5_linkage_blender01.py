#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Persistent one-control nonlinear R5 rig. Reference rods are not hardware.

CAD Python: this.py --prepare --mesh-json WORK/mesh.json
Blender: --background --python this.py -- --mesh-json WORK/mesh.json
Reopen: --disable-autoexec FILE --python this.py -- --mesh-json ... --review
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/r5-linkage-blender01'
SHAPES=ROOT/'engineering/generated/r5-petal-form01'
LINK=ROOT/'engineering/generated/r5-link01/study.json'
GEOM=ROOT/'engineering/generated/r5-head-geometry01/study.json'
FINGERS=[('UR','upper','right',35.),('UL','upper','left',145.),('LL','lower','left',225.),('LR','lower','right',315.)]
SAMPLES=[0.,.1,.25,.5,.75,.861875,.9,1.]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');parser.add_argument('--review',action='store_true');parser.add_argument('--no-render',action='store_true');parser.add_argument('--mesh-json',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:])

def angle(s,p):
 x=p['x_open_mm']+(p['x_closed_mm']-p['x_open_mm'])*s;d=p['root_radius_mm']-p['slider_ear_radius_mm'];a=p['crank_mm'];L=p['rod_mm']
 return -math.acos((L*L-d*d-a*a-x*x)/(2*a*math.hypot(d,x)))-math.atan2(x,d)-p['phase_rad']

if args.prepare:
 import cadquery as cq
 from build_layout import moved
 from r5_head_geometry01 import transform
 shapes=[];params=json.loads(LINK.read_text())['parameters'];hashes={str(p.relative_to(ROOT)):sha(p) for p in [LINK,GEOM,SHAPES/'qa.json',Path(__file__)]};expected={}
 for f in FINGERS:
  for path in sorted((SHAPES/(f[1]+'-'+f[2])).glob('*.step')):
   if path.name.startswith('R5-'):continue
   shape=cq.importers.importStep(str(path)).val();v,t=shape.tessellate(.035,.08);name=f[0]+'_'+path.stem;vertices=(np.array([x.toTuple() for x in v])-[0,0,3.5])*.001
   shapes.append(dict(id=name,finger=f[0],part=path.stem,vertices_m=vertices.tolist(),triangles=t,source=str(path.relative_to(ROOT)),source_sha256=sha(path)));hashes[str(path.relative_to(ROOT))]=sha(path)
   expected[name]={}
   for s in SAMPLES:
    target=moved(shape,transform((*f,params[f[1]]['q_closed_deg']),angle(s,params[f[1]])));b=target.BoundingBox();expected[name][str(s)]=[[b.xmin,b.ymin,b.zmin],[b.xmax,b.ymax,b.zmax]]
 assert len(shapes)==28
 data=dict(revision='R5-LINKAGE-BLENDER01',source_hashes=hashes,parameters=params,parts=shapes,samples=SAMPLES,independent_CAD_bounds_mm=expected,scope='28 frozen shaped-petal CAD meshes; one active slider coordinate; nonlinear closed-loop rod constraints; rods/slider/pivots are visible kinematic references, not detailed load-bearing hardware; central motor/hub/cameras/screen/cabling absent')
 args.mesh_json.parent.mkdir(parents=True,exist_ok=True);args.mesh_json.write_text(json.dumps(data)+'\n');print('Prepared 28 CAD meshes and',len(SAMPLES)*28,'independent pose bounds');raise SystemExit

import bpy
from mathutils import Vector
data=json.loads(args.mesh_json.read_text());params=data['parameters'];OUT.mkdir(parents=True,exist_ok=True)
for path,expected_sha in data['source_hashes'].items():
 assert sha(ROOT/path)==expected_sha,('Changed input; prepare again',path)

def material(name,rgb,metal=0,emission=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*rgb,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=.4
 if emission:p.inputs['Emission Color'].default_value=(*rgb,1);p.inputs['Emission Strength'].default_value=emission
 return m
def empty(name,collection,xyz,parent=None):
 ob=bpy.data.objects.new(name,None);collection.objects.link(ob);ob.location=xyz;ob.parent=parent;ob.empty_display_type='PLAIN_AXES';ob.empty_display_size=.015;return ob
def driver(ob,path,index,expression,control):
 fc=ob.driver_add(path,index);d=fc.driver;d.type='SCRIPTED';v=d.variables.new();v.name='s';v.type='SINGLE_PROP';v.targets[0].id=control;v.targets[0].data_path='["close_fraction"]';d.expression=expression
def cyl_mesh(name,radius,length,collection,mat):
 verts=[];n=24
 for z in [0,length]:verts.extend((radius*math.cos(2*math.pi*i/n),radius*math.sin(2*math.pi*i/n),z) for i in range(n))
 faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();ob=bpy.data.objects.new(name,mesh);collection.objects.link(ob);ob.data.materials.append(mat);ob['representation']='Kinematic reference only; no selected pin, bearing, rod section, material, mass or manufacturing interface';return ob
def aim(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
def pose(s):
 c=bpy.data.objects['MASTER_SLIDER'];c['close_fraction']=float(s);c.update_tag();bpy.context.scene.frame_set(1);bpy.context.view_layer.update()

if not args.review:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;scene=bpy.context.scene;scene.name='R5_SINGLE_ACTIVE_COORDINATE';scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='MILLIMETERS'
 product=bpy.data.collections.new('CAD petals (28 solids, electronics reserved)');scene.collection.children.link(product)
 controls=bpy.data.collections.new('ONE active control / nonlinear passive followers');scene.collection.children.link(controls)
 refs=bpy.data.collections.new('REFERENCE linkage (not production hardware)');scene.collection.children.link(refs)
 ctrl=empty('MASTER_SLIDER',controls,(0,0,0));ctrl['close_fraction']=0.;ctrl.id_properties_ui('close_fraction').update(min=0,max=1,description='One commanded slider:0 open,0.861875 common90deg,1 emptyclosed. No individual finger inputs.');ctrl['slider_Z_mm']='-80 + 40*close_fraction';ctrl['physical_motor_selected_and_integrated']=False
 mats={'frame':material('Graphite structure',(.055,.08,.10),.45),'retainer':material('Dark front retainer',(.018,.027,.034),.35),'bearing_cover':material('PC bearing cover',(.28,.52,.59)),'compliant_skin':material('Luminous contact skin (appearance)',(.98,.49,.07),0,.4),'PCB_blank_reservation':material('Unpopulated board volume',(.025,.16,.09)),'back_electronics_reservation':material('Electronic allocation',(.17,.10,.25)),'LED_front_reservation':material('LED allocation',(.4,.2,.03)),'reference':material('Amber kinematic reference',(.7,.35,.08),.5)}
 hinges={}
 for fid,kind,hand,phi in FINGERS:
  p=params[kind];ph=math.radians(phi);er=Vector((math.cos(ph),math.sin(ph),0));az=empty('ROOT_'+fid,controls,er*(p['root_radius_mm']*.001));az.rotation_euler[2]=ph;hinge=empty('FOLLOWER_'+fid,controls,(0,0,0),az);hinges[fid]=hinge
  x=f'({p["x_open_mm"]:.17g}+({p["x_closed_mm"]-p["x_open_mm"]:.17g})*s)';d=p['root_radius_mm']-p['slider_ear_radius_mm'];a=p['crank_mm'];L=p['rod_mm'];expr=f'acos(({L*L-d*d-a*a:.17g}-{x}*{x})/({2*a:.17g}*sqrt({d*d:.17g}+{x}*{x})))+atan2({x},{d:.17g})+({p["phase_rad"]:.17g})';driver(hinge,'rotation_euler',1,expr,ctrl)
  B=empty('PIN_B_'+fid,refs,(a*math.cos(p['phase_rad'])*.001,0,a*math.sin(p['phase_rad'])*.001),hinge)
  C=empty('PIN_C_'+fid,refs,er*(p['slider_ear_radius_mm']*.001));driver(C,'location',2,x+'*0.001',ctrl)
  crank=cyl_mesh('REF_CRANK_'+fid,.0022,a*.001,refs,mats['reference']);crank.parent=hinge;crank.rotation_euler=Vector(B.location).to_track_quat('Z','Y').to_euler()
  rod=cyl_mesh('REF_ROD_'+fid,.0013,L*.001,refs,mats['reference']);rod.parent=C;track=rod.constraints.new('DAMPED_TRACK');track.target=B;track.track_axis='TRACK_Z'
  # Hollow guide-reference circle follows the common slider, no nut implied.
 curve=bpy.data.curves.new('REFERENCE_SLIDER_PATH','CURVE');curve.dimensions='3D';curve.bevel_depth=.001;curve.bevel_resolution=2;spline=curve.splines.new('POLY');spline.points.add(63)
 for i,point in enumerate(spline.points):ang=2*math.pi*i/64;point.co=(.020*math.cos(ang),.020*math.sin(ang),0,1)
 spline.use_cyclic_u=True;ring=bpy.data.objects.new('REF_COMMON_SLIDER',curve);refs.objects.link(ring);ring.data.materials.append(mats['reference']);driver(ring,'location',2,'(-80+40*s)*0.001',ctrl)
 for part in data['parts']:
  mesh=bpy.data.meshes.new(part['id']);mesh.from_pydata(part['vertices_m'],[],part['triangles']);mesh.update();ob=bpy.data.objects.new(part['id'],mesh);product.objects.link(ob);ob.parent=hinges[part['finger']];ob.data.materials.append(mats[part['part']]);ob['source']=part['source'];ob['source_sha256']=part['source_sha256'];ob['manufacturing_release']=False
  if 'reservation' in part['part']:ob.hide_render=True;ob.hide_set(True)
 scene['scope']=data['scope'];scene['source_hashes']=json.dumps(data['source_hashes']);scene['hardware_qualified']=False;scene['active_head_control_count']=1;scene['no_hidden_four_motor_architecture']=True;scene['render_light_is_material_appearance_not_LED_board']=True
 bpy.context.view_layer.update()

# Re-evaluate at several slider positions, including the shared 90deg contact.
bound_errors=[];angle_errors=[];rod_errors=[]
for s in data['samples']:
 pose(s)
 for fid,kind,hand,phi in FINGERS:
  ob=bpy.data.objects['FOLLOWER_'+fid];angle_errors.append(abs(ob.rotation_euler.y+angle(s,params[kind])))
  B=bpy.data.objects['PIN_B_'+fid].matrix_world.translation;C=bpy.data.objects['PIN_C_'+fid].matrix_world.translation;rod_errors.append(abs((B-C).length*1000-params[kind]['rod_mm']))
 for part in data['parts']:
  ob=bpy.data.objects[part['id']];T=np.array(ob.matrix_world);v=np.array([tuple(x.co) for x in ob.data.vertices]);v=np.einsum('ij,nj->ni',T[:3,:3],v)+T[:3,3];b=np.array([v.min(0),v.max(0)])*1000;target=np.array(data['independent_CAD_bounds_mm'][part['id']][str(s)]);bound_errors.append(float(np.max(abs(b-target))))
assert max(bound_errors)<.15,max(bound_errors)
assert max(angle_errors)<2e-5,max(angle_errors)
assert max(rod_errors)<.02,max(rod_errors)
drivers=[]
for ob in bpy.data.objects:
 if ob.animation_data:
  for fc in ob.animation_data.drivers:
   d=fc.driver;assert d.is_valid and d.is_simple_expression,(ob.name,d.expression);drivers.append(dict(object=ob.name,expression=d.expression,valid=True,simple=True))
assert len(drivers)==9,len(drivers)
pose(0.)
report=dict(revision='R5-LINKAGE-BLENDER01',source_hashes=data['source_hashes'],generator_sha256=sha(__file__),product_meshes=28,active_controls=1,drivers=drivers,independent_CAD_bounds_checked=len(bound_errors),maximum_CAD_bound_error_mm=max(bound_errors),maximum_angle_error_rad=max(angle_errors),maximum_rod_length_error_mm=max(rod_errors),geometry_only_no_physical_release=True)
if args.review:
 assert not bpy.app.autoexec_fail and not bpy.context.preferences.filepaths.use_scripts_auto_execute
 report.update(reopened_blend_sha256=sha(bpy.data.filepath),python_autoexec_enabled=False,handlers_required=False,resaved=False);(OUT/'reopen-review.json').write_text(json.dumps(report,indent=2)+'\n');print('Reopened single-drive rig:',len(bound_errors),'checks');raise SystemExit

scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=40;scene.cycles.use_denoising=True;scene.render.resolution_x=1500;scene.render.resolution_y=1150;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Review world');scene.world.color=(.7,.7,.7)
scene.view_settings.view_transform='AgX'
for name,loc,power,size in [('Key',(.35,.1,.65),70,.6),('Fill',(-.4,-.25,.35),35,.5),('Rear',(.1,.4,-.25),45,.5)]:
 light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size;ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=loc;aim(ob,(0,0,.02))
camera=bpy.data.cameras.new('Review camera');cam=bpy.data.objects.new('Review camera',camera);scene.collection.objects.link(cam);camera.type='ORTHO';camera.ortho_scale=.52;cam.location=(0,-.24,.62);aim(cam,(0,0,.02));scene.camera=cam
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False;scene.world.use_nodes=True;scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.85,.86,.87,1);scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.4
bpy.context.view_layer.objects.active=bpy.data.objects['MASTER_SLIDER'];bpy.data.objects['MASTER_SLIDER'].select_set(True)
for area in bpy.context.screen.areas:
 if area.type=='VIEW_3D':area.spaces.active.region_3d.view_distance=.7;area.spaces.active.region_3d.view_location=(0,0,.025)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'odradek-r5-single-drive.blend'))
(OUT/'build-review.json').write_text(json.dumps(report,indent=2)+'\n')
if not args.no_render:
 for name,s in [('open',0.),('common90',.861875),('closed',1.)]:
  pose(s);scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
print('Built native one-slider rig;',len(bound_errors),'CAD checks')
