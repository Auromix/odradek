#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Original connector envelopes, mounting board and coax ledge; no vendor BREP."""
from pathlib import Path
import cadquery as cq,json,math,hashlib
D=Path(__file__).resolve().parents[1];M=D/'mechanical';M.mkdir(exist_ok=True)
N=json.loads((D/'netlist.json').read_text());F=json.loads((D/'footprint-dimensions.json').read_text());C=json.loads((D/'connector-contract.json').read_text())
parts=[]
def box(a,b):return cq.Workplane('XY').box(b[0]-a[0],b[1]-a[1],b[2]-a[2],centered=(False,False,False)).val().translate(a)
def add(name,s,col,role,basis):
 b=s.BoundingBox();parts.append(dict(name=name,shape=s,color=col,role=role,basis=basis,bbox_local=[[b.xmin,b.ymin,b.zmin],[b.xmax,b.ymax,b.zmax]]))
def place(s,c):return s.rotate((0,0,0),(0,0,1),-c['rotation_deg']).translate((c['u_mm'],c['v_mm'],1.6))
def globalize(s):return s.rotate((0,0,0),(1,0,0),-90).translate((-58,-27,-9))
b=box([0,0,0],[116,56,1.6])
for c in N['components']:
 for num,x,y,w,h,dr,typ in F[c['footprint']]['pads']:
  a=math.radians(-c['rotation_deg']);X=c['u_mm']+x*math.cos(a)-y*math.sin(a);Y=c['v_mm']+x*math.sin(a)+y*math.cos(a)
  if isinstance(dr,list):cut=cq.Workplane('XY').center(X,Y).slot2D(max(dr),min(dr),90).extrude(5).val().translate((0,0,-1))
  else:cut=cq.Solid.makeCylinder(dr/2,5,cq.Vector(X,Y,-1))
  b=b.cut(cut)
add('BRI01_PCB',b,(.05,.28,.15),'PCB','actual board outline and all current native footprint drills; no copper thickness geometry')
for c in N['components']:
 fp=c['footprint'];name=c['ref']
 if fp=='M3':continue
 if fp=='RJ45_615008160221':
  # Separate nominal shell cavity from maximum spring keep-volume.
  s=box([-7.5,0,0],[7.5,13.45,14.7]);s=s.cut(box([-6.2,-.1,2.0],[6.2,10.9,10.8]));add(name+'_shell_reference',place(s,c),(.55,.57,.61),'connector','Original shell/cavity abstraction; cavity not controlled mating geometry')
  for x in[-8.65,7.5]:add(name+'_spring_reservation_'+str(x),place(box([x,1.0,1],[x+1.15,8.5,15.84]),c),(.7,.72,.73),'spring-envelope','Bounds derived from private vendor STEP; rectangular envelope, not metal distribution')
 elif fp=='PC5_2_762':
  s=box([-9.02,0,0],[9.02,29.25,14.29]);s=s.cut(box([-7.7,-.1,1.2],[7.7,14.7,12.6]));add(name+'_header_reference',place(s,c),(.10,.45,.25),'connector','Original catalogue-envelope/cavity abstraction; exact6-pin footprint independently audited')
 else:
  s=box([-3.5,-3.5,.5],[3.5,3.5,3.5]).fuse(cq.Solid.makeCylinder(1.5,5,cq.Vector(0,0,3.5)));add(name+'_M3_stud',place(s,c),(.68,.63,.4),'terminal','Nominal manufacturer dimensions; no thread helix.0.5mm stand-off included')
  # Explicit nut/eyelet planning envelope, not a selected lug drawing.
  add(name+'_lug_nut_reservation',place(box([-5,-7,3.5],[5,3.5,12]),c),(.65,.45,.2),'planned-lug','M3 ring/nut upper envelope; exact wire lug and insulation part not yet selected')
 for i,(num,x,y,w,h,dr,typ)in enumerate(F[fp]['pads']):
  if typ=='NPTH':continue
  length=5 if fp=='PC5_2_762'else 3.3 if fp=='RJ45_615008160221'else 2.5
  if fp=='PC5_2_762':s=box([x-.4,y-.5,-length],[x+.4,y+.5,0])
  elif fp=='THR_M3_74651173':s=box([x-.6,y-.6,-length],[x+.6,y+.6,0])
  else:s=cq.Solid.makeCylinder(.23,length,cq.Vector(x,y,-length))
  add(name+'_tail_'+str(i),place(s,c),(.72,.7,.57),'tail','Physical pin planning; alloy/contact details omitted')
