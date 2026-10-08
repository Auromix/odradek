# SPDX-License-Identifier: CC-BY-NC-4.0
"""A10 long hybrid arm: bolted printable end modules, stock tubes, split armour."""
from pathlib import Path
import json,math,numpy as np,cadquery as cq
import interfaces as c
b=c.legacy;OUT=c.OUT;L=c.L;I=c.I
A09=c.ROOT/'engineering/arm_a09/build/long'

def load(id):return cq.importers.importStep(str(A09/'step'/f'{id}.step')).val()
def box(x,y,z,dx,dy,dz):return cq.Solid.makeBox(dx,dy,dz,b.V([x,y,z]))
def insert_hole(s,p,n,d=3):
 # Captive hex nut slot, loaded sideways before the armour is fitted.
 n=np.array(n,float);p=np.array(p,float);af,h=(5.5,2.4) if d==3 else (7,3.2)
 s=b.drill(s,p-n*8,n,d+.5,12)
 pocket=cq.Workplane(b.plane(p-n*5,n)).polygon(6,(af+.3)/math.cos(math.pi/6)).extrude(h+.4).val()
 # Side-access slot parallel Y; printed bottom supports nut, no printed thread.
 z0=float(p[2]-5 if n[2]>0 else p[2]+5-h-.4)
 slot=box(float(p[0]-af/2-.3),-40,z0,af+.6,float(p[1]+40),h+.4)
 return s.cut(pocket,tol=1e-5).cut(slot,tol=1e-5).fix()

def captive_nut(id,p,n,owner,fr=None):
 # p is outer face of printed module, nut is 5mm below it.
 n=np.array(n,float);origin=np.array(p,float)-n*5
 c.std_nut(id,origin,n,3,owner,fr)

def socket(x0,x1,cy,tube0,tube1):
 profile=[(-14,-20.4),(-10,-24.4),(10,-24.4),(14,-20.4),(14,20.4),(10,24.4),(-10,24.4),(-14,20.4)]
 s=cq.Workplane(cq.Plane(origin=b.V([x0,cy,0]),normal=b.V([1,0,0]),xDir=b.V([0,1,0]))).polyline(profile).close().extrude(x1-x0).val()
 # Rectangular tube pocket opens through the insertion end and stops at the end wall.
 lo=max(x0,tube0);hi=min(x1,tube1)
 s=s.cut(box(lo,cy-10.2,-20.2,hi-lo,20.4,40.4),tol=1e-5).fix()
 # Nut access / thread ports for upper and lower armour.
 capx=(x0+tube0)/2 if x0<tube0 else (x1+tube1)/2
 for sign in [-1,1]:s=insert_hole(s,[capx,cy,sign*24.4],[0,0,sign])
 return s,capx

