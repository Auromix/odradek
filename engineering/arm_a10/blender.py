# SPDX-License-Identifier: CC-BY-NC-4.0
"""Import original A10 CAD meshes into a seven-joint editable Blender rig."""
import bpy,json,math,sys,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'engineering/arm_a10/build';ACTUAL='--actual' in sys.argv
FILE=OUT/'manifest.json';D=json.loads(FILE.read_text());L=D['layout']
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='MILLIMETERS'
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=1280;scene.render.resolution_y=960;scene.render.resolution_percentage=100
scene.world.color=(.35,.38,.42);scene.view_settings.view_transform='AgX'
cols={}
for name in ['00_Rig','01_Load_Structure','02_Removable_Shrouds','03_Purchased_Parts','04_Fit_Gauges_HIDDEN','05_Official_Motors_LOCAL','80_Base_Context','99_Presentation']:
 c=bpy.data.collections.new(name);scene.collection.children.link(c);cols[name]=c

def mat(name,color,metal=.0):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=.38
 return m
M={'core':mat('Graphite_load_structure',(.07,.09,.115)), 'cover':mat('Shield_grey',(.56,.61,.65)), 'metal':mat('Purchased_metal',(.075,.095,.115),.65), 'amber':mat('Amber_mechanical_insert',(.78,.47,.12),.3)}
def link(obj,col):
 for c in list(obj.users_collection):c.objects.unlink(obj)
 cols[col].objects.link(obj)
def empty(name,parent,loc):
 o=bpy.data.objects.new(name,None);cols['00_Rig'].objects.link(o);o.parent=parent;o.matrix_parent_inverse=Matrix.Identity(4);o.location=Vector(loc)*.001;o.empty_display_size=.02
 return o
root=empty('Arm_mount_B04',None,[0,135,34.6]);root.rotation_euler.z=math.pi/2
frames={'world':root};parent=root
for j in L['joints']:
 fixed=empty(j['id']+'.fixed',parent,j['offset']);rotor=empty(j['id']+'.rotor',fixed,[0,0,0])
 rotor['angle_deg']=L['poses']['attention'][int(j['id'][1])-1]
 rotor.id_properties_ui('angle_deg').update(min=j['limits_deg'][0],max=j['limits_deg'][1],description=j['name']+'; J2 upright = 0deg')
 index=j['axis'].index(1);f=rotor.driver_add('rotation_euler',index).driver
 v=f.variables.new();v.name='q';v.targets[0].id=rotor;v.targets[0].data_path='["angle_deg"]'
 f.expression=f'(q+({j["zero_deg"]}))*pi/180'
 frames[j['id']+'.fixed']=fixed;frames[j['id']+'.rotor']=rotor;parent=rotor
empty('Output_flange_DATUM',parent,D['flange_from_J7_mm'])

def meshobj(id,verts,faces,col,parent,material):
 mesh=bpy.data.meshes.new(id);mesh.from_pydata([tuple(.001*x for x in v) for v in verts],[],faces);mesh.update()
 o=bpy.data.objects.new(id,mesh);cols[col].objects.link(o);o.parent=parent;o.matrix_parent_inverse=Matrix.Identity(4);mesh.materials.append(material)
 for p in mesh.polygons:p.use_smooth=True
 mesh.set_sharp_from_angle(angle=math.radians(35))
 return o
for p in D['parts']:
 role=p['role'];col='04_Fit_Gauges_HIDDEN' if role=='fit_coupon' else '03_Purchased_Parts' if role in ['hardware','motor_envelope'] else '02_Removable_Shrouds' if role=='printed_cover' else '01_Load_Structure'
 material=M['metal'] if col=='03_Purchased_Parts' else M['cover'] if role=='printed_cover' else M['amber'] if p['id'].startswith('B7') or 'retainer' in p['id'] else M['core']
 material=M['core'] if role=='printed_cover' and (p['id'].startswith('J') or p['id'].startswith('S00')) else material
 o=meshobj(p['id'],p['vertices_mm'],p['triangles'],col,frames[p['frame']],material)
 for k in ['role','material','note','mass_kg','frame','solid_count']:o[k]=p[k]
 o['Printable']=role.startswith('printed') or role=='fit_coupon';o['Source STEP']=f'step/{p["id"]}.step'
 if role=='fit_coupon' or ACTUAL and role=='motor_envelope':o.hide_render=True;o.hide_set(True)

if ACTUAL:
 for p in json.loads((ROOT/'work/arm-a10/vendor/meshes.json').read_text()):
  o=meshobj(p['id'],p['vertices_mm'],p['triangles'],'05_Official_Motors_LOCAL',frames[p['frame']],M['metal'])
  o['Source SHA256']=p['source_sha256'];o['Model']=p['model'];o['Reference only']=True
