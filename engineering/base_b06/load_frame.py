# SPDX-License-Identifier: CC-BY-NC-4.0
"""B06 original metal load-path CAD. Millimetres, common assembly datum.

Threads are drill solids with explicit tap callouts. Hardware is bought,
not printed. This module does not inherit B04 dimensions or its release state.
"""
from pathlib import Path
import json,math,hashlib
import cadquery as cq
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'build/load-frame'
POSTS=[(-60,75),(60,75),(-38,120),(38,120)]
PARTS=[]
def box(x,y,z,dx,dy,dz):return cq.Workplane('XY').box(dx,dy,dz,centered=False).translate((x,y,z)).val()
def cyl(x,y,z,r,h):return cq.Solid.makeCylinder(r,h,cq.Vector(x,y,z),cq.Vector(0,0,1))
def add(id,s,material,process,notes=None,category='metal'):
 p={'id':id,'shape':s,'material':material,'process':process,'notes':notes or [],'features':[],'category':category};PARTS.append(p);return p
def hole(p,x,y,z,d,h,callout,axis=(0,0,1)):
 p['shape']=p['shape'].cut(cq.Solid.makeCylinder(d/2,h,cq.Vector(x,y,z),cq.Vector(*axis)))
 p['features'].append({'entry_mm':[x,y,z],'axis':list(axis),'model_diameter_mm':d,'depth_mm':h,'callout':callout})
def make_carrier():
 s=cyl(0,75,3,84,4).cut(cyl(0,75,2,78,6))
 def join(t):
  nonlocal s;s=s.fuse(t)
 def cut(t):
  nonlocal s;s=s.cut(t)
 def beam(p,q,width,z0,z1):
  dx,dy=q[0]-p[0],q[1]-p[1];l=math.hypot(dx,dy);nx,ny=-dy/l*width/2,dx/l*width/2
  return cq.Workplane('XY').polyline([(p[0]+nx,p[1]+ny),(q[0]+nx,q[1]+ny),(q[0]-nx,q[1]-ny),(p[0]-nx,p[1]-ny)]).close().extrude(z1-z0).translate((0,0,z0)).val()
 def hexz(x,y,af,z0,z1):
  r=af/math.sqrt(3);return cq.Workplane('XY').polyline([(x+r*math.cos(math.pi/6+i*math.pi/3),y+r*math.sin(math.pi/6+i*math.pi/3)) for i in range(6)]).close().extrude(z1-z0).translate((0,0,z0)).val()
 def hexy(x,z,af,y0,y1):
  h=hexz(0,0,af,0,y1-y0);return h.rotate((0,0,0),(1,0,0),-90).translate((x,y0,z))
 for side in (-1,1):
  join(box(min(side*58,side*63),-30,18,5,60,2))
  join(box(min(side*72,side*78),28,6,6,12,14))
  join(box(min(side*61,side*77),28,18,16,12,2))
 for y0,y1 in [(-30,-27),(26,30)]:join(box(-63,y0,18,126,y1-y0,2))
 for x,y in [(-87,36),(87,36),(-72,125),(72,125)]:
  r=math.hypot(x,y-75);q=(x*81/r,75+(y-75)*81/r)
  join(beam((x,y),q,12,3,7));cut(cyl(x,y,2,1.7,6));cut(cyl(x,y,2,3.2,3.5))
 for x in (-60,60):
  join(beam((x,-29),(math.copysign(74,x),34),8,18,20))
  join(box(x-5,-31,18,10,8,19))
  cut(box(-59,-26.5,23.5,118,57,2.5))
  cut(cq.Solid.makeCylinder(1.7,10,cq.Vector(x,-32,32),cq.Vector(0,1,0)))
  cut(hexy(x,32,5.8,-28.8,-26))
  cut(box(x-2.9,-28.8,32,5.8,2.8,6))
 for x in (-52,52):
  for y in (-20,24):
   lo,hi=sorted([x,math.copysign(63,x)])
   join(box(lo,y-5,18,hi-lo,10,2));join(cyl(x,y,18,4.5,6))
   cut(cyl(x,y,14,1.7,11));cut(hexz(x,y,5.8,19,21.8))
   lo,hi=sorted([x,math.copysign(65,x)])
   cut(box(lo,y-2.9,19,hi-lo,5.8,2.8))
 for side in (-1,1):
  lo,hi=sorted([side*61,side*69]);join(box(lo,3,19.8,hi-lo,15,7.2))
  for y in (5,12):cut(box(side*65-1.1,y,19,2.2,5,9))
 cut(box(-70.8,-80,2,141.6,155,15.8))
 return s.clean()

