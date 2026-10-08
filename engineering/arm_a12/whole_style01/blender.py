# SPDX-License-Identifier: CC-BY-NC-4.0
"""Whole-arm selected-A surface study over actual, unchanged motor/axis geometry.
These are editable Blender design surfaces, NOT manufacturing definitions.
"""
from pathlib import Path
import bpy,bmesh,json,sys,math,hashlib
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent/'build';OUT.mkdir(exist_ok=True)
ACTUAL='--actual' in sys.argv
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
S=ROOT/'engineering/arm_a12/shoulder01/build';INPUTS=json.loads((S/'inputs.json').read_text())
BASE=ROOT/'work/arm-a12/shoulder01-actual-motors.blend' if ACTUAL else S/'A12-A-shoulder01.blend'
BASELINE=json.loads((ROOT/'engineering/arm_a11/build/manifest.json').read_text());L=BASELINE['layout']
SOURCE=ROOT/'engineering/arm_a11/build/manifest.json';assert sha(SOURCE)==json.loads((S/'manifest.json').read_text())['baseline_manifest_sha256']
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.context.scene
assert scene['A12 canonical base native SHA256']==INPUTS['base_native_sha256']
for p in BASELINE['parts']:
 if p['role']=='printed_cover' and p['id'] in bpy.data.objects:bpy.data.objects.remove(bpy.data.objects[p['id']],do_unlink=True)
col=bpy.data.collections.new('A12_WHOLE_STYLE_Editable_Surfaces');scene.collection.children.link(col)
reservations=bpy.data.collections.new('A12_WHOLE_STYLE_Routing_Intent_HIDDEN');scene.collection.children.link(reservations)
def mat(name,color,metal=.1,rough=.38):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;return m
M=mat('A12 Graphite blue carapace',(.018,.035,.049),.35)
GAP=mat('A12 Dark recessed spine and moving seams',(.012,.021,.028),.05)
TRIM=mat('A12 Quiet bronze insert',(.38,.24,.11),.5)
WIRE=mat('A12 Amber reservation not installed cable',(1,.4,.06),.05)
for obj in bpy.data.collections['A12_01_J2_Selected_A_Shields'].objects:
 obj.data.materials.clear();obj.data.materials.append(M);obj['Whole style role']='Inherited checked J2 prototype, not new whole-arm proof'
profiles={
 'shield':[(-1.1,-.32),(-.86,-.85),(-.3,-1.08),(.33,-1.07),(.87,-.8),(1.12,-.24),(1.13,.31),(.72,.98),(.10,1.20),(-.58,1.11),(-1.05,.67)],
 'blade':[(-1,0),(-1,.65),(-.72,.94),(0,1.10),(.72,.94),(1,.65),(1,0),(1,-.65),(.65,-.96),(0,-1.04),(-.65,-.96),(-1,-.65)],
 'root':[(math.cos(2*math.pi*k/16),math.sin(2*math.pi*k/16)) for k in range(16)]}
definitions=[]
def mesh(name,verts,faces,frame,material=M,role='style_surface'):
 me=bpy.data.meshes.new(name);me.from_pydata([tuple(v*.001 for v in co) for co in verts],[],faces);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();faces=[tuple(p.vertices) for p in me.polygons];me.materials.append(material)
 me.set_sharp_from_angle(angle=math.radians(34))
 for f in me.polygons:f.use_smooth=True
 o=bpy.data.objects.new(name,me);col.objects.link(o);o.parent=bpy.data.objects['Arm_mount_B05' if frame=='world' else frame];o.matrix_parent_inverse=Matrix.Identity(4)
 o['Design surface only']=True;o['Printable release']=False;o['Frame']=frame;o['role']=role
 definitions.append(dict(id=name,frame=frame,role=role,material_rgba=list(material.diffuse_color),vertices_mm=verts,triangles=faces))
 return o
