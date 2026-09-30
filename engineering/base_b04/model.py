# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""B04 base: exact prototype solids, global millimetre assembly datum.

Original manufacturing geometry; purchased items are explicitly envelopes.
Threads are pilot cylinders, not helical solids. See feature metadata.
"""
import json
import math
from pathlib import Path
import cadquery as cq

HERE = Path(__file__).resolve().parent
P = json.loads((HERE / 'parameters.json').read_text())
DENSITY = {'6061-T651': 2.70e-6, 'S355': 7.85e-6, 'PETG': 1.27e-6,
           'silicone': 1.15e-6, 'steel':7.85e-6, 'brass':8.50e-6, 'FR4':1.85e-6}

def box(x,y,z,dx,dy,dz):
    return cq.Workplane('XY').box(dx,dy,dz,centered=False).translate((x,y,z)).val()

def cyl(point, direction, radius, length):
    return cq.Solid.makeCylinder(radius,length,cq.Vector(*point),cq.Vector(*direction))

def rounded_box(x,y,z,dx,dy,dz,r=1):
    return cq.Workplane(obj=box(x,y,z,dx,dy,dz)).edges('|Z').fillet(r).val()

class Part:
    def __init__(self,id,shape,material,process,notes=None,category='custom',color=None):
        self.id,self.shape,self.material,self.process = id,shape,material,process
        self.features=[];self.notes=notes or [];self.category=category
        self.color=color or {'6061-T651':[.45,.48,.51,1],'S355':[.12,.14,.17,1],
             'PETG':[.10,.12,.15,1],'silicone':[.06,.07,.08,1],
             'steel':[.38,.40,.43,1],'brass':[.62,.43,.20,1],
             'FR4':[.02,.28,.16,1]}.get(material,[.45,.45,.45,1])
    def hole(self,point,axis,d,depth,callout=None,extra=None):
        self.shape=self.shape.cut(cyl(point,axis,d/2,depth))
        self.features.append({'type':'hole','entry_xyz':list(point),'axis':list(axis),
           'model_diameter_mm':d,'model_depth_mm':depth,'callout':callout or f'D{d} THRU',**(extra or {})})
        return self
    def note(self,text):self.notes.append(text);return self

def make(t=30, covers=True, environment=False):
    parts=[]
    def add(*a,**kw):
        p=Part(*a,**kw);parts.append(p);return p
    deck=cq.Workplane('XY').polyline(P['deck_outline']).close().extrude(12).edges('|Z').fillet(4).translate((0,0,2)).val()
    d=add('B04-101-DECK',deck,'6061-T651','CNC profile + mill + drill/tap',
          ['Profile R4; metal top z14, desk pad plane z0. Side tapped holes drill 17 deep, full thread >=14.',
           'Bottom flange-post counterbores seat at z10.5; screw heads remain above z2.5.'])
    for x,y in P['flange_posts']:
        d.hole((x,y,2),(0,0,1),8.5,12,'D8.5 THRU')
        d.hole((x,y,2),(0,0,1),15,8.5,'CBORE D15 x 8.5 FROM BOTTOM')
    for sign in [-1,1]:
        for y in [15,45,75]:d.hole((sign*110,y,8),(-sign,0,0),5,17,'M6x1-6H; FULL THREAD >=14; DRILL 17')
    for x,y in P['cover_posts']:
        d.hole((x,y,2),(0,0,1),3.4,12,'D3.4 THRU')
        # 90 degree flat head, D6.3 major diameter, 1.45 deep.
        d.shape=d.shape.cut(cq.Solid.makeCone(3.15,1.70,1.45,cq.Vector(x,y,2),cq.Vector(0,0,1)))
        d.features.append({'type':'countersink','entry_xyz':[x,y,2],'axis':[0,0,1],'callout':'CSK D6.3 x 90 DEG FROM BOTTOM; M3x20 FLAT HEAD'})
    for u,v in P['pcb_holes_local']:
        d.hole((u-40,v-2,14),(0,0,-1),2.5,8,'M3x0.5-6H; FULL THREAD 6; DRILL 8')
    d.hole((90,-15,14),(0,0,-1),3.3,9,'M4x0.7-6H; FULL THREAD 7; CHASSIS BOND LUG')
    d.shape=d.shape.cut(rounded_box(43,-34,1,36,16,14,4))
    d.features.append({'type':'slot','entry_xyz':[61,-26,2],'callout':'36 x16 THRU WINDOW, R4; X43..79 Y-34..-18; CABLE DROP'})
    for sign in [-1,1]:
        s=cq.Workplane('YZ').polyline(P['side_profile_yz']).close().extrude(10).edges('|X').fillet(5).translate((110 if sign>0 else -120,0,0)).val()
        p=add(f'B04-102-CPLATE-{"R" if sign>0 else "L"}',s,'S355','Profile cut oversize; finish mill + drill/tap',
              ['All profile corners R5. 10 mm certified steel plate; coat after machining; mask mating faces.',
               'Left/right differ by installation only; hole axes shown from outer face.'])
        for y in [15,45,75]:p.hole((sign*120,y,8),(-sign,0,0),6.6,10,'D6.6 THRU; M6x25 + WASHER')
        for y in [40,75]:p.hole((sign*120,y,-101),(-sign,0,0),8.5,10,'D8.5 THRU; M8x25 + WASHER')
        for y in [10,50]:p.hole((sign*120,y,-88),(-sign,0,0),5,10,'M6x1-6H THRU; CRADLE; WEB HAS NO HOLES')
    bridge=add('B04-103-BRIDGE',box(-110,22,-112,220,68,22),'6061-T651','CNC mill + drill/tap',
               ['M12 thrust screws: certified DIN6332-5.8, AF6 drive; no ordinary cup-point grub screws.'])
    for x,y in P['clamp_axes']:bridge.hole((x,y,-112),(0,0,1),10.2,22,'M12x1.75-6H THRU; BREAK BOTH ENTRIES 0.5')
    for sign in [-1,1]:
        for y in [40,75]:bridge.hole((sign*110,y,-101),(-sign,0,0),6.8,18,'M8x1.25-6H; FULL THREAD >=15; DRILL 18')
    flange=cyl((0,135,46),(0,0,1),80,12).cut(cyl((0,135,46),(0,0,1),30,12))
    f=add('B04-104-FLANGE',flange,'6061-T651','CNC turn/mill + drill/tap',
           ['Base test interface only. OD160 / ID60, PCD120: 8 x M6 phase22.5deg.',
            'Face z58 flatness0.1; no commercial motor compatibility claimed.'])
    for x,y in P['flange_posts']:f.hole((x,y,46),(0,0,1),8.5,12,'D8.5 THRU; M8x25 + WASHER')
    for i in range(8):
        a=math.radians(22.5+45*i)
        f.hole((60*math.cos(a),135+60*math.sin(a),46),(0,0,1),5,12,'M6x1-6H THRU; PCD120')
    for i,(x,y) in enumerate(P['flange_posts']):
        p=add(f'B04-105-POST-{i+1}',cyl((x,y,14),(0,0,1),11,32),'6061-T651','Turn + drill/tap',
              ['OD22 x32; M8x1.25-6H through; end faces parallel0.05. Four identical posts.'])
        p.hole((x,y,14),(0,0,1),6.8,32,'M8x1.25-6H THRU')
    for sign in [-1,1]:
        add(f'B04-106-TOPPAD-{sign}',rounded_box(sign*75-21.5,8,0,43,154,2,3),'silicone','Knife/waterjet cut',
             ['2 mm solid silicone sheet 60 Shore A nominal; adhesive to metal only; friction not qualified.'])
        x=sign*85
        p=add(f'B04-107-PRESSPAD-{sign}',rounded_box(x-35,10,-t-10,70,90,8,3),'6061-T651','CNC mill/drill/tap',
              ['Steel thrust foot directly bears on flat underside; polymer retaining clips carry no clamp load.'])
        for yy in [32,78]:p.hole((x,yy,-t-10),(0,0,1),2.5,6,'M3x0.5-6H; FULL THREAD4; DRILL6; FOOT RETAINER')
        add(f'B04-108-LOWPAD-{sign}',rounded_box(x-35,10,-t-2,70,90,2,3),'silicone','Knife/waterjet cut',
             ['2 mm solid silicone sheet; bond to spreader upper face.'])
        # Two split halves install sideways after fitting the DIN6311 foot.
        r=cyl((x,55,-t-20),(0,0,1),17,10).fuse(rounded_box(x-30,50,-t-20,60,10,10,2))
        r=r.cut(cyl((x,55,-t-18),(0,0,1),14,8)).cut(cyl((x,55,-t-20),(0,0,1),11,10))
        for half in [-1,1]:
            piece=r.intersect(box(x-40 if half<0 else x+.2,30,-t-21,39.8,50,12))
            piece=piece.rotate((x,55,0),(x,55,1),90)
            rp=add(f'B04-109-FOOT-CAGE-{sign}-{half}',piece,'PETG','FDM; 0.2 layer, 4 walls, solid around screws',
                ['Split retainer, D28 x8 chamber / D22 throat; 0.4mm split gap. Non-load-bearing. Post-drill screw holes D3.4 +0.2/0.',
                 'Steel foot D25 flange x6, D18 neck x7 allocation. Verify received part articulation before use.'])
            rp.hole((x,55+half*23,-t-20),(0,0,1),3.4,10,'D3.4 THRU; M3x14, ENGAGEMENT4')
    # Under-desk cradle: rear hangers and inward horizontal arms are single plates.
    profile=[(-30,-195),(285,-195),(285,-175),(-6,-175),(-6,-108),(65,-108),(65,-78),(-30,-78)]
    for sign in [-1,1]:
        sh=cq.Workplane('YZ').polyline(profile).close().extrude(8).edges('|X').fillet(4).translate((120 if sign>0 else -128,0,0)).val()
        p=add(f'B04-201-CRADLE-{"R" if sign>0 else "L"}',sh,'6061-T651','CNC profile + drill/tap',
               ['Profile corners R4. Withdraw controller toward +Y; cradle removed without loosening main desk clamp.'])
        for y in [10,50]:p.hole((sign*128,y,-88),(-sign,0,0),6.6,8,'D6.6 THRU; M6x16 + WASHER')
        p.hole((sign*128,40,-101),(-sign,0,0),20,8,'D20 OPEN-EDGE RELIEF FOR BRIDGE M8 HEAD/WASHER')
        for y in [140,250]:p.hole((sign*124,y,-175),(0,0,-1),3.3,12,'M4x0.7-6H; FULL THREAD9; DRILL12')
    tray=add('B04-202-TRAY',box(-128,102,-175,256,188,5),'6061-T651','CNC profile + drill/tap',
              ['Controller mechanical gauge 180x150x50, max3kg allocation; controller ventilation to be checked separately.',
               'Do not install screws within the central controller footprint.'])
    for x in [-124,124]:
        for y in [140,250]:tray.hole((x,y,-175),(0,0,1),4.5,5,'D4.5 THRU; M4x12')
    # Two crossbars outside box envelope. Front one is removed for service.
    for label,y in [('REAR',107),('FRONT',273)]:
        st=add('B04-203-STOP-'+label,rounded_box(-108,y,-170,216,10,12,1),'6061-T651','Mill + drill',
               ['Front stop removable using 2 M4x16; controller gauge slides toward +Y.',
                'Use separate adjustable strap through tray side slots to retain vertically.'])
        # Hole locations differ from initial shared list, map correctly to tray.
        yy=y+5
        for x in [-100,100]:tray.hole((x,yy,-175),(0,0,1),3.3,5,'M4x0.7-6H THRU; STOP M4x16')
        for x in [-100,100]:st.hole((x,yy,-170),(0,0,1),4.5,12,'D4.5 THRU; M4x16')
    # 20mm hook/loop strap passes through real radiused tray slots.
    for x in [-108,108]:
        slot=rounded_box(x-2,175,-176,4,24,7,1.5)
        tray.shape=tray.shape.cut(slot)
        tray.features.append({'type':'slot','entry_xyz':[x,187,-175], 'callout':'4 x24 THRU SLOT, R1.5; 20mm RETAINING STRAP'})
    # Real cover screw posts and PCB standoffs are purchased envelopes, not custom blanks.
    for i,(x,y) in enumerate(P['cover_posts']):
        p=add(f'HW-COVER-POST-{i}',cyl((x,y,14),(0,0,1),3.2,35),'brass','Purchase M3 F/F hex AF5.5 x35',category='hardware')
        p.hole((x,y,14),(0,0,1),2.5,35,'M3 F/F; envelope only')
    for i,(u,v) in enumerate(P['pcb_holes_local']):
        x,y=u-40,v-2
        p=add(f'HW-PCB-POST-{i}',cyl((x,y,14),(0,0,1),3.2,9),'brass','Purchase M3 M/F hex AF5.5 x9; male6',category='hardware')
        p.hole((x,y,14),(0,0,1),2.5,9,'M3 M/F; envelope only')
    # Split roof at y50; same global dimensions as contract.
    outline=[(-126,-42),(126,-42),(126,50),(118,100),(126,170),(100,212),(45,232),(-45,232),(-100,212),(-126,170),(-118,100),(-126,50)]
    outer=cq.Workplane('XY').polyline(outline).close().extrude(38).edges('|Z').fillet(6).translate((0,0,14)).val()
    # A polygon offset creates a constant wall, preserving an open bottom and 3mm roof.
    inner=cq.Workplane('XY').polyline(outline).close().wires().offset2D(-2.5).extrude(35.1).translate((0,0,13.9)).val()
    shell=outer.cut(inner).cut(cyl((0,135,13),(0,0,1),81,41))
    # Metal C-arms penetrate sidewall at z14..30: deliberate clearance windows.
    for sign in [-1,1]:shell=shell.cut(box(109 if sign>0 else -128,-43,13,19,143,18))
    # Rear feed-down slots, generous cable envelope, opening from underside.
    shell=shell.cut(box(48,-44,13,54,7,33))
    rear=shell.intersect(box(-150,-50,0,300,99.6,80))
    front=shell.intersect(box(-150,50.4,0,300,220,80))
    if covers:
        for label,sh,positions in [('REAR',rear,P['cover_posts'][:2]),('FRONT',front,P['cover_posts'][2:])]:
            p=add('B04-301-COVER-'+label,sh,'PETG','FDM; 0.2mm layer; 4 walls; supports under roof',
                  ['Nominal wall2.5, roof3.0; clearances checked on nominal geometry.',
                   'Print as separate front/rear pieces; rear lifts vertically for PCB access; seam0.8mm.',
                   'Cosmetic shroud carries no arm or clamp load. Post-drill screw holes D3.4 +0.2/0 at assembly jig.'])
            for x,y in positions:p.hole((x,y,49),(0,0,1),3.4,3,'D3.4 THRU; M3x8 + WASHER')
    # Service PCB envelope is replaced/augmented by the actual PCB assembly during build.
    pcb_path=HERE.parent/'electronics/base-b04/mechanical/base-b04-board-only.step'
    pcb_shape=cq.importers.importStep(str(pcb_path)).val().translate(tuple(P['pcb_origin'])) if pcb_path.exists() else box(-40,-2,23,80,50,1.6)
    pcb=add('ENV-PCB',pcb_shape,'FR4','Actual KiCad drilled board, see electronics/base-b04',category='envelope')
    for u,v in P['pcb_holes_local']:pcb.hole((u-40,v-2,23),(0,0,1),3.2,1.6,'NPTH D3.2')
    add('ENV-CONTROLLER',box(-90,120,-170,180,150,50),'FR4','Controller volume gauge; electronics not yet designed',category='envelope',color=[.14,.18,.23,1])
    # Simplified purchased thrust hardware: exact catalog outer allocation, no redistribution of vendor CAD.
    for sign in [-1,1]:
        x=sign*85
        foot=cyl((x,55,-t-16),(0,0,1),12.5,6).fuse(cyl((x,55,-t-23),(0,0,1),9,7))
        add(f'HW-THRUST-FOOT-{sign}',foot,'steel','Ganter DIN6311-25-S envelope; articulation not simulated',category='hardware')
        # Manufacturer pin is smaller; conservative shank envelope excludes the foot overlap.
        add(f'HW-THRUST-SCREW-{sign}',cyl((x,55,-t-114.6),(0,0,1),6,91.6),'steel','Ganter DIN6332-M12-100-SK; threads/neck simplified',category='hardware')
    # Fasteners: purchasing envelopes, all assembly positions and lengths explicit.
    def bolt(id,seat,axis,size,length,washer=0,countersunk=False,engagement=None):
        diam={3:5.5,4:7,6:10,8:13}[size]
        q=list(seat); a=list(axis)
        headbase=[q[k]-a[k]*size for k in range(3)]
        if countersunk:
            sh=cq.Solid.makeCone(size*1.05,size/2,size*.55,cq.Vector(*q),cq.Vector(*a))
            sh=sh.fuse(cyl(q,a,size/2,length))
        else:
            sh=cyl(q,a,size/2,length).fuse(cyl(headbase,a,diam/2,size))
        if washer:
            sh=sh.fuse(cyl(q,a,{3:3.5,4:4.5,6:6,8:8}[size],washer))
        p=add(id,sh,'steel',f'Purchase {"ISO10642 flat head" if countersunk else "ISO4762 cap screw"} M{size}x{length}; class8.8 minimum'+(f'; washer t{washer}' if washer else ''),category='fastener')
        p.notes=['Thread and drive simplified. Washer is included in this visualization group, purchase separately.',f'Nominal engaged length {engagement}mm' if engagement else 'See assembly stack.']
        p.free_shape=sh.cut(cyl(q,a,size/2+.001,length+.01))
    for i,(x,y) in enumerate(P['flange_posts']):
        bolt(f'HW-M8-FLANGE-{i}',(x,y,59.6),(0,0,-1),8,25,1.6,engagement=11.4)
        bolt(f'HW-M8-DECK-{i}',(x,y,10.5),(0,0,1),8,16,engagement=12.5)
    for s in [-1,1]:
        for i,y in enumerate([15,45,75]):bolt(f'HW-M6-DECK-{s}-{i}',(s*121.6,y,8),(-s,0,0),6,25,1.6,engagement=13.4)
        for i,y in enumerate([40,75]):bolt(f'HW-M8-BRIDGE-{s}-{i}',(s*121.6,y,-101),(-s,0,0),8,25,1.6,engagement=13.4)
        for i,y in enumerate([10,50]):bolt(f'HW-M6-CRADLE-{s}-{i}',(s*129.6,y,-88),(-s,0,0),6,16,1.6,engagement=6.4)
        for h in [-1,1]:bolt(f'HW-M3-CAGE-{s}-{h}',(s*85,55+h*23,-t-20),(0,0,1),3,14,engagement=4)
    for i,(x,y) in enumerate(P['cover_posts']):
        bolt(f'HW-M3-COVER-BOTTOM-{i}',(x,y,2),(0,0,1),3,20,countersunk=True,engagement=8)
        if covers:bolt(f'HW-M3-COVER-TOP-{i}',(x,y,52.5),(0,0,-1),3,8,.5,engagement=4.5)
    for i,(u,v) in enumerate(P['pcb_holes_local']):bolt(f'HW-M3-PCB-{i}',(u-40,v-2,25.1),(0,0,-1),3,8,.5,engagement=5.9)
    for x in [-124,124]:
        for y in [140,250]:bolt(f'HW-M4-TRAY-{x}-{y}',(x,y,-170),(0,0,-1),4,12,engagement=7)
    for x in [-100,100]:
        for y in [112,278]:bolt(f'HW-M4-STOP-{x}-{y}',(x,y,-158),(0,0,-1),4,16,engagement=4)
    if environment:
        add('ENV-DESK',box(-450,0,-t,900,600,t),'wood','Test environment; not part of BOM',category='environment',color=[.46,.31,.19,1])
        add('ENV-WALL',box(-450,-58,-260,900,10,380),'wall','Clearance plane at y=-48',category='environment',color=[.75,.77,.80,1])
    return parts

if __name__=='__main__':
    a=make()
    for p in a: print(p.id, p.shape.isValid(), len(p.shape.Solids()), round(p.shape.Volume(),2))
