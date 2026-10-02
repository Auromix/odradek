# SPDX-License-Identifier: CC-BY-NC-4.0
"""Original printable arm fit prototype; dimensional CAD -> editable Blender.
All dimensions mm. Supplier interfaces must be gauged before powered assembly.
"""
from pathlib import Path
import json,math,csv
import cadquery as cq
import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'engineering/arm_a08/build'
L=json.loads((ROOT/'engineering/parameters/arm-a05-layout.json').read_text())
SRC=json.loads((ROOT/'docs/engineering/sources/arm-a05-mechanical-sources.json').read_text())['models']
PARTS=[];SHAPES={};DENSITY=1.15e-6

def V(v):return cq.Vector(*map(float,v))
def unit(v):
    v=np.array(v,float);return v/np.linalg.norm(v)
def plane(p,n):
    n=unit(n);u=np.array([1.,0,0]) if abs(n[0])<.9 else np.array([0.,1,0])
    u=unit(u-n*np.dot(n,u));return cq.Plane(origin=V(p),xDir=V(u),normal=V(n))
def cyl(p,n,r,h):return cq.Solid.makeCylinder(r,h,V(p),V(n))
def ring(p,n,ro,ri,h):return cq.Workplane(plane(p,n)).circle(ro).circle(ri).extrude(h).val()
def ball(p,r):return cq.Solid.makeSphere(r,V(p),angleDegrees1=-90,angleDegrees2=90)
def beam(a,b,r=7.5):
    a,b=np.array(a),np.array(b);v=b-a
    if np.linalg.norm(v)<1e-8:return ball(a,r)
    # Eight broad faces echo the shield base and petal bevels.
    return cyl(a,unit(v),r,float(np.linalg.norm(v))).fuse(ball(a,r),ball(b,r)).fix().clean()
def rect_beam(a,b,r=7.5):
    a,b=np.array(a),np.array(b);size=abs(b-a)+2*r
    return cq.Solid.makeBox(*map(float,size),V(np.minimum(a,b)-r))
def fuse(ss):
    s=ss[0]
    for t in ss[1:]:s=s.fuse(t,tol=1e-5).fix().clean()
    if not s.isValid():raise RuntimeError('Invalid union before machining')
    return s
def drill(s,p,n,d,h):
    result=s.cut(cyl(p,n,d/2,h),tol=1e-5)
    if not result.isValid():result=result.fix()
    return result
def local_frame(i):return 'world' if i==0 else f'J{i}.rotor'
def info(j):
    m=SRC[j['model']];a=np.array(j['axis'],float);sign=-1 if j['id'] in ['J2','J5','J6'] else 1
    n=a*sign;low,high=m['interface_frame']['step_axial_bounds_interface_mm'];d=-(low+high)/2
    out=np.array(j['motor_center'],float)+n*d
    proj=m['interface_frame']['output_to_housing_front_mm'];fixed=out-n*proj
    pl=plane(out,n);u=np.array(pl.xDir.toTuple());v=np.array(pl.yDir.toTuple())
    pilot={'RS03':35,'RS04':35,'RS06':26,'RS00':17.5}[j['model']]
    fixed_th=11 if j['model']=='RS04' else 8
    outer=j['diameter_mm']/2+7
    if j['id']=='J7':outer=42
    return dict(j=j,m=m,n=n,out=out,fixed=fixed,u=u,v=v,pilot=pilot,outer=outer,th=fixed_th,depth=-low)
I=[info(j) for j in L['joints']]

def xy_holes(inf,kind):
    flip=inf['m']['interface_frame']['T_raw_from_interface_mm'][1][1]
    return [inf['u']*x+inf['v']*y*flip for x,y in inf['m'][kind]['raw_step_xy_mm']]
