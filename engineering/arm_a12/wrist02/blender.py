# SPDX-License-Identifier: CC-BY-NC-4.0
"""Integrate wrist02 actual CAD with the approved selected-A native arm study."""
from pathlib import Path
import bpy,bmesh,json,sys,math,hashlib
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent/'build';ACTUAL='--actual' in sys.argv
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
D=json.loads((OUT/'manifest.json').read_text());PREV=ROOT/'engineering/arm_a12/whole_style01/build';A=json.loads((PREV/'audit.json').read_text());L=json.loads((PREV/'style-surfaces.json').read_text())['layout']
source=ROOT/'work/arm-a12/whole-style01/actual-motors.blend' if ACTUAL else PREV/'A12-A-whole-style.blend'
assert sha(source)==A['actual_native_sha256' if ACTUAL else 'public_native_sha256']
bpy.ops.wm.open_mainfile(filepath=str(source));scene=bpy.context.scene
context=json.loads((OUT/'base-context.json').read_text());basefile=ROOT/context['read_only_cache_relative_path'];assert sha(basefile)==context['base_native_sha256']
for obj in list(bpy.data.collections['80_Base_Context'].objects):bpy.data.objects.remove(obj,do_unlink=True)
with bpy.data.libraries.load(str(basefile),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.startswith('B06-')]
for obj in dst.objects:
 assert obj is not None;bpy.data.collections['80_Base_Context'].objects.link(obj);obj['A12 context only']='Authoritative base context; root integration not qualified'
scene['A12 canonical base native SHA256']=context['base_native_sha256'];scene['A12 canonical base path']=context['base_canonical_relative_path'];scene['Canonical base revision']=context['base_revision'];scene['Canonical base manifest SHA256']=context['base_manifest_sha256']
for name in D['replaced_style_parts']:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
col=bpy.data.collections.new('A12_WRIST02_Split_CAD_Geometry');scene.collection.children.link(col)
material=bpy.data.materials['A12 Graphite blue carapace']
def mesh(id,verts,faces,parent,collection):
 me=bpy.data.meshes.new(id);me.from_pydata([tuple(v*.001 for v in co) for co in verts],[],faces);me.update();me.materials.append(material)
 me.set_sharp_from_angle(angle=math.radians(28))
 for p in me.polygons:p.use_smooth=True
 o=bpy.data.objects.new(id,me);collection.objects.link(o);o.parent=bpy.data.objects[parent];o.matrix_parent_inverse=Matrix.Identity(4);return o
for p in D['parts']:
 obj=mesh(p['id'],p['vertices_mm'],p['triangles'],p['frame'],col)
 obj['Frame']=p['frame'];obj['role']='style_surface';obj['Source STEP SHA256']=p['step_sha256'];obj['Prototype']='Non-load-bearing split cover; no powered/print release';obj['Printable release']=False
# The old visual fore-blade intruded into the new J5 shield; trim the visual
# loft at X118, leaving the actual structural members and actuator unchanged.
old=bpy.data.objects['A12-W21-fore-blade'];parent=old.parent.name;collection=old.users_collection[0];bpy.data.objects.remove(old,do_unlink=True)
profile=[(-1,0),(-1,.65),(-.72,.94),(0,1.10),(.72,.94),(1,.65),(1,0),(1,-.65),(.65,-.96),(0,-1.04),(-.65,-.96),(-1,-.65)]
st=[(18,31,36),(39,25,31),(75,19,25),(111,21,27),(118,22,28)];verts=[];faces=[];N=len(profile);K=len(st)
for inset in [0,2.6]:
 for x,y,z in st:
  verts.extend([[x,62+(y-inset)*a,(z-inset)*b] for a,b in profile])
off=K*N
for k in range(K-1):
 for i in range(N):
  j=(i+1)%N;a=k*N+i;b=k*N+j;c=(k+1)*N+j;d=(k+1)*N+i;faces.extend([(a,b,c),(a,c,d),(off+a,off+d,off+c),(off+a,off+c,off+b)])
for k in [0,K-1]:
 for i in range(N):
  j=(i+1)%N;a=k*N+i;b=k*N+j;faces.extend([(a,b,off+b),(a,off+b,off+a)])
o=mesh('A12-W21-fore-blade',verts,faces,parent,collection);bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();o['Design surface only']=True;o['role']='style_surface';o['Printable release']=False
scene['A12 design status']='Wrist02 split CAD prototypes on otherwise unqualified selected-A whole-arm style'
scene['Wrist02 manifest SHA256']=sha(OUT/'manifest.json');scene['Wrist02 source native SHA256']=sha(source);scene['Wrist02 fit release']=False
for name in ['A12_SCOPE','A12_WHOLE_STYLE_README']:
 if name in bpy.data.texts:bpy.data.texts[name].name=name+'_HISTORICAL_SOURCE'