def main():
 OUT.mkdir(parents=True,exist_ok=True);b.OUT=OUT;b.L=L;b.I=I;b.PARTS.clear();b.SHAPES.clear();c.HARDWARE.clear();c.JOINTS.clear()
 # Root is separately opened to install the real J1. Four catalogue heat-set inserts.
 fz=float(I[0]['fixed'][2]+L['joints'][0]['offset'][2])
 posts=[box(54,-9,31.4,9,18,fz-31.4).rotate((0,0,0),(0,0,1),90*k) for k in range(4)]
 root=b.fuse([b.ring([0,0,23.4],[0,0,1],80,30,8)]+posts)
 top=b.ring([0,0,fz],[0,0,1],63,36.2,8)
 for k in range(8):
  angle=math.radians(22.5+45*k);p=[60*math.cos(angle),60*math.sin(angle),23.4]
  root=b.drill(root,np.array(p)-[0,0,1],[0,0,1],6.6,10);root=b.drill(root,np.array(p)+[0,0,8],[0,0,1],13,18)
  c.std_bolt(f'ROOT-M6-{k+1}',p,[0,0,1],6,20,8,0,washer=1.6,motor='B04-base-thread')
 for k in range(4):
  angle=math.radians(90*k);p=np.array([58.5*math.cos(angle),58.5*math.sin(angle),fz])
  root=b.drill(root,p-[0,0,9.1],[0,0,1],5.5,9.2)
  top=b.drill(top,p-[0,0,1],[0,0,1],4.5,10)
  c.std_bolt(f'ROOT-M4-{k+1}',p,[0,0,1],4,16,8,0,motor='ROOT-insert-'+str(k+1))
  ins=b.ring(p-[0,0,8.1],[0,0,1],3.15,2,8.1)
  e=c.part('ROOT-insert-'+str(k+1),ins,0,'hardware',material='ruthex RX-M4x8.1 brass heat-set insert',mass=ins.Volume()*8.5e-6,note='OD6.3 / nominal pilot5.5 / L8.1; intentional hot-insert interference; coupon first.')
  c.HARDWARE.append(dict(id=e['id'],type='insert',nominal=e['material'],frame='world'))
  top=top.cut(box(-66,-7,31.4,10,14,fz-31.4+20),tol=1e-5).fix()
 top=c.tool_holes(top,I[0],'fixed_front_fasteners',8,offset=[0,0,L['joints'][0]['offset'][2]])
 c.part('P00-root-open',root,0,note='D160/PCD120. Four open posts leave M6 hex-key access; separate8mm ring and four heat-setM4 inserts; rear windows for split harness. Supported fit prototype only.')
 c.part('P00-J1-top-ring',top,0,note='Eight source M4 bolts to J1, fourM4x16 to root inserts; fit shim and real motor required.')
 # Fuse the shoulder partitions into one printable module: no unconnected plate load path.
 shoulder=b.fuse([load(id) for id in ['P01-flat-back-plate','P01-flat-top-plate','P01-output-seat','P01-J2-fixed-seat']])
 shoulder=c.tool_holes(shoulder,I[0],'output_fasteners',20)
 shoulder=c.tool_holes(shoulder,I[1],'fixed_front_fasteners',11,offset=L['joints'][1]['offset'])
 c.part('P01-shoulder-monobloc',shoulder,1,note='Unified print module; source output6M4x25 and shoulder fixed10M4x16. Printed material not3kg qualified.')
 cross=load('P02-cross-shoulder-adapter')
 cross=c.tool_holes(cross,I[1],'output_fasteners',10)
 cross=c.tool_holes(cross,I[2],'fixed_front_fasteners',8)
 c.part('P02-cross-shoulder',cross,2,note='J2/J3 axes cross; RS04 asymmetrical9M5 screws and3 locating-pin pockets; original motor clocking retained.')
 # Two stock tubes with four positive retention bolts each; source bolt bores remain clear.
 for owner in [3,4]:
  prev,nxt=I[owner-1],I[owner];off=np.array(nxt['j']['offset'])
  t0,t1,cy=(70,270,0) if owner==3 else (20,115,62)
  prox,cx1=socket(t0-10,t0+32,cy,t0,t1)
  dist,cx2=socket(t1-32,t1+10,cy,t0,t1)
  op=b.output(prev);hd=b.holder(nxt).translate(b.V(off))
  if owner==3:
   ribs=[b.rect_beam([33,0,z],[t0-4,0,z],4) for z in [-20,20]]
   path=[[[t1+5,cy,z],[t1+5,float(nxt['fixed'][1]+4),z],[float(off[0]-45),float(nxt['fixed'][1]+4),z]] for z in [-22,22]]
  else:
   ribs=[rib for z in [-22,22] for rib in [b.rect_beam([0,float(prev['out'][1]+5),z],[0,float(prev['out'][1]+14),z],4),b.rect_beam([0,float(prev['out'][1]+14),z],[t0+4,cy,z],4)]]
   path=[[[t1+5,cy,z],[t1+5,float(off[1]+nxt['fixed'][1]-4),z],[float(off[0]-35),float(off[1]+nxt['fixed'][1]-4),z]] for z in [-22,22]]
  proximal=b.fuse([op,prox]+ribs)
  distal=b.fuse([hd,dist]+[b.rect_beam(x,y,4) for pp in path for x,y in zip(pp,pp[1:])])
  proximal=proximal.cut(box(t0,cy-10.2,-20.2,32,20.4,40.4),tol=1e-5).fix()
  distal=distal.cut(box(t1-32,cy-10.2,-20.2,32,20.4,40.4),tol=1e-5).fix()
  proximal=c.tool_holes(proximal,prev,'output_fasteners',10)
  distal=c.tool_holes(distal,nxt,'fixed_front_fasteners',nxt['th'],offset=off)
  for sh_name,inf,offset in [('proximal',prev,np.zeros(3)),('distal',nxt,off)]:
   sh=proximal if sh_name=='proximal' else distal
   sh=sh.cut(b.housing_keepout(inf,offset,.6),tol=1e-5).fix()
   if sh_name=='proximal':proximal=sh
   else:distal=sh
  positions=[t0+10,t0+25,t1-25,t1-10]
  tube=box(t0,cy-10,-20,t1-t0,20,40).cut(box(t0-1,cy-8,-18,t1-t0+2,16,36),tol=1e-5).fix()
  for k,x in enumerate(positions,1):
   tube=b.drill(tube,[x,cy,-21],[0,0,1],8.2,42)
   if k<3:proximal=b.drill(proximal,[x,cy,-26],[0,0,1],4.5,52)
   else:distal=b.drill(distal,[x,cy,-26],[0,0,1],4.5,52)
   spacer=b.ring([x,cy,-18],[0,0,1],4,2.25,36)
   c.part(f'T{owner}-crush-sleeve-{k}',spacer,owner,'hardware',material='Aluminum OD8 ID4.5 cut36mm anti-crush sleeve',mass=spacer.Volume()*2.7e-6,note='Deburr, insert through8.2mm tube hole before fitting printed socket.')
   c.std_bolt(f'T{owner}-M4-{k}',[x,cy,-24.4],[0,0,1],4,60,48.8,owner)
   c.std_nut(f'T{owner}-nut-{k}',[x,cy,-28.4],[0,0,1],4,owner)
   washer=b.ring([x,cy,-25.2],[0,0,1],4.5,2.2,.8)
   c.part(f'T{owner}-nut-washer-{k}',washer,owner,'hardware',material='steel M4 washer9x4.4x0.8',mass=washer.Volume()*7.85e-6)
  e=c.part(f'T0{owner}-stock-tube',tube,owner,'stock_tube',material='Aluminum20x40x2 straight tube',mass=tube.Volume()*2.7e-6,note=f'Cut{t1-t0}mm; four8.2mm through holes for sleeve alignment, no thread in tube.')
  e['tube_drawing']=dict(cut_length_mm=t1-t0,section_mm=[20,40,2],hole_offsets_from_start_mm=[x-t0 for x in positions],hole_diameter_mm=8.2)
  c.part(f'P0{owner}-proximal-socket',proximal,owner,note='Motor flange and closed rectangular tube socket printed as one module; insert tube against internal stop; no adhesive.')
  c.part(f'P0{owner}-distal-socket',distal,owner,note='Source stator ring and tube socket printed as one module. TwoM4 positive retention bolts; armour captiveM3 nuts.')
  # Four captive nuts fitted through the side slots before the tube/armour.
  for end,cx in [('prox',cx1),('dist',cx2)]:
   for sign in [-1,1]:
    p=np.array([cx,cy,sign*24.4]);n=np.array([0,0,sign]);captive_nut(f'S0{owner}-{end}-{sign}-nut',p,n,owner)
  # Eight-sided, tapered shell, upper/lower removable; an angular ridge over a curved waist.
  # Width36 at roots,32 in waist;24.4mm collar clearance,21mm tube clearance.
  stations=[(t0-10,18,28),(t0+28,18,28),((t0+t1)/2,16,24.2),(t1-28,18,28),(t1+10,18,28)]
  def section(y,z):return [(-y,-z+6),(-y+5,-z),(y-5,-z),(y,-z+6),(y,z-6),(y-5,z),(-y+5,z),(-y,z-6)]
  def loft(delta):
   wp=cq.Workplane(cq.Plane(origin=b.V([stations[0][0],cy,0]),normal=b.V([1,0,0]),xDir=b.V([0,1,0])))
   for idx,(x,y,z) in enumerate(stations):
    if idx:wp=wp.workplane(offset=x-stations[idx-1][0])
    wp=wp.polyline(section(y-delta,z-delta)).close()
   return wp.loft(ruled=False).val()
  skin=loft(0).cut(loft(2.4),tol=1e-5).fix()
  # Correct central cavity: shell has extra ends for captive-nut mounting seats.
  for end,cx in [('prox',cx1),('dist',cx2)]:
   for sign in [-1,1]:
    pad=b.cyl([cx,cy,sign*24.7],[0,0,sign],5.0,3.3)
    skin=skin.fuse(pad).fix()
    skin=b.drill(skin,[cx,cy,-30],[0,0,1],3.5,60)
  for shape in [proximal,distal]:
   for delta in [(0,0,0),(.4,0,0),(-.4,0,0),(0,.4,0),(0,-.4,0),(0,0,.4),(0,0,-.4)]:skin=skin.cut(shape.translate(delta),tol=1e-5).fix()
  for side,z0 in [('upper',.2),('lower',-100)]:
   height=100 if side=='upper' else 99.8
   sh=skin.intersect(box(t0-15,cy-40,z0,t1-t0+30,80,height)).fix()
   c.part(f'S0{owner}-armour-{side}',sh,owner,'printed_cover',note='Curved eight-sided waist and hard ridges; upper/lower split0.4mm. Two M3x12 screws into side-loaded captive nuts, install last.')
  for end,cx in [('prox',cx1),('dist',cx2)]:
   for sign in [-1,1]:
    p=np.array([cx,cy,sign*24.4]);n=np.array([0,0,sign]);c.std_bolt(f'S0{owner}-{end}-{sign}-M3',p,n,3,12,3.6,owner)
 # Small wrist carriers and independent J7 bearing cartridge.
 p5=load('P05-end-carrier');p5=c.tool_holes(p5,I[4],'output_fasteners',10);p5=c.tool_holes(p5,I[5],'fixed_front_fasteners',8,offset=L['joints'][5]['offset']);c.part('P05-wrist-pitch-to-yaw',p5,5,note='Open planar wrist carrier, output6M4 and stator6M3; print as one component.')
 p6=load('P06-end-carrier');p6=c.tool_holes(p6,I[5],'output_fasteners',10);p6=c.tool_holes(p6,I[6],'fixed_front_fasteners',8,offset=L['joints'][6]['offset'])
 for k in range(6):
  a=math.radians(30+60*k);p=[50.3,35*math.cos(a),35*math.sin(a)];p6=b.drill(p6,np.array(p)-[1,0,0],[1,0,0],3.5,10)
 c.part('P06-yaw-to-roll',p6,6,note='25mm axis offset; six newPCD70 M3 through holes match separate J7 cartridge. Cage installed after stator screws.')
 for id in ['B7-output-flange','J7-bearing-cage','J7-bearing-retainer','J7-inner-spacer','J7-6807-1','J7-6807-2']:
  old=next(p for p in c.BASE['parts'] if p['id']==id);s=load(id)
  if id=='J7-bearing-cage':
   # Fixed motor button heads must clear the cage, distinct from PCD70 cage bolts.
   for v in b.xy_holes(I[6],'fixed_front_fasteners'):s=b.drill(s,I[6]['fixed']+v+[7.9,0,0],[1,0,0],6.8,2.5)
  role='hardware' if old['role']=='hardware' else 'printed_structure'
  c.part(id,s,old['owner'],role,old['note'],old['frame'],old['material'] if role=='hardware' else None,old['mass_kg'] if role=='hardware' else None)
 central=b.ring([43.2,0,0],[1,0,0],18.5,17.55,4)
 c.part('J7-inner-centre-spacer',central,7,note='4mm nominal inner-ring separation; shim based on real stack, no printed preload.')
 for k in range(6):
  angle=math.radians(30+60*k);p=np.array([25.3,35*math.cos(angle),35*math.sin(angle)])
  c.std_bolt(f'J7-cage-M3-{k+1}',p,[1,0,0],3,40,31.4,6,'J7.fixed')
  c.std_nut(f'J7-cage-nut-{k+1}',p-[2.9,0,0],[1,0,0],3,6,'J7.fixed')
  w=b.ring(p-[.5,0,0],[1,0,0],3.5,1.7,.5);c.part(f'J7-cage-nut-washer-{k+1}',w,6,'hardware',frame_name='J7.fixed',material='steel M3 flat washer',mass=w.Volume()*7.85e-6)
 for k in range(3):
  angle=math.radians(30+120*k);c.std_nut(f'J7-tool-M4-nut-{k+1}',[57.85,22.5*math.cos(angle),22.5*math.sin(angle)],[1,0,0],4,7)
 # Seven correctly accounted actuator screw sets and original analytic envelopes.
 for idx,j in enumerate(L['joints']):
  c.mounting_bolts(idx,35.5 if idx==6 else 20 if idx==0 else 10,I[idx]['th'])
  p=next(p for p in c.BASE['parts'] if p['id']==j['id']+'-motor-envelope')
  c.part(p['id'],load(p['id']),idx,'motor_envelope',frame_name=j['id']+'.fixed',material='purchased '+j['model'],mass=j['mass_kg'],note='Original analytic envelope in public model; full official CAD imported in local vendor assembly.')
 armour()
 gauges()
 import refine
 refine.refine()
 data=dict(revision='A10-long-validation',status='geometry_validation_prototype_no_load_rating',units='mm',layout=L,flange_from_J7_mm=[65.7,0,0],parts=b.PARTS,base_interface=dict(**c.BASE['base_interface'],pcd_mm=120,bolt='8xM6x20 with1.6mm washers',source='B04-104-FLANGE M6x1 THRU12mm',source_note='A09 inherited M8 was wrong; A10 holes6.6 match actual base.'),hardware=c.HARDWARE,joint_mounting=c.JOINTS,printing=dict(bed_mm=[250,250,250],material_density_kg_mm3=b.DENSITY,load_test_allowed=False),assumptions=['SolidPA12 mass for structural prints, PETG cosmetic shell; slice and weigh actual parts.','Catalog motor masses at fixed centres; source rotor mass partition unknown.','Stock aluminum tubes and metallic fasteners are not printable substitutes.'],physical_gates=['Supplier interface dimensions and bolt engagement measured on purchased motors.','Supported manual assembly and removable covers verified.','Printing direction, wall/infill and threaded connections tested.','Heat and output-bearing ratings, motor brake/recovery strategy pending.'])
 (OUT/'manifest.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
 compact={k:v for k,v in data.items() if k!='parts'};compact['parts']=[{k:v for k,v in p.items() if k not in ['vertices_mm','triangles']} for p in b.PARTS];(OUT/'parts.json').write_text(json.dumps(compact,ensure_ascii=False,indent=2)+'\n')
 keep={p['id'] for p in b.PARTS}
 for directory in ['step','stl']:
  for path in (OUT/directory).glob('*'):
   if path.stem not in keep:path.unlink()
 print('A10 BUILD',len(b.PARTS),flush=True)

def armour():
 # Body-side waist shell split at X=0, joined by four M3 nuts/screws, broad curved shield.
 def loft(d):
  wp=cq.Workplane('XY').workplane(offset=31.4).ellipse(85-d,80-d)
  wp=wp.workplane(offset=24).ellipse(74-d,68-d)
  return wp.workplane(offset=82).circle(68-d).loft(ruled=True).val()
 sh=loft(0).cut(loft(2.4),tol=1e-5).fix()
 # Two seam tabs on each side, holes acrossX; their bosses stay outside the root.
 for z,r in [(45,72),(120,69)]:
  for sign in [-1,1]:
   boss=b.cyl([-6,sign*r,z],[1,0,0],4.5,12);sh=sh.fuse(boss).fix();sh=b.drill(sh,[-7,sign*r,z],[1,0,0],3.5,14)
   c.std_bolt(f'S00-{z}-{sign}-M3',[-6,sign*r,z],[1,0,0],3,20,12,0)
   c.std_nut(f'S00-{z}-{sign}-nut',[-8.9,sign*r,z],[1,0,0],3,0)
   w=b.ring([-6.5,sign*r,z],[1,0,0],3.5,1.7,.5);c.part(f'S00-{z}-{sign}-rear-washer',w,0,'hardware',material='steel M3 washer',mass=w.Volume()*7.85e-6)
 for name,x in [('A',.2),('B',-150)]:
  width=150 if name=='A' else 149.8
  s=sh.intersect(box(x,-150,30,width,300,125)).fix()
  c.part('S00-waist-'+name,s,0,'printed_cover',note='Separate body-side curved shield, clamped around root shoulder; fourM3x20 with nuts. Not a load member.')
 # Split slotted cuffs: case geometry remains actual size. Broad open sectors for airflow.
 for idx,j in enumerate(L['joints']):
  if idx==0:continue
  inf=I[idx];rad=j['diameter_mm']/2;org=inf['out']-inf['n']*(inf['depth']-5)
  depth=inf['depth']-inf['m']['interface_frame']['output_to_housing_front_mm']-13
  clamp_station=19 if idx==6 else 8
  pl=b.plane(org,inf['n']);band=cq.Workplane(pl).polygon(12,2*(rad+3)/math.cos(math.pi/12)).circle(rad+.6).extrude(depth).val()
  # Two narrow clamp tabs, one per seam side. Soft liner fixes the0.6mm radial clearance.
  for sign in [-1,1]:
   boss=b.cyl(org+inf['v']*sign*(rad+5)+inf['n']*clamp_station-inf['u']*6,inf['u'],4.5,12)
   band=band.fuse(boss).fix();band=b.drill(band,org+inf['v']*sign*(rad+5)+inf['n']*clamp_station-inf['u']*7,inf['u'],3.5,14)
   p=org+inf['v']*sign*(rad+5)+inf['n']*clamp_station-inf['u']*6
   c.std_bolt(j['id']+f'-armour-{sign}-M3',p,inf['u'],3,20,12,idx,j['id']+'.fixed')
   c.std_nut(j['id']+f'-armour-{sign}-nut',p-inf['u']*2.9,inf['u'],3,idx,j['id']+'.fixed')
   w=b.ring(p-inf['u']*.5,inf['u'],3.5,1.7,.5);c.part(j['id']+f'-armour-{sign}-rear-washer',w,idx,'hardware',frame_name=j['id']+'.fixed',material='steel M3 washer',mass=w.Volume()*7.85e-6)
  # Axial vent windows in six face sectors, keeping front/rear rings and clamp spine.
  for angle in [30,90,150,210,270,330]:
   t=math.radians(angle);u=inf['u']*math.cos(t)+inf['v']*math.sin(t);v=-inf['u']*math.sin(t)+inf['v']*math.cos(t)
   p=org+u*(rad-1)+inf['n']*13
   cutter=cq.Workplane(cq.Plane(origin=b.V(p),normal=b.V(inf['n']),xDir=b.V(u))).rect(12,8).extrude(max(1,depth-18)).val()
   band=band.cut(cutter,tol=1e-5).fix()
  # Same-rigid-frame support keepouts only, converted from upstream rotor to joint fixed.
  for e in b.PARTS:
   if e['role']=='printed_structure' and e['owner']==idx:
    s=b.SHAPES[e['id']]
    if e['frame']==c.frame(idx):s=s.translate(b.V(-np.array(j['offset'])))
    elif e['frame']!=j['id']+'.fixed':continue
    band=band.cut(s,tol=1e-5).fix()
  for name,x0 in [('A',.2),('B',-200)]:
   width=200 if name=='A' else 199.8
   cutter=cq.Workplane(pl).center(x0+width/2,0).rect(width,400).extrude(depth+1).val()
   s=band.intersect(cutter).fix()
   c.part(j['id']+'-armour-'+name,s,idx,'printed_cover',frame_name=j['id']+'.fixed',note='Slotted split graphite cuff;two M3x20 clamp screws and nuts;0.6mm radial liner gap. Do not obstruct real connector or cooling test.')

def gauges():
 for d in [46.9,47.1,47.3]:c.part(f'GAUGE-bearing-{d}',b.ring([0,0,0],[0,0,1],29,d/2,5),0,'fit_coupon',note='Print first in final cage orientation; bearing must slide by hand without pressing on balls.')
 for d in [34.8,34.95,35.1]:c.part(f'GAUGE-journal-{d}',b.cyl([0,0,0],[0,0,1],d/2,8),0,'fit_coupon',note='Calibrate actual35mm bearing bore and slicing compensation.')
 for d in [5.3,5.5,5.7]:
  s=box(-8,-8,0,16,16,12);s=b.drill(s,[0,0,3],[0,0,1],d,10);c.part(f'GAUGE-insert-{d}',s,0,'fit_coupon',note='RX-M4x8.1 insertion pilot coupon; choose delivered filament and insertion process.')
 for delta in [.2,.4,.6]:
  s=box(-15,-25,0,30,50,12).cut(box(-10-delta/2,-20-delta/2,-1,20+delta,40+delta,14),tol=1e-5).fix();c.part(f'GAUGE-tube-{delta}',s,0,'fit_coupon',note='Slide a cut/deburred20x40 tube; use clearance with no force.')
 for j in [I[0],I[1],I[4],I[6]]:
  s=b.output(j);c.part('GAUGE-'+j['j']['model']+'-output',s,0,'fit_coupon',note='Exact source hole/pin pattern; verify against delivered actuator before full print.')

if __name__=='__main__':main()
