#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""CD-EC01 schematic/packing candidate; does not create PCB or manufacturing data."""
from pathlib import Path
from collections import defaultdict,Counter
import csv,json,copy,hashlib,math
D=Path(__file__).resolve().parent;ROOT=D.parents[2];FPL=ROOT/'engineering/electronics/final-petal-fpl01/upper'
PIX=ROOT/'engineering/generated/central-display-mount01/led-centres.csv';HW=ROOT/'docs/engineering/sources/central-display-hardware01.json';HEAD=ROOT/'engineering/electronics/head-ctrl02/pin-net.csv'
K=D/'kicad';K.mkdir(exist_ok=True);(K/'checks').mkdir(exist_ok=True)
def save(p,o):p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n')
def csvsave(p,rows):
 with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
base=json.loads((FPL/'netlist.json').read_text());fp=json.loads((FPL/'footprint-constraints.json').read_text());regbase=json.loads((FPL/'register-plan.json').read_text());hw=json.loads(HW.read_text())
raw=list(csv.DictReader(PIX.open()));assert len(raw)==285
# Spatial halves, centre column split lower9/upper10. Native source index remains stable.
groups={k:[] for k in 'AB'}
for p in raw:
 x=float(p['x_mm']);y=float(p['y_mm']);g='A' if x<0 or (x==0 and y<0) else 'B'
 groups[g].append(dict(index=int(p['index']),x_mm=x,y_mm=y,old_driver=p['old_driver'],old_SW=int(p['old_SW']),old_CS=int(p['old_CS'])))
maprows=[]
for g,rows in groups.items():
 xs=sorted({p['x_mm'] for p in rows});ordered=[]
 for j,x in enumerate(xs):ordered+=sorted((p for p in rows if p['x_mm']==x),key=lambda p:p['y_mm'],reverse=bool(j%2))
 for j,p in enumerate(ordered):
  sw,cs=divmod(j,13);dot=18*sw+cs
  maprows.append(dict(p,ref='D'+str(p['index']+1),driver=g,driver_ref='U1' if g=='A' else 'U2',sw=sw,cs=cs,dot_index=dot,dc_address=f'0x{0x100+dot:03X}',pwm_low_address=f'0x{0x200+2*dot:03X}',cathode_pin=1,anode_pin=2))
maprows.sort(key=lambda p:p['index']);assert len({(p['driver'],p['dot_index']) for p in maprows})==285
assert all(p['sw']<=10 and p['cs']<=12 for p in maprows)
comps=[];pins=[];counts=Counter();oldnew={}
common={'GND':'GND','VLED_3V3':'LED_POWER4','VCC_3V3':'3V3_LOGIC','VIO_EN':'LED_VIO','SCLK':'LED_SCK','MOSI':'LED_MOSI','VSYNC':'LED_VSYNC','MISO_HOST':'LED_MISO_BUS','NTC_NODE':'NTC_NODE','NTC_RETURN':'NTC_C'}
# Full per-IC decoupling/VCAP/IFS/SS/MISO; common bus pulldowns and one NTC only once.
for g in 'AB':
 for c0 in base['components']:
  old=c0['ref']
  if old.startswith('D') or old=='J1':continue
  if g=='B' and old in ['C9','R3','R4','R5','R6','R8','R9','TH1']:continue
  c=copy.deepcopy(c0);kind='TH' if old.startswith('TH') else old[0];counts[kind]+=1;ref=kind+str(counts[kind]);oldnew[g,old]=ref
  c.update(ref=ref,selection_status='CD-EC01-schematic-candidate',notes=f'{g}:{old} circuit inherited from FPL-01; no board routing release',projection_rotation_deg=0)
  comps.append(c)
  for p0 in base['pins']:
   if p0['ref']!=old:continue
   p=copy.deepcopy(p0);n=p['net']
   if old=='U1' and p['pin_name'].startswith('CS') and int(p['pin_name'][2:])>12:n=None
   if n:
    n=common.get(n, {'SS_N':'LED_CS4' if g=='A' else 'LED_CS5'}.get(n,g+'_'+n))
   p.update(ref=ref,net=n)
   if p['pin_name']=='VCAP':p['electrical_role']='power_out'
   if p['pin_name']=='ADDR0_MISO':p['electrical_role']='tri_state'
   pins.append(p)
