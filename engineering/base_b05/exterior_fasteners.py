# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Exterior screw seats and detachable non-load-bearing carriers.
Executed inside blender_exterior.py's native Blender construction namespace.
Standard hardware meshes are simplified references, never print parts.
"""
from mathutils.bvhtree import BVHTree

COVER_POINTS={
 'B05-301-ARMOR-L':[(-99,-28),(-112,67),(-79,125)],
 'B05-301-ARMOR-R':[(99,-28),(112,67),(79,125)],
 'B05-302-NOSE':[(-55,151),(55,151),(-20,167),(20,167)],
 'B05-304-REAR-LID':[(-66,-28),(66,-28)],
}
COLLAR_POINTS=[(80*math.cos(math.radians(a)),75+80*math.sin(math.radians(a))) for a in (45,135,225,315)]
MOUNTS=[]
COLLAR_BODY={}
DECK_FIXES=[]


def cylinder_mm(name,x,y,r,z0,z1,n=64):
    bpy.ops.mesh.primitive_cylinder_add(vertices=n,radius=r*M,depth=(z1-z0)*M,location=(x*M,y*M,(z0+z1)*.5*M))
    obj=bpy.context.object;obj.name=name
    move_collection(obj,'90_Construction_native_loft')
    return obj


def hex_mm(name,x,y,af,z0,z1):
    radius=af/math.sqrt(3)
    points=[(x+radius*math.cos(math.radians(30+60*i)),y+radius*math.sin(math.radians(30+60*i))) for i in range(6)]
    return contour_prism(name,points,(z0,z1))


def z_on(tree,x,y):
    p,_,_,_=tree.ray_cast(Vector((x*M,y*M,.12)),Vector((0,0,-1)))
    if p is None: raise ValueError(f'Mount ({x},{y}) is outside its actual panel')
    return p.z/M


def z_under(tree,x,y):
    p,_,_,_=tree.ray_cast(Vector((x*M,y*M,-.01)),Vector((0,0,1)))
    if p is None: raise ValueError(f'Underside mount ({x},{y}) is outside its panel')
    return p.z/M


def cover_mounts(obj,mirrored=False):
    if mirrored:
        left=obj.name[:-1]+'L'
        for m in list(MOUNTS):
            if m['owner']==left:
                cp=dict(m);cp['x']=-m['x'];cp['owner']=obj.name
                cp['seat_profile']=[[-x,y,z] for x,y,z in reversed(m['seat_profile'])]
                MOUNTS.append(cp)
        for key,value in list(COLLAR_BODY.items()):
            if key[0]<0: COLLAR_BODY[(-key[0],key[1])]=value
        return
    tree=BVHTree.FromObject(obj,bpy.context.evaluated_depsgraph_get())
    for x,y in COVER_POINTS[obj.name]:
        z=z_on(tree,x,y);seat=z_under(tree,x,y);floor=z-.5
        profile=[]
        for i in range(40):
            a=x+6.5*math.cos(2*math.pi*i/40);b=y+6.5*math.sin(2*math.pi*i/40)
            profile.append([a,b,z_under(tree,a,b)])
        boolean(obj,cylinder_mm('M3 clearance',x,y,1.7,-10,100),'DIFFERENCE')
        boolean(obj,cylinder_mm('Shallow button-head seat',x,y,3.3,floor,100),'DIFFERENCE')
        MOUNTS.append(dict(owner=obj.name,x=x,y=y,head_floor=floor,seat_top=seat,seat_profile=profile,length=10,kind='cover'))
    if obj.name=='B05-301-ARMOR-L':
        for x,y in COLLAR_POINTS:
            if x>=0: continue
            # The ring's independent supports pass through concealed shell
            # apertures: collar tightening does not deform the thin armour.
            boolean(obj,cylinder_mm('Independent collar support clearance',x,y,4.7,-10,100),'DIFFERENCE')
            COLLAR_BODY[(round(x,6),round(y,6))]=57.85


def collar_mounts(obj):
    for x,y in COLLAR_POINTS:
        key=(round(x,6),round(y,6))
        # Mirroring at 6 decimals gives a stable nominal matching datum.
        seat=COLLAR_BODY.get(key)
        if seat is None:
            seat=min(COLLAR_BODY.items(),key=lambda p:(p[0][0]-x)**2+(p[0][1]-y)**2)[1]
        boolean(obj,cylinder_mm('Collar shallow screw well',x,y,3.3,60.5,100),'DIFFERENCE')
        boolean(obj,cylinder_mm('Collar M3 clearance',x,y,1.7,40,100),'DIFFERENCE')
        MOUNTS.append(dict(owner=obj.name,x=x,y=y,head_floor=60.5,seat_top=seat,length=10,kind='collar'))


def arc_prism(name,r0,r1,a0,a1,z0,z1):
    n=max(3,math.ceil(abs(a1-a0)/4))
    aa=[math.radians(a0+(a1-a0)*i/n) for i in range(n+1)]
    contour=[(r1*math.cos(a),75+r1*math.sin(a)) for a in aa]+[(r0*math.cos(a),75+r0*math.sin(a)) for a in reversed(aa)]
    return contour_prism(name,contour,(z0,z1))


def beam_mm(name,p,q,z0=9,z1=15,width=8):
    dx,dy=q[0]-p[0],q[1]-p[1];d=math.hypot(dx,dy)
    if d<.01: return None
    obj=box(name,((-d/2,-width/2,z0),(d/2,width/2,z1)))
    obj.rotation_euler.z=math.atan2(dy,dx);obj.location.x=(p[0]+q[0])*.5*M;obj.location.y=(p[1]+q[1])*.5*M
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return obj


def nut_channel(name,x,y,z0,z1):
    # One continuous cutter avoids coplanar hex/box CSG sliver faces. The
    # lower V and X flats retain the nut while +Y remains an insertion route.
    af=5.8;h=af/math.sqrt(3)
    contour=[(x-af/2,y-h/2),(x,y-h),(x+af/2,y-h/2),
             (x+af/2,y+10),(x-af/2,y+10)]
    return contour_prism(name,contour,(z0,z1))


def nut_slot(obj,x,y,z_top):
    boolean(obj,nut_channel('Captive M3 nut insertion channel',x,y,z_top-5.4,z_top-2.6),'DIFFERENCE')
    boolean(obj,cylinder_mm('M3 through standoff',x,y,1.7,2,z_top+3),'DIFFERENCE')


def hardware_descriptor(obj,name,role='fasteners'):
    finalize_mesh(obj);bevel_and_shade(obj,0)
    key='hardware' if 'SCREW' in obj.name else 'nut'
    obj.data.materials.clear();obj.data.materials.append(MATERIALS[key]);move_collection(obj,'04_Purchased_fasteners_reference')
    obj['Source']='Purchased ISO7380-1 M3 button screw / DIN934 M3 hex nut; threads simplified'
    write_stl(obj,OUT/'stl'/(obj.name+'.stl'))
    return dict(id=obj.name,name=name,category='hardware',quantity=1,material='Purchased steel hardware; reference geometry only',process='Buy standard hardware; do not print',color=list(MATERIALS[key].diffuse_color),color_space='linear',bbox=bounding_box_mm(obj),stl='stl/'+obj.name+'.stl',viewer_group=role,assembly_role=role,prototype_status='标准件尺寸参考；螺纹与强度未建模',notes=['ISO7380-1 M3: head D5.7, H1.65, 2 mm hex; DIN934 M3 nut AF5.5, H2.4','Screw threads are simplified cylinders; not a screw manufacturing model'],explode_mm=[0,0,25 if 'SCREW' in obj.name else -8])


def make_screw(index,m):
    x,y,z,length=m['x'],m['y'],m['head_floor'],m['length']
    head=cylinder_mm(f'STD-SCREW-{index:02d}',x,y,2.85,z,z+1.65)
    bev=head.modifiers.new('Button head visual rounding','BEVEL');bev.width=.45*M;bev.segments=3;apply_modifier(head,bev)
    if m.get('upward'):
        boolean(head,cylinder_mm('Screw shank',x,y,1.5,z+1.55,z+1.65+length),'UNION')
        boolean(head,hex_mm('2 mm Allen socket',x,y,2,z-.1,z+1.1),'DIFFERENCE')
    else:
        boolean(head,cylinder_mm('Screw shank',x,y,1.5,z-length,z+.1),'UNION')
        boolean(head,hex_mm('2 mm Allen socket',x,y,2,z+.55,z+1.8),'DIFFERENCE')
    return head


def make_nut(index,m):
    x,y=m['x'],m['y'];top=m.get('nut_top',m['seat_top']-2.6)
    nut=hex_mm(f'STD-NUT-{index:02d}',x,y,5.5,top-2.4,top)
    boolean(nut,cylinder_mm('Simplified threaded bore reference',x,y,1.55,top-3,top+1),'DIFFERENCE')
    return nut


def shoulder_groove(obj):
    # Cosmetic cut: 0.8 mm width, 0.4 mm depth. This never divides the wing.
    tree=BVHTree.FromObject(obj,bpy.context.evaluated_depsgraph_get())
    profile=[]
    for x in [-76.4-i*.5 for i in range(152)]:
        samples=[]
        for y in (-14.4,-13.6):
            hit,_,_,_=tree.ray_cast(Vector((x*M,y*M,.12)),Vector((0,0,-1)))
            if hit is None: break
            samples.append((x,y,hit.z/M-.4))
        if len(samples)==2: profile.append(samples)
    if len(profile)<2: raise ValueError('Decorative wing groove missed surface')
    n=len(profile);vertices=[p for pair in profile for p in pair]
    vertices += [(x,y,100) for x,y,z in vertices]
    faces=[]
    for i in range(n-1):
        a=2*i; b=a+2
        faces.extend([(a,a+1,b+1,b),(a+2*n,b+2*n,b+1+2*n,a+1+2*n),
                      (a,b,b+2*n,a+2*n),(a+1,a+1+2*n,b+1+2*n,b+1)])
    faces.extend([(0,2*n,2*n+1,1),(2*n-2,2*n-1,4*n-1,4*n-2)])
    boolean(obj,mesh_object('Shallow rear shoulder armor groove',vertices,faces,'90_Construction_native_loft'),'DIFFERENCE')


def integrated_frames():
    out=[]
    for side in ('L','R'):
        name='B05-307-FRAME-'+side
        obj=cylinder_mm(name,0,75,96,3,15,n=160)
        boolean(obj,cylinder_mm('Central future load-chassis reserve',0,75,80,2,16,n=160),'DIFFERENCE')
        bounds=((-120,-30,2),(-.4,180,16)) if side=='L' else ((.4,-30,2),(120,180,16))
        boolean(obj,box('Integrated frame half',bounds),'INTERSECT')
        selected=[m for m in MOUNTS if (m['x']<0)==(side=='L')]
        for m in selected:
            p=(m['x'],m['y']);a=math.atan2(p[1]-75,p[0]);q=(88*math.cos(a),75+88*math.sin(a))
            b=beam_mm('Integral radial tie',p,q,3,15)
            if b: boolean(obj,b,'UNION')
            if m['kind']=='collar':
                tower=cylinder_mm('Integral independent collar post',*p,4.5,3,m['seat_top'])
            else:
                profile=m['seat_profile'];n=len(profile)
                verts=[(x,y,3) for x,y,z in profile]+[tuple(v) for v in profile]+[(m['x'],m['y'],m['seat_top'])]
                faces=[tuple(range(n-1,-1,-1))]+[(i+n,(i+1)%n+n,2*n) for i in range(n)]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
                tower=mesh_object('Integral surface-matched tower',verts,faces,'90_Construction_native_loft')
            boolean(obj,tower,'UNION')
        for m in selected: nut_slot(obj,m['x'],m['y'],m['seat_top'])
        # Two lap joints at the annular frame ends. Their walls locate X/Y;
        # the screw clamps Z. They are printed as part of the two frame halves.
        for y in (-8,159):
            if side=='L':
                boolean(obj,box('Integral locating lap tongue',((-2.5,y-6,3),(9,y+6,11.5))),'UNION')
                nut_slot(obj,5,y,11.5)
            else:
                boolean(obj,box('Integral lap-joint receiver',((.4,y-8,3),(15,y+8,15))),'UNION')
                boolean(obj,box('Lap tongue clearance',((-.5,y-6.3,2),(9.3,y+6.3,11.8))),'DIFFERENCE')
                boolean(obj,cylinder_mm('Frame lap M3 through hole',5,y,1.7,1,20),'DIFFERENCE')
                boolean(obj,cylinder_mm('Frame lap shallow head seat',5,y,3.3,14.5,20),'DIFFERENCE')
                DECK_FIXES.append(dict(owner=name,support_owner='B05-307-FRAME-L',x=5,y=y,kind='frame_lap',head_floor=14.5,seat_top=11.5,length=10))
        move_collection(obj,'03_Exterior_mount_carriers')
        out.append((obj,('左' if side=='L' else '右')+'一体安装骨架'))
    return out


def mounting_contract():
    return dict(schema='odradek.exterior-mount.v2',revision='B05-EXTERIOR-SHAPE-08',length_unit='mm',module_scope='Cosmetic exterior fastening only; this is not the arm load deck',mounts=MOUNTS,deck_fixings=DECK_FIXES,
      nominal=dict(cover_clearance_d=3.4,head_well_d=6.6,cover_head_well_depth=.5,cover_screw='ISO7380-1 M3x10',collar_screw='ISO7380-1 M3x10',nut='DIN934 M3, AF5.5 H2.4',nut_pocket_af=5.8,nut_slot_height=2.8,frame_lap_xy_clearance=.3,frame_lap_z_clearance=.3,frame_lap_tongue_z=[3,11.5],frame_lap_receiver_top_z=15),
      rear_service=dict(split_y=-14.4,collar_back_y=-10.,nominal_xy_gap=4.4,steps=['Remove only two rear-lid screws','Lift rear lid 2 mm, then withdraw toward -Y','Final flexible cable and actual tool access to be verified']),
      pcb_reservation=dict(x=[-58,58],y=[-40,16],z=[18,34],status='116x56 PCB size reservation only; native EDA components and panel interface not integrated in this module',lid_standoff_inner_abs_x=59.5,nominal_lateral_gap=1.5),
      sources=['https://www.accu.co.uk/socket-button-screws/8288-SSB-M3-35-A4','https://www.accu.co.uk/api/product-datasheet?id=268686'],
      not_verified=['Physical assembly, nut insertion and tool access','Print process compensation and wall minima','Full chassis mounting and joint rotation','Loaded structure','Actual PCB components, coax bend radii and lamp board','Complete collision and tolerance stack'])
