# SPDX-License-Identifier: CC-BY-NC-4.0
"""A09 manufacturing architecture: flat side plates, straight tubes, machined end seats.
Proposal geometry, not a released fabrication kit. mm. No supplier meshes copied.
"""
from pathlib import Path
import sys,json,math
import numpy as np
import cadquery as cq
from shapely.geometry import LineString,box
import trimesh
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'engineering/arm_a08'));import build as b
BASE=json.loads((ROOT/'engineering/parameters/arm-a09-layout.json').read_text())

def polygon_solid(poly,z,h):
 w=cq.Workplane('XY').workplane(offset=z).polyline(list(poly.exterior.coords)[:-1]).close()
 for hole in poly.interiors:w=w.polyline(list(hole.coords)[:-1]).close()
 return w.extrude(h).val()
def rectangular(a,c,w=16,h=24):
 a,c=np.array(a),np.array(c);n=b.unit(c-a);x=np.array([0,0,1.])
 if abs(n[2])>.95:x=np.array([1.,0,0])
 return cq.Workplane(cq.Plane(origin=b.V(a),normal=b.V(n),xDir=b.V(x))).rect(w,h).extrude(float(np.linalg.norm(c-a))).val()
def carrier_beams(path,owner):
 return [rectangular(x,y,w=11 if owner==5 else 5 if owner==6 and k==1 else 6 if owner==6 else 16,h=8 if owner==5 else 10 if owner==6 else 24) for k,(x,y) in enumerate(zip(path,path[1:]))]

def add(id,s,owner,role,material,mass=None,note='',frame=None):
 return b.add(id,s,owner,role,material,note,frame,mass)
def machine_voids(s,owner):
 prev=b.I[owner-1];nxt=b.I[owner];off=np.array(nxt['j']['offset'])
 for inf,t in [(prev,np.zeros(3)),(nxt,off)]:
  s=s.cut(b.housing_keepout(inf,t,3),tol=1e-5).fix()
  s=s.cut(b.cyl(inf['out']+t-inf['n']*inf['m']['interface_frame']['output_to_housing_front_mm'],inf['n'],inf['pilot'],inf['m']['interface_frame']['output_to_housing_front_mm']),tol=1e-5).fix()
 for inf,t,kind,th in [(prev,np.zeros(3),'output_fasteners',10),(nxt,off,'fixed_front_fasteners',nxt['th'])]:
  d=5.5 if kind=='output_fasteners' and inf['j']['model']=='RS04' else 3.5 if inf['j']['model']=='RS00' or kind=='fixed_front_fasteners' and inf['j']['model']=='RS06' else 4.5
  for v in b.xy_holes(inf,kind):s=b.drill(s,inf['out' if kind.startswith('output') else 'fixed']+t+v-inf['n'],inf['n'],d,th+2)
 return s