headpins=[p for p in csv.DictReader(HEAD.open()) if p['ref']=='J15'];assert len(headpins)==14
j=copy.deepcopy(next(c for c in base['components'] if c['ref']=='J1'));j.update(ref='J1',manufacturer_part_number='SM12B-GHS-TB(LF)(SN)',value='GH12 side-entry',footprint='JST_GH_12_SIDE',x_mm=0,y_mm=-14,projection_rotation_deg=0,selection_status='CD-EC01-schematic-candidate',notes='CD-HW01 exact mounting-side transform headX=-u,headY=-14+v,headZ=-3-h; catalogue reference not controlled maximum')
comps.append(j)
for p in headpins:pins.append(dict(ref='J1',pin=p['pin'],pin_name=p['pin_name'],net=p['net'],electrical_role='passive'))
# Physically reproducible conservative packing witness; pads AND bodies included.
local={'U1':(0,0),'C1':(0,-7.8),'C2':(0,-10.5),'C3':(-.2,-4.7),'C6':(-4.1,-3.8),'C4':(4.5,2.4),'C7':(4.5,0),'C5':(-1.4,4.7),'C8':(2,4.7),'R1':(-5,4.7),'R2':(-5,7.4),'R7':(.5,7.4)}
shared={'R3':(0,-3),'R4':(0,0),'R5':(0,3),'R6':(0,6),'TH1':(0,10),'R8':(-2,13),'R9':(2,13),'C9':(0,16)}
for g,cx in [('A',-10),('B',10)]:
 for old,(dx,dy) in local.items():
  c=next(c for c in comps if c['ref']==oldnew[g,old]);c.update(x_mm=cx+dx,y_mm=3+dy)
for old,(x,y) in shared.items():
 c=next(c for c in comps if c['ref']==oldnew['A',old]);c.update(x_mm=x,y_mm=y)
led0=next(c for c in base['components'] if c['ref']=='D1')
for p in maprows:
 c=copy.deepcopy(led0);c.update(ref=p['ref'],x_mm=p['x_mm'],y_mm=p['y_mm'],selection_status='CD-EC01-schematic-candidate',notes=f'unchanged source index {p["index"]}; {p["driver"]} SW{p["sw"]}/CS{p["cs"]}',projection_rotation_deg=0);comps.append(c)
 pins.extend([dict(ref=p['ref'],pin='1',pin_name='K',net=f'{p["driver"]}_CS{p["cs"]}',electrical_role='passive'),dict(ref=p['ref'],pin='2',pin_name='A',net=f'{p["driver"]}_SW{p["sw"]}',electrical_role='passive')])
nets=defaultdict(list)
for p in pins:
 if p['net']:nets[p['net']].append(dict(ref=p['ref'],pin=p['pin']))
