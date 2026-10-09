# SPDX-License-Identifier: CC-BY-NC-4.0
"""B06 compact one-piece shield. Run using Blender --background --python.

Own frozen project meshes are integration references, not a completed load path.
"""
from pathlib import Path
import json, math, sys, struct
HERE = Path(__file__).resolve().parent
exec(compile((HERE/'geometry.py').read_text(), str(HERE/'geometry.py'), 'exec'), globals())
MOUNTS = [(-87,36),(87,36),(-72,125),(72,125)]
REAR_MOUNTS = [(-60,-29),(60,-29)]
REAR_SCREW_Z = 32
DESCRIPTORS, PAYLOAD = [], {}

def cylinder(name,x,y,r,z0,z1,n=64):
    bpy.ops.mesh.primitive_cylinder_add(vertices=n, radius=r*M, depth=(z1-z0)*M,
                                      location=(x*M,y*M,(z0+z1)*M/2))
    o=bpy.context.object; o.name=name
    return o

def hexagon(name,x,y,af,z0,z1):
    r=af/math.sqrt(3)
    return contour_prism(name,[(x+r*math.cos(math.pi/6+i*math.pi/3),y+r*math.sin(math.pi/6+i*math.pi/3)) for i in range(6)],(z0,z1))

def along_y(o,x,z):
    # Local cylinder/hex axial Z becomes global +Y. Keep millimetre datums.
    coords=[(o.matrix_world @ v.co)/M for v in o.data.vertices]
    o.location=(0,0,0);o.rotation_euler=(0,0,0);o.scale=(1,1,1)
    for v,(a,b,c) in zip(o.data.vertices,coords):
        v.co=Vector((x+a,c,z-b))*M
    return o

def rear_bore(name,x,r,y0,y1):
    return along_y(cylinder(name,0,0,r,y0,y1),x,REAR_SCREW_Z)

def rear_hex(name,x,af,y0,y1):
    return along_y(hexagon(name,0,0,af,y0,y1),x,REAR_SCREW_Z)

def rear_hardware(index,x):
    s=rear_bore('HW-REAR-M3-'+str(index),x,1.5,-34.6,-24.5)
    boolean(s,rear_bore('Rear button head',x,2.85,-36.15,-34.5),'UNION')
    boolean(s,rear_hex('Rear 2mm hex socket',x,2,-36.2,-35.1),'DIFFERENCE')
    add(s,'M3×10 后向检修螺钉','fasteners','hardware',['Rear-facing axis +Y; loosen from behind without underside tool access; simplified standard hardware'],False,'fasteners')
    n=rear_hex('HW-REAR-NUT-'+str(index),x,5.5,-28.6,-26.2)
    boolean(n,rear_bore('Nut thread envelope',x,1.5,-30,-25),'DIFFERENCE')
    add(n,'后盖底架内藏M3螺母','fasteners','nut',['Nut stays in lower carrier, not in removable lid'],False,'fasteners')

def pcb_hardware(index,x,y):
    s=cylinder('HW-PCB-M3-'+str(index),x,y,1.5,15.6,25.7)
    boolean(s,cylinder('PCB button head',x,y,2.85,25.6,27.25),'UNION')
    boolean(s,hexagon('PCB 2mm hex socket',x,y,2,26.2,27.3),'DIFFERENCE')
    add(s,'PCB M3×10上装固定','fasteners','hardware',['Underhead datum Z25.6; shaft end Z15.6; buy standard screw, not print'],False,'fasteners')
    n=hexagon('HW-PCB-NUT-'+str(index),x,y,5.5,19.2,21.6)
    boolean(n,cylinder('PCB nut thread envelope',x,y,1.5,19,22),'DIFFERENCE')
    add(n,'PCB柱内藏M3螺母','fasteners','nut',['Side insertion before board fit; DIN934 nominal envelope; threads omitted'],False,'fasteners')

def beam(name,p,q,width=12,z0=3,z1=7):
    dx,dy=q[0]-p[0],q[1]-p[1];length=math.hypot(dx,dy)
    nx,ny=-dy/length*width/2,dx/length*width/2
    return contour_prism(name,[(p[0]+nx,p[1]+ny),(q[0]+nx,q[1]+ny),(q[0]-nx,q[1]-ny),(p[0]-nx,p[1]-ny)],(z0,z1))

