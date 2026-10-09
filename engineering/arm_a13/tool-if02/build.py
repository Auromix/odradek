# SPDX-License-Identifier: CC-BY-NC-4.0
"""Recessed, layered manual tool interface. mm; supported unpowered trial.

HFM bodies are dimension-based conservative envelopes, not supplier CAD.
The full connector retention and dynamic cable chain remain open.
"""
from pathlib import Path
import sys,json,math,hashlib,csv,importlib.util
import cadquery as cq
import numpy as np
import trimesh
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common,BRepAlgoAPI_Cut
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=HERE/'build'
CORE=HERE.parent/'j7-fit01/build';PREV=HERE.parent/'tool-if01/build'
sys.path.insert(0,str(ROOT/'engineering/arm_a11'));import interfaces as c;import collision
spec=importlib.util.spec_from_file_location('fit_mesh',HERE.parent/'j7-fit01/build.py');fit=importlib.util.module_from_spec(spec);spec.loader.exec_module(fit)
b=c.legacy;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def box(p,s):return cq.Solid.makeBox(*s,b.V(p))
def hexa(p,n,d,h):return cq.Workplane(b.plane(p,n)).polygon(6,d).extrude(h).val()
def record(id,s,role,**kw):
 m=fit.mesh(s);return dict(id=id,frame='J7.rotor',role=role,vertices_mm=m.vertices.tolist(),triangles=m.faces.tolist(),**kw)
def clean(s):
 s=s.clean().fix();assert s.isValid() and len(s.Solids())==1;return s

