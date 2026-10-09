# SPDX-License-Identifier: CC-BY-NC-4.0
"""Ordinary fasteners, tube crush sleeves and explicitly bounded thread zones."""
import json,math,numpy as np,cadquery as cq
import common as c
from vendor import interfaces
g=c.cad;I=interfaces();O=c.OUT/'hardware01';O.mkdir(exist_ok=True);g.OUT=O
H=[]

def add(id,s,owner,frame,note):
    e=g.add(id,s,owner,role='hardware',material='purchased steel, nominal dimensional envelope; do not print',note=note,frame=frame,mass=s.Volume()*7.85e-6)
    assert e['solid_count']==1;return e
def washer(id,p,n,d,owner,frame,th,outer):
    return add(id,g.ring(p,n,outer/2,d/2+.2,th),owner,frame,f'Purchased washer OD{outer} /hole{d+.4} /th{th}')
def bolt(id,p,n,d,length,grip,owner,frame,w=.8,od=None,motor=None,depth=None,button=False):
    p=np.array(p,float);n=np.array(n,float);outer,height={3:(5.5,3),4:(7,4),5:(8.5,5),6:(10,6)}[d]
    if button:outer,height=5.7,1.65
    start=p+n*(grip+w-length);bearing=p+n*(grip+w)
    s=g.cyl(start,n,d/2,length).fuse(g.cyl(bearing,n,outer/2,height)).clean()
    af=2 if button else {3:2.5,4:3,5:4,6:5}[d]
    tool=cq.Workplane(g.plane(bearing+n*(height+.1),-n)).polygon(6,af/math.cos(math.pi/6)).extrude(min(height-.3,af/2)+.1).val();s=s.cut(tool)
    e=add(id,s,owner,frame,f'ISO4762 M{d}x{length}' if not button else f'ISO7380-1 M{d}x{length}; hexsocketAF{af}')
    outer_washer=od if od is not None else {3:7,4:9,5:9,6:12}[d]
    washer(id+'-washer',p+n*grip,n,d,owner,frame,w,outer_washer)
    entry=dict(id=id,frame=frame,owner=owner,p_mm=p.tolist(),n=n.tolist(),diameter_mm=d,length_mm=length,plate_grip_mm=grip,washer_mm=w,washer_outer_mm=outer_washer,head_diameter_mm=outer,head_height_mm=height,motor=motor,source_blind_depth_mm=depth,engagement_mm=length-grip-w)
    if motor:
        assert 0<entry['engagement_mm']
        if depth is not None:assert entry['engagement_mm']<depth-.4
        e['intentional_thread_motor']=motor;e['thread_zone_mm']=dict(p=p.tolist(),n=n.tolist(),depth=entry['engagement_mm'],diameter=d+.02)
    H.append(entry);return e
def nut(id,p,n,d,owner,frame,h=None):
    af,height={3:(5.5,2.4),4:(7,3.2),5:(8,4.7)}[d]
    height=h or height;s=cq.Workplane(g.plane(p,n)).polygon(6,af/math.cos(math.pi/6)).extrude(height).val();s=g.drill(s,np.array(p)-np.array(n)*.1,n,d,height+.2)
    return add(id,s,owner,frame,f'ISO4032 nut M{d}; AF{af}, envelope height{height}; thread helix omitted')
def points(inf,kind):
    flip=inf['model_source']['interface_frame']['T_raw_from_interface_mm'][1][1]
    return [np.array(inf['u'])*x+np.array(inf['v'])*y*flip for x,y in inf['model_source'][kind]['raw_step_xy_mm']]