assert all(len(v)>1 for v in nets.values())
csvsave(D/'bom.csv',comps);csvsave(D/'pin-net.csv',pins);csvsave(D/'pixel-map.csv',maprows)
save(D/'netlist.json',dict(revision='CD-EC01',components=comps,pins=pins,nets=nets,no_connect_pins=[p for p in pins if not p['net']]))
# Do not import superseded GH10 data or unrelated FPL 0.8mm board stack.
for key in ['JST_GH_10_SIDE','routing']:fp.pop(key,None)
fp['JST_GH_12_SIDE']=dict(pads=[dict(pad=p['pad'],xy_mm=p['center_uv_mm'],size_mm=p['size_uv_mm']) for p in hw['connector']['pads']],body_bounds_mount_uv_mm=hw['connector']['header_body_reference_bounds_uv_mm'],source=hw['sources'][0]['url'],status='CD-HW01 catalogue reference dimensions only')
fp['routing']=dict(status='not routed; no PCB generated in CD-EC01',candidate_thickness_mm=1,layer_count_not_frozen=True,continuous_GND_plane_required=True,via_in_pad_under_front_LEDs_requires_filled_capped_process=True)
save(D/'footprint-constraints.json',fp)
for g in 'AB':
 r=copy.deepcopy(regbase);pts=[p for p in maprows if p['driver']==g];installed={p['dot_index'] for p in pts};masks=[0]*33
 for p in pts:masks[3*p['sw']+p['cs']//8]|=1<<(p['cs']%8)
 for op in r['operations']:
  if op['register']=='0x043':op.update(bytes=masks,reason=f'only {len(pts)} fitted CD-EC01 {g} sites enabled')
  if op['register']=='0x100':op.update(bytes=[255 if i in installed else 0 for i in range(198)])
 r.update(revision='CD-EC01',panel=g,installed_LED_count=len(pts),active_CS=list(range(13)),active_SW=list(range(11)),scan_rows_configured=11)
 save(D/f'register-plan-{g}.json',r)
# Packing uses nominal chosen land/body max +.25 XY review margin except fixed GH model.
layout=[]
for c in comps:
 if c['side']=='F':continue
 name=c['footprint'];x=c['x_mm'];y=c['y_mm']
 sizes={'TI_RKP0040B':(5.4,5.4,1.1),'C0603':(2.2,1.0,1.05),'R0603':(2.5,.95,.65),'NTC0603':(2.1,.95,1.05),'C0805':(2.9,1.45,1.55)}
 if name=='JST_GH_12_SIDE':lo=[-9.225,-19.55,-7.45];hi=[9.225,-11.3,-3]
 else:
  w,h,depth=sizes[name];lo=[x-w/2-.25,y-h/2-.25,-3-depth];hi=[x+w/2+.25,y+h/2+.25,-3]
 layout.append(dict(ref=c['ref'],MPN=c['manufacturer_part_number'],footprint=name,center_head_xy_mm=[x,y],side='B',envelope_head_min_mm=lo,envelope_head_max_mm=hi,contains='land/body plus .25mm per-side planning clearance' if name!='JST_GH_12_SIDE' else 'union of supplied mated reference/pads; not max tolerance nor insertion corridor',pad_transform='headX=x-u;headY=y+v;headZ=-3-h'))
pairs=[]
for i,a in enumerate(layout):
 for b in layout[i+1:]:
  gap=[max(a['envelope_head_min_mm'][k]-b['envelope_head_max_mm'][k],b['envelope_head_min_mm'][k]-a['envelope_head_max_mm'][k]) for k in range(2)]
  if max(gap)<-1e-9:pairs.append([a['ref'],b['ref'],gap])
maxr=max(math.hypot(x,y) for a in layout for x in [a['envelope_head_min_mm'][0],a['envelope_head_max_mm'][0]] for y in [a['envelope_head_min_mm'][1],a['envelope_head_max_mm'][1]])
frontmax=max(math.hypot(p['x_mm']+dx,p['y_mm']+dy) for p in maprows for dx in [-1.2,1.2] for dy in [-.45,.45])
mech=dict(revision='CD-EC01',status='component packing witness only; no routing or assembly process release',PCB=dict(diameter_mm=60,thickness_mm=1,head_z_mm=[-3,-2]),back_reserved=dict(radius_mm=28,head_z_mm=[-10,-3]),front_LED=dict(land_body_union_mm=[2.4,.9],package_plus_solder_height_mm=.9,head_z_mm=[-2,-1.1],window_bottom_z_mm=-.5,nominal_optical_gap_mm=.6,max_radius_mm=frontmax,aperture_radius_mm=28.5,aperture_nominal_gap_mm=28.5-frontmax),connector=hw['connector'],components=layout,backpacking=dict(pairs_checked=len(layout)*(len(layout)-1)//2,XY_overlaps=pairs,max_corner_radius_mm=maxr,reserve_radial_gap_mm=28-maxr,min_z_mm=min(a['envelope_head_min_mm'][2] for a in layout)),thermal_bridge_candidate_regions=[dict(center_xy_mm=[x,15],size_mm=[4,4],status='bare component-free rear planning patch; no thermal path or pressure design') for x in [-10,10]],not_covered=['routing feasibility','GH wire fanout/bend/unmating/latch and controlled tolerance','PCB process stackup/warpage','actual solder height','thermal coupling/bridge/metal insulation','assembled part masses','optical diffuser tolerance and luminous uniformity'])
save(D/'mechanical-packing.json',mech)
assert not pairs,pairs
assert maxr<=28 and frontmax<28.5
current={}
for g in 'AB':
 pp=[p for p in maprows if p['driver']==g];rows=Counter(p['sw'] for p in pp)
 current[g]=dict(pixels=len(pp),row_population=[rows[i] for i in range(11)],peak_VLED_A_20mA=max(rows.values())*.02,mean_before_blanking_A_20mA=len(pp)*.02/11,driver_loss_typVF2V_W=(3.3-2)*len(pp)*.02/11,bulk_nominal_uF=44,droop_at8us_44uF_V=max(rows.values())*.02*8/44,droop_at8us_assumed20uF_V=max(rows.values())*.02*8/20)
pow=dict(revision='CD-EC01',voltage_nominal_V=3.3,first_light_mA=3,full_mA_requires_review=20,drivers=current,total_VLED_peak_A_20mA=sum(r['peak_VLED_A_20mA'] for r in current.values()),total_VLED_mean_A_20mA=285*.02/11,VLED_power_W_20mA=3.3*285*.02/11,LED_electrical_power_at_typVF2V_W=2*285*.02/11,logic_planning_W_not_datasheet_max=.1,total_board_planning_W=3.3*285*.02/11+.1,closed_head_thermal_load_including_4petal_baseline_W=2.264+3.3*285*.02/11+.1,total_VLED_peak_A_firstlight=.078,total_VLED_mean_A_firstlight=285*.003/11,GH_single_VLED_contact_rating_A_at_AWG26=1,GH_contact_derating_and_wire_TBD=True,GH_current_utilization_of_catalogue_20mA=.52,voltage_drop_and_dynamic_current_not_measured=True,brightness_multiply='all-full upper bound before blanking; mean scales with DC/CC/MC/global/group/pixel PWM, not temperature proof',thermal='input electrical power is conservative closed-head heat budget; escaping light uncredited; typicalVf is not a driver worst case; no JEDEC thetaJA used as enclosure result',SPI_two_full_frames_bytes=792,SPI_2MHz_payload_fraction_at60Hz=792*8*60/2e6,per_driver_current_tolerance_not_budgeted=True)
save(D/'power-budget.json',pow)
sources=[s for s in json.loads((FPL/'sources.json').read_text())['inherited_circuit_sources']['sources'] if s['id'] not in ['GH','GH-CAD-access']]
save(D/'sources.json',dict(revision='CD-EC01',access_date='2026-09-27',primary_sources=sources,GH12=hw['sources'][:2],inputs={str(p.relative_to(ROOT)):sha(p) for p in [PIX,HW,HEAD,FPL/'netlist.json',FPL/'footprint-constraints.json',FPL/'register-plan.json']},raw_vendor_material_redistributed=False,scope='FPL circuit inheritance rechecked; pin numbering and manufacturer reference dimensions, not released product availability or assembly guarantee'))
save(D/'mapping-revision.json',dict(revision='CD-EC01',authority='pixel-map.csv index/ref/driver/sw/cs/dot_index and generated register plans',source= str(PIX.relative_to(ROOT)),source_sha256=sha(PIX),all_XY_unchanged=True,old_columns_retained_as_history=True,algorithm='A:x<0 or(x=0,y<0); B:others. Within half sort X ascending with alternating Y direction, chunk13 -> SW0..10; ordinal mod13 -> CS0..12.',note='No longer the old sparse circle_0/1 mapping. Pixel index matches input CSV independent of serial/address order.',driver_counts={g:len(rows) for g,rows in groups.items()},previous_FPL_geometry_or_HEAD_files_modified=False))
print('CD-EC01',len(comps),'parts',len(pins),'pins',len(nets),'nets; back',len(layout),'parts; radius',maxr)