def holder(inf):
    s=ring(inf['fixed'],inf['n'],inf['outer'],inf['pilot']+1.2,inf['th'])
    d=4.5 if inf['j']['model'] in ['RS03','RS04'] else 3.5
    for v in xy_holes(inf,'fixed_front_fasteners'):
        s=drill(s,inf['fixed']+v-inf['n'],inf['n'],d,inf['th']+2)
    return s
def output(inf):
    s=cyl(inf['out'],inf['n'],inf['pilot'],10)
    d=5.5 if inf['j']['model']=='RS04' else 4.5
    for v in xy_holes(inf,'output_fasteners'):
        s=drill(s,inf['out']+v-inf['n'],inf['n'],d,12)
    if inf['j']['model']=='RS04':
        for px,py in [(-12.67842,12.67842),(17.31905,4.64063),(-4.64063,-17.31905)]:
            s=drill(s,inf['out']+inf['u']*px+inf['v']*py-.1*inf['n'],inf['n'],6.5,3.6)
    return s
def housing_keepout(inf,offset,clearance=0):
    # Main body excludes protruding output pilot and RS04 locating pins.
    p=inf['out']-inf['n']*inf['depth']+offset
    return cyl(p,inf['n'],inf['j']['diameter_mm']/2+clearance,inf['depth']-inf['m']['interface_frame']['output_to_housing_front_mm'])

def add(id,s,owner,role='printed_structure',material='PA12 fit prototype',note='',frame=None,mass=None):
    PARTS[:]=[p for p in PARTS if p['id']!=id]
    cleaned=s.clean()
    if cleaned.isValid():s=cleaned
    solids=s.Solids()
    if not s.isValid():raise RuntimeError(f'{id}: invalid BREP')
    vol=sum(t.Volume() for t in solids);com=s.Center();bb=s.BoundingBox()
    verts,tris=s.tessellate(.15,.18)
    mesh=trimesh.Trimesh(vertices=[v.toTuple() for v in verts],faces=tris,process=True)
    mesh.merge_vertices(digits_vertex=4)
    mesh.update_faces(mesh.nondegenerate_faces())
    if not mesh.is_watertight:raise RuntimeError(f'{id}: non-watertight exported mesh')
    mesh.remove_unreferenced_vertices()
    (OUT/'stl').mkdir(parents=True,exist_ok=True);(OUT/'step').mkdir(exist_ok=True)
    if role.startswith('printed') or role=='fit_coupon':
        mesh.export(OUT/'stl'/f'{id}.stl')
    cq.exporters.export(s,str(OUT/'step'/f'{id}.step'))
    rho=1.27e-6 if role=='printed_cover' else DENSITY
    actual_mass=mass if mass is not None else vol*rho
    inertia=mesh.moment_inertia*(actual_mass/mesh.volume) # homogeneous proxy, correct assigned mass
    entry=dict(id=id,owner=owner,frame=frame or local_frame(owner),role=role,material=material,note=note,solid_count=len(solids),volume_mm3=vol,mass_kg=actual_mass,density_assumption_kg_mm3=actual_mass/vol,com_mm=list(com.toTuple()),bbox_size_mm=[bb.xlen,bb.ylen,bb.zlen],watertight=True,inertia_kg_mm2=inertia.tolist(),vertices_mm=mesh.vertices.tolist(),triangles=mesh.faces.tolist())
    PARTS.append(entry);SHAPES[id]=s
    print(id,len(solids),round(entry['mass_kg'],4),[round(x,1) for x in entry['bbox_size_mm']],flush=True)
    return entry

