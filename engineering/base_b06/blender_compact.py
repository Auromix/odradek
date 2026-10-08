# SPDX-License-Identifier: CC-BY-NC-4.0
"""B06 compact one-piece shield. Run using Blender --background --python.

Own frozen project meshes are integration references, not a completed load path.
"""
from pathlib import Path
import json, math, sys
HERE = Path(__file__).resolve().parent
exec(compile((HERE/'geometry.py').read_text(), str(HERE/'geometry.py'), 'exec'), globals())
MOUNTS = [(-87,36),(87,36),(-72,125),(72,125)]
REAR_MOUNTS = [(-60,-29),(60,-29)]
DESCRIPTORS, PAYLOAD = [], {}

def cylinder(name,x,y,r,z0,z1,n=64):
    bpy.ops.mesh.primitive_cylinder_add(vertices=n, radius=r*M, depth=(z1-z0)*M,
                                      location=(x*M,y*M,(z0+z1)*M/2))
    o=bpy.context.object; o.name=name
    return o

def hexagon(name,x,y,af,z0,z1):
    r=af/math.sqrt(3)
    return contour_prism(name,[(x+r*math.cos(math.pi/6+i*math.pi/3),y+r*math.sin(math.pi/6+i*math.pi/3)) for i in range(6)],(z0,z1))

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

def boss(owner,x,y,top):
    # M3 captive nut is inserted from the interior before lowering the cover.
    from mathutils.bvhtree import BVHTree
    t=BVHTree.FromObject(owner,bpy.context.evaluated_depsgraph_get())
    n=64;upper=[]
    for i in range(n):
        a=i*math.tau/n;px=x+5.6*math.cos(a);py=y+5.6*math.sin(a)
        h,_,_,_=t.ray_cast(Vector((px*M,py*M,.2)),Vector((0,0,-1)))
        if h is None:raise ValueError('Conformal post extends beyond the cover outline')
        upper.append((px,py,h.z/M-.5))
    verts=[(px,py,7.8) for px,py,_ in upper]+upper
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    post=mesh_object('Integral conformal hidden post',verts,faces)
    boolean(owner,post,'UNION')
    boolean(owner,cylinder('M3 clearance',x,y,1.7,7,17),'DIFFERENCE')
    boolean(owner,hexagon('M3 captive nut pocket',x,y,5.8,10,12.8),'DIFFERENCE')
    sign=1 if x>0 else -1
    lo,hi=sorted([x,x+sign*8])
    boolean(owner,box('Side nut insertion',((lo,y-2.9,10),(hi,y+2.9,12.8))),'DIFFERENCE')

def hardware(index,x,y,zseat=7):
    s=cylinder('HW-M3-'+str(index),x,y,1.5,zseat,zseat+10)
    boolean(s,cylinder('Purchased button head',x,y,2.85,zseat-1.65,zseat+.1),'UNION')
    boolean(s,hexagon('2mm hex socket',x,y,2,zseat-1.65,zseat-.6),'DIFFERENCE')
    add(s,'M3×10 底部固定螺钉','fasteners','hardware',['Nominal standard hardware; simplified threads; buy, do not print'],False,'fasteners')
    nut=hexagon('HW-NUT-'+str(index),x,y,5.5,10,12.4)
    boolean(nut,cylinder('Nominal nut thread',x,y,1.5,9,14),'DIFFERENCE')
    add(nut,'M3 内藏螺母','fasteners','nut',['DIN934 nominal dimensions; thread omitted'],False,'fasteners')

