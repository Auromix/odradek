#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Native rig of FORM02 petals on the STAGE01 candidate path.
One mean-radius input and three passive redistribution review parameters.
Not a physical differential, head assembly, or dynamic simulation.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'engineering/generated/r5-stage-blender01';FORM=ROOT/'engineering/generated/r5-petal-form02';STAGE=ROOT/'engineering/generated/r5-stage01/study.json'
FINGERS=[('UR','upper','right',45.),('UL','upper','left',135.),('LL','lower','left',225.),('LR','lower','right',315.)]
POSES={'open':[91.,91.,91.,91.],'folded':[66.,66.,66.,66.],'cylinder80':[46.,46.,46.,46.],'rectangle50x120':[31.,66.,31.,66.],'minimum50':[31.,31.,31.,31.]}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');parser.add_argument('--review',action='store_true');parser.add_argument('--no-render',action='store_true');parser.add_argument('--mesh-json',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:])
def q_from_R(R):
 u=min(1,max(0,(91-R)/25));return math.pi/2*(10*u**3-15*u**4+6*u**5)
def transform(R,phi):
 q=q_from_R(R);p=math.radians(phi);er=np.array([math.cos(p),math.sin(p),0]);et=np.array([-math.sin(p),math.cos(p),0]);ez=np.array([0,0,1]);rot=np.column_stack([math.cos(q)*er+math.sin(q)*ez,et,-math.sin(q)*er+math.cos(q)*ez]);T=np.eye(4);T[:3,:3]=rot;T[:3,3]=R*er+20*ez-rot@np.array([0,0,3.5]);return T
if args.prepare:
 import cadquery as cq
 from build_layout import moved
 hashes={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),STAGE,FORM/'study.json',FORM/'parameters.json']};parts=[];expected={};contact=[]
 cylinder=cq.Solid.makeCylinder(40,60,cq.Vector(0,0,55));box=cq.Workplane('XY').box(50,120,60).translate((0,0,85)).rotate((0,0,0),(0,0,1),45).val()
 for i,(fid,kind,hand,phi) in enumerate(FINGERS):
  for path in sorted((FORM/(kind+'-'+hand)).glob('*.step')):
   if path.name.startswith('R5-'):continue
   s=cq.importers.importStep(str(path)).val();v,f=s.tessellate(.035,.08);name=fid+'_'+path.stem
   parts.append(dict(id=name,finger=fid,part=path.stem,vertices_m=((np.array([x.toTuple() for x in v])-[0,0,3.5])*.001).tolist(),triangles=f,source=str(path.relative_to(ROOT)),source_sha256=sha(path)));hashes[str(path.relative_to(ROOT))]=sha(path);expected[name]={}
   for pose,Rs in POSES.items():
    t=moved(s,transform(Rs[i],phi));b=t.BoundingBox();expected[name][pose]=[[b.xmin,b.ymin,b.zmin],[b.xmax,b.ymax,b.zmax]]
    if pose in ['cylinder80','rectangle50x120']:
     obj=cylinder if pose=='cylinder80' else box;distance=t.distance(obj);v=sum(abs(x.Volume()) for x in t.intersect(obj).Solids());assert v<1e-4
     if path.stem=='compliant_skin':assert distance<1e-5
     else:assert distance>.49
     contact.append(dict(pose=pose,part=name,distance_mm=distance,intersection_mm3=v))
 assert len(parts)==28
 data=dict(revision='R5-STAGE-BLENDER01',source_hashes=hashes,parts=parts,poses=POSES,independent_CAD_bounds_mm=expected,object_BREP_checks=contact,scope='Only 28 FORM02 petal solids follow nominal STAGE01 q(R). One active mean coordinate plus three passive review offsets. No physical differential/cam/carrier/cameras/display/motor/wiring; synchronous state is imposed, not simulated.')
 args.mesh_json.parent.mkdir(parents=True,exist_ok=True);args.mesh_json.write_text(json.dumps(data)+'\n');print('Prepared28 meshes,140 BREP bounds,56 object queries');raise SystemExit

