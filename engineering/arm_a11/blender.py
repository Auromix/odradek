# SPDX-License-Identifier: CC-BY-NC-4.0
"""Import original A11 CAD meshes into a seven-joint editable Blender rig."""
import bpy,json,math,sys,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
from context_source import canonical_repo
CANONICAL=canonical_repo()
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'engineering/arm_a11/build';ACTUAL='--actual' in sys.argv
FILE=OUT/'manifest.json';D=json.loads(FILE.read_text());L=D['layout']
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='MILLIMETERS'
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1600;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.world.color=(.35,.38,.42);scene.view_settings.view_transform='AgX'
cols={}
for name in ['00_Rig','01_Load_Structure','02_Removable_Shrouds','03_Purchased_Parts','04_Fit_Gauges_HIDDEN','05_Official_Motors_LOCAL','80_Base_Context','99_Presentation']:
 c=bpy.data.collections.new(name);scene.collection.children.link(c);cols[name]=c

def mat(name,color,metal=.0):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=.38
 return m
M={'core':mat('Graphite_load_structure',(.045,.055,.066)), 'cover':mat('Alien_graphite_armour',(.09,.125,.15)), 'metal':mat('Purchased_metal',(.075,.095,.115),.65), 'amber':mat('Amber_mechanical_insert',(.52,.32,.10),.3)}
def link(obj,col):
 for c in list(obj.users_collection):c.objects.unlink(obj)
 cols[col].objects.link(obj)
def empty(name,parent,loc):
 o=bpy.data.objects.new(name,None);cols['00_Rig'].objects.link(o);o.parent=parent;o.matrix_parent_inverse=Matrix.Identity(4);o.location=Vector(loc)*.001;o.empty_display_size=.02
 return o
root=empty('Arm_mount_B05',None,[0,75,34.6]);root.rotation_euler.z=math.pi/2
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
# Append current shared base from the authoritative sibling repository.
BASE_REPO=CANONICAL
BASE_NATIVE=BASE_REPO/'engineering/base_b05/build/exterior/ODR-BASE-B05-EXTERIOR.blend'
BASE_MANIFEST=BASE_REPO/'engineering/base_b05/build/exterior/exterior-manifest.json'
bd=json.loads(BASE_MANIFEST.read_text());ids=[p['id'] for p in bd['parts']]
with bpy.data.libraries.load(str(BASE_NATIVE),link=False) as (src,dst):
 dst.objects=ids
for obj in dst.objects:
 if obj is None:raise RuntimeError('Missing canonical base object')
 cols['80_Base_Context'].objects.link(obj)
 obj['Context only']='Canonical shared base exterior; not arm load chassis'
scene['Canonical base manifest SHA256']=hashlib.sha256(BASE_MANIFEST.read_bytes()).hexdigest()
scene['Canonical base revision']=bd['revision']
scene['Canonical base repository']=str(BASE_REPO)
# Head form is a removable visual reference only: exact existing R5 petal solids.
# It is not the 1-motor mechanism and is excluded from loads/assembly certification.
headcol=bpy.data.collections.new('81_Petal_Form_Reference_HIDDEN');scene.collection.children.link(headcol)
headroot=empty('Petal_visual_reference_DATUM',frames['J7.rotor'],D['flange_from_J7_mm'])
headroot.rotation_euler=(math.pi/2,0,math.pi/2)
headroot['Scope']='Four source petal forms plus schematic face; visual continuity only, not tool assembly.'
lightmat=mat('Luminous_contact_face',(1,.61,.14),.05)
bs=lightmat.node_tree.nodes.get('Principled BSDF');bs.inputs['Emission Color'].default_value=(1,.55,.10,1);bs.inputs['Emission Strength'].default_value=.6
head_materials={'frame':M['cover'],'retainer':M['metal'],'compliant_skin':lightmat}
for fid,kind,hand,angle in [('UR','upper','right',25),('UL','upper','left',155),('LL','lower','left',220),('LR','lower','right',320)]:
 for part in ['frame','retainer','compliant_skin']:
  path=BASE_REPO/'engineering/generated/r5-petal-form02'/f'{kind}-{hand}'/(part+'.stl')
  bpy.ops.wm.stl_import(filepath=str(path));o=bpy.context.object;o.name='HEAD_FORM_'+fid+'_'+part
  for co in list(o.users_collection):co.objects.unlink(o)
  headcol.objects.link(o);o.parent=headroot;o.matrix_parent_inverse=Matrix.Identity(4);o.scale=(.001,)*3
  a=math.radians(angle);o.location=(.055*math.cos(a),.055*math.sin(a),.09)
  o.rotation_euler.z=a;o.data.materials.clear();o.data.materials.append(head_materials[part])
  o['Source STL SHA256']=hashlib.sha256(path.read_bytes()).hexdigest();o['Source source']=str(path);o['Visual reference only']=True
# Schematic eye face matches the approved drawing, explicitly not a manufactured head.
def head_cylinder(name,r,depth,loc,material):
 bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=r,depth=depth,location=(0,0,0));o=bpy.context.object;o.name=name
 for co in list(o.users_collection):co.objects.unlink(o)
 headcol.objects.link(o);o.parent=headroot;o.location=loc;o.data.materials.append(material)
 bevel=o.modifiers.new('Edge_break_visual_only','BEVEL');bevel.width=.001;bevel.segments=2
 return o
