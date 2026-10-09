# SPDX-License-Identifier: CC-BY-NC-4.0
"""Tool-side mechanical prototype and replaceable electrical space cassette.
mm, J7.rotor coordinates. Connector blocks are design allocations, not CAD.
"""
from pathlib import Path
import sys,json,math,hashlib,csv
import cadquery as cq
import numpy as np
import trimesh

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=HERE/'build'
PREV=HERE.parent/'j7-fit01/build';BASE=ROOT/'engineering/arm_a11/build'
sys.path.insert(0,str(ROOT/'engineering/arm_a11'));import interfaces as c;import collision
import importlib.util
spec=importlib.util.spec_from_file_location('j7_fit_mesh',HERE.parent/'j7-fit01/build.py');fit=importlib.util.module_from_spec(spec);spec.loader.exec_module(fit)
b=c.legacy;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def box(p,s):return cq.Solid.makeBox(*s,b.V(p))
def finish(s):
 s=s.clean().fix();assert s.isValid() and len(s.Solids())==1;return s
def hexagon(p,n,d,h):return cq.Workplane(b.plane(p,n)).polygon(6,d).extrude(h).val()
def mesh_record(id,s,role,**data):
 m=fit.mesh(s);return dict(id=id,frame='J7.rotor',role=role,vertices_mm=m.vertices.tolist(),triangles=m.faces.tolist(),**data)