import bpy
from mathutils import Vector
data=json.loads(args.mesh_json.read_text());OUT.mkdir(parents=True,exist_ok=True)
for path,h in data['source_hashes'].items():assert sha(ROOT/path)==h,path
def material(name,rgb,metal=0,emission=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*rgb,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=.35
 if emission:p.inputs['Emission Color'].default_value=(*rgb,1);p.inputs['Emission Strength'].default_value=emission
 return m
def empty(name,col,xyz=(0,0,0),parent=None):
 o=bpy.data.objects.new(name,None);col.objects.link(o);o.location=xyz;o.parent=parent;o.empty_display_size=.008;return o
def add_driver(o,path,index,expr,ctrl):
 d=o.driver_add(path,index).driver;d.type='SCRIPTED'
 for name,prop in [('m','mean_radius_mm'),('a','passive_UR_mm'),('b','passive_UL_mm'),('c','passive_LL_mm')]:
  v=d.variables.new();v.name=name;v.type='SINGLE_PROP';v.targets[0].id=ctrl;v.targets[0].data_path='["'+prop+'"]'
 d.expression=expr
def setpose(name):
 Rs=POSES[name];mean=sum(Rs)/4;ctrl=bpy.data.objects['MEAN_INPUT_AND_PASSIVE_OFFSETS'];ctrl['mean_radius_mm']=mean
 for prop,R in zip(['passive_UR_mm','passive_UL_mm','passive_LL_mm'],Rs):ctrl[prop]=R-mean
 ctrl.update_tag();bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
 for o in bpy.data.collections['Example objects / Z55 to115 only'].objects:
  hidden=o.name!='OBJ_'+name;o.hide_render=hidden;o.hide_set(hidden)
def aim(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
if not args.review:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;scene=bpy.context.scene;scene.name='R5_FOLD_RADIAL_CANDIDATE';scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='MILLIMETERS'
 col=bpy.data.collections.new('28 original petal CAD solids');scene.collection.children.link(col);controls=bpy.data.collections.new('1 active mean / 3 PASSIVE review offsets');scene.collection.children.link(controls);objects=bpy.data.collections.new('Example objects / Z55 to115 only');scene.collection.children.link(objects)
 ctrl=empty('MEAN_INPUT_AND_PASSIVE_OFFSETS',controls);ctrl['mean_radius_mm']=91.;ctrl.id_properties_ui('mean_radius_mm').update(min=31,max=91,description='Mean of four branch radii. One commanded quantity only in ideal differential algebra; no physical drive implemented.')
 for prop in ['passive_UR_mm','passive_UL_mm','passive_LL_mm']:
  ctrl[prop]=0.;ctrl.id_properties_ui(prop).update(min=-60,max=60,description='PASSIVE redistribution review parameter, not a motor command. Fourth offset=negative sum. Ensure all four radii stay31..91.')
 ctrl['passive_LR_mm']='-(passive_UR_mm+passive_UL_mm+passive_LL_mm)';ctrl['four_motors_implied']=False;ctrl['branch_bounds_must_be_checked']=True;ctrl['mean_constraint']='sum(Ri)=4*mean_radius_mm; offsets are NOT independently driven actuators'
 mats={'frame':material('Graphite frame',(.045,.065,.08),.5),'retainer':material('Front retainer',(.018,.024,.031),.4),'bearing_cover':material('Transparent bearing cover reference',(.25,.42,.46)),'compliant_skin':material('Amber luminous gripping skin',(.98,.51,.09),0,.35),'reservation':material('Unresolved electronics',(.16,.24,.2)),'object':material('Example object',(.32,.54,.67),.1)}
 hinges={}
 for (fid,kind,hand,phi),Rexpr in zip(FINGERS,['m+a','m+b','m+c','m-a-b-c']):
  p=math.radians(phi);base=empty('RADIAL_'+fid,controls,(0,0,.02));base.rotation_euler[2]=p
  add_driver(base,'location',0,f'({Rexpr})*{math.cos(p)*.001:.17g}',ctrl);add_driver(base,'location',1,f'({Rexpr})*{math.sin(p)*.001:.17g}',ctrl)
  hinge=empty('HINGE_'+fid,controls,parent=base);hinges[fid]=hinge;u=f'min(1,max(0,(91-({Rexpr}))/25))';angle=f'-{math.pi/2:.17g}*(10*pow({u},3)-15*pow({u},4)+6*pow({u},5))';add_driver(hinge,'rotation_euler',1,angle,ctrl)
 for p in data['parts']:
  mesh=bpy.data.meshes.new(p['id']);mesh.from_pydata(p['vertices_m'],[],p['triangles']);mesh.update();o=bpy.data.objects.new(p['id'],mesh);col.objects.link(o);o.parent=hinges[p['finger']];o.data.materials.append(mats.get(p['part'],mats['reservation']));o['source']=p['source'];o['source_sha256']=p['source_sha256']
  if 'reservation' in p['part']:o.hide_render=True;o.hide_set(True)
 bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=.04,depth=.06,location=(0,0,.085));o=bpy.context.object;o.name='OBJ_cylinder80';o.data.materials.append(mats['object'])
 for c in list(o.users_collection):c.objects.unlink(o)
 objects.objects.link(o)
 bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,.085));o=bpy.context.object;o.name='OBJ_rectangle50x120';o.dimensions=(.05,.12,.06);o.rotation_euler.z=math.pi/4;o.data.materials.append(mats['object'])
 for c in list(o.users_collection):c.objects.unlink(o)
 objects.objects.link(o)
 scene['scope']=data['scope'];scene['physical_drive_implemented']=False;scene['minimum_aperture_is_full_closure']=False;scene['known_material_mass_kg']=json.loads((FORM/'study.json').read_text())['four_petal_known_material_subtotal_kg'];scene['one_second_cycle_qualified']=False