def main(variant='slim'):
 L=json.loads(json.dumps(BASE));L['tube_sections_mm']['forearm']=[20,40,2]
 if variant=='long':L['joints'][3]['offset'][0]+=40;L['joints'][4]['offset'][0]+=40
 b.L=L;b.I=[b.info(j) for j in L['joints']];b.I[5]['outer']=32.0;b.PARTS.clear();b.SHAPES.clear();b.OUT=ROOT/'engineering/arm_a09/build'/variant;b.OUT.mkdir(parents=True,exist_ok=True)
 # Turned tube pedestal, rather than bent struts. Two end faces + clearance slots.
 j1off=float(L['joints'][0]['offset'][2])
 fixed=b.I[0]['fixed']+np.array([0,0,j1off]);stem=b.ring([0,0,31.4],[0,0,1],60,54, float(fixed[2]-31.4))
 base=b.ring([0,0,23.4],[0,0,1],80,30,8);root=b.fuse([stem,base])
 top=b.holder(b.I[0]).translate((0,0,j1off))
 for k in range(8):
  a=math.radians(22.5+45*k);p=[60*math.cos(a),60*math.sin(a),22.4]
  root=b.drill(root,p,[0,0,1],8.8,10);root=b.drill(root,[p[0],p[1],31.4],[0,0,1],18,16)
 # Separate top ring makes the large internal cavity accessible to ordinary boring tools.
 for k in range(6):
  a=math.radians(30+60*k);p=[57*math.cos(a),57*math.sin(a),float(fixed[2])]
  top=b.drill(top,np.array(p)-[0,0,1],[0,0,1],4.5,10)
  root=b.drill(root,np.array(p)-[0,0,16],[0,0,1],3.3,17)
 channel=cq.Solid.makeBox(9,14,float(fixed[2]-31.4+10),b.V([-62.5,-7,31.4]))
 root=root.cut(channel,tol=1e-5).fix();top=top.cut(channel,tol=1e-5).fix()
 add('P00-open-pedestal',root,0,'cnc_adapter','6061 open-ended turned pedestal blank',mass=root.Volume()*2.70e-6,note='D160 / PCD120 inherited base interface. Top ring separate: internal boring from open108mm mouth; rear14mm split-bundle channel. SixM4 tapped holes, patternPCD114, thread/edge strength and bolt access require validation.')
 add('P00-top-motor-ring',top,0,'cnc_adapter','6061 separate flat motor ring8mm',mass=top.Volume()*2.70e-6,note='Bolted top ring; actual motor pattern plus sixM4 clearance holes onPCD114. Pedestal design target includes21.8mm cable-loop space below J1 motor; no cable-life qualification.')
 # Compact machined shoulder and wrist carriers, with planar ribs and real bolt patterns.
 a=b.I[1]['fixed'][1]-5.5;bx=100+b.I[2]['fixed'][0]+4
 e=b.I[4]['out'][1]-5;f=b.I[5]['fixed'][2]-4
 g=b.I[5]['out'][2]-5;hx=L['joints'][6]['offset'][0]+b.I[6]['fixed'][0]+4
 paths={1:[[-20,0,5],[-20,0,14],[-75,0,18],[-75,a,85],[-57,a,85]],
 2:[[20,a,0],[20,a-22,0],[75,a-22,0],[bx,48,0],[bx,40,0]],
 5:[[-16,22,0],[-16,22,f],[float(L['joints'][5]['offset'][0])-24,22,f]],
 6:[[0,12,g],[0,12,33.5],[0,39,33.5],[hx,39,33.5],[hx,39,8]]}
 for owner,path in paths.items():
  prev,nxt=b.I[owner-1],b.I[owner];off=np.array(nxt['j']['offset'])
  out=b.output(prev) if prev['j']['model']!='RS00' else b.cyl(prev['out'],prev['n'],17.5,10)
  if owner==1:
   from shapely.geometry import Polygon
   height=float(off[2]);profile=LineString([[-23,15],[-85,18],[-85,height-6]]).buffer(8,cap_style='round',join_style='round')
   back=polygon_solid(profile,-4,8).rotate((0,0,0),(1,0,0),90)
   back=back.cut(cq.Solid.makeBox(200,200,100,b.V([-100,-100,height-6])),tol=1e-5).fix()
   top_profile=Polygon([[-94,-5],[-78,-5],[-49,a-5],[-49,float(nxt['fixed'][1])],[-65,float(nxt['fixed'][1])],[-94,8]])
   top_plate=polygon_solid(top_profile,height-6,12)
   out=b.cyl(prev['out'],prev['n'],35,20)
   for v in b.xy_holes(prev,'output_fasteners'):out=b.drill(out,prev['out']+v-prev['n'],prev['n'],4.5,22)
   # Two proposed ordinary verticalM4 bolts into the flat back plate.
   for x in [-90,-80]:
    top_plate=b.drill(top_plate,[x,0,height-7],[0,0,1],4.5,14)
    back=b.drill(back,[x,0,height-22],[0,0,1],3.3,17)
   # Cross-pin/bolt retention for the plate pocket, above the stator carrier.
   for shape_name in ['back','out']:
    if shape_name=='back':back=b.drill(back,[-23,-40,15],[0,1,0],4.5,80)
    else:out=b.drill(out,[-23,-40,15],[0,1,0],4.5,80)
   holder=b.holder(nxt).translate(b.V(off))
   pieces=[('P01-flat-back-plate',back,'cnc_support_plate','6061 constant8mm XZ plate'),('P01-flat-top-plate',top_plate,'cnc_support_plate','6061 constant12mm XY plate'),('P01-output-seat',out.cut(back,tol=1e-5).fix(),'cnc_adapter','6061 output disk with flat plate pocket'),('P01-J2-fixed-seat',holder.cut(back,tol=1e-5).cut(top_plate,tol=1e-5).fix(),'cnc_adapter','6061 stator ring with flat plate pockets')]
   for id,piece,role,material in pieces:
    piece=machine_voids(piece,owner)
    add(id,piece,owner,role,material,mass=piece.Volume()*2.70e-6,note='Separate planar plate / motor seat. Shoulder bridge plate-to-seat fasteners not frozen; geometry partitions do not prove a bolted load path.')
   continue
  if owner==2:
   bridge=cq.Solid.makeBox(8,15.65,20,b.V([25.8,58,-10]))
   s=machine_voids(b.fuse([out,b.holder(nxt).translate(b.V(off)),bridge]),owner)
   add('P02-cross-shoulder-adapter',s,owner,'cnc_adapter','6061 compact cross-adapter proposal',mass=s.Volume()*2.70e-6,note='J2/J3 co-located axes; J2 motor shifted sideways15mm to keep10mm output plate and original bolt positions. Head/tool access and carrier strength still require validation.')
   continue
  parts=[out,b.holder(nxt).translate(b.V(off))]+carrier_beams(path,owner)
  # Wrist carrier needs the mirrored rib for a closed load path.
  if owner in [5,6]:
   mirror=[[-p[0],p[1],p[2]] if owner==5 else [p[0],-p[1],p[2]] for p in path]
   if owner==5:mirror=[[float(L['joints'][5]['offset'][0])*2-p[0] if k>1 else -p[0],p[1],p[2]] for k,p in enumerate(path)]
   parts.extend(carrier_beams(mirror,owner))
  s=machine_voids(b.fuse(parts),owner)
  if owner==6:
   s=s.cut(cq.Solid.makeBox(100,200,200,b.V([float(off[0]+nxt['fixed'][0]+nxt['th']),-100,-100])),tol=1e-5).fix()
  add(f'P{owner:02d}-end-carrier',s,owner,'cnc_adapter','6061 planar end-seat proposal',mass=s.Volume()*2.7e-6,note='Flat-faced end carrier: finish bolt/pilot interfaces from actual motor drawings. Small-carrier milling/setup review pending.')
 # Major links: flat laser/CNC plates + genuinely straight rectangular hollow tube.
 for owner in [3,4]:
  prev,nxt=b.I[owner-1],b.I[owner];off=np.array(nxt['j']['offset']);length=float(off[0])
  if owner==3:path=[[prev['out'][0]+5,0],[65,0],[length-70,0],[length-70,float(nxt['fixed'][1]+4)],[length-50,float(nxt['fixed'][1]+4)]];tx0,tx1,ty=70,length-70,0;tw=20
  else:path=[[0,float(prev['out'][1]+5)],[0,62],[length-65,62],[length-65,float(off[1]+nxt['fixed'][1]-4)],[length-40,float(off[1]+nxt['fixed'][1]-4)]];tx0,tx1,ty=20,length-70,62;tw=20
  poly=LineString(path).buffer(7,cap_style='round',join_style='round')
  # Conservative projected keep-outs preserve a constant plate thickness (2.5D machining).
  if owner==3:
   poly=poly.difference(box(-200,-200,float(prev['out'][0]),200))
   poly=poly.difference(box(length-nxt['j']['diameter_mm']/2-3,-100,length+nxt['j']['diameter_mm']/2+3,float(nxt['fixed'][1])))
  else:
   poly=poly.difference(box(-200,-200,200,float(prev['out'][1])))
   poly=poly.difference(box(length-52,-200,length+80,float(off[1]+nxt['fixed'][1]-nxt['th'])))
   poly=poly.difference(box(length-nxt['j']['diameter_mm']/2-3,float(off[1]+nxt['fixed'][1]),length+nxt['j']['diameter_mm']/2+3,250))
  if poly.geom_type!='Polygon':raise RuntimeError('Disconnected flat plate '+str(owner))
  tube=cq.Workplane(b.plane([tx0,ty,0],[1,0,0])).rect(tw,40).rect(tw-4,36).extrude(tx1-tx0).val()
  holes=[tx0+10,tx1-10]
  for x in holes:tube=b.drill(tube,[x,ty,-21],[0,0,1],4.5,42)
  add(f'T{owner:02d}-straight-tube',tube,owner,'stock_tube',f'aluminum hollow tube {tw}x40x2, square cut',mass=tube.Volume()*2.7e-6,note=f'Cut length {tx1-tx0:g}mm; two coaxial clearance holes, no curved extrusion or bent tube.')
  plate_shapes=[]
  (b.OUT/'dxf').mkdir(exist_ok=True)
  for label,z in [('A',20.2),('B',-24.2)]:
   s=polygon_solid(poly,z,4)
   for x in holes:s=b.drill(s,[x,ty,z-1],[0,0,1],4.5,6)
   entry=add(f'P{owner:02d}-flat-plate-{label}',s,owner,'cnc_plate','6061 flat plate 4mm',mass=s.Volume()*2.7e-6,note='Constant-thickness planar profile. 0.2mm fit gap to tube; metal shims and internal tube crush spacers required. End-seat bolting still under design.')
   entry['manufacturing']={'thickness_mm':4,'z_mm':z,'outer_xy_mm':list(poly.exterior.coords)[:-1],'holes_xy_mm':[[x,ty] for x in holes],'clearance_hole_diameter_mm':4.5,'drawing_status':'profile_and_tube_holes_only_end_seat_fastening_not_frozen'}
   plate_shapes.append(s)
   face=min((f for f in s.Faces() if f.geomType()=='PLANE' and abs(abs(f.normalAt().z)-1)<1e-6),key=lambda f:f.Center().z)
   wp=cq.Workplane(cq.Plane(origin=b.V([0,0,z]),normal=b.V([0,0,1]),xDir=b.V([1,0,0]))).newObject(face.Wires())
   cq.exporters.exportDXF(wp,str(b.OUT/'dxf'/f'P{owner:02d}-flat-plate-{label}.dxf'))
  # Separate end seats; matching plate pockets avoid material interpenetration.
  for label,inf,t,shape in [('in',prev,np.zeros(3),b.output(prev)),('out',nxt,off,b.holder(nxt).translate(b.V(off)))]:
   for plate in plate_shapes:shape=shape.cut(plate,tol=1e-5).fix()
   add(f'A{owner:02d}-{label}-motor-seat',shape,owner,'cnc_adapter','6061 motor flange/pilot seat',mass=shape.Volume()*2.7e-6,note='Motor pattern exact; plate-to-seat fastening and tolerances not frozen.')
  # Skin is 3D printed, structurally separate, no curved CNC requirement.
  # Straight sleeve only: structural end seats remain accessible and exposed.
  outline=[(tx0-8,ty-8),(tx0+8,ty-15),(tx1-8,ty-15),(tx1+8,ty-8),(tx1+8,ty+8),(tx1-8,ty+15),(tx0+8,ty+15),(tx0-8,ty+8)]
  from shapely.geometry import Polygon
  outer=Polygon(outline)
  skin=polygon_solid(outer,-27,54).cut(cq.Solid.makeBox(tx1-tx0+18,26.6,50.6,b.V([tx0-9,ty-13.3,-25.3])),tol=1e-5).fix()
  for plate in plate_shapes:
   for dy,dz in [(0,0),(.3,.3),(.3,-.3),(-.3,.3),(-.3,-.3)]:skin=skin.cut(plate.translate((0,dy,dz)),tol=1e-5).fix()
  add(f'S{owner:02d}-blade-fairing',skin,owner,'printed_cover','PETG cosmetic fairing',note='Thin independent cosmetic blade. Can be split for printing after silhouette approval; not part of the load path.')
 # Exact-size purchased motor envelopes; no cosmetic rescaling.
 for index,j in enumerate(L['joints']):
  inf=b.I[index];s=b.housing_keepout(inf,np.zeros(3))
  s=s.fuse(b.cyl(inf['fixed'],inf['n'],inf['pilot'],inf['m']['interface_frame']['output_to_housing_front_mm']))
  add(j['id']+'-motor-envelope',s,index,'motor_envelope','purchased '+j['model'],j['mass_kg'],frame=j['id']+'.fixed')
  if index==0:continue # J1 is already enclosed by the waist pedestal.
  org=inf['out']-inf['n']*(inf['depth']-6);le=inf['depth']-inf['m']['interface_frame']['output_to_housing_front_mm']-8;rad=j['diameter_mm']/2
  shell=cq.Workplane(b.plane(org,inf['n'])).polygon(16,2*(rad+2.5)/math.cos(math.pi/16)).circle(rad+.8).extrude(le).val()
  # Clear only rigidly attached carriers, not posed neighboring objects.
  for part in b.PARTS:
   if part['frame']==j['id']+'.fixed' or part['owner']==index and part['frame']==('world' if index==0 else f'J{index}.rotor'):
    if part['role'] in ['cnc_adapter','cnc_support_plate']:shell=shell.cut(b.SHAPES[part['id']].translate(b.V(-np.array(j['offset']))),tol=1e-5).fix()
  add(j['id']+'-dark-cuff',shell,index,'printed_cover','dark graphite PETG cuff',frame=j['id']+'.fixed',note='2mm-class cosmetic cuff; bolt-on fixing, split line, ventilation and thermal validation pending.')
 # Carry forward the separately supported J7 tool nose at unchanged dimensions.
 a08=ROOT/'engineering/arm_a08/build';old=json.loads((a08/'print-manifest.json').read_text())
 for p in old['parts']:
  if p['id'] not in ['B7-output-flange','J7-bearing-cage','J7-bearing-retainer','J7-inner-spacer','J7-6807-1','J7-6807-2']:continue
  s=cq.importers.importStep(str(a08/'step'/f'{p["id"]}.step')).val();add(p['id'],s,p['owner'],p['role'],p['material'],p['mass_kg'],p['note'],p['frame'])
 # Pedestal shell bridges existing shield base and the shoulder; zero motor rescaling.
 def loft(delta):
  w=cq.Workplane('XY').workplane(offset=31.4).ellipse(83-delta,78-delta)
  w=w.workplane(offset=24).ellipse(71-delta,67-delta)
  return w.workplane(offset=58).circle(65-delta).loft().val()
 pedestal=loft(0).cut(loft(2.0),tol=1e-5).fix()
 add('S00-waisted-base-transition',pedestal,0,'printed_cover','grey PETG removable pedestal',note='Body-side transition proposal only; does not modify original B04 desk clamp files.')
 # Printable geometry is exported only as proposal coupons/shape inspection, not a kit.
 data=dict(revision='A09-'+variant,status='manufacturing_architecture_and_silhouette_proposal_not_assembly_release',units='mm',layout=L,flange_from_J7_mm=[65.7,0,0],parts=b.PARTS,base_interface=dict(rotation_deg=90,translation_mm=[0,135,34.6]),omissions=['End-seat to flat-plate fasteners are not complete.','Fairing split lines, fixtures and connector ports are not complete.','Tube fits require shims and metal crush spacers.','No thermal/strength/cable-life qualification.'])
 (b.OUT/'manifest.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
 compact={k:v for k,v in data.items() if k!='parts'};compact['parts']=[{k:v for k,v in p.items() if k not in ['vertices_mm','triangles']} for p in b.PARTS]
 (b.OUT/'parts.json').write_text(json.dumps(compact,ensure_ascii=False,indent=2)+'\n')
 keep={p['id'] for p in b.PARTS}
 for folder in ['step','stl']:
  for file in (b.OUT/folder).glob('*'):
   if file.stem not in keep:file.unlink()
 print('A09 COMPLETE',variant,len(b.PARTS),flush=True)

if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else 'slim')