def add(o,title,role,mat,notes,printable=True,group=None):
    print("Exporting",o.name,flush=True)
    if printable:
        d=export_part(o,title,role,mat,notes)
    else:
        finalize_mesh(o);o.data.materials.clear();o.data.materials.append(MATERIALS[mat])
        write_stl(o,OUT/'stl'/(o.name+'.stl'))
        d=dict(id=o.name,name=title,category='component',quantity=1,material='Integration reference only',
               process='Original project mesh or declared envelope; do not print',
               color=list(MATERIALS[mat].diffuse_color),color_space='linear',bbox=bounding_box_mm(o),
               stl='stl/'+o.name+'.stl',assembly_role=role,notes=notes,
               prototype_status='集成参考；未经采购或实物验证')
    if group:d['viewer_group']=group
    if not printable:d['print_stl']=None
    DESCRIPTORS.append(d);PAYLOAD[o.name]=render_payload(o)
    return d

def conformal_post(owner,x,y,r,z0,inset):
    # Curved roofs cannot safely use a flat-ended vertical cylinder.
    from mathutils.bvhtree import BVHTree
    t=BVHTree.FromObject(owner,bpy.context.evaluated_depsgraph_get())
    n=64;upper=[]
    for i in range(n):
        a=i*math.tau/n;px=x+r*math.cos(a);py=y+r*math.sin(a)
        h,_,_,_=t.ray_cast(Vector((px*M,py*M,.2)),Vector((0,0,-1)))
        if h is None:raise ValueError('Conformal post extends beyond the cover outline')
        if h.z/M-inset<=z0:raise ValueError('Conformal post has no local thickness')
        upper.append((px,py,h.z/M-inset))
    verts=[(px,py,z0) for px,py,_ in upper]+upper
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh_object('Integral conformal hidden post',verts,faces)

def boss(owner,x,y,top):
    # M3 captive nut is inserted from the interior before lowering the cover.
    boolean(owner,conformal_post(owner,x,y,5.6,7,.5),'UNION')
    boolean(owner,cylinder('M3 clearance',x,y,1.7,7,17),'DIFFERENCE')
    boolean(owner,hexagon('M3 captive nut pocket',x,y,5.8,10,12.8),'DIFFERENCE')
    sign=1 if x>0 else -1
    lo,hi=sorted([x,x+sign*8])
    boolean(owner,box('Side nut insertion',((lo,y-2.9,10),(hi,y+2.9,12.8))),'DIFFERENCE')

def hardware(index,x,y,zseat=5.5):
    s=cylinder('HW-M3-'+str(index),x,y,1.5,zseat-.1,zseat+10)
    boolean(s,cylinder('Purchased button head',x,y,2.85,zseat-1.65,zseat),'UNION')
    boolean(s,hexagon('2mm hex socket',x,y,2,zseat-1.65,zseat-.6),'DIFFERENCE')
    add(s,'M3×10 底部固定螺钉','fasteners','hardware',['Nominal standard hardware; simplified threads; buy, do not print'],False,'fasteners')
    nut=hexagon('HW-NUT-'+str(index),x,y,5.5,10,12.4)
    boolean(nut,cylinder('Nominal nut thread',x,y,1.5,9,14),'DIFFERENCE')
    add(nut,'M3 内藏螺母','fasteners','nut',['DIN934 nominal dimensions; thread omitted'],False,'fasteners')