txt=bpy.data.texts.new('A12_WRIST02_README');txt.write('Wrist02: six original CAD cosmetic shields, actual motors and seven axes unchanged.\nInherited whole-arm appearance remains a style study.\nNominal M3 clamp locations/head/nut seats retained; physical retention/liners/thermal tests pending.\nNo complete flexible wiring, load rating or print release.\nOld fore-blade visual mesh shortened to avoid new shield; actual structural members unchanged.\nSource STEP and scoped collision reports live in engineering/arm_a12/wrist02/build.\n')
head=bpy.data.collections['81_Petal_Form_Reference_HIDDEN'];head.hide_render=True;head.hide_viewport=True
def pose(name):
 for j,q in zip(L['joints'],L['poses'][name]):obj=bpy.data.objects[j['id']+'.rotor'];obj['angle_deg']=q;obj.update_tag()
 bpy.context.view_layer.update()
def camera(pos,target,scale):
 obj=bpy.data.objects['Review_camera'];obj.location=pos;obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler();obj.data.type='ORTHO';obj.data.ortho_scale=scale;scene.camera=obj
pose('attention');camera((-.70,1.28,.67),(0,.33,.27),1.19);scene.cycles.samples=20
scene.render.resolution_x=1600;scene.render.resolution_y=1100;bpy.context.preferences.filepaths.save_version=0
native=ROOT/'work/arm-a12/wrist02/actual-motors.blend' if ACTUAL else OUT/'A12-A-wrist02.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
if ACTUAL:
 prior=json.loads((PREV/'style-surfaces.json').read_text());styles=[p for p in prior['style_surfaces'] if p['id'] not in D['replaced_style_parts']]
 for p in styles:
  obj=bpy.data.objects[p['id']];p['vertices_mm']=[[float(v)*1000 for v in q.co] for q in obj.data.vertices];p['triangles']=[list(q.vertices) for q in obj.data.polygons]
 for p in D['parts']:styles.append(dict(p,role='style_surface',material_rgba=list(material.diffuse_color)))
 (OUT/'style-surfaces.json').write_text(json.dumps(dict(revision='A12-A-WRIST02-INTEGRATION',layout=L,style_surfaces=styles,flange_from_J7_mm=prior['flange_from_J7_mm'],base_native_sha256=context['base_native_sha256'],base_revision=context['base_revision'],baseline_manifest_sha256=D['baseline_manifest_sha256'],whole_style_source_manifest_sha256=D['whole_style_manifest_sha256'],source_native_sha256=sha(source),motor_geometry_unchanged=True,full_collision_audit=False,head_schematic=True),separators=(',',':'))+'\n')
if '--no-render' not in sys.argv:
 head.hide_render=False;head.hide_viewport=False;scene.render.filepath=str(OUT/'whole-attention.png');bpy.ops.render.render(write_still=True);head.hide_render=True;head.hide_viewport=True
 camera((-.88,1.18,.62),(0,.32,.27),1.04);scene.render.filepath=str(OUT/'whole-bare.png');bpy.ops.render.render(write_still=True)
 pose('idle');camera((-.8,1.03,.6),(0,.23,.22),.88);scene.render.filepath=str(OUT/'whole-idle.png');bpy.ops.render.render(write_still=True)
 pose('attention');tip=bpy.data.objects['J6.fixed'].matrix_world.translation;camera(tip+Vector((-.28,.30,.22)),tip,.33)
 # Hide remote arm to inspect wrist components. Cameras/lights retained.
 hidden=[]
 for obj in scene.objects:
  if obj.type=='MESH' and obj.parent is not None and obj.parent.name in ['Arm_mount_B05','J1.fixed','J1.rotor','J2.fixed','J2.rotor','J3.fixed','J3.rotor']:
   hidden.append((obj,obj.hide_render));obj.hide_render=True
 scene.render.filepath=str(OUT/'wrist-assembled.png');bpy.ops.render.render(write_still=True)
 saved=[]
 for p in D['parts']:
  obj=bpy.data.objects[p['id']];saved.append((obj,obj.location.copy()));axis=0 if not p['id'].startswith('A12-WR02-J7') else 1
  obj.location[axis]=.052 if p['id'].endswith('-A') else -.052
 camera(tip+Vector((-.36,.36,.27)),tip,.47);scene.render.filepath=str(OUT/'wrist-exploded.png');bpy.ops.render.render(write_still=True)
 for obj,loc in saved:obj.location=loc
 for obj,value in hidden:obj.hide_render=value
 (OUT/'render-source.json').write_text(json.dumps(dict(native_sha256=sha(native),source_native_sha256=sha(source),base_native_sha256=context['base_native_sha256'],manifest_sha256=sha(OUT/'manifest.json'),supplier_geometry=ACTUAL,scope='Actual unchanged actuators; split wrist cosmetic prototypes, other body surfaces unqualified; exploded shields only.'),indent=2)+'\n')
print('WRIST02_NATIVE',ACTUAL,len(D['parts']),flush=True)