# Read-only B04 context; these existing base parts are excluded from this print kit.
base=ROOT/'engineering/arm_a10/context/base_b04'
if (base/'manifest.json').exists():
 bd=json.loads((base/'manifest.json').read_text());bm=json.loads((base/'cad-surface-meshes.json').read_text())
 for p in bd['parts']:
  if p['category'] in ['guide','routing','environment'] or p['id'].startswith('ENV-'):continue
  if p['id'] in bm:
   m=bm[p['id']];o=meshobj('BASE-'+p['id'],m['vertices'],m['faces'],'80_Base_Context',None,M['cover'])
  elif p.get('stl') and (base/p['stl']).exists():
   bpy.ops.wm.stl_import(filepath=str(base/p['stl']));o=bpy.context.object;o.name='BASE-'+p['id'];o.scale=(.001,.001,.001);link(o,'80_Base_Context')
  else:continue
  color=p.get('color',[.3,.35,.4,1]);ma=mat(o.name+'_material',color[:3],.5 if p['material'] in ['steel','S355','6061-T651','brass'] else .0);o.data.materials.clear();o.data.materials.append(ma)
  o['Context only']='Existing B04-P2, not an arm printable part'
  if p['id']=='B04-302-LIGHT-LENS':
   bs=ma.node_tree.nodes.get('Principled BSDF');bs.inputs['Emission Color'].default_value=(1,.45,.08,1);bs.inputs['Emission Strength'].default_value=.35

def pose(name):
 for j,q in zip(L['joints'],L['poses'][name]):frames[j['id']+'.rotor']['angle_deg']=q
 bpy.context.view_layer.update()
def camera(pos,target,scale):
 o=bpy.data.objects.get('Review_camera')
 if not o:
  bpy.ops.object.camera_add();o=bpy.context.object;o.name='Review_camera';link(o,'99_Presentation')
 o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();o.data.type='ORTHO';o.data.ortho_scale=scale;scene.camera=o
 return o
for name,loc,energy,size in [('Key',(.4,.6,1.4),18,.8),('Fill',(-.7,.5,.7),10,.7),('Rim',(.0,-.4,1.0),12,.6)]:
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name=name;o.data.energy=energy;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector((0,.3,.25))-o.location).to_track_quat('-Z','Y').to_euler();link(o,'99_Presentation')
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.22));o=bpy.context.object;o.name='Render_ground';link(o,'99_Presentation');o.data.materials.append(mat('Background',(.63,.66,.69)))
text=bpy.data.texts.new('READ_ME_3KG_TARGET');text.write('A10: long geometry-validation assembly.\n3kg is a target, not a proven rating.\nPrint kit contains PA12 structural prototypes and PETG covers. Tubes, sleeves, bearings and fasteners remain metal.\nJ2 thermal margin and motor output-bearing ratings remain unresolved. No unsupported 3kg loading.\nSelect J1.rotor ... J7.rotor and edit angle_deg. Range is exploratory, not a qualified collision-free domain.\nOfficial-motor geometry is local reference under supplier rights, not project licensing.\nPrint files are in print-ready/, not object-space CAD STL.\nNative units metres internally, display mm.\nPurchased and BASE-context parts must not be printed.\nCAD manifest SHA256: '+hashlib.sha256(FILE.read_bytes()).hexdigest())
scene['Design status']=D['status'];scene['Payload target kg']=3;scene['Petal head installed']=False
scene['Source manifest SHA256']=hashlib.sha256(FILE.read_bytes()).hexdigest()
bpy.context.preferences.filepaths.save_version=0
pose('attention');camera((.95,1.1,.8),(0,.38,.23),1.15)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.region_3d.view_distance=1.1;area.spaces.active.region_3d.view_location=Vector((0,.36,.21));area.spaces.active.region_3d.view_rotation=scene.camera.rotation_euler.to_quaternion();area.spaces.active.clip_start=.001
   area.spaces.active.shading.type='MATERIAL'
bpy.ops.object.select_all(action='DESELECT');frames['J7.rotor'].select_set(True);bpy.context.view_layer.objects.active=frames['J7.rotor']
destination=ROOT/'work/arm-a10/odradek-a10-long-actual-motors.blend' if ACTUAL else OUT/'odradek-a10-long-validation.blend'
destination.parent.mkdir(parents=True,exist_ok=True)
scene['Official motor CAD imported']=ACTUAL
bpy.ops.wm.save_as_mainfile(filepath=str(destination),compress=True)
if '--no-render' not in sys.argv:
 for name in ['attention','idle','reference']:
  pose(name);scene.render.filepath=str(OUT/f'{name}.png');bpy.ops.render.render(write_still=True)
 pose('attention');camera((.85,1.08,.69),(0,.39,.33),.87)
 scene.render.filepath=str(OUT/'body-detail.png');bpy.ops.render.render(write_still=True)
 # Technical J7 close-up with cage separated axially; restore after render.
 pose('attention');tip=frames['J7.fixed'].matrix_world.translation
 for id,dist in [('J7-bearing-cage',.04),('J7-bearing-retainer',.07),('B7-output-flange',.10),('J7-inner-spacer',.09),('J7-inner-centre-spacer',.05)]:bpy.data.objects[id].location.x=dist
 camera(tip+Vector((.22,.25,.18)),tip,.32);scene.render.filepath=str(OUT/'j7-exploded.png');bpy.ops.render.render(write_still=True)
print('BLENDER_A10_COMPLETE',len(D['parts']),flush=True)