def lamp_retainer(surface,lens):
    from mathutils.bvhtree import BVHTree
    tree=BVHTree.FromObject(surface,bpy.context.evaluated_depsgraph_get())
    hit,_,_,_=tree.ray_cast(Vector((23*M,163.5*M,.2)),Vector((0,0,-1)))
    z=hit.z/M
    bar=box('B06-308-LENS-RETAINER',((-27,162,z-12.3),(27,165,z-10.3)))
    lt=BVHTree.FromObject(lens,bpy.context.evaluated_depsgraph_get())
    # Use the lowest underside over the entire pad footprint, not just its
    # centre. The lamp is sloped; a centre sample could pierce its lower edge.
    heights=[]
    for r in (0,.675,1.35):
        for k in range(64):
            a=k*math.tau/64
            low,_,_,_=lt.ray_cast(Vector((r*math.cos(a)*M,(164.5+r*math.sin(a))*M,0)),Vector((0,0,1)))
            if low is None:raise ValueError('Support pad misses lens')
            heights.append(low.z/M)
    boolean(bar,cylinder('Lens central support pad',0,164.5,1.35,z-11,min(heights)-.4),'UNION')
    for x in (-23,23):boolean(bar,cylinder('M2 clamp-bar hole',x,163.5,1.2,z-14,z-5),'DIFFERENCE')
    return bar