def main():
 for folder in ['step','stl-object','print-bed']:(OUT/folder).mkdir(parents=True,exist_ok=True)
 sources={};old=json.loads((PREV/'manifest.json').read_text())
 def load(folder,id):
  p=folder/'step'/(id+'.step');sources[str(p.relative_to(ROOT))]=sha(p)
  return cq.importers.importStep(str(p)).val()
 def outer(x,L):
  # 16 facets give a hard outer silhouette without projecting an auxiliary box.
  return cq.Workplane(b.plane([x,0,0],[1,0,0])).polygon(16,88).extrude(L).val()
 # Original Ø18 pilot remains internal at the lower motor-to-collar interface.
 # The TOOL boundary is now the separate outer Ø76 annular pilot at X110.
 body=outer(65.7,44.3)
 body=body.cut(b.cyl([76.7,0,0],[1,0,0],32,29.3))
 body=body.cut(b.cyl([106,0,0],[1,0,0],27,4.1))
 body=body.fuse(b.ring([110,0,0],[1,0,0],38,27,2))
 body=body.cut(b.cyl([65.6,0,0],[1,0,0],9.15,2.3))
 body=b.drill(body,[65.6,24,0],[1,0,0],3.3,4.1)
 # Detach the upper shell over the internal service cavity.
 roof_box=box([76.7,-50,20],[29.3,100,40])
 cover=outer(76.7,29.1).cut(b.cyl([76.6,0,0],[1,0,0],41,29.3)).intersect(roof_box)
 body=body.cut(roof_box)
 # Hollow lower shell with three retained longitudinal ribs, instead of a thick tube.
 light=b.ring([76.7,0,0],[1,0,0],40,32,29.3)
 for p,size in [([76.6,31,-3.5],[29.5,14,7]),([76.6,-45,-3.5],[29.5,14,7]),([76.6,-3.5,-45],[29.5,7,14])]:
  light=light.cut(box(p,size))
 body=body.cut(light)
 for y in [-14,14]:
  # Front tabs use axial screws, hidden by the tool.
  for x in [102.7]:
   tab=box([x,y-4,29],[3,8,18]).intersect(outer(x,3))
   cover=cover.fuse(tab)
  body=b.drill(body,[105.9,y,33],[1,0,0],3.5,4.2)
  for x in [102.6]:cover=b.drill(cover,[x,y,33],[1,0,0],3.5,3.2)
  cover=cover.cut(hexa([103.2,y,33],[1,0,0],6.8,2.5))
  cover=cover.cut(box([102.6,y-3.4,29.6],[.6,6.8,6.8]))
 # Rear screws are accessible from above; no key has to pass a front captive nut.
 for y in [-10,10]:
  body=body.fuse(box([76.7,y-4,30],[11.3,8,8]))
  body=b.drill(body,[84,y,30.4],[0,0,1],3.5,7.7)
  body=body.cut(hexa([84,y,34],[0,0,1],6.8,2.5))
  body=body.cut(box([84,y-3.4,34],[5,6.8,2.5]))
  pad=box([80,y-4,38],[8,8,8]).intersect(outer(80,8))
  cover=cover.fuse(pad)
  cover=b.drill(cover,[84,y,37.9],[0,0,1],3.5,2.2)
  cover=cover.cut(b.cyl([84,y,40],[0,0,1],3.8,7))
 for k in range(3):
  a=math.radians(30+120*k);body=b.drill(body,[65.6,22.5*math.cos(a),22.5*math.sin(a)],[1,0,0],4.5,11.2)
 # Side entry joins the cavity AFTER the motor; this is not a hollow motor route.
 body=body.cut(box([70,-46,-7],[15,22,14]))
 # Four outer tool stations. Nuts load radially before the tool is installed.
 for k in range(4):
  a=math.radians(45+90*k);y,z=36*math.cos(a),36*math.sin(a)
  body=b.drill(body,[101.7,y,z],[1,0,0],4.5,10.5)
  body=body.cut(hexa([106,y,z],[1,0,0],8.3,3.5))
  chute=box([106,36,-4.15],[3.5,12,8.3]).rotate([0,0,0],[1,0,0],45+90*k)
  body=body.cut(chute)
 # Replaceable face insert with captive nuts in two side bosses.
 panel=b.cyl([103,0,0],[1,0,0],26,3)
 for y in [-29,29]:
  body=body.fuse(b.cyl([98.7,y,0],[1,0,0],5,4.3))
  body=body.cut(b.cyl([102.9,y,0],[1,0,0],4.2,3.2))
  body=b.drill(body,[98.5,y,0],[1,0,0],3.5,11.6)
  body=body.cut(hexa([98.7,y,0],[1,0,0],6.8,2.5))
  entry_y=-36 if y<0 else 22
  body=body.cut(box([98.7,entry_y,-3.4],[2.5,14,6.8]))
  panel=panel.fuse(b.cyl([103,y,0],[1,0,0],4,3))
  panel=b.drill(panel,[102.9,y,0],[1,0,0],3.5,3.2)
 ports=[dict(id='PWR',yz=[-10,11],opening=[12,14],kind='Allocation; Micro-Fit family drawing not dimension-released',budget=[40,12,13]),
        dict(id='CTRL',yz=[10,10],opening=[16,16],kind='Allocation only; change insert for selected protocol',budget=[48,16,16]),
        dict(id='CAM_UP',yz=[-9,-12],opening=[11.6,11.6],kind='HFM single, coded A proposed; chain and retention pending'),
        dict(id='CAM_DOWN',yz=[9,-12],opening=[11.6,11.6],kind='HFM single, coded C proposed; chain and retention pending')]
 volumes=[];blocks=[]
 for p in ports:
  y,z=p['yz'];w,h=p['opening'];panel=panel.cut(box([102.9,y-w/2,z-h/2],[3.2,w,h]))
  if p['id'].startswith('CAM'):
   # Conservative placement adds FULL housing lengths without assumed mating overlap.
   for suffix,start,size,pn in [
    ('jack',[82,y-4.8,z-10.9],[19.8,9.6,21.8],'AMK21A-103Z5-y'),
    ('plug',[101.8,y-4.55,z-5.275],[25.23,9.1,10.55],'AMS11A-103Z5-y')]:
    s=box(start,size);volumes.append((p['id']+'-'+suffix,s))
    blocks.append(record(p['id']+'-'+suffix,s,'datasheet_nominal_box_not_supplier_mesh',part_number=pn,dimensions_mm=size,origin_mm=start))
   p['sum_full_housing_lengths_mm']=45.03;p['mating_reference_verified']=False
   p['wire_exit_budget_origin_mm']=[127.03,y,z]
  else:
   L,w,h=p['budget'];start=[82,y-w/2,z-h/2];s=box(start,[L,w,h]);volumes.append((p['id'],s))
   blocks.append(record(p['id']+'-space',s,'unsourced_design_allocation',origin_mm=start,dimensions_mm=[L,w,h]))
   p['wire_exit_budget_origin_mm']=[82+L,y,z]
 # Tool-side dummy rear cup demonstrates the required hidden pocket; it is NOT the head.
 receiver=outer(110,23).cut(b.cyl([109.9,0,0],[1,0,0],27,23.2))
 receiver=receiver.cut(b.ring([109.9,0,0],[1,0,0],38.15,27,2.3))
 cap=outer(133,3).cut(b.cyl([132.9,0,0],[1,0,0],21,3.2))
 for k in range(4):
  a=math.radians(45+90*k);y,z=36*math.cos(a),36*math.sin(a)
  receiver=b.drill(receiver,[109.9,y,z],[1,0,0],4.5,23.2)
  cap=b.drill(cap,[132.9,y,z],[1,0,0],4.5,3.2)
 # One off-centre tool key rejects the other three bolt-compatible clocks.
 body=b.drill(body,[107,0,31],[1,0,0],3.1,5.1)
 receiver=b.drill(receiver,[109.9,0,31],[1,0,0],3.3,6.3)
 # Assembly service screws remain reachable with the tool cup removed.
 for y,z in [(-14,33),(14,33),(-29,0),(29,0)]:
  body=body.cut(b.cyl([110,y,z],[1,0,0],3.8,2.1))
  receiver=receiver.cut(b.cyl([109.9,y,z],[1,0,0],3.8,4.3))
 definitions=[('A13-IF-301-recessed-carrier',body,'motor_side_collar'),
  ('A13-IF-302-dorsal-cover',cover,'removable_dorsal_shell'),
  ('A13-IF-303-face-insert',panel,'replaceable_connector_space_insert'),
  ('A13-IF-304-tool-pocket',receiver,'dummy_tool_side_receiver'),
  ('A13-IF-305-tool-pocket-cover',cap,'dummy_tool_pocket_cap')]
 for d in [76.1,76.2,76.3]:definitions.append((f'A13-IF-G-ring-{d:.1f}',b.ring([0,0,0],[1,0,0],42,d/2,3),'fit_coupon'))
 parts=[];shapes={}
 for id,s,role in definitions:
  s=clean(s);shapes[id]=s;m=fit.mesh(s);step=OUT/'step'/(id+'.step');cq.exporters.export(s,str(step));m.export(OUT/'stl-object'/(id+'.stl'))
  R=np.array([[0,0,-1],[0,1,0],[1,0,0]],float)
  if role=='removable_dorsal_shell':R=np.eye(3)
  bed=m.copy();bed.vertices=bed.vertices@R.T;T=-bed.bounds[0];bed.apply_translation(T);bedfile=OUT/'print-bed'/(id+'.stl');bed.export(bedfile)
  assert m.is_watertight and m.is_winding_consistent and max(bed.extents)<230
  parts.append(record(id,s,role,step_sha256=sha(step),object_stl_sha256=sha(OUT/'stl-object'/(id+'.stl')),print_stl_sha256=sha(bedfile),
   volume_mm3=s.Volume(),bbox_mm=m.bounds.tolist(),centroid_mm=list(s.Center().toTuple()),print_size_mm=bed.extents.tolist(),print_rotation=R.tolist(),print_translation_mm=T.tolist()))
  print('PART',id,np.round(bed.extents,2),flush=True)
 hardware=[];hs=[]
 def hw(id,s,note):
  s=clean(s);hardware.append(record(id,s,'nominal_purchased_hardware',note=note));hs.append((id,s))
 def bolt(id,p,d,L,washer,n=(1,0,0),button=False):
  p=np.array(p);n=np.array(n);D,H=(7,4) if d==4 else ((5.7,1.65) if button else (5.5,3))
  hw(id,b.cyl(p-n*L,n,d/2,L).fuse(b.cyl(p,n,D/2,H)),f'M{d}x{L} nominal; no tightening specification')
  hw(id+'-washer',b.ring(p-n*washer,n,4.4 if d==4 else 3.5,2.15 if d==4 else 1.6,washer),'Nominal flat washer')
 def nut(id,x,y,z,d):
  D,H=(8.083,3.2) if d==4 else (6.351,2.4)
  hw(id,hexa([x,y,z],[1,0,0],D,H).cut(b.cyl([x-.1,y,z],[1,0,0],d/2,H+.2)),f'M{d} captive nut; print fit required')
 hw('IF02-dowel',b.cyl([62.7,24,0],[1,0,0],1.5,6),'Inherited internal D3x6 pin; physical retention pending')
 hw('IF02-tool-key',b.cyl([107,0,31],[1,0,0],1.5,8),'D3x8 unique tool clock pin; trial retention measured/bonded')
 for k in range(3):
  a=math.radians(30+120*k);y,z=22.5*math.cos(a),22.5*math.sin(a)
  bolt(f'IF02-core-M4-{k}',[77.5,y,z],4,20,.8);nut(f'IF02-core-nut-{k}',57.7,y,z,4)
 for k in range(4):
  a=math.radians(45+90*k);y,z=36*math.cos(a),36*math.sin(a)
  bolt(f'IF02-tool-M4-{k}',[136.8,y,z],4,35,.8);nut(f'IF02-tool-nut-{k}',106,y,z,4)
 for i,y in enumerate([-14,14]):
  bolt(f'IF02-roof-front-{i}',[110.5,y,33],3,10,.5);nut(f'IF02-roof-front-nut-{i}',103.2,y,33,3)
 for i,y in enumerate([-10,10]):
  bolt(f'IF02-roof-rear-{i}',[84,y,40.5],3,10,.5,n=(0,0,1),button=True)
  hw(f'IF02-roof-rear-nut-{i}',hexa([84,y,34],[0,0,1],6.351,2.4).cut(b.cyl([84,y,33.9],[0,0,1],1.5,2.6)),'M3 nut loaded via side chute')
 for i,y in enumerate([-29,29]):
  bolt(f'IF02-panel-{i}',[110.5,y,0],3,12,.5);nut(f'IF02-panel-nut-{i}',98.7,y,0,3)
 checks=[]
 def overlap(s,t):
  op=BRepAlgoAPI_Common(s.wrapped,t.wrapped)
  if op.IsDone():
   if op.Shape().IsNull():return 0,'common_empty'
   result=cq.Shape.cast(op.Shape());assert result.isValid()
   return sum(q.Volume() for q in result.Solids()),'common'
  # Coplanar mating faces can defeat Common. Verify both exact BREP cuts agree;
  # never classify a failed kernel operation as clearance.
  diffs=[]
  for a,z in [(s,t),(t,s)]:
   cut=BRepAlgoAPI_Cut(a.wrapped,z.wrapped);assert cut.IsDone()
   if cut.Shape().IsNull():diffs.append(a.Volume());continue
   result=cq.Shape.cast(cut.Shape());assert result.isValid()
   diffs.append(a.Volume()-sum(q.Volume() for q in result.Solids()))
  assert abs(diffs[0]-diffs[1])<.001,diffs
  assert min(diffs)>-.001,diffs
  return max(0,*diffs),'bidirectional_exact_cut'
 def check(id,s,jid,t,**kw):
  v,method=overlap(s,t)
  checks.append(dict(a=id,b=jid,volume_mm3=v,method=method,**kw))
 assembly=[(p['id'],shapes[p['id']]) for p in parts if p['role']!='fit_coupon']
 for i,(id,s) in enumerate(assembly):
  for jid,t in assembly[i+1:]:check(id,s,jid,t)
  for jid,t in hs:check(id,s,jid,t)
 # Pinned motor and inherited core are exact solids; new additions rotate with J7.
 fixed=[]
 for id in ['A13-J7-101-bearing-housing','A13-J7-102-bearing-retainer','A13-J7-105-carrier']:fixed.append((id,load(CORE,id)))
 vp=ROOT/'work/arm-a10/vendor/J7-stator.step';sources[str(vp.relative_to(ROOT))]=sha(vp);fixed.append(('actual-RS00-stator',cq.importers.importStep(str(vp)).val()))
 inherited=[]
 for id in ['A13-J7-103-output-journal','A13-J7-104-inner-spacer']:inherited.append((id,load(CORE,id)))
 inherited.append(('A13-IF-107-piloted-flange',load(PREV,'A13-IF-107-piloted-flange')))
 for q in [-90,-45,0,45,90]:
  for id,s in assembly:
   for jid,t in fixed:check(id,s.rotate([0,0,0],[1,0,0],q),jid,t,J7_deg=q)
 for id,s in assembly:
  for jid,t in inherited:check(id,s,jid,t)
 # Connector envelopes are checked separately, so uncertainties are visible.
 for i,(id,s) in enumerate(volumes):
  for jid,t in volumes[i+1:]:check(id,s,jid,t,connector_envelope=True)
  for jid,t in assembly:check(id,s,jid,t,connector_envelope=True)
 # Insert removal and tool removal, after removing the stated screws/cup.
 for travel in [0,10,25]:
  for id in ['A13-IF-303-face-insert','A13-IF-304-tool-pocket','A13-IF-305-tool-pocket-cover']:
   for jid in ['A13-IF-301-recessed-carrier','A13-IF-302-dorsal-cover']:
    check(id,shapes[id].translate([travel,0,0]),jid,shapes[jid],removal_dx_mm=travel)
 for travel in [0,10,30]:check('cover-lift',cover.translate([0,0,travel]),'carrier',body,cover_lift_dz_mm=travel)
 # Nominal straight drivers and straight wire exits; no flexible bend is asserted.
 tools=[]
 for i,y in enumerate([-14,14]):
  tools.append((f'cover-driver-front-{i}',b.cyl([113.6,y,33],[1,0,0],1.6,35)))
 for i,y in enumerate([-10,10]):tools.append((f'cover-driver-rear-{i}',b.cyl([84,y,42.3],[0,0,1],1.25,35)))
 for i,y in enumerate([-29,29]):tools.append((f'panel-driver-{i}',b.cyl([113.6,y,0],[1,0,0],1.6,35)))
 for k in range(4):
  a=math.radians(45+90*k);tools.append((f'tool-driver-{k}',b.cyl([140.9,36*math.cos(a),36*math.sin(a)],[1,0,0],2,35)))
 for name,s in tools:
  for id,t in assembly:
   # Rear cover screw drivers require the tool cup removed.
   service_driver=name.startswith(('cover-driver','panel-driver'))
   if service_driver and id in ['A13-IF-304-tool-pocket','A13-IF-305-tool-pocket-cover']:continue
   check(name,s,id,t,tool_access=True,requires_tool_removed=service_driver)
 for p in ports:
  x,y,z=p['wire_exit_budget_origin_mm'];r=1.55 if p['id'].startswith('CAM') else 2.5
  rod=b.cyl([x,y,z],[1,0,0],r,18)
  check(p['id']+'-straight-wire-exit',rod,'dummy-cup',receiver)
  check(p['id']+'-straight-wire-exit',rod,'dummy-cap',cap)
 clock=[];pin=dict(hs)['IF02-tool-key']
 for a in [0,90,180,270]:
  v,_=overlap(receiver.rotate([0,0,0],[1,0,0],a),pin)
  clock.append(dict(clock_deg=a,key_overlap_mm3=v))
 assert clock[0]['key_overlap_mm3']<.05 and all(p['key_overlap_mm3']>.05 for p in clock[1:]),clock
 bad=[p for p in checks if p['volume_mm3']>.05]
 audit=dict(scope='Recessed manual mechanical fit, nominal hardware and conservative housing envelopes. No full head or dynamic harness',checks=checks,overlaps=bad,clock_checks=clock,physical_trial_pass=False)
 (OUT/'fit-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
 assert not bad,bad[:20]
 # Supplier PDFs stay in ignored work; publish dimension facts and source hashes only.
 connectors=[]
 for name,pn,dimensions in [('AMK21A-103Z5-Y.pdf','AMK21A-103Z5-y',[19.8,9.6,21.8]),('AMS11A-103Z5-Y.pdf','AMS11A-103Z5-y',[25.23,9.1,10.55])]:
  p=ROOT/'work/arm-a13/tool-if02/vendor'/name;assert p.exists();sources[str(p.relative_to(ROOT))]=sha(p)
  connectors.append(dict(part_number=pn,source_url='https://products.rosenberger.com/_ocassets/db/'+name,source_sha256=sha(p),nominal_full_body_dimensions_mm=dimensions,
    geometry='Conservative full housing box, no original supplier mesh',complete_mating_datum=False,retention_released=False))
 interface=dict(revision='TOOL-IF02',ports=ports,connectors=connectors,
  mechanical=dict(motor='RS00 unchanged',axis='+X',original_motor_attachment_unchanged=True,core_interface_plane_x_mm=65.7,
   tool_interface_plane_x_mm=110,outer_tool_pilot=dict(OD_mm=76,ID_mm=54,length_mm=2,mating_outer_bore_mm=76.3,depth_mm=2.2),
   tool_bolts='4 M4x35 with 0.8 washer, PCD72, 45+90k deg; all dummy cup layers included',
   core_bolts='Original 3 M4x20, PCD45, 30+120k; nominal 0.8 mm tip clearance to original retainer',
   centre_opening_mm=54,body_front_x_mm=112,dummy_tool_front_x_mm=136,max_nominal_outer_diameter_mm=88,
   hollow_motor=False,tool_index_key=dict(pin='D3x8',yz_mm=[0,31],male_bore_mm=3.1,female_bore_mm=3.3,retention='Measured/bonded trial; no released press fit')),
  service=dict(sequence=['Remove four tool M4 and slide dummy tool cup +X','Unplug manually; connectors are not blind-mate qualified','Remove two front axial and two rear vertical M3 cover screws, lift dorsal cover +Z','Remove two M3 face-insert screws and withdraw insert +X'],
   rear_side_entry='X70..85, Y-46..-24, Z+/-7; placeholder passage after motor; no dynamic route claimed',
   camera_wire='Straight OD3.1 exits only; no R75 dynamic bend inside wrist',power_control_voltage_pinout_pending=True,live_power=False,
   head_rear_pocket_required='Dummy tool cup represents needed space, not final petal head geometry',
   control_insert='CAN-size reference allocation; EtherCAT/RJ45 module must be rechecked with actual PN before adoption'))
 (OUT/'interface.json').write_text(json.dumps(interface,indent=2)+'\n')
 manifest=dict(revision='TOOL-IF02',parts=parts,hardware=hardware,allocations=blocks,source_hashes=sources,
  source_native_public=str((PREV/'A13-TOOL-IF01.blend').relative_to(ROOT)),source_native_public_sha256=sha(PREV/'A13-TOOL-IF01.blend'),
  source_native_actual='work/arm-a13/tool-if01/actual-RS00-tool-interface.blend',source_native_actual_sha256=sha(ROOT/'work/arm-a13/tool-if01/actual-RS00-tool-interface.blend'),
  preserve_arm_joint_centres=True,tool_plane_shift_from_IF01_mm=44.3,whole_arm_TCP_updated=False,qualification='Supported unpowered mechanical trial; complete connectors/dynamic cable not released')
 (OUT/'manifest.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n');audit['manifest_sha256']=sha(OUT/'manifest.json')
 (OUT/'fit-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
 with (OUT/'parts.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['id','role','quantity','bed_x_mm','bed_y_mm','bed_z_mm'])
  for p in parts:w.writerow([p['id'],p['role'],1,*[round(v,2) for v in p['print_size_mm']]])
 print('PASS',len(parts),'closed print meshes',len(checks),'local checks',flush=True)
if __name__=='__main__':main()