# Coax carrier is a separate metalL part sharing H5/H6 PCB holes.
# Vertical spine behind adaptors; ledge at v=56 corresponds globalZ-65.
ledge=box([36,54.5,1.6],[80,56,20]);spine=box([36,34,1.6],[80,55,3.1]);s=ledge.fuse(spine)
for x in[48,68]:
 # True D-hole: clipping a6.5dia disk flat at+2.75mm: full hole extent6.0mm.
 cut=cq.Solid.makeCylinder(3.25,4,cq.Vector(x,53,11),cq.Vector(0,1,0)).intersect(box([x-3.25,52,7.75],[x+2.75,58,14.25]));s=s.cut(cut)
 s=s.cut(cq.Solid.makeCylinder(1.6,5,cq.Vector(x,38,0)))
add('BRI01_COAX_LEDGE',s,(.38,.4,.43),'original-bracket','1.5mm right-angle carrier; no bend radius/manufacturing relief included yet; supplied as interface reference')
for i,x in enumerate([48,68],1):
 # Original Amphenol catalogue p47: long-end->fixed-shoulder bearing face14.6;
 # far flange face16.3; short end22.1. Panel outside plane is localv56.
 # Nut AF8; fixed shoulder AF9.5. Nut/washer thickness remains a planning envelope.
 body=cq.Solid.makeCylinder(3.175,22.1,cq.Vector(x,41.4,11),cq.Vector(0,1,0));body=body.cut(cq.Solid.makeCylinder(.7,22.3,cq.Vector(x,41.3,11),cq.Vector(0,1,0)))
 # Body flat is a cutout-conformal display abstraction: exact threaded flat is undimensioned.
 body=body.cut(box([x+2.75,54.5,7.7],[x+3.3,56,14.3]))
 add('X'+str(i)+'_132170_reference',body,(.76,.58,.18),'coax-adapter','Original old manufacturer catalogue p47 axial reference: longend41.4; bearingface56; shortend63.5. Not current tolerance-controlled vendorCAD')
 def hexring(af,v,th):
  pts=[(x+af/math.sqrt(3)*math.cos(j*math.pi/3),11+af/math.sqrt(3)*math.sin(j*math.pi/3))for j in range(6)]
  # build XY then map second coordinate to localz; extrude along +localv
  sh=cq.Workplane('XY').polyline(pts).close().extrude(th).val().rotate((0,0,0),(1,0,0),90).translate((0,v+th,0))
  return sh.cut(cq.Solid.makeCylinder(3.175,th+.2,cq.Vector(x,v-.1,11),cq.Vector(0,1,0)))
 add('X'+str(i)+'_fixed_flange',hexring(9.5,56,1.7),(.76,.58,.18),'coax-flange','AF9.5 fixed flange, nominal1.7 axial thickness from catalogue14.6/16.3')
 add('X'+str(i)+'_nut_washer_reservation',hexring(8,52.0,2.5),(.72,.57,.19),'planned-nut-washer','AF8 removable nut;2.5mm combined nut/washer axial planning only, thickness not dimensioned by source')
# Keep plug/service reservations out of solidmanufacturingassembly until actualmateddatum is confirmed.
a=cq.Assembly(name='BRI01_global_assembly');al=cq.Assembly(name='BRI01_local_assembly')
for p in parts:a.add(globalize(p['shape']),name=p['name'],color=cq.Color(*p['color']));al.add(p['shape'],name=p['name'],color=cq.Color(*p['color']))
a.save(str(M/'base-rear-interface01-assembly.step'));al.save(str(M/'base-rear-interface01-local.step'));al.save(str(M/'base-rear-interface01-local.glb'));cq.exporters.export(globalize(b),str(M/'board-only.step'))
metadata=[]
for p in parts:
 s=globalize(p['shape']);bb=s.BoundingBox();metadata.append({k:v for k,v in p.items()if k not in['shape','color']}|dict(bbox_global=[[bb.xmin,bb.ymin,bb.zmin],[bb.xmax,bb.ymax,bb.zmax]],valid=s.isValid(),solid_count=len(s.Solids())))
out=dict(revision='BRI01',status='mechanical contract populated; pin/net/routing audit separate',transform='X=u-58;Y=z-27;Z=-9-v',board_size_mm=[116,56,1.6],mount_holes_mm=[[6,6],[110,6],[110,50],[6,50]],bracket_holes_mm=[[48,38],[68,38]],parts=metadata,connector_contract='connector-contract.json',not_mass_model=True,excluded=['externalpluggeometry until mateddatum closure','cableminimum bend path','3Dtest of latch access','formal tolerance stack','RFperformance'])
(D/'mechanical-interface.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
(M/'parts.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
(M/'verification.json').write_text(json.dumps(dict(valid=all(p['valid']for p in metadata),parts=len(metadata),solids=sum(p['solid_count']for p in metadata),assembly_sha256=hashlib.sha256((M/'base-rear-interface01-assembly.step').read_bytes()).hexdigest(),scope='Original board/package envelopes; no manufacturing release, no supplier BREP redistribution'),indent=2)+'\n')
print('mechanical',len(parts),'parts')