def skin(name,frame,axis,stations,profile='shield',wall=2.6,cap=False,material=M):
 # Each station is(q,radial_u,radial_v,centre_u,centre_v), mm.
 # Native vertices keep actual dimensions; no scaled motor placeholders.
 if name in ['A12-W20-upper-blade','A12-W21-fore-blade']:
  dense=[]
  for k in range(len(stations)-1):
   a=stations[max(0,k-1)];b=stations[k];c=stations[k+1];d=stations[min(len(stations)-1,k+2)]
   for step in range(6):
    t=step/6;values=[b[0]+(c[0]-b[0])*t]
    for j in range(1,5):values.append(.5*((2*b[j])+(-a[j]+c[j])*t+(2*a[j]-5*b[j]+4*c[j]-d[j])*t*t+(-a[j]+3*b[j]-3*c[j]+d[j])*t*t*t))
    dense.append(tuple(values))
  stations=dense+[stations[-1]]
 uv=[i for i in range(3) if i!=axis];poly=profiles[profile];N=len(poly);verts=[];faces=[]
 axial_direction=1 if stations[-1][0]>stations[0][0] else -1
 inner=[tuple([s[0]+axial_direction*wall if cap and i==0 else s[0],max(1,s[1]-wall),max(1,s[2]-wall),s[3],s[4]]) for i,s in enumerate(stations)]
 for seq in [stations,inner]:
  for q,ru,rv,cu,cv in seq:
   for a,b in poly:
    xyz=[0,0,0];xyz[axis]=q;xyz[uv[0]]=cu+ru*a;xyz[uv[1]]=cv+rv*b;verts.append(xyz)
 K=len(stations);offset=K*N
 for j in range(K-1):
  for i in range(N):
   k=(i+1)%N;a=j*N+i;b=j*N+k;c=(j+1)*N+k;d=(j+1)*N+i
   faces.extend([(a,b,c),(a,c,d),(offset+a,offset+d,offset+c),(offset+a,offset+c,offset+b)])
 for i in range(N):
  k=(i+1)%N;a=(K-1)*N+i;b=(K-1)*N+k
  faces.extend([(a,offset+a,offset+b),(a,offset+b,b)])
 if cap:
  for start,seq,flip in [(0,stations,False),(offset,inner,True)]:
   q,ru,rv,cu,cv=seq[0];centre=[0,0,0];centre[axis]=q;centre[uv[0]]=cu;centre[uv[1]]=cv;idx=len(verts);verts.append(centre)
   for i in range(N):faces.append((idx,start+(i+1)%N,start+i) if not flip else (idx,start+i,start+(i+1)%N))
 else:
  for i in range(N):k=(i+1)%N;faces.extend([(i,offset+k,offset+i),(i,k,offset+k)])
 return mesh(name,verts,faces,frame,material)
# Root and upstream shoulder: the major contour is tapered, not a barrel stack.
skin('A12-W01-root-carapace','world',2,[(43,78,74,0,0),(68,71,70,0,0),(110,67,66,0,0),(137.4,69,68,0,0)],'root')
skin('A12-W02-shoulder-lower-cowl','J1.rotor',2,[(10,67,65,-2,4),(31,81,65,-8,15),(58,88,58,-10,21)],'blade')
skin('A12-W03-bridge-spine','J1.rotor',2,[(119,8,12,-82,1),(101,10,18,-86,1),(65,11,19,-88,0),(31,10,16,-86,0)],'blade',cap=True,material=GAP)
# Full-size fixed motor-side guards: open output mouths remain independent of rotors.
for idx,lo,hi,r,cu,cv in [(3,-35,33,60,0,0),(4,-35,33,60,0,0),(5,92,29,50,0,0),(6,104,39,32,0,0),(7,-35,56,45,0,0)]:
 axis=L['joints'][idx-1]['axis'].index(1);direction=1 if hi>lo else -1
 st=[(lo,r*.88,r*.91,cu,cv),(lo+direction*9,r+2,r+1,cu-1,cv),(hi-direction*6,r,r,cu,cv),(hi,r-1,r-1,cu,cv)]
 skin(f'A12-W{idx+1:02}-J{idx}-fixed-guard',f'J{idx}.fixed',axis,st,cap=True)