def lamp_retainer(surface,lens):
    from mathutils.bvhtree import BVHTree
    tree=BVHTree.FromObject(surface,bpy.context.evaluated_depsgraph_get())
    hit,_,_,_=tree.ray_cast(Vector((23*M,169.5*M,.2)),Vector((0,0,-1)))
    z=hit.z/M
    bar=box('B06-308-LENS-RETAINER',((-27,168,z-10.3),(27,171,z-8.3)))
    lt=BVHTree.FromObject(lens,bpy.context.evaluated_depsgraph_get())
    low,_,_,_=lt.ray_cast(Vector((0,169.5*M,0)),Vector((0,0,1)))
    boolean(bar,cylinder('Lens central support pad',0,169.5,1.35,z-9,low.z/M-.4),'UNION')
    for x in (-23,23):boolean(bar,cylinder('M2 clamp-bar hole',x,169.5,1.2,z-12,z-3),'DIFFERENCE')
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
    # Existing mating flange space stays Ø160; it is not reduced with the skin.
    flange=cylinder('REF-LOAD-FLANGE',0,75,80,46,58)
    boolean(flange,cylinder('Central harness opening reserve',0,75,28,45,59),'DIFFERENCE')
    for k in range(8):
        a=math.radians(22.5+45*k);x,y=60*math.cos(a),75+60*math.sin(a)
        boolean(flange,cylinder('M6 tapped-hole nominal',x,y,2.5,45,59),'DIFFERENCE')
    add(flange,'Ø160 / PCD120八M6承载接口空间','structure','collar',
        ['Mating-plane Z58. Thread minor bore is nominal; no manufacturing drawing or support chassis released.'],False,'structure')
    io=json.loads((HERE/'inputs/io-snapshot.json').read_text())
    for p in io['parts']:
        o=mesh_object(p['id'],p['vertices_mm'],p['triangles'],'03_Exterior_mount_carriers')
        add(o,p['id'],'electronics','support' if 'PCB' not in p['id'] else 'armor',
            ['Full-size owned MCAD from B05 frame, Y-36; '+io['source_sha256'],*p.get('notes',[])],False,'electronics')
    # Separate conservative plug/latch reserve. Coax route remains direct cable.
    for name,bounds in [('REF-IO-J2-PLUG',((-15,40,19),(15,80,43.9))),
                        ('REF-REAR-PLUGS',((-56,-70,18),(56,-30,40)))]:
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
    boolean(cover,rounded_rect_prism('Amber window',((-19,168),(19,174)),(-10,100),2.7),'DIFFERENCE')
    from mathutils.bvhtree import BVHTree
    tree=BVHTree.FromObject(cover,bpy.context.evaluated_depsgraph_get())
    for x,y in MOUNTS:
        hit,_,_,_=tree.ray_cast(Vector((x*M,y*M,.2)),Vector((0,0,-1)))
        if hit is None:raise ValueError('Hidden cover post misses real shield')
        boss(cover,x,y,hit.z/M-1)
    # Lens ears are lower and shifted rearward to clear the steep front apron.
    for x in (-23,23):
        hit,_,_,_=tree.ray_cast(Vector((x*M,169.5*M,.2)),Vector((0,0,-1)))
        z=hit.z/M
        boolean(cover,cylinder('Lens M2 mounting boss',x,169.5,3.8,z-8,z-1),'UNION')
        boolean(cover,cylinder('Lens pilot hole',x,169.5,.8,z-9,z-4),'DIFFERENCE')
    retainer=lamp_retainer(cover,lens)
    add(cover,'前鼻＋双翼＋颈台一体外罩','cover','armor',
        ['3mm nominal wall; four concealed underside M3 captive-nut fixings',
         'Integral ID136 neck, Z74 top; continuous shoulder chine; no cosmetic top screw holes',
         'A11 root snapshot required; old A10 waist is not compatible without redesign'])
    add(lens,'琥珀透光灯窗','cover','lens',['Curved closed optical blank; retained from inside by a separate screw bar; optical PCB pending'])
    add(retainer,'灯窗内藏压条','cover_support','support',['Two M2x6 screws into hidden cover pilot bosses; 0.3mm seat allowance; central pad nominal0.4mm below lens; compliant optical shim to be trial-fitted; physical fit coupon required'])
    lid=copy_mesh(master,'B06-304-REAR-LID')
    boolean(lid,box('Rear lid partition',((-66.6,-80,-10),(66.6,-22.4,100))),'INTERSECT')
    boolean(lid,rounded_rect_prism('Cable egress',((-54,-8),(54,18)),(-80,-25),4,'XZ'),'DIFFERENCE')
    tree=BVHTree.FromObject(lid,bpy.context.evaluated_depsgraph_get())
    for x,y in REAR_MOUNTS:
        hit,_,_,_=tree.ray_cast(Vector((x*M,y*M,.2)),Vector((0,0,-1)))
        if hit is None:raise ValueError('Rear post misses lid')
        boss(lid,x,y,hit.z/M-1)
    add(lid,'独立后部检修盖','rear_lid','rear',['0.8mm partition seam; two bottom M3 fixings; bottom cable throat 108x18mm',
         'Lift after unplugging cables; paired full-size I/O remains under main cover'])
    carrier=cylinder('B06-307-LOWER-CARRIER',0,75,84,3,7)
    boolean(carrier,cylinder('Load chassis reservation',0,75,78,2,8),'DIFFERENCE')
    boolean(carrier,box('PCB mounting shelf',((-63,-20,3),(63,40,7))),'UNION')
    for x,y in MOUNTS+REAR_MOUNTS:
        r=math.hypot(x,y-75);q=(x*81/r,75+(y-75)*81/r)
        boolean(carrier,beam('Underside fixing bridge',(x,y),q),'UNION')
        boolean(carrier,cylinder('Bottom fastener clearance',x,y,1.7,2,8),'DIFFERENCE')
    for x in (-52,52):
        for y in (-10,34):
            boolean(carrier,cylinder('Full-size PCB standoff',x,y,3.2,6,20),'UNION')
            boolean(carrier,cylinder('PCB M3 pilot',x,y,1.25,12,21),'DIFFERENCE')
    add(carrier,'一体底部外罩／接口板安装架','cover_support','support',
        ['Ø156 centre clearance for future chassis; DOES NOT carry arm load',
         'PCB 116x56 retained; four board holes x±52,y-10/34 at Z20; M3 pilot holes',
         'Main hidden posts start Z7.8; carrier top Z7; nominal Z gap0.8'])
    for k,(x,y) in enumerate(MOUNTS+REAR_MOUNTS,1):hardware(k,x,y)
    native_context()
    # Save shape-only and integrated review modes from the same native solids.
    move_collection(master,'90_Construction_native_loft');source.hide_set(True);master.hide_set(True);master.hide_render=True
    refs=[bpy.data.objects[d['id']] for d in DESCRIPTORS if not d.get('print_stl') and d['assembly_role'] in ('structure','electronics','routing')]
    for o in refs:o.hide_render=True
    camera,target=render_setup();SCENE.cycles.samples=20
    SCENE.render.resolution_x=1440;SCENE.render.resolution_y=1080
    point_camera(camera,(.30,.43,.29),target,.32)
    manifest=dict(revision='B06-COMPACT-01',length_unit='mm',module='compact_integration_candidate',
        scope=PARAMETERS['prototype_scope'],parameters=PARAMETERS,parts=DESCRIPTORS,
        review_status='紧凑一体底座 · 无动力试装候选',not_verified=['load chassis and clamp','dynamic collisions','physical fit','PCB routing','thermal','slicing/supports'])
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