def bolt(id,x,y,seat,d,length,hd,hh,axis=(0,0,1),af=4):
 # Local +Z is the head/driver side. Threads are maximum major envelopes.
 s=cyl(0,0,-length,d/2,length).fuse(cyl(0,0,0,hd/2,hh))
 key=cq.Workplane('XY').polygon(6,af/math.cos(math.pi/6)).extrude(hh*.65).translate((0,0,hh*.35)).val()
 s=s.cut(key)
 if axis==(0,0,-1):s=s.rotate((0,0,0),(1,0,0),180)
 elif axis==(1,0,0):s=s.rotate((0,0,0),(0,1,0),90)
 elif axis==(-1,0,0):s=s.rotate((0,0,0),(0,1,0),-90)
 s=s.translate((x,y,seat))
 return add(id,s,'steel','Purchase standard screw; strength class8.8 minimum for load-path screws',
            [f'M{d}x{length}; head envelope D{hd} x{hh}; hex AF{af}','Threads and chamfers omitted; dimensions are maximum planning envelopes, NOT hardware manufacturing STLs'],category='hardware')
def washer(id,x,y,z,od,idiam,t,axis=(0,0,1)):
 s=cyl(0,0,0,od/2,t).cut(cyl(0,0,0,idiam/2,t))
 if axis==(1,0,0):s=s.rotate((0,0,0),(0,1,0),90)
 elif axis==(-1,0,0):s=s.rotate((0,0,0),(0,1,0),-90)
 return add(id,s.translate((x,y,z)),'steel','Purchase ISO7089 washer',category='hardware')
def make_hardware(mating_hardware=False):
 for i,(x,y) in enumerate(POSTS,1):
  bolt(f'HW-M8-TOP-{i}',x,y,49.5,8,16,13,8,af=6)
  bolt(f'HW-M8-BOTTOM-{i}',x,y,10.5,8,20,13,8,axis=(0,0,-1),af=6)
 if mating_hardware:
  for i in range(8):
   a=math.radians(22.5+45*i);x=60*math.cos(a);y=75+60*math.sin(a)
   washer(f'HW-ROOT-WASHER-{i+1}',x,y,66,12,6.4,1.6)
   bolt(f'HW-ROOT-M6-{i+1}',x,y,67.6,6,20,10,6,af=5)
 for side in (-1,1):
  for i,z in enumerate((-80,-67),1):
   washer(f'HW-HANGER-WASHER-{side}-{i}',side*78,-55,z,12,6.4,1.6,axis=(side,0,0))
   bolt(f'HW-HANGER-M6-{side}-{i}',side*79.6,-55,z,6,20,10,6,axis=(side,0,0),af=5)
 for i,(x,y) in enumerate([(x,y) for x in (-74,74) for y in (120,270)],1):
  bolt(f'HW-TRAY-M4-{i}',x,y,-155,4,10,7.6,2.2,af=2.5)
 for label,y in [('BACK',112.5),('FRONT',282.5)]:
  for x in (-88,88):bolt(f'HW-STOP-M4-{label}-{x}',x,y,-140,4,20,7.6,2.2,af=2.5)
 for side in (-1,1):
  x=side*10;washer(f'HW-COAX-TOP-WASHER-{side}',x,-8,27.6,7,3.2,.5)
  washer(f'HW-COAX-BOTTOM-WASHER-{side}',x,-8,23.5,7,3.2,.5)
  bolt(f'HW-COAX-M3-{side}',x,-8,28.1,3,8,5.7,1.65,af=2)
  r=5.5/math.sqrt(3);n=cq.Workplane('XY').polyline([(x+r*math.cos(math.pi/6+i*math.pi/3),-8+r*math.sin(math.pi/6+i*math.pi/3)) for i in range(6)]).close().extrude(2.4).translate((0,0,21.1)).val().cut(cyl(x,-8,21.1,1.5,2.4))
  add(f'HW-COAX-NUT-{side}',n,'steel','Purchase DIN934 M3 nut; nominal unthreaded bore envelope',category='hardware')