def main():
    c.base_context();g.PARTS.clear();g.SHAPES.clear();H.clear()
    for k in range(8):
        a=np.radians(22.5+45*k);bolt(f'A16-H-base-M6-{k+1}',[60*np.cos(a),60*np.sin(a),58],[0,0,1],6,20,8,0,'world',w=1.6,od=12,motor='B06')
    for k,(x,y) in enumerate([(60,0),(0,60),(-60,0),(0,-60)],1):
        bolt(f'A16-H-column-M5-{k}',[x,y,66],[0,0,1],5,110,102.5,0,'world',w=1,od=10)
        nut(f'A16-H-column-nut-{k}',[x,y,61],[0,0,1],5,0,'world')
    for k,(x,y) in enumerate([(x,y) for x in [-38,38] for y in [-28,28]],1):
        bolt(f'A16-H-shoulder-foot-M5-{k}',[x,y,20],[0,0,1],5,30,18,1,'J1.rotor',w=1,od=10)
        washer(f'A16-H-shoulder-foot-rear-washer-{k}',[x,y,19],[0,0,1],5,1,'J1.rotor',1,10)
        nut(f'A16-H-shoulder-foot-nut-{k}',[x,y,14.3],[0,0,1],5,1,'J1.rotor')
    # Fixed screws follow their fixed frames; complete native output screws
    # follow the rotor. No cable bore is assumed through any actuator.
    for index,inf in enumerate(I):
        j=inf['joint'];model=inf['model']
        fd,fl,ft,fw,depth=(4,12,6,.8,8) if index==0 else (4,12,8,.8,5) if model=='RS04' else (4,12,8,.8,4.5) if model=='RS10P' else (3,12,8,.5,None)
        od,ol,ot,ow,odepth=(4,25,20,.8,6) if index==0 else (5,16,10,1,6.5) if model=='RS04' else (4,14,10,.8,5) if model=='RS10P' else (3,40,35.5,.5,5)
        for k,v in enumerate(points(inf,'fixed_front_fasteners'),1):bolt(f'A16-H-{j}-fixed-{k}',np.array(inf['fixed_mm'])+v,inf['n'],fd,fl,ft,index,j+'.fixed',w=fw,motor=j,depth=depth,button=index==6)
        for k,v in enumerate(points(inf,'output_fasteners'),1):bolt(f'A16-H-{j}-output-{k}',np.array(inf['out_mm'])+v,inf['n'],od,ol,ot,index+1,j+'.rotor',w=ow,motor=j,depth=odepth)
    for owner,xs,cy in [(3,[60,72,250,262],0),(4,[27,37,60,70],62)]:
        for k,x in enumerate(xs,1):
            f=f'J{owner}.rotor';prefix=f'A16-H-tube-{owner}-{k}'
            bolt(prefix+'-M4',[x,cy-14,0],[0,1,0],4,35,28,owner,f,w=.8)
            washer(prefix+'-rear-washer',[x,cy-14.8,0],[0,1,0],4,owner,f,.8,9)
            nut(prefix+'-nut',[x,cy-18,0],[0,1,0],4,owner,f)
            s=g.ring([x,cy-8,0],[0,1,0],4,2.25,16)
            add(prefix+'-crush-spacer',s,owner,f,'Stock spacer OD8 ID4.5 length16 nominal; match measured tube internal width before cutting; bolt captures sleeve. No tube wall crushing used as a clamp strategy.')
    for k in range(6):
        a=np.radians(30+60*k);y,z=35*np.cos(a),35*np.sin(a)
        bolt(f'A16-H-J7-cage-M3-{k+1}',[25.3,y,z],[1,0,0],3,40,31.4,6,'J7.fixed',w=.5)
        washer(f'A16-H-J7-cage-rear-washer-{k+1}',[24.8,y,z],[1,0,0],3,6,'J7.fixed',.5,7)
        nut(f'A16-H-J7-cage-nut-{k+1}',[22.4,y,z],[1,0,0],3,6,'J7.fixed')
    # Retained body-side interface only: no dummy tool cup or its screws.
    add('A16-H-IF-core-dowel',g.cyl([62.7,24,0],[1,0,0],1.5,6),7,'J7.rotor','Purchased steel D3x6 clock dowel; actual retention trial required.')
    for k in range(3):
        a=np.radians(30+120*k);y,z=22.5*np.cos(a),22.5*np.sin(a)
        bolt(f'A16-H-IF-core-M4-{k+1}',[57.7,y,z],[1,0,0],4,20,19,7,'J7.rotor',w=.8,od=8.8)
        nut(f'A16-H-IF-core-nut-{k+1}',[57.7,y,z],[1,0,0],4,7,'J7.rotor')
    for k,y in enumerate([-14,14],1):
        bolt(f'A16-H-IF-roof-front-{k}',[103.2,y,33],[1,0,0],3,10,6.8,7,'J7.rotor',w=.5)
        nut(f'A16-H-IF-roof-front-nut-{k}',[103.2,y,33],[1,0,0],3,7,'J7.rotor')
    for k,y in enumerate([-10,10],1):
        bolt(f'A16-H-IF-roof-rear-{k}',[84,y,34],[0,0,1],3,10,6,7,'J7.rotor',w=.5,button=True)
        nut(f'A16-H-IF-roof-rear-nut-{k}',[84,y,34],[0,0,1],3,7,'J7.rotor')
    for k,y in enumerate([-29,29],1):
        bolt(f'A16-H-IF-panel-{k}',[98.7,y,0],[1,0,0],3,12,11.3,7,'J7.rotor',w=.5)
        nut(f'A16-H-IF-panel-nut-{k}',[98.7,y,0],[1,0,0],3,7,'J7.rotor')
    for k,x in enumerate([36.2,47.2],1):
        add(f'A16-H-J7-6807-{k}',g.ring([x,0,0],[1,0,0],23.5,17.5,7),6,'J7.fixed','6807 ID35 OD47 width7 nominal closed envelope, not internal rolling geometry. Uniform steel envelope mass is conservative, not catalogue mass. Shim after physical endplay measurement.')
    parts=[{k:v for k,v in p.items() if k not in ['vertices_mm','triangles']} for p in g.PARTS]
    (O/'manifest.json').write_text(json.dumps(dict(revision='A16-HARDWARE01',layout=c.L,parts=parts,bolts=H,
      narrow_M5_motor_washer='DIN433 small washer OD9; standard DIN125 OD10 would overlap adjacent native bolt stations and is not substituted.',
      body_tool_interface_fasteners='Body core/dorsal cover/insert fasteners and two6807 envelopes included. Tool cup, tool bolts/key and head excluded.',
      assembly_qualified=False,production_release=False),indent=2)+'\n')
    (O/'meshes.json').write_text(json.dumps(g.PARTS,separators=(',',':'))+'\n');print('HARDWARE_TOTAL',len(parts),len(H),flush=True)

if __name__=='__main__':main()