def bone(owner,paths):
    previous=I[owner-1];nxt=I[owner];offset=np.array(nxt['j']['offset'],float)
    ss=[output(previous),holder(nxt).translate(V(offset))]
    for path in paths:
        ss.extend((rect_beam if owner==5 else beam)(a,b) for a,b in zip(path,path[1:]))
    s=fuse(ss)
    # Cut only the adjacent stator envelopes, preserving contact planes.
    for inf,off in [(previous,np.zeros(3)),(nxt,offset)]:
        s=s.cut(housing_keepout(inf,off,6),tol=1e-5).fix().clean()
        s=s.cut(cyl(inf['out']+off-inf['n']*inf['m']['interface_frame']['output_to_housing_front_mm'],inf['n'],inf['pilot'],inf['m']['interface_frame']['output_to_housing_front_mm']),tol=1e-5).fix().clean()
    # Clear straight hex-key approach above output screws (cover installed last).
    for v in xy_holes(previous,'output_fasteners'):
        s=drill(s,previous['out']+v+previous['n']*10,previous['n'],9 if previous['j']['model']=='RS04' else 8,32)
    add(f'B{owner}-core',s,owner,note='Original two-rail rigid link with catalogue bolt patterns; printed fit prototype, load qualification pending.')

def screw(id,p,n,d,length,plate,washer,owner,frame=None,motor=None,button=False):
    n=np.array(n,float);p=np.array(p,float);head={3:(5.5,3),4:(7,4),5:(8.5,5),8:(13,8)}[d]
    if button:head=(5.7,1.65)
    shank=cyl(p+n*(plate+washer-length),n,d/2,length)
    cap=cyl(p+n*(plate+washer),n,head[0]/2,head[1])
    s=shank.fuse(cap).clean()
    e=add(id,s,owner,'hardware',material=f'steel ISO4762 M{d}x{length}',frame=frame,mass=s.Volume()*7.85e-6,note=f'Nominal shank/head envelope; thread helix omitted. Washer thickness {washer}mm required; nominal engagement {length-plate-washer:.2f}mm.')
    e['washer_thickness_mm']=washer;e['plate_thickness_mm']=plate;e['thread_engagement_mm']=length-plate-washer
    e['machining']={'p':p.tolist(),'n':n.tolist(),'d':d,'length':length,'plate':plate,'washer':washer,'head':head}
    if button:e['material']='steel ISO7380-1 M3x12 button head, D5.7 H1.65'
    if motor:e['intentional_thread_motor']=motor
    # Purchased washer is a separate solid; its mass is included independently.
    w=ring(p+n*plate,n,{3:3.5,4:4.5,5:4.5,8:8}[d],d/2+.2,washer)
    add(id+'-washer',w,owner,'hardware',material='steel flat washer',frame=frame,mass=w.Volume()*7.85e-6,note='Flat washer envelope; verify delivered thickness.')