def weld_bead(side,z,up,leg=5.0):
 # W01 four continuous fillets. Profiles are clearance approximations, not
 # metallurgical penetration models or proof of an approved weld procedure.
 y=-51 if side=='FRONT' else -59;dy=leg if side=='FRONT' else -leg
 return cq.Workplane('YZ').polyline([(y,z),(y+dy,z),(y,z+(leg if up else -leg))]).close().extrude(140).translate((-70,0,0)).val()
def add_welds():
 for side in ('FRONT','REAR'):
  for label,z,up in [('UPPER',2,False),('LOWER',-90,True)]:
   add('B06-W01-'+label+'-'+side,weld_bead(side,z,up),'S355',
       'W01 weld seam; NOT a separately purchased or machined component',
       ['Nominal fillet leg5.0; proposed process range5.0..5.5, concave/flat profile within modeled keepout',
        'Length140; weld procedure, end craters, inspection and distortion control require fabricator qualification'],category='weld')
def make(desk=30,mating_hardware=False):
 PARTS.clear()
 # 15 mm top plate + 2 mm desk protection. Flat pad seats, rear weld lands.
 outline=box(-70,-59,2,140,134,15).fuse(cyl(0,75,2,76,15).intersect(box(-70,75,2,140,80,15)))
 d=add('B06-101-LOAD-DECK',outline,'S355','CNC profile and drill/counterbore; weld assembly B06-W01',
       ['15 mm finished thickness; rear Y-59, table rear edge Y-45; corners deburr R0.5','Datum A upper Z17; flatness0.15 after welding; no polymer carries arm preload'])
 hole(d,0,75,2,56,15,'D56 THRU; harness passage')
 for x,y in POSTS:
  hole(d,x,y,2,8.5,15,'D8.5 THRU')
  hole(d,x,y,2,14.5,8.5,'BOTTOM CBORE D14.5 x8.5; M8x20 ISO4762; underhead Z10.5')
 for x in [-52,52]:
  for y in [-20,24]:hole(d,x,y,2,3.6,15,'D3.6 THRU; clearance for PCB screw tip, no electrical board contact')
 hole(d,62,15,17,5,12,'M6x1-6H; full thread9; drill12; dedicated chassis bonding point',axis=(0,0,-1))
 web=add('B06-102-REAR-WEB',box(-70,-59,-90,140,8,92),'S355','CNC plate profile/drill/tap; weld B06-W01',
         ['8 mm thickness; top Z2; rear Y-59; Four z5 continuous fillets; leg5.0..5.5 clearance envelope at upper and lower plate joints','Front fillet nominal toe Y-46, maximum envelope Y-45.5; nominal desk edgeY-45; machine datums after weld/stress relief; no weld in desk pad seat'])
 for sign in [-1,1]:
  for z in [-80,-67]:hole(web,sign*70,-55,z,5,16,'M6x1-6H; full thread13; drill16; shelf hanger',axis=(-sign,0,0))
 jaw_shape=box(-70,-59,-104,140,134,14).cut(box(-25,-35,-105,50,112,16))
 jaw=add('B06-103-LOWER-JAW',jaw_shape,'S355','CNC profile/drill/tap; weld B06-W01',
         ['14 mm finished thickness; two full steel threaded legs','M12 thrust screws turn from BELOW with AF6 key; no side knob hidden behind the box'])
 for x in [-45,45]:hole(jaw,x,50,-104,10.2,14,'M12x1.75-6H THRU; deburr both entries0.5; DIN6332 M12x100')
 flange=cyl(0,75,46,80,12).cut(cyl(0,75,46,28,12))
 # J2 plug/latch reserve is kept, not silently removed to pass intersection tests.
 flange=flange.cut(box(-17,28,46,34,55,2))
 f=add('B06-104-LOAD-FLANGE',flange,'6061-T651','CNC turn/mill + drill/tap; clear anodize, mask datums',
       ['OD160/ID56 x12; upper mating datum Z58 flatness0.1; 8xM6 PCD120 phase22.5deg; interface-contract.json governs','Bottom open cable pocket X±17/Y28..83/Z46..48; breaks into central bore','No motor dependency: independent test adapter or arm module fits this same base interface'])
 for k in range(8):
  a=math.radians(22.5+45*k);hole(f,60*math.cos(a),75+60*math.sin(a),46,5,12,'M6x1-6H THRU; PCD120, 22.5deg + k45deg')
 for x,y in POSTS:
  hole(f,x,y,46,8.5,12,'D8.5 THRU')
  hole(f,x,y,58,14.5,8.5,'TOP CBORE D14.5 x8.5; M8x16 ISO4762; underhead Z49.5',axis=(0,0,-1))
 for i,(x,y) in enumerate(POSTS,1):
  p=add(f'B06-105-POST-{i}',cyl(x,y,17,9,29),'6061-T651','Turn + through drill/tap',
        ['Four identical OD18 x29 spacers; ends parallel0.05','M8 full through thread; top bolt engagement12.5, bottom13.5 mm; nominal tip gap3.0 mm'])
  hole(p,x,y,17,6.8,29,'M8x1.25-6H THRU; ends chamfer0.5')
 # A large top pad with tool reliefs is trapped by adhesive only, never threaded.
 pad=add('B06-106-DESK-PAD',outline.translate((0,0,-2)).intersect(box(-70,-45,0,140,200,2)),
         'silicone','Cut 2 mm solid silicone, nominal60A; bond to deck', ['Friction and desk-surface compression require bench test'],'soft')
 pad['shape']=pad['shape'].cut(cyl(0,75,0,29,2))
 for x,y in POSTS:pad['shape']=pad['shape'].cut(cyl(x,y,0,8,2))
 for side in [-1,1]:
  x=side*45
  spread=add(f'B06-107-SPREADER-{side}',box(x-35,5,-desk-10,70,90,8),'6061-T651','CNC flat plate; R2 edge breaks',
             ['Foot bears directly on metal at (X±45,Y50); swivel foot retained by its supplied retaining spring','Place spreader during installation; pad must cover the entire contact footprint'])
  add(f'B06-108-PRESS-PAD-{side}',box(x-35,5,-desk-2,70,90,2),'silicone','Cut 2 mm solid silicone60A; bond to spreader',category='soft')
  # Inverted supplier envelope: flat D25 face bears upward against spreader.
  seat=-desk-10
  footshape=cyl(x,50,seat-13,9,7).fuse(cyl(x,50,seat-6,12.5,6))
  footshape=footshape.cut(cyl(x,50,seat-13,4.05,10))
  add(f'HW-DIN6311-{side}',footshape,'steel','Purchase Ganter DIN6311-25-S',
      ['D25 x13; inverted flat face at spreader underside; snap ring supplied','Bore represented as conservative cylindrical clearance, supplier swivel seat omitted; sample fit required'],'hardware')
  pinend=seat-3.3
  screwshape=cyl(x,50,pinend-100,6,90).fuse(cyl(x,50,pinend-10,4,10))
  socket=cq.Workplane('XY').center(x,50).polygon(6,6/math.cos(math.pi/6)).extrude(8).translate((0,0,pinend-100)).val()
  screwshape=screwshape.cut(socket)
  add(f'HW-DIN6332-{side}',screwshape,'steel','Purchase Ganter DIN6332-M12-100-SK; AF6',
      ['Length100 includes thrust pin; thread portion conservatively90; thread class5.8','Thrust seat approximation, not machining geometry; verify supplier seat/pin retention','Tighten from BELOW; do not print hardware'],'hardware')
  # Explicit external-controller shelf budget confirmed by user, inward only.
 profile=[(-63,-177),(290,-177),(290,-157),(-39,-157),(-39,-96),(-51,-96),(-51,-57),(-63,-57)]
 for sign in [-1,1]:
  s=cq.Workplane('YZ').polyline(profile).close().extrude(8).edges('|X').fillet(2).translate((70 if sign>0 else -78,0,0)).val()
  p=add(f'B06-201-HANGER-{sign}',s,'6061-T651','CNC profile from8 mm plate + drill/tap',
        ['Inward cantilever height20 mm; remove hanger independently of desk clamp; deburr R0.5'])
  for z in [-80,-67]:hole(p,sign*78,-55,z,6.6,8,'D6.6 THRU; M6x20 + washer',axis=(-sign,0,0))
  for y in [120,270]:hole(p,sign*74,y,-157,3.3,12,'M4x0.7-6H; full thread9; drill12; tray attachment',axis=(0,0,-1))
 tray=add('B06-202-TRAY',box(-100,100,-157,200,190,5),'6061-T651','CNC profile + drill/tap',
          ['Confirmed maximum box180x150x50 mm/3 kg; footprint X±90,Y120..270; slides +Y','20 mm hook/loop straps secure vertically; front stop removable; ventilation not covered by this mechanical budget'])
 for x in [-74,74]:
  for y in [120,270]:
   hole(tray,x,y,-157,4.5,5,'D4.5 THRU; M4x10 ISO7380-1; NO washer')
   hole(tray,x,y,-152,8.4,3,'TOP CBORE D8.4 x3; head top Z-152.8 below box seat; floor2 mm',axis=(0,0,-1))
 for x in [-96,96]:
  slot=cq.Workplane('XY').center(x,197).slot2D(24,4,90).extrude(6).translate((0,0,-157)).val();tray['shape']=tray['shape'].cut(slot)
  tray['features'].append({'callout':'4x24 vertical strap slot R2 THRU','entry_mm':[x,197,-157]})
 for label,y in [('BACK',110),('FRONT',280)]:
  st=add('B06-203-STOP-'+label,box(-95,y,-152,190,5,12),'6061-T651','Mill/drill', ['Front stop removes before box slides toward +Y'])
  for x in [-88,88]:
   hole(tray,x,y+2.5,-157,3.3,5,'M4x0.7-6H THRU; stop M4x20')
   hole(st,x,y+2.5,-152,4.5,12,'D4.5 THRU; M4x20')
 bracket=box(-20,-16,25.6,40,16,2).fuse(box(-20,-19,27.6,40,4.5,14.4))
 inner=[e for e in bracket.Edges() if abs(e.Center().y+14.5)<1e-5 and abs(e.Center().z-27.6)<1e-5 and e.Length()>30]
 if inner:bracket=bracket.fillet(1,inner)
 p=add('B06-309-COAX-BRACKET',bracket,'6061-T651','CNC mill original RF bulkhead bracket',
       ['Base2 mm at PCB top Z25.6; rear panel4.5 mm Y-19..-14.5; flange bearing face Y-16, internal fillet R1','H5/H6 mounting centres X±10,Y-8; coax axes X±10,Z35; mounts independent of cosmetic rear lid','Fixed coax rear datum retained at Y-16, separate from RJ45/power PCB shift; bond to chassis via J6 lug'])
 for x in (-10,10):
  hole(p,x,-8,25.6,3.6,2,'D3.6 THRU; M3x8 + washer0.5 + nut below PCB')
  hole(p,x,-19,35,6.8,4.5,'D6.8 round THRU; external flange captured in hex pocket',axis=(0,1,0))
  r=9.8/math.sqrt(3)
  key=cq.Workplane('XZ').polyline([(x+r*math.cos(i*math.pi/3),35+r*math.sin(i*math.pi/3)) for i in range(6)]).close().extrude(3).translate((0,-16,0)).val()
  for k in range(6):
   a=k*math.pi/3
   key=key.fuse(cq.Solid.makeCylinder(1.05,3,cq.Vector(x+r*math.cos(a),-19,35+r*math.sin(a)),cq.Vector(0,1,0)))
  p['shape']=p['shape'].cut(key)
  p['features'].append({'entry_mm':[x,-19,35],'axis':[0,1,0],'model_diameter_mm':9.8,'depth_mm':3,'callout':'AF9.8 rear HEX pocket depth3, six R1.05 corner reliefs; flange seat Y-16; source nominal AF9.5'})
 add('B06-307-LOWER-CARRIER',make_carrier(),'PETG','FDM print; exported exact CAD geometry',
     ['Printed PCB/cover locating scaffold only; no arm or clamp load','Board bottom Z24; side-insert nuts Z19.2..21.6; rear screw axis Z32','Retain 1mm nut-pocket floor and >=2.2mm roof; verify print fit coupon'],category='printed')
 add_welds()
 make_hardware(mating_hardware)
 add('REF-DESK',box(-400,-45,-desk,800,700,desk),'none','Environment only',category='environment')
 add('REF-BOX',box(-90,120,-152,180,150,50),'none','Confirmed clearance budget only',category='environment')
 return PARTS