errors=[];qerrors=[];means=[]
for name,Rs in POSES.items():
 setpose(name);actual=[]
 for (fid,_,_,_),R in zip(FINGERS,Rs):
  p=bpy.data.objects['RADIAL_'+fid].matrix_world.translation;actual.append(math.hypot(p.x,p.y)*1000);qerrors.append(abs(bpy.data.objects['HINGE_'+fid].rotation_euler.y+q_from_R(R)))
 assert max(abs(np.array(actual)-Rs))<1e-4
 means.append(abs(sum(actual)/4-bpy.data.objects['MEAN_INPUT_AND_PASSIVE_OFFSETS']['mean_radius_mm']))
 for p in data['parts']:
  o=bpy.data.objects[p['id']];T=np.array(o.matrix_world);v=np.array([tuple(v.co) for v in o.data.vertices]);w=np.einsum('ij,nj->ni',T[:3,:3],v)+T[:3,3];assert np.isfinite(w).all();b=np.array([w.min(0),w.max(0)])*1000;errors.append(float(max(abs(b-np.array(data['independent_CAD_bounds_mm'][p['id']][name])).ravel())))
assert max(errors)<.1 and max(qerrors)<1e-6 and max(means)<1e-4
drivers=[]
for o in bpy.data.objects:
 if o.animation_data:
  for fc in o.animation_data.drivers:
   assert fc.driver.is_valid and fc.driver.is_simple_expression,(o.name,fc.driver.expression,len(fc.driver.expression),fc.driver.is_valid,fc.driver.is_simple_expression);drivers.append(dict(object=o.name,path=fc.data_path,expression=fc.driver.expression))
assert len(drivers)==12
report=dict(revision='R5-STAGE-BLENDER01',source_hashes=data['source_hashes'],generator_sha256=sha(__file__),CAD_meshes=28,independent_CAD_bound_checks=len(errors),max_CAD_bound_error_mm=max(errors),max_q_error_rad=max(qerrors),max_mean_constraint_error_mm=max(means),object_BREP_checks=data['object_BREP_checks'],drivers=drivers,commanded_coordinates=1,passive_review_parameters=3,physical_differential_simulated=False,manufacturing_release=False)
setpose('open')
if args.review:
 assert not bpy.context.preferences.filepaths.use_scripts_auto_execute and not bpy.app.autoexec_fail
 report.update(reopened_blend_sha256=sha(bpy.data.filepath),python_autoexec_enabled=False,handlers_required=False);(OUT/'reopen-review.json').write_text(json.dumps(report,indent=2)+'\n');print('Reopened',len(errors),'CAD checks');raise SystemExit
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True;scene.render.resolution_x=1500;scene.render.resolution_y=1150;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Review background');scene.world.use_nodes=True;scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.83,.85,.87,1);scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.5
for name,loc,power,size in [('Key',(.35,.1,.7),65,.6),('Fill',(-.4,-.2,.5),35,.5),('Rear',(.1,.4,-.25),40,.5)]:
 light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size;o=bpy.data.objects.new(name,light);scene.collection.objects.link(o);o.location=loc;aim(o,(0,0,.04))
camera=bpy.data.cameras.new('Review camera');o=bpy.data.objects.new('Review camera',camera);scene.collection.objects.link(o);camera.type='ORTHO';camera.ortho_scale=.56;o.location=(0,-.3,.62);aim(o,(0,0,.06));scene.camera=o;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
bpy.ops.object.select_all(action='DESELECT');ctrl=bpy.data.objects['MEAN_INPUT_AND_PASSIVE_OFFSETS'];ctrl.select_set(True);bpy.context.view_layer.objects.active=ctrl
for area in bpy.context.screen.areas:
 if area.type=='VIEW_3D':area.spaces.active.region_3d.view_distance=.7;area.spaces.active.region_3d.view_location=(0,0,.03)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'odradek-r5-fold-radial-candidate.blend'));(OUT/'build-review.json').write_text(json.dumps(report,indent=2)+'\n')
if not args.no_render:
 for name in ['open','cylinder80','rectangle50x120']:
  setpose(name);camera.ortho_scale=.56 if name=='open' else .32;aim(scene.camera,(0,0,.06 if name=='open' else .085));scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
print('Built fold-radial review rig;140 CAD bounds and56 contact queries')