def nut(id,p,n,d,owner,frame=None,back_washer=True):
    af,h={3:(5.5,2.4),4:(7,3.2),5:(8,4)}[d]
    s=cq.Workplane(plane(p,n)).polygon(6,af/math.cos(math.pi/6)).extrude(h).val();s=drill(s,np.array(p)-np.array(n),n,d, h+2)
    e=add(id,s,owner,'hardware',material=f'steel M{d} hex nut',frame=frame,mass=s.Volume()*7.85e-6,note='Nominal hex nut; major-diameter thread void envelope.')
    e['nut_machining']={'p':list(p),'n':list(n),'af':af,'height':h}
    if back_washer:
        th=1 if d==5 else .5
        w=ring(np.array(p)+np.array(n)*h,n,5 if d==5 else 3.5,d/2+.2,th)
        add(id+'-washer',w,owner,'hardware',material='steel rear flat washer',frame=frame,mass=w.Volume()*7.85e-6)
    return e

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    # B0 mounts to B04 eight M8 taps, PCD120 phase22.5 degrees.
    z=90;fixed=I[0]['fixed']+[0,0,z]
    root=ring([0,0,23.4],[0,0,1],80,30,8)
    ss=[root,holder(I[0]).translate((0,0,z))]
    for x in [-50,50]:
        for y in [-50,50]:
            ss.append(beam([x,y,29],[x,y,float(fixed[2]+4)],7))
            ss.append(beam([x,y,float(fixed[2]+4)],[x*.8,y*.8,float(fixed[2]+4)],7))
    s=fuse(ss).cut(housing_keepout(I[0],np.array([0,0,z]),6))
    for k in range(8):
        a=math.radians(22.5+45*k);s=drill(s,[60*math.cos(a),60*math.sin(a),22.4],[0,0,1],8.8,10)
    add('B0-root-adapter',s,0,note='B04-P2 interface: D160, PCD120 eight M8 clearance holes; align by +90deg around desk Z and +34.6mm vertical translation.')
    # Paths are in the previous joint rotor frame; endpoints on real interface planes.
    a=I[1]['fixed'][1]-I[1]['th']/2
    b=I[2]['fixed'][0]+4
    c=I[3]['fixed'][1]+4
    d=90+I[4]['fixed'][1]-4
    e=I[4]['out'][1]-5;f=I[5]['fixed'][2]-4
    g=I[5]['out'][2]-5;h=65+I[6]['fixed'][0]+4
    paths={
      1:[[[ -20,t,5],[-77,t,35],[-77,a,85+t],[-57,a,85+t]] for t in [-18,18]],
      2:[[[20,a,t],[74,a,t],[74,73,t],[100+b,73,t],[100+b,48,t]] for t in [-18,18]],
      3:[[[I[2]['out'][0]+5,20,t],[86,65,t],[102,65,t],[102,c,t]] for t in [-18,18]],
      4:[[[0,I[3]['out'][1]+5,t],[0,90,t],[130,90,t],[135,d,t]] for t in [-18,18]],
      5:[[[t,e,0],[55+t,42,0],[55+t,42,f],[55+t,34,f]] for t in [-18,18]],
      6:[[[0,t,g],[50,t,g],[h,18 if t>0 else -18,38],[h,18 if t>0 else -18,20]] for t in [-14,14]],
    }
    # Leave the stationary flange axially before going radially outward.
    # Otherwise a swept rotor rail intersects its own stator carrier.
    for owner,pp in paths.items():
        n=I[owner-1]['n']
        for path in pp:
            first=np.array(path[0]);exit_point=first+n*20
            path.insert(1,exit_point.tolist())
            if owner==2:path[2][1]=float(exit_point[1])
            if owner==5:
                t=path[0][0]
                path[:]=[[t,e,0],[t,e-20,0],[55+t,e-20,0],[55+t,32,0],[55+t,32,f]]
            if owner==6:path[2][2]=float(exit_point[2])
            path[:]=[p for k,p in enumerate(path) if k==0 or np.linalg.norm(np.array(p)-np.array(path[k-1]))>1e-6]
    for owner in range(1,7):bone(owner,paths[owner])
    # J7 output journal + flange; external 6807 pair has 11mm centre spacing.
    j=I[6];x=float(j['out'][0]);shaft=cyl([x,0,0],[1,0,0],17.475,32)
    shaft=shaft.fuse(cyl([x+8.5,0,0],[1,0,0],18.5,2),cyl([x+32,0,0],[1,0,0],30,8)).clean()
    for v in xy_holes(j,'output_fasteners'):
        shaft=drill(shaft,j['out']+v-[1,0,0],[1,0,0],3.5,42)
        shaft=drill(shaft,j['out']+v+[35.5,0,0],[1,0,0],7.6,5)
    for k in range(3):
        a=math.radians(30+120*k);p=[x+31.9,22.5*math.cos(a),22.5*math.sin(a)]
        shaft=drill(shaft,p,[1,0,0],4.5,8.2)
        shaft=shaft.cut(cq.Workplane(plane(p,[1,0,0])).polygon(6,8.3).extrude(3.5).val())
    add('B7-output-flange',shaft,7,note='D60 project flange, 3 M4 on PCD45 with rear nut traps; 6 recessed M3 motor bolts. Journal must be fit-tested; printed journal is not a precision metal shaft.')
    # Stator bearing cartridge slides onto B6 after motor screw installation.
    start=x+7.6
    cage=ring([start,0,0],[1,0,0],42,23.6,20.9)
    cage=cage.fuse(ring([x+17.5,0,0],[1,0,0],23.6,22.4,4))
    # Six through bolts join cartridge to B6 flange; M3 nuts are fitted from rear.
    for k in range(6):
        a=math.radians(30+60*k);y,z=35*math.cos(a),35*math.sin(a)
        cage=drill(cage,[start-1,y,z],[1,0,0],3.5,23)
        core=SHAPES['B6-core'];p=[float(j['fixed'][0]+65)-.1,y,z]
        core=drill(core,p,[1,0,0],3.5,10)
        core=core.cut(cq.Workplane(plane(p,[1,0,0])).polygon(6,6.8).extrude(3).val())
        SHAPES['B6-core']=core
    # Re-export revised B6 (not an extra physical part).
    SHAPES['B6-core']=SHAPES['B6-core'].cut(cq.Solid.makeBox(100,200,200,V([65+start,-100,-100])))
    old=next(p for p in PARTS if p['id']=='B6-core');PARTS.remove(old)
    add('B6-core',SHAPES['B6-core'],6,note=old['note'])
    add('J7-bearing-cage',cage,6,frame='J7.fixed',note='47.2mm prototype seat; 6807 outer rings supported by 44.8mm shoulders; gauge fit and axial stack before load test.')
    retain=ring([x+28.5,0,0],[1,0,0],42,22.4,2.5)
    for k in range(6):
        a=math.radians(30+60*k);retain=drill(retain,[x+28.4,35*math.cos(a),35*math.sin(a)],[1,0,0],3.5,3)
    add('J7-bearing-retainer',retain,6,frame='J7.fixed',note='Bolted outer-ring front retainer; 1mm nominal clearance to rotating flange.')
    spacer=ring([x+28.5,0,0],[1,0,0],18.5,17.55,3.5)
    add('J7-inner-spacer',spacer,7,note='Axial inner-ring spacer; shim to avoid binding; do not preload by deforming printed cage.')
    for index,pos in enumerate([x+14,x+25],1):
        add(f'J7-6807-{index}',ring([pos-3.5,0,0],[1,0,0],23.5,17.5,7),6,'hardware',material='NSK 6807 purchased steel bearing',frame='J7.fixed',mass=.027,note='Original envelope, not supplier internal CAD; 35x47x7mm, C0r4100N; mounted mass assigned stator for gravity bookkeeping.')
    # Reference motor shapes: original analytic envelopes, never print these.
    for i,j in enumerate(L['joints']):
        inf=I[i];s=housing_keepout(inf,np.zeros(3))
        s=s.fuse(cyl(inf['out']-inf['n']*inf['m']['interface_frame']['output_to_housing_front_mm'],inf['n'],inf['pilot'],inf['m']['interface_frame']['output_to_housing_front_mm']))
        add(j['id']+'-motor-envelope',s,i,'motor_envelope',material='purchased '+j['model'],frame=j['id']+'.fixed',mass=j['mass_kg'],note='Envelope only; purchased actuator; connector pigtail gauge pending.')
    # Two removable shield panels; broad facets, soft corners, amber inserts.
    for owner,poly,points in [
        (3,[(40,33),(55,28),(98,56),(105,66),(92,75),(48,44)],[(60,42.8),(95,65)]),
        (4,[(20,70),(120,70),(140,90),(122,110),(20,110),(10,90)],[(40,90),(125,90)])]:
        s=SHAPES[f'B{owner}-core']
        panel_z=34 if owner==4 else 32
        panel=cq.Workplane('XY').workplane(offset=panel_z).polyline(poly).close().extrude(2.4).val()
        for px,py in points:
            s=s.fuse(cyl([px,py,10],[0,0,1],4,panel_z-10)).fix().clean()
            s=drill(s,[px,py,8],[0,0,1],3.5,32)
            panel=drill(panel,[px,py,panel_z-1],[0,0,1],3.5,5)
        add(f'B{owner}-core',s,owner,note='Twin-rail printed core with through-bolted removable shield; PA12 material qualification pending.')
        add(f'B{owner}-shield',panel,owner,'printed_cover',material='grey PETG cosmetic panel',note=f'2.4mm removable panel; two M3x{35 if owner==4 else 30} screws, washers and nuts; non-load-bearing.')
    # B4 exceeds a 256mm bed; a two-rail staggered splice uses metal spacers.
    s=SHAPES['B4-core']
    for px in [90,110]:
        for z0 in [-26,10]:
            pad=cq.Solid.makeBox(18,18,16,V([px-9,81,z0]));s=s.fuse(pad).fix().clean()
        s=drill(s,[px,90,-27],[0,0,1],5.5,54)
    left=s.intersect(cq.Solid.makeBox(500,500,500,V([-385,-250,-250])))
    left=left.cut(cq.Solid.makeBox(100,500,250,V([85,-250,0])))
    right=s.intersect(cq.Solid.makeBox(500,500,500,V([85,-250,-250])))
    right=right.cut(cq.Solid.makeBox(30,500,250,V([85,-250,-250])))
    PARTS[:]=[p for p in PARTS if p['id']!='B4-core']
    for ext in ['stl','step']:(OUT/ext/f'B4-core.{ext}').unlink(missing_ok=True)
    add('B4-proximal',left,4,note='Staggered 30mm splice; M5x60 bolts and 20mm steel spacers; do not use polymer spacers for a load test.')
    add('B4-distal',right,4,note='Upper/lower rails mate without interference; ream splice clearance holes to5.5mm after printing.')
    for index,px in enumerate([90,110],1):
        add(f'B4-spacer-{index}',ring([px,90,-10],[0,0,1],4,2.6,20),4,'hardware',material='steel OD8 ID5.2 length20 spacer',mass=.0045,note='Purchased or cut/deburred metal tube; actual length calibrated to printed inner faces.')
        screw(f'B4-splice-M5-{index}',[px,90,-26],[0,0,1],5,60,52,1,4)
        nut(f'B4-splice-nut-{index}',[px,90,-31],[0,0,1],5,4)
    # Split clamshell motor shrouds with 0.5mm joint gap and open rear.
    # The conservative motor envelope needs a replaceable TPU/foam liner at fit.
    for index,inf in enumerate(I):
        radius=inf['j']['diameter_mm']/2
        rear=8.5 if index==0 else 4
        front=4 if index==6 else 1
        org=inf['out']-inf['n']*(inf['depth']-rear)
        length=inf['depth']-inf['m']['interface_frame']['output_to_housing_front_mm']-rear-front
        pl=plane(org,inf['n'])
        band=cq.Workplane(pl).polygon(12,2*(radius+3)/math.cos(math.pi/12)).circle(radius+.6).extrude(length).val()
        for sign in [-1,1]:
            tab=cq.Workplane(pl).center(0,sign*(radius+5)).rect(16,12).extrude(8).val()
            tab=tab.cut(cyl(org-inf['n'],inf['n'],radius+.6,10),tol=1e-5).fix()
            band=band.fuse(tab).fix().clean()
        for sign in [-1,1]:
            hole=org+inf['v']*sign*(radius+7)+inf['n']*4-inf['u']*10
            band=drill(band,hole,inf['u'],3.5,20)
        for side,x0 in [('A',.25),('B',-200)]:
            width=200 if side=='A' else 199.75
            box=cq.Workplane(pl).center(x0+width/2,0).rect(width,400).extrude(length+1).val()
            half=band.intersect(box).clean()
            add(f'{inf["j"]["id"]}-shroud-{side}',half,index,'printed_cover',material='grey PETG cosmetic shroud',frame=inf['j']['id']+'.fixed',note='Split rear-open cosmetic cover; two M3x25 clamp bolts with nuts. Thermal test required with cover fitted; liner fitted to delivered motor.')
    # All actuator flange screws follow the drawing pattern; stator and rotor masses belong to different bodies.
    for index,inf in enumerate(I):
        j=inf['j'];model=j['model'];mid=j['id']+'-motor-envelope'
        fd=4 if model in ['RS03','RS04'] else 3;fl=12 if model=='RS00' else 16;fw=.8 if fd==4 else .5
        for k,v in enumerate(xy_holes(inf,'fixed_front_fasteners'),1):screw(f'{j["id"]}-fixed-bolt-{k}',inf['fixed']+v,inf['n'],fd,fl,inf['th'],fw,index,j['id']+'.fixed',mid,button=j['id']=='J7')
        od=5 if model=='RS04' else 3 if model=='RS00' else 4;ol=40 if model=='RS00' else 16;ow=1 if od in [3,5] else .8;op=35.5 if model=='RS00' else 10
        for k,v in enumerate(xy_holes(inf,'output_fasteners'),1):screw(f'{j["id"]}-output-bolt-{k}',inf['out']+v,inf['n'],od,ol,op,ow,index+1,j['id']+'.rotor',mid)
        org=inf['out']-inf['n']*(inf['depth']-(8.5 if index==0 else 4))
        for k,sign in enumerate([-1,1],1):
            p=org+inf['v']*sign*(j['diameter_mm']/2+7)+inf['n']*4-inf['u']*8
            screw(f'{j["id"]}-cover-bolt-{k}',p,inf['u'],3,25,16,.5,index,j['id']+'.fixed')
            nut(f'{j["id"]}-cover-nut-{k}',p-inf['u']*2.9,inf['u'],3,index,j['id']+'.fixed')
    for k in range(8):
        a=math.radians(22.5+45*k);screw(f'B0-base-M8-{k+1}',[60*math.cos(a),60*math.sin(a),23.4],[0,0,1],8,20,8,1.6,0)
    for owner,points,pz,ln in [(3,[(60,42.8),(95,65)],32,30),(4,[(40,90),(125,90)],34,35)]:
        for k,(px,py) in enumerate(points,1):
            screw(f'B{owner}-panel-bolt-{k}',[px,py,10],[0,0,1],3,ln,pz+2.4-10,.5,owner)
            nut(f'B{owner}-panel-nut-{k}',[px,py,7.1],[0,0,1],3,owner)
    for k in range(6):
        a=math.radians(30+60*k);p=[x-.4,35*math.cos(a),35*math.sin(a)]
        screw(f'J7-cage-M3-{k+1}',p,[1,0,0],3,40,31.4,.5,6,'J7.fixed')
        nut(f'J7-cage-nut-{k+1}',np.array(p)-[2.9,0,0],[1,0,0],3,6,'J7.fixed')
    for k in range(3):
        a=math.radians(30+120*k);nut(f'J7-tool-nut-{k+1}',[x+32,22.5*math.cos(a),22.5*math.sin(a)],[1,0,0],4,7,back_washer=False)
    # Drill after all rail unions: a fused rail must never refill a bolt hole.
    # Only corresponding rigid-body bolts are used, never arbitrary moving poses.
    for part in list(PARTS):
        if part['role']!='printed_structure':continue
        owner=part['owner'];s=SHAPES[part['id']]
        for bolt in PARTS:
            if bolt['owner']!=owner or 'machining' not in bolt:continue
            m=bolt['machining'];off=np.zeros(3)
            if bolt['frame']!=part['frame']:
                if owner<7 and bolt['frame']==f'J{owner+1}.fixed':off=np.array(L['joints'][owner]['offset'])
                else:continue
            p=np.array(m['p'])+off;n=np.array(m['n']);plate=m['plate'];w=m['washer'];head=m['head'];ln=m['length']
            s=drill(s,p+n*(plate+w-ln-.2),n,m['d']+.6,ln+.4)
            # Recess sufficient for head plus compact washer and socket access.
            dia=max(head[0],{3:7,4:9,5:9,8:16}[m['d']])+.6
            s=drill(s,p+n*(plate-.1),n,dia,w+head[1]+.4)
            if not s.isValid():raise RuntimeError(f'Final machining {part["id"]} by {bolt["id"]} invalid')
        for fastener in PARTS:
            if fastener['owner']!=owner or 'nut_machining' not in fastener:continue
            off=np.zeros(3)
            if fastener['frame']!=part['frame']:
                if owner<7 and fastener['frame']==f'J{owner+1}.fixed':off=np.array(L['joints'][owner]['offset'])
                else:continue
            m=fastener['nut_machining'];n=np.array(m['n']);p=np.array(m['p'])+off-n*.2
            pocket=cq.Workplane(plane(p,n)).polygon(6,m['af']/math.cos(math.pi/6)+.6).extrude(m['height']+.4).val()
            s=s.cut(pocket,tol=1e-5).fix()
        add(part['id'],s,owner,part['role'],part['material'],part['note'],part['frame'])
    # Printable fit coupons for independent motor patterns and bearing seats.
    for key in ['RS00','RS03','RS04','RS06']:
        inf=next(i for i in I if i['j']['model']==key);s=cyl([0,0,0],[0,0,1],inf['outer'],3)
        for kind,dd in [('output_fasteners',3.5 if key=='RS00' else 5.5 if key=='RS04' else 4.5),('fixed_front_fasteners',4.5 if key in ['RS03','RS04'] else 3.5)]:
            flip=inf['m']['interface_frame']['T_raw_from_interface_mm'][1][1]
            for px,py in inf['m'][kind]['raw_step_xy_mm']:s=drill(s,[px,py*flip,-1],[0,0,1],dd,5)
        add('GAUGE-'+key,s,0,'fit_coupon',material='PLA dimensional coupon',note='Check both patterns against delivered motor; gauge contains no tapped threads.')
    for dia in [46.9,47.1,47.3]:add(f'GAUGE-bearing-{dia}',ring([0,0,0],[0,0,1],29,dia/2,5),0,'fit_coupon',material='same filament as cage',note='Select/calibrate actual bearing fit before printing cage.')
    # Manifest meshes are local to their kinematic owner, STL preserves mm.
    manifest=dict(revision='A08-P0',status='dimensioned_printable_fit_prototype_not_3kg_load_qualified',units='mm',density_kg_mm3=DENSITY,layout=L,flange_from_J7_mm=[x+40,0,0],parts=PARTS,printing=dict(bed_mm=[256,256,256],load_test_allowed=False,material='PA12 or PA12-CF candidate; PLA/PETG fit-only',notes=['Run fit coupons first.','Slicer support/orientation and material creep require physical coupons.','Never print purchased motor or bearing envelopes.']),base_interface=dict(source='B04-P2',pcd_mm=120,count=8,clearance_d_mm=8.8,arm_to_base_rotation_deg=90,translation_mm=[0,135,34.6]),open_items=['Motor rated torque heat sinks do not match printed enclosure.','J1-J6 output bearing limits are absent in current source manuals.','RS00 drawing/STEP output projection mismatch: fit/shim required.','Printed bearing journals and seats require dimensional calibration; metal inserts preferred for load qualification.','Connector plugs and constant-length moving harness still require actual purchased cables.','No complete inverse dynamics or fatigue/creep qualification.'])
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':'))+'\n')
    summary={k:v for k,v in manifest.items() if k not in ['parts','layout']};summary['parts']=[{k:v for k,v in p.items() if k not in ['vertices_mm','triangles']} for p in PARTS]
    (OUT/'print-manifest.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    with (OUT/'parts.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['id','role','frame','mass_kg','solid_count','material','note'])
        for p in PARTS:w.writerow([p[k] for k in ['id','role','frame','mass_kg','solid_count','material','note']])
    print('DONE',len(PARTS),flush=True)

if __name__=='__main__':main()