head_cylinder('HEAD_REFERENCE_connector_SCHEMATIC',.025,.075,(0,0,.038),M['core'])
head_cylinder('HEAD_REFERENCE_face_rim',.052,.022,(0,0,.08),M['cover'])
head_cylinder('HEAD_REFERENCE_matrix',.046,.003,(0,0,.092),M['core'])
for y in [-.068,.068]:
 head_cylinder('HEAD_REFERENCE_fisheye_housing',.020,.025,(0,y,.08),M['cover'])
 o=head_cylinder('HEAD_REFERENCE_fisheye',.015,.008,(0,y,.096),M['metal']);o.rotation_euler.x=math.copysign(math.radians(-12),y)
for i in range(48):
 a=2*math.pi*i/48;head_cylinder('HEAD_REFERENCE_ring_pixel',.0014,.0005,(.039*math.cos(a),.039*math.sin(a),.094),lightmat)
for row in range(9):
 for x in range(-6,7):
  if abs(x)==row//2 or row==5 and abs(x)<3:
   head_cylinder('HEAD_REFERENCE_attention_pixel',.0014,.0005,(.0035*x,.019-row*.0035,.094),lightmat)
scene['Head source geometry unchanged']=True
scene['Head presentation only']=True
headcol.hide_render=True;headcol.hide_viewport=True

def pose(name):
 for j,q in zip(L['joints'],L['poses'][name]):frames[j['id']+'.rotor']['angle_deg']=q
 bpy.context.view_layer.update()
def camera(pos,target,scale):
 o=bpy.data.objects.get('Review_camera')
 if not o:
  bpy.ops.object.camera_add();o=bpy.context.object;o.name='Review_camera';link(o,'99_Presentation')
 o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();o.data.type='ORTHO';o.data.ortho_scale=scale;scene.camera=o
 return o
for name,loc,energy,size in [('Key',(.4,.6,1.4),32,.8),('Fill',(-.7,.5,.7),18,.7),('Rim',(.0,-.4,1.0),25,.6)]:
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name=name;o.data.energy=energy;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector((0,.3,.25))-o.location).to_track_quat('-Z','Y').to_euler();link(o,'99_Presentation')
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,0));o=bpy.context.object;o.name='Render_ground';link(o,'99_Presentation');o.data.materials.append(mat('Background',(.75,.78,.79)))
text=bpy.data.texts.new('READ_ME_3KG_TARGET');text.write('A11: long geometry-validation assembly.\n3kg is a target, not a proven rating.\nPrint kit contains PA12 structural prototypes and PETG covers. Tubes, sleeves, bearings and fasteners remain metal.\nJ2 thermal margin and motor output-bearing ratings remain unresolved. No unsupported 3kg loading.\nSelect J1.rotor ... J7.rotor and edit angle_deg. Range is exploratory, not a qualified collision-free domain.\nOfficial-motor geometry is local reference under supplier rights, not project licensing.\nPrint files are in print-ready/, not object-space CAD STL.\nNative units metres internally, display mm.\nPurchased and BASE-context parts must not be printed.\nCAD manifest SHA256: '+hashlib.sha256(FILE.read_bytes()).hexdigest())
scene['Design status']=D['status'];scene['Payload target kg']=3;scene['Petal head installed']=False
scene['Source manifest SHA256']=hashlib.sha256(FILE.read_bytes()).hexdigest()
bpy.context.preferences.filepaths.save_version=0
pose('attention');camera((.9,1.05,.75),(0,.27,.24),1.05)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.region_3d.view_distance=1.1;area.spaces.active.region_3d.view_location=Vector((0,.36,.21));area.spaces.active.region_3d.view_rotation=scene.camera.rotation_euler.to_quaternion();area.spaces.active.clip_start=.001
   area.spaces.active.shading.type='MATERIAL'
bpy.ops.object.select_all(action='DESELECT');frames['J7.rotor'].select_set(True);bpy.context.view_layer.objects.active=frames['J7.rotor']
destination=ROOT/'work/arm-a11/odradek-a11-long-actual-motors.blend' if ACTUAL else OUT/'odradek-a11-long-validation.blend'
destination.parent.mkdir(parents=True,exist_ok=True)
scene['Official motor CAD imported']=ACTUAL
bpy.ops.wm.save_as_mainfile(filepath=str(destination),compress=True)
if '--no-render' not in sys.argv:
 for name in ['attention','idle','reference']:
  pose(name);scene.render.filepath=str(OUT/f'{name}.png');bpy.ops.render.render(write_still=True)
 pose('attention');camera((.85,1.08,.69),(0,.39,.33),.87)
 scene.render.filepath=str(OUT/'body-detail.png');bpy.ops.render.render(write_still=True)
 headcol.hide_render=False;headcol.hide_viewport=False
 pose('attention');camera((1.05,1.15,.8),(0,.30,.24),1.20)
 scene.render.filepath=str(OUT/'style-context.png');bpy.ops.render.render(write_still=True)
 headcol.hide_render=True;headcol.hide_viewport=True
 # Technical J7 close-up with cage separated axially; restore after render.
 pose('attention');tip=frames['J7.fixed'].matrix_world.translation
 for id,dist in [('J7-bearing-cage',.04),('J7-bearing-retainer',.07),('B7-output-flange',.10),('J7-inner-spacer',.09),('J7-inner-centre-spacer',.05)]:bpy.data.objects[id].location.x=dist
 camera(tip+Vector((.22,.25,.18)),tip,.32);scene.render.filepath=str(OUT/'j7-exploded.png');bpy.ops.render.render(write_still=True)
print('BLENDER_A11_COMPLETE',len(D['parts']),flush=True)
