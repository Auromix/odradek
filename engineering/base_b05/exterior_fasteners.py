# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Exterior screw seats and detachable non-load-bearing carriers.
Executed inside blender_exterior.py's native Blender construction namespace.
Standard hardware meshes are simplified references, never print parts.
"""
from mathutils.bvhtree import BVHTree

COVER_POINTS={
 'B05-301-ARMOR-L':[(-99,8),(-112,67),(-79,125)],
 'B05-301-ARMOR-R':[(99,8),(112,67),(79,125)],
 'B05-302-NOSE':[(-55,151),(55,151),(0,167)],
 'B05-303-REAR-SHOULDER-L':[(-90,-32),(-97,-22)],
 'B05-303-REAR-SHOULDER-R':[(90,-32),(97,-22)],
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


def carriers():
    groups={
      'B05-307-CARRIER-L':('左外罩与环台支架',lambda m:m['x']<0 and m['owner']!='B05-302-NOSE' and m['owner']!='B05-304-REAR-LID',[165,195]),
      'B05-307-CARRIER-R':('右外罩与环台支架',lambda m:m['x']>0 and m['owner']!='B05-302-NOSE' and m['owner']!='B05-304-REAR-LID',[-15,15]),
      'B05-308-NOSE-CARRIER':('前鼻支架',lambda m:m['owner']=='B05-302-NOSE',[65,115]),
      'B05-309-REAR-CARRIER':('独立后盖支架',lambda m:m['owner']=='B05-304-REAR-LID',[-105,-75]),
    }
    out=[]
    for name,(cn,selector,fix_angles) in groups.items():
        selected=[m for m in MOUNTS if selector(m)]
        angles=[math.degrees(math.atan2(m['y']-75,m['x'])) for m in selected]
        if name.endswith('-L'): angles=[a+360 if a<0 else a for a in angles]
        obj=arc_prism(name,82,90,min(angles)-1,max(angles)+1,9,15)
        for m,a in zip(selected,angles):
            p=(m['x'],m['y']);q=(86*math.cos(math.radians(a)),75+86*math.sin(math.radians(a)))
            b=beam_mm('Radial tie',p,q)
            if b: boolean(obj,b,'UNION')
            if m['kind']=='collar':
                tower=cylinder_mm('Independent collar standoff',*p,4.5,9,m['seat_top'])
            else:
                profile=m['seat_profile'];n=len(profile)
                verts=[(x,y,9) for x,y,z in profile]+[tuple(v) for v in profile]+[(m['x'],m['y'],m['seat_top'])]
                faces=[tuple(range(n-1,-1,-1))]+[(i+n,(i+1)%n+n,2*n) for i in range(n)]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
                tower=mesh_object('Surface-matched exterior standoff',verts,faces,'90_Construction_native_loft')
            boolean(obj,tower,'UNION')
        for m in selected: nut_slot(obj,m['x'],m['y'],m['seat_top'])
        for a in fix_angles:
            x,y=86*math.cos(math.radians(a)),75+86*math.sin(math.radians(a))
            # Base fastening pocket: slot floor10.5, ceiling13.3, 1.7 mm roof.
            boolean(obj,nut_channel('Deck captive M3 nut insertion channel',x,y,10.5,13.3),'DIFFERENCE')
            boolean(obj,cylinder_mm('Deck M3 clearance',x,y,1.7,2,17),'DIFFERENCE')
            pa=a+7
            px,py=86*math.cos(math.radians(pa)),75+86*math.sin(math.radians(pa))
            boolean(obj,cylinder_mm('Deck locating pin socket',px,py,1.55,8,11.3),'DIFFERENCE')
            DECK_FIXES.append(dict(owner=name,x=x,y=y,angle=a,pin_xy=[px,py],upward=True,head_floor=1.85,length=10,nut_top=12.9,seat_top=15))
        move_collection(obj,'03_Exterior_mount_carriers');out.append((obj,cn))
    return out


def deck_halves():
    out=[]
    for side in ('L','R'):
        obj=cylinder_mm('B05-310-DECK-'+side,0,75,96,3,9,n=160)
        boolean(obj,cylinder_mm('Central load-chassis reserve',0,75,80,2,10,n=160),'DIFFERENCE')
        bounds=((-120,-30,2),(-.4,180,10)) if side=='L' else ((.4,-30,2),(120,180,10))
        boolean(obj,box('Split exterior locating deck',bounds),'INTERSECT')
        for f in DECK_FIXES:
            if (f['x']<0)!=(side=='L'): continue
            x,y=f['x'],f['y'];px,py=f['pin_xy']
            boolean(obj,cylinder_mm('M3 deck clearance',x,y,1.7,1,12),'DIFFERENCE')
            boolean(obj,cylinder_mm('Underside button head spotface',x,y,3.3,1,3.5),'DIFFERENCE')
            boolean(obj,cylinder_mm('2.8 mm locating pin',px,py,1.4,8.8,11),'UNION')
        move_collection(obj,'03_Exterior_mount_carriers');out.append((obj,'外罩定位底环'+('左' if side=='L' else '右')))
    return out


def mounting_contract():
    return dict(schema='odradek.exterior-mount.v1',length_unit='mm',module_scope='Cosmetic exterior fastening only; this is not the arm load deck',mounts=MOUNTS,deck_fixings=DECK_FIXES,
      nominal=dict(cover_clearance_d=3.4,head_well_d=6.6,cover_head_well_depth=.5,cover_screw='ISO7380-1 M3x10',collar_screw='ISO7380-1 M3x10',nut='DIN934 M3, AF5.5 H2.4',nut_pocket_af=5.8,nut_slot_height=2.8,locating_pin_d=2.8,locating_socket_d=3.1,locating_pin_h=2.0,locating_socket_depth=2.3),
      rear_service=dict(split_y=-14.4,collar_back_y=-10.,nominal_xy_gap=4.4,steps=['Remove only two rear-lid screws','Lift rear lid 2 mm, then withdraw toward -Y','Final flexible cable and actual tool access to be verified']),
      pcb_reservation=dict(x=[-58,58],y=[-40,16],z=[18,34],status='116x56 PCB size reservation only; native EDA components and panel interface not integrated in this module',lid_standoff_inner_abs_x=59.5,nominal_lateral_gap=1.5),
      sources=['https://www.accu.co.uk/socket-button-screws/8288-SSB-M3-35-A4','https://www.accu.co.uk/api/product-datasheet?id=268686'],
      not_verified=['Physical assembly, nut insertion and tool access','Print process compensation and wall minima','Full chassis mounting and joint rotation','Loaded structure','Actual PCB components, coax bend radii and lamp board','Complete collision and tolerance stack'])