def main():
 for name in ['step','stl-object','print-bed']: (OUT/name).mkdir(parents=True,exist_ok=True)
 old=json.loads((PREV/'manifest.json').read_text());source_hashes={str((PREV/'manifest.json').relative_to(ROOT)):sha(PREV/'manifest.json')}
 def load(name):
  path=PREV/'step'/(name+'.step');p=next(p for p in old['parts'] if p['id']==name)
  assert sha(path)==p['step_sha256'];source_hashes[str(path.relative_to(ROOT))]=sha(path)
  return cq.importers.importStep(str(path)).val()
 flange=load('A13-J7-106-detachable-flange')
 flange=flange.fuse(b.cyl([65.7,0,0],[1,0,0],9,2))
 flange=b.drill(flange,[62.7,24,0],[1,0,0],3.1,3.1)
 receiver=b.cyl([65.7,0,0],[1,0,0],30,11)
 receiver=receiver.cut(b.cyl([65.6,0,0],[1,0,0],9.15,2.3))
 receiver=b.drill(receiver,[65.6,24,0],[1,0,0],3.3,4.1)
 for k in range(3):
  a=math.radians(30+120*k);receiver=b.drill(receiver,[65.6,22.5*math.cos(a),22.5*math.sin(a)],[1,0,0],4.5,11.2)
 # Captive nut access from the top; mounting screws do not pierce the flange.
 for y in [-14,14]:
  receiver=receiver.fuse(b.cyl([69.2,y,24],[1,0,0],4,7.5))
  receiver=b.drill(receiver,[69.1,y,24],[1,0,0],3.5,7.7)
  receiver=receiver.cut(hexagon([70.2,y,24],[1,0,0],6.8,2.5))
  receiver=receiver.cut(box([70.2,y-3.4,24],[2.5,6.8,18]))

 tray=box([76.7,-42,27],[68,84,2.5])
 tray=tray.fuse(box([76.7,-25,18],[4,50,13.5]))
 for y in [-42,37.5]:tray=tray.fuse(box([80.7,y,29.5],[64,4.5,26]))
 for y in [-14,14]:tray=b.drill(tray,[76.6,y,24],[1,0,0],3.5,4.2)
 for y in [-14,14]:tray=tray.cut(b.cyl([80.6,y,24],[1,0,0],3.7,.7))
 # Panel slides from above into two guide grooves; it is captured by the lid.
 for y in [-39.15,37.5]:tray=tray.cut(box([96.55,y,29.5],[3.3,1.65,26.1]))
 for x in [86.7,133.7]:
  for y in [-40,40]:
   tray=tray.fuse(b.cyl([x,y,49],[0,0,1],4,6.5))
   tray=b.drill(tray,[x,y,48],[0,0,1],3.5,7.6)
   tray=tray.cut(hexagon([x,y,48.9],[0,0,1],6.8,3.5))
 # Four independent tie locations downstream of the mated connector budgets.
 for y in [-28.5,-9.5,9.5,26.5]:
  for x in [137.7,141.7]:tray=tray.cut(box([x,y-4,26.9],[2,8,2.7]))
 panel=box([96.7,-39,29.8],[3,78,25.4])
 ports=[
  dict(id='PWR',y=-28.5,z=41,opening=[14,16],budget=[40,12,13],candidate='Molex Micro-Fit 3.0 4-circuit family',function='Tool supply; voltage, current, contacts and pinout not released'),
  dict(id='CTRL',y=-9.5,z=40.5,opening=[18,18],budget=[48,16,16],candidate='Replaceable locking CAN insert or RJ45-size EtherCAT insert',function='Control only; protocol/PN/pinout not frozen; not ordinary LAN'),
  dict(id='CAM_UP',y=9.5,z=41,opening=[14,16],budget=[56,12,14],candidate='Independent 50-ohm GMSL coax assembly',function='Upper fisheye video/return control; PoC conditional on actual camera chain'),
  dict(id='CAM_DOWN',y=26.5,z=41,opening=[14,16],budget=[56,12,14],candidate='Independent 50-ohm GMSL coax assembly',function='Lower fisheye video/return control; PoC conditional on actual camera chain')]
 volumes=[]
 for p in ports:
  w,h=p['opening'];panel=panel.cut(box([96.6,p['y']-w/2,p['z']-h/2],[3.2,w,h]))
  length,width,height=p['budget'];start=[106.7-length/2,p['y']-width/2,p['z']-height/2]
  p.update(budget_origin_mm=start,frame='J7.rotor',budget_kind='Design allocation only; no exact supplier fit qualification',unplug_budget_dx_mm=25,
           latch_access='Lid removed; open-top probe budget above Z55.5',part_number_frozen=False)
  volumes.append((p,box(start,[length,width,height])))
 # Faceted removable cover, broader at its edge and tapered on top.
 profile=[(-44,-32),(-40,-34),(40,-34),(44,-32),(44,32),(40,34),(-40,34),(-44,32)]
 # XY plane coordinates are offset to cassette centre; axial X extent 76.7..144.7.
 poly=[(110.7+v,y) for y,v in profile]
 lid=cq.Workplane('XY').workplane(offset=55.5).polyline(poly).close().extrude(2.5).val()
 for x in [86.7,133.7]:
  for y in [-40,40]:lid=b.drill(lid,[x,y,55.4],[0,0,1],3.5,2.7)
 definitions=[('A13-IF-107-piloted-flange',flange,'modified_rotor_flange'),
  ('A13-IF-201-tool-receiver',receiver,'tool_side_fit_receiver'),
  ('A13-IF-202-service-tray',tray,'non_load_cassette_fit'),
  ('A13-IF-203-replaceable-panel',panel,'connector_opening_space_prototype'),
  ('A13-IF-204-service-cover',lid,'removable_cosmetic_cover_fit')]
 for diameter in [18.2,18.3,18.4]:definitions.append((f'A13-IF-G-pilot-{diameter:.1f}',b.ring([0,0,0],[1,0,0],14,diameter/2,4),'fit_coupon'))
 parts=[];shapes={}
 for id,s,role in definitions:
  s=finish(s);shapes[id]=s;m=fit.mesh(s);step=OUT/'step'/(id+'.step');cq.exporters.export(s,str(step));m.export(OUT/'stl-object'/(id+'.stl'))
  rotation=np.array([[0,0,1],[0,1,0],[-1,0,0]],float) if role in ['modified_rotor_flange','tool_side_fit_receiver'] else np.eye(3)
  if role in ['connector_opening_space_prototype','fit_coupon']:rotation=np.array([[0,0,-1],[0,1,0],[1,0,0]],float)
  bed=m.copy();bed.vertices=bed.vertices@rotation.T;translation=-bed.bounds[0];bed.apply_translation(translation);bedfile=OUT/'print-bed'/(id+'.stl');bed.export(bedfile)
  assert m.volume>0 and max(bed.extents)<230
  parts.append(mesh_record(id,s,role,step_sha256=sha(step),object_stl_sha256=sha(OUT/'stl-object'/(id+'.stl')),print_stl_sha256=sha(bedfile),
   volume_mm3=s.Volume(),bbox_mm=m.bounds.tolist(),print_size_mm=bed.extents.tolist(),print_rotation=rotation.tolist(),print_translation_mm=translation.tolist()))
  print('PART',id,np.round(bed.extents,2),flush=True)
 hardware=[];hardware_shapes=[]
 def hw(id,s,note):
  s=finish(s);hardware.append(mesh_record(id,s,'nominal_purchased_hardware',note=note));hardware_shapes.append((id,s))
 hw('IF-dowel-3x6',b.cyl([62.7,24,0],[1,0,0],1.5,6),'Steel D3x6 dowel; prototype retention measured/bonded, no released press-fit')
 def fastener(id,p,n,d,L,washer_t):
  p=np.array(p,float);n=np.array(n,float);headD,headH=(7,4) if d==4 else (5.5,3)
  hw(id,b.cyl(p-n*L,n,d/2,L).fuse(b.cyl(p,n,headD/2,headH)),f'Nominal M{d}x{L} socket screw, not tightening specification')
  hw(id+'-washer',b.ring(p-n*washer_t,n,4.4 if d==4 else 3.5,2.15 if d==4 else 1.6,washer_t),'Nominal flat washer')
 for k in range(3):
  a=math.radians(30+120*k);y,z=22.5*math.cos(a),22.5*math.sin(a)
  fastener(f'IF-tool-M4-{k+1}',[77.5,y,z],[1,0,0],4,20,.8)
  hw(f'IF-tool-nut-{k+1}',hexagon([57.7,y,z],[1,0,0],8.083,3.2).cut(b.cyl([57.6,y,z],[1,0,0],2,3.4)),'M4 rear captive nut; original flange stations')
 for i,y in enumerate([-14,14],1):
  fastener(f'IF-tray-M3-{i}',[81.2,y,24],[1,0,0],3,12,.5)
  hw(f'IF-tray-nut-{i}',hexagon([70.2,y,24],[1,0,0],6.351,2.4).cut(b.cyl([70.1,y,24],[1,0,0],1.5,2.6)),'M3 nut loaded from receiver top chute')
 for i,(x,y) in enumerate((x,y) for x in [86.7,133.7] for y in [-40,40]):
  fastener(f'IF-cover-M3-{i+1}',[x,y,58.5],[0,0,1],3,10,.5)
  hw(f'IF-cover-nut-{i+1}',hexagon([x,y,50],[0,0,1],6.351,2.4).cut(b.cyl([x,y,49.9],[0,0,1],1.5,2.6)),'M3 nut inserted from beneath side boss before cover')

 assembly=[(p['id'],shapes[p['id']]) for p in parts if p['role']!='fit_coupon']
 checks=[]
 def check(a,s,bname,t,**data):
  v=collision.volume(collision.common_solids(s,t));checks.append(dict(a=a,b=bname,volume_mm3=v,**data))
 for i,(id,s) in enumerate(assembly):
  for jid,t in assembly[i+1:]:check(id,s,jid,t)
 # Fasteners model nominal thread cores, so solid shanks must clear every owned print.
 for id,s in assembly:
  for name,t in hardware_shapes:check(id,s,name,t)
 # Local rotating additions against the fixed bearing cartridge and actual stator.
 fixed=[]
 for id in ['A13-J7-101-bearing-housing','A13-J7-102-bearing-retainer','A13-J7-105-carrier']:fixed.append((id,load(id)))
 vendor=ROOT/'work/arm-a10/vendor/J7-stator.step';source_hashes[str(vendor.relative_to(ROOT))]=sha(vendor)
 fixed.append(('actual-RS00-stator',cq.importers.importStep(str(vendor)).val()))
 for q in [-90,-45,0,45,90]:
  for id,s in assembly:
   for jid,t in fixed:check(id,s.rotate([0,0,0],[1,0,0],q),jid,t,J7_deg=q)
 # Planning blocks plus specified unplug travel with the lid removed.
 for p,s in volumes:
  for travel in [0,12.5,25]:
   for id,t in assembly:
    if id=='A13-IF-204-service-cover':continue
    check(p['id']+'-mated-space',s.translate([travel,0,0]),id,t,unplug_dx_mm=travel)
  # This is an allocated finger/probe region, not a measured latch geometry.
  probe=box([104.7,p['y']-6,49.6],[12,12,25])
  for id,t in assembly:
   if id!='A13-IF-204-service-cover':check(p['id']+'-latch-access-budget',probe,id,t,lid_removed=True)
 tools=[]
 for k in range(3):
  a=math.radians(30+120*k)
  tools.append((f'tool-M4-{k+1}-driver',b.cyl([81.6,22.5*math.cos(a),22.5*math.sin(a)],[1,0,0],2,60)))
 for i,y in enumerate([-14,14],1):tools.append((f'tray-M3-{i}-driver',b.cyl([84.3,y,24],[1,0,0],2,25)))
 for i,(x,y) in enumerate((x,y) for x in [86.7,133.7] for y in [-40,40]):tools.append((f'cover-M3-{i+1}-driver',b.cyl([x,y,61.6],[0,0,1],2,25)))
 for name,tool in tools:
  for id,s in assembly:check(name,tool,id,s,tool_access_budget=True)
 # At the three wrong 120 degree clockings, a single pin must reject fitting.
 pin=hardware_shapes[0][1];clock=[]
 for angle in [0,120,240]:
  v=collision.volume(collision.common_solids(receiver.rotate([0,0,0],[1,0,0],angle),pin))
  clock.append(dict(clock_deg=angle,dowel_overlap_mm3=v))
 assert clock[0]['dowel_overlap_mm3']<=.05 and all(p['dowel_overlap_mm3']>.05 for p in clock[1:])
 bad=[p for p in checks if p['volume_mm3']>.05]
 audit=dict(scope='Local owned interface, nominal fasteners, fixed RS00/cage and planning connector blocks; five roll poses, three unplug samples. No full head, J5/J6, real plugs or dynamic cables',
  checks=checks,overlaps=bad,clock_checks=clock,physical_fit_pending=True)
 (OUT/'fit-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
 assert not bad,bad[:10]
 allocations=[mesh_record(p['id']+'-space-budget',s,'connector_space_allocation',port=p['id']) for p,s in volumes]
 interface=dict(revision='TOOL-IF01',mechanical=dict(frame='J7.rotor',body_flange_plane_x_mm=65.7,receiver_front_x_mm=76.7,receiver_thickness_mm=11,
  flange_OD_mm=60,fasteners='3 M4x20 + 0.8 washer + rear M4 nut on PCD45',angle_start_deg=30,
  pilot=dict(male_OD_mm=18,male_length_mm=2,female_ID_mm=18.3,female_depth_mm=2.2),
  unique_clock_pin=dict(centre_yz_mm=[24,0],pin='D3x6',male_bore_mm=3.1,female_bore_mm=3.3,retention='Physical prototype measurement/bonding; future metal fit separate'),
  load_path='Tool receiver -> three M4 clamp stations / piloted flange -> journal / external bearings -> carrier; no qualification from print',
  independent_of_J7_motor_screws=True),ports=ports,
  service=dict(cover_removal='+Z',connector_panel_removal='+Z after cover removal',unplug='+X, 25mm design budget',
  per_port_strain_relief='Two 2x8 tie windows downstream of the connector budget; use selected cable saddle later',
  local_camera_bend_and_roll='Not solved: do not assume tight bend or hollow RS00',
  power='Separate from motor 48V bus unless matched converter/head is validated; tool supply voltage/current pending',
  video='Two independent coax channels; never on CAN/RJ45 control contacts; PoC only with compatible source/camera',
  control='CAN or EtherCAT chosen with actual head electronics; different removable inserts; no arbitrary RJ45 pinout or STO claim',
  hotplug=False,live_wiring_released=False,exact_connector_retention_released=False))
 (OUT/'interface.json').write_text(json.dumps(interface,indent=2)+'\n')
 manifest=dict(revision='TOOL-IF01',status='unpowered_mechanical_and_connector_space_prototype',parts=parts,hardware=hardware,allocations=allocations,
  source_hashes=source_hashes,previous_native_public=str((PREV/'A13-J7-plastic-fit.blend').relative_to(ROOT)),
  previous_native_public_sha256=sha(PREV/'A13-J7-plastic-fit.blend'),previous_native_actual='work/arm-a13/j7-fit01/actual-RS00-fit.blend',
  previous_native_actual_sha256=sha(ROOT/'work/arm-a13/j7-fit01/actual-RS00-fit.blend'),
  replaces='A13-J7-106-detachable-flange',world_arm_length_unchanged=True,whole_arm_release=False,head_interface_frozen=False)
 (OUT/'manifest.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n');audit['manifest_sha256']=sha(OUT/'manifest.json')
 (OUT/'fit-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
 with (OUT/'parts.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['id','role','quantity','bed_x_mm','bed_y_mm','bed_z_mm'])
  for p in parts:w.writerow([p['id'],p['role'],1,*[round(v,2) for v in p['print_size_mm']]])
 print('PASS',len(parts),'closed print parts',len(checks),'exact local checks',clock,flush=True)

if __name__=='__main__':main()