# Quiet rotating lips obscure front bolt discs without joining fixed and moving skins.
for idx,axis,q0,q1,r,opening in [(3,0,36,48,58,34),(4,1,36,44,60,35),(5,1,25,18,49,24),(6,2,35,29,35,17),(7,0,58,63,32,25)]:
 # A short annulus with constant inner aperture; all units mm.
 N=48;verts=[];faces=[]
 uv=[i for i in range(3) if i!=axis]
 for q,rad in [(q0,r),(q1,r-2),(q0,opening),(q1,opening)]:
  for i in range(N):
   xyz=[0,0,0];xyz[axis]=q;xyz[uv[0]]=rad*math.cos(2*math.pi*i/N);xyz[uv[1]]=rad*math.sin(2*math.pi*i/N);verts.append(xyz)
 for a,b,reverse in [(0,N,False),(2*N,3*N,True),(0,2*N,True),(N,3*N,False)]:
  for i in range(N):j=(i+1)%N;f=[(a+i,a+j,b+j),(a+i,b+j,b+i)];faces.extend(tuple(reversed(v)) if reverse else v for v in f)
 mesh(f'A12-W{idx+10:02}-J{idx}-rotor-lip',verts,faces,f'J{idx}.rotor',GAP)
# Tensioned long blade skins: separate structural metal members remain underneath.
skin('A12-W20-upper-blade','J3.rotor',0,[(43,51,51,0,0),(76,32,35,0,0),(122,23,28,0,0),(197,20,26,0,0),(248,25,32,0,0),(289,45,52,0,0)],'blade')
skin('A12-W21-fore-blade','J4.rotor',0,[(18,31,36,62,0),(39,25,31,62,0),(75,19,25,62,0),(111,21,27,62,0),(165,35,39,62,0)],'blade')
# Slim dark dorsal conduit is a removable-service intent, not an installed harness.
skin('A12-W22-upper-dorsal-lid','J3.rotor',0,[(82,5,1.6,0,37),(132,4,1.6,0,30),(194,4,1.6,0,29),(244,5,1.6,0,35)],'blade',wall=1.2,material=GAP)
skin('A12-W23-fore-dorsal-lid','J4.rotor',0,[(35,4,1.5,62,34),(75,4,1.5,62,28),(111,4,1.5,62,30)],'blade',wall=1.2,material=GAP)
def route(name,frame,coords):
 curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.bevel_depth=.006;curve.bevel_resolution=2;curve.use_fill_caps=True
 sp=curve.splines.new('POLY');sp.points.add(len(coords)-1)
 for p,co in zip(sp.points,coords):p.co=(*[x*.001 for x in co],1)
 o=bpy.data.objects.new(name,curve);reservations.objects.link(o);o.parent=bpy.data.objects[frame];o.matrix_parent_inverse=Matrix.Identity(4);curve.materials.append(WIRE)
 o['Scope']='Fixed link D12 route intent only; unconnected joint transitions; not actual cable'