def build():
 OUT.mkdir(parents=True,exist_ok=True)
 for n in ['step','stl']:(OUT/n).mkdir(exist_ok=True)
 parts=make();ass=cq.Assembly();manifest=[]
 for p in parts:
  s=p['shape'];assert s.isValid() and len(s.Solids())==1,(p['id'],'invalid solid')
  b=s.BoundingBox();item={k:v for k,v in p.items() if k!='shape'}
  item.update(bbox_mm=[[b.xmin,b.ymin,b.zmin],[b.xmax,b.ymax,b.zmax]],volume_mm3=s.Volume())
  cq.exporters.export(s,str(OUT/'step'/(p['id']+'.step')))
  imported=cq.importers.importStep(str(OUT/'step'/(p['id']+'.step'))).val();assert imported.isValid()
  assert abs(imported.Volume()-s.Volume())<max(.01,s.Volume()*1e-7)
  cq.exporters.export(s,str(OUT/'stl'/(p['id']+'.stl')),tolerance=.05,angularTolerance=.1)
  item['step']='step/'+p['id']+'.step';item['stl']='stl/'+p['id']+'.stl';manifest.append(item);ass.add(s,name=p['id'])
 ass.export(str(OUT/'B06-load-frame.step'))
 active={p['id'] for p in parts}
 for folder,extension in [('step','*.step'),('stl','*.stl')]:
  for path in (OUT/folder).glob(extension):
   if path.stem not in active:path.unlink()
 report={'revision':'B06-LOAD-03-WELD','arm_required':False,'datum':'Z0 desk, axis XY(0,75), +Y toward desk interior','desk_thickness_mm':[15,60],'desk_model_mm':30,'posts_mm':POSTS,'parts':manifest,'release':'Candidate; drawings, loads and physical fit qualification pending'}
 (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
 print('LOAD_FRAME_BUILT',len(parts),flush=True)
if __name__=='__main__':build()