def native_context():
    root=json.loads((HERE/'inputs/root-snapshot.json').read_text())
    for p in root['parts']:
        vertices=[(-v[1],75+v[0],34.6+v[2]) for v in p['vertices_mm']]
        o=mesh_object('REF-'+p['id'],vertices,p['triangles'],'03_Exterior_mount_carriers')
        add(o,'本体参考 '+p['id'],'structure','armor' if p['id'].startswith('S') else 'support',
            ['Frozen A11 project mesh; yaw90; translation(0,75,34.6); source '+root['source_sha256']],False,'structure')
    motor=cylinder('REF-J1-RS03',0,75,53,107.6,164.6)
    add(motor,'J1 RS03 Ø106×57包络','structure','collar',
        ['Motor dimensional envelope only; fixed M4 PC98 interface remains in original top-ring mesh'],False,'structure')
    frame=HERE/'build/load-frame'
    for p in json.loads((frame/'manifest.json').read_text())['parts']:
        if p['category']=='printed':continue
        data=(frame/p['stl']).read_bytes();vertices=[];faces=[];vertex_index={}
        count=struct.unpack_from('<I',data,80)[0]
        for k in range(count):
            t=struct.unpack_from('<12fH',data,84+50*k)
            face=[]
            for vertex in [t[3:6],t[6:9],t[9:12]]:
                if vertex not in vertex_index:vertex_index[vertex]=len(vertices);vertices.append(vertex)
                face.append(vertex_index[vertex])
            faces.append(tuple(face))
        pid={'REF-DESK':'ENV-DESK','REF-BOX':'ENV-BOX'}.get(p['id'],p['id'])
        o=mesh_object(pid,vertices,faces,'03_Exterior_mount_carriers')
        if p['id']=='REF-DESK':MATERIALS['desk']=material('Desk budget',(.19,.095,.045,1),0,.7)
        d=add(o,p['id'],'environment' if p['category']=='environment' else 'structure',
              'desk' if p['id']=='REF-DESK' else ('hardware' if p['category']=='hardware' else 'support'),p['notes'],False,'environment' if p['category']=='environment' else 'structure')
        d.update(category=p['category'],material=p['material'],process=p['process'],
                 manufacturing_step='../load-frame/'+p['step'],prototype_status='工程集成候选；加工图与载荷检查未完成')
    io=json.loads((HERE/'inputs/io-snapshot.json').read_text())
    for p in io['parts']:
        if p['id']=='IO-BRI01_COAX_LEDGE':continue
        dy=0 if p['id'].startswith('IO-X') else -10
        o=mesh_object(p['id'],[(v[0],v[1]+dy,v[2]+4) for v in p['vertices_mm']],p['triangles'],'03_Exterior_mount_carriers')
        add(o,p['id'],'electronics','support' if 'PCB' not in p['id'] else 'armor',
            [f'Full-size owned MCAD; additional Y shift{dy} and Z+4; '+io['source_sha256'],*p.get('notes',[])],False,'electronics')
    # Separate conservative plug/latch reserve. Coax route remains direct cable.
    for name,bounds in [('REF-IO-J2-PLUG',((-15,30,23),(15,70,47.9))),
                        ('REF-REAR-PLUGS',((-56,-80,22),(56,-40,44)))]:
        o=box(name,bounds);o.hide_render=True
        add(o,'插头与释放区 '+name,'routing','support',['Planning envelope; actual cables, latch action and bend radius still need samples'],False,'routing')

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for folder in ('stl','print-parts'):(OUT/folder).mkdir(exist_ok=True)
    source=make_native_loft();master=make_solid_shell(source)
    cover=copy_mesh(master,'B06-301-MAIN-SHIELD')
    boolean(cover,box('Rear service opening',((-67,-80,-10),(67,-21.6,100))),'DIFFERENCE')
    # Sample the actual continuous surface for the lens before cutting the window.
    lens=light_lens(cover);lens.name='B06-306-LIGHT-LENS'
    boolean(cover,rounded_rect_prism('Amber window',((-19,162),(19,168)),(-10,100),2.7),'DIFFERENCE')
    from mathutils.bvhtree import BVHTree
    tree=BVHTree.FromObject(cover,bpy.context.evaluated_depsgraph_get())
    for x,y in MOUNTS:
        hit,_,_,_=tree.ray_cast(Vector((x*M,y*M,.2)),Vector((0,0,-1)))
        if hit is None:raise ValueError('Hidden cover post misses real shield')
        boss(cover,x,y,hit.z/M-1)
    # Lens ears are lower and shifted rearward to clear the steep front apron.
    for x in (-23,23):
        hit,_,_,_=tree.ray_cast(Vector((x*M,163.5*M,.2)),Vector((0,0,-1)))
        z=hit.z/M
        boolean(cover,conformal_post(cover,x,163.5,3.8,z-10,1),'UNION')
        boolean(cover,cylinder('Lens pilot hole',x,163.5,.8,z-11,z-5),'DIFFERENCE')
    boolean(cover,box('RJ45 upper spring clearance',((29,-23,24),(48,-18.4,42.0))),'DIFFERENCE')
    retainer=lamp_retainer(cover,lens)
    boolean(cover,box('Metal chassis rear exit',((-70.8,-80,2),(70.8,-34,18))),'DIFFERENCE')
    add(cover,'前鼻＋双翼＋颈台一体外罩','cover','armor',
        ['3mm nominal wall; four concealed underside M3 captive-nut fixings',
         'Integral ID136 neck, Z74 top; lower swept four-petal shoulders with continuous chine; no cosmetic top screw holes',
         'A11 root snapshot required; old A10 waist is not compatible without redesign'])
    add(lens,'琥珀透光灯窗','cover','lens',['Curved closed optical blank; retained from inside by a separate screw bar; optical PCB pending'])
    add(retainer,'灯窗内藏压条','cover_support','support',['Two M2x6 screws into hidden cover pilot bosses; 0.3mm seat allowance; central pad nominal minimum0.4mm below sampled lens underside; compliant optical shim to be trial-fitted; physical fit coupon required'])
    lid=copy_mesh(master,'B06-304-REAR-LID')
    boolean(lid,box('Rear lid partition',((-66.6,-80,-10),(66.6,-22.4,100))),'INTERSECT')
    boolean(lid,box('Metal chassis rear exit',((-70.8,-80,2),(70.8,-20,18))),'DIFFERENCE')
    # Separate connector apertures replace the large open-bottom cable throat.
    # These are access windows; they do not transfer plug torque to the FR4.
    for name,rect in [('RJ45 latch access',((27,23),(49,44))),
                      ('48V locking plug access',((-52,23),(-25,44)))]:
        boolean(lid,rounded_rect_prism(name,rect,(-80,-20),2,'XZ'),'DIFFERENCE')
    for x in (-10,10):
        o=along_y(cylinder('Coax coupling access',0,0,7.4,-80,-20,n=72),x,35)
        boolean(lid,o,'DIFFERENCE')
    for x,_ in REAR_MOUNTS:
        boolean(lid,rear_bore('Integral rear screw seat',x,5,-40,-31.8),'UNION')
        boolean(lid,box('Flat recessed rear screw landing',((x-5.5,-50,26),(x+5.5,-37.8,38))),'DIFFERENCE')
        boolean(lid,rear_bore('Rear screw clearance',x,1.7,-50,-20),'DIFFERENCE')
        boolean(lid,rear_bore('Recessed button head',x,3.2,-50,-34.5),'DIFFERENCE')
    add(lid,'后向拆卸接口检修盖','rear_lid','rear',['0.8mm partition seam; two rear-facing M3x10; nuts retained in lower carrier',
         'RJ45 22x22 latch window; 48V 27x22 access window; two coax coupling windows diameter14.8',
         'Unplug first, pull rearward before lifting; physical plug/latch fit still needs samples'])
    data=(HERE/'build/load-frame/stl/B06-307-LOWER-CARRIER.stl').read_bytes()
    vertices=[];faces=[];index={}
    for k in range(struct.unpack_from('<I',data,80)[0]):
        t=struct.unpack_from('<12fH',data,84+50*k);face=[]
        for v in [t[3:6],t[6:9],t[9:12]]:
            if v not in index:index[v]=len(vertices);vertices.append(v)
            face.append(index[v])
        faces.append(tuple(face))
    carrier=mesh_object('B06-307-LOWER-CARRIER',vertices,faces)
    carrier['ExactCAD']=True
    add(carrier,'一体底部外罩／接口板安装架','cover_support','support',
        ['Original exact BREP source load_frame.make_carrier; STEP also provided',
         'Polymer scaffold DOES NOT carry arm load; steel deck top Z17',
         'PCB116x56 at Z24; holes x±52,y-20/24; rear fastener axis Z32'])
    for k,(x,y) in enumerate(MOUNTS,1):hardware(k,x,y)
    for k,(x,_) in enumerate(REAR_MOUNTS,1):rear_hardware(k,x)
    for k,(x,y) in enumerate([(x,y) for x in (-52,52) for y in (-20,24)],1):pcb_hardware(k,x,y)
    native_context()
    # Save shape-only and integrated review modes from the same native solids.
    move_collection(master,'90_Construction_native_loft');source.hide_set(True);master.hide_set(True);master.hide_render=True
    refs=[bpy.data.objects[d['id']] for d in DESCRIPTORS if not d.get('print_stl') and d['assembly_role'] in ('structure','electronics','routing','environment')]
    for o in refs:o.hide_render=True
    camera,target=render_setup();SCENE.cycles.samples=20
    SCENE.render.resolution_x=1440;SCENE.render.resolution_y=1080
    point_camera(camera,(.30,.43,.29),target,.32)
    manifest=dict(revision='B06-COMPACT-04',length_unit='mm',module='compact_integration_candidate',
        scope=PARAMETERS['prototype_scope'],parameters=PARAMETERS,parts=DESCRIPTORS,
        review_status='紧凑一体底座 · 无动力试装候选',not_verified=['load chassis and clamp','dynamic collisions','physical fit','PCB signal integrity','thermal','slicing/supports'])
    for name in ('exterior-manifest.json','manifest.json'):(OUT/name).write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    (OUT/'render-meshes.json').write_text(json.dumps(PAYLOAD,separators=(',',':')))
    bpy.data.texts.new('B06 compact parameters.json').write(json.dumps(PARAMETERS,ensure_ascii=False,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ODR-BASE-B06-COMPACT.blend'))
    if '--no-render' not in sys.argv:
        for name,position,scale in [('front-three-quarter',(.30,.43,.29),.32),('top',(0,.075,.85),.32),('rear',(-.30,-.35,.24),.32)]:
            point_camera(camera,position,target,scale);SCENE.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
        for o in refs:o.hide_render=False
        for d in DESCRIPTORS:
            if d['assembly_role'] in ('cover','rear_lid'):bpy.data.objects[d['id']].hide_render=True
        point_camera(camera,(.30,.43,.34),Vector((0,.065,.085)),.34)
        SCENE.render.filepath=str(OUT/'internal-fit.png');bpy.ops.render.render(write_still=True)
        for d in DESCRIPTORS:bpy.data.objects[d['id']].hide_render=d['assembly_role']=='routing'
        point_camera(camera,(.30,.43,.34),Vector((0,.075,.080)),.34)
        SCENE.render.filepath=str(OUT/'root-integrated.png');bpy.ops.render.render(write_still=True)
    print('B06_COMPACT_COMPLETE',flush=True)

if __name__=='__main__':main()