route('INTENT-upper-fixed-conduit','J3.rotor',[[82,0,26],[132,0,25],[194,0,24],[242,0,26]])
route('INTENT-fore-fixed-conduit','J4.rotor',[[35,62,23],[75,62,23],[111,62,24]])
reservations.hide_render=True;reservations.hide_viewport=True
scene['Whole style status']='Selected-A global surface study, not fit/print/thermal/load release'
scene['Whole style baseline SHA256']=sha(SOURCE)
scene['Whole style full collisions checked']=False
scene['Head presentation only']=True
scene['Whole style supplied motor scaling']=False
txt=bpy.data.texts.new('A12_WHOLE_STYLE_README');txt.write('Whole-arm selected-A silhouette FIRST, before mounting detail.\nActual seven-axis geometry retained. New meshes are editable design surfaces, not manufacturing parts.\nNo full-shroud collision, bend, connector, temperature, rated-load or print qualification.\nJ2 inherited module checks are NOT whole-arm checks.\nHead is unchanged form plus schematic face, excluded from arm loads.\nDorsal routes are unconnected volume intents, not completed wiring.\nSelect any J*.rotor and edit angle_deg.\nPublic native has owned envelopes; actual supplier model stays local.\n')
def pose(name):
 for j,q in zip(L['joints'],L['poses'][name]):o=bpy.data.objects[j['id']+'.rotor'];o['angle_deg']=q;o.update_tag()
 bpy.context.view_layer.update()
def camera(pos,target,scale):
 o=bpy.data.objects['Review_camera'];o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();o.data.type='ORTHO';o.data.ortho_scale=scale;scene.camera=o
head=bpy.data.collections['81_Petal_Form_Reference_HIDDEN'];head.hide_render=True;head.hide_viewport=True
# A neutral studio, preserving material contrast rather than flattening to clay.
scene.view_settings.exposure=-.4
scene.view_settings.look='AgX - Medium High Contrast'
for light in bpy.data.lights:
 if light.name=='Fill':light.energy=10
# Head frame follows the approved common material; source forms stay unchanged.
for obj in head.objects:
 if obj.type=='MESH' and ('frame' in obj.name or 'rim' in obj.name or 'housing' in obj.name):
  obj.data.materials.clear();obj.data.materials.append(M)
scene.cycles.samples=32;scene.render.resolution_x=1600;scene.render.resolution_y=1100
pose('attention');camera((-.95,1.1,.72),(0,.32,.26),1.08)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.region_3d.view_distance=1.1;area.spaces.active.region_3d.view_location=Vector((0,.32,.26));area.spaces.active.region_3d.view_rotation=scene.camera.rotation_euler.to_quaternion()
bpy.context.preferences.filepaths.save_version=0
native=ROOT/'work/arm-a12/whole-style01/actual-motors.blend' if ACTUAL else OUT/'A12-A-whole-style.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
if ACTUAL:
 data=dict(revision='A12-A-WHOLE-STYLE01',status='overall_style_surfaces_not_manufacturing',baseline_manifest_sha256=sha(SOURCE),base_native_sha256=INPUTS['base_native_sha256'],layout=L,flange_from_J7_mm=BASELINE['flange_from_J7_mm'],style_surfaces=definitions,source_native_sha256=sha(BASE),motor_geometry_unchanged=True,full_collision_audit=False,head_schematic=True)
 (OUT/'style-surfaces.json').write_text(json.dumps(data,separators=(',',':'))+'\n')
if '--no-render' not in sys.argv:
 for name in ['attention','idle']:
  pose(name);camera((-.95,1.1,.72) if name=='attention' else (-.78,.95,.55),(0,.32,.26) if name=='attention' else (0,.22,.20),1.08 if name=='attention' else .83)
  scene.render.filepath=str(OUT/(name+'-bare.png'));bpy.ops.render.render(write_still=True)
 pose('attention');head.hide_render=False;head.hide_viewport=False
 camera((-.70,1.28,.67),(0,.33,.27),1.19);scene.render.filepath=str(OUT/'attention-with-head.png');bpy.ops.render.render(write_still=True)
 head.hide_render=True;head.hide_viewport=True
 (OUT/'render-source.json').write_text(json.dumps(dict(whole_native_sha256=sha(native),source_native_sha256=sha(BASE),base_native_sha256=INPUTS['base_native_sha256'],baseline_manifest_sha256=sha(SOURCE),supplier_geometry=ACTUAL,scope='Whole selected-A style surfaces; no complete manufacturing or fit release.'),indent=2)+'\n')
print('WHOLE_STYLE_COMPLETE',ACTUAL,len(definitions),flush=True)
