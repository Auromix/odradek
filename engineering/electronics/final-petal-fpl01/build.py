# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""FPL-01 source generation. New mechanical-fit candidate, not fabrication release.
Reuses checked circuit topology, not ULP-02 layout/routing or LED coordinates.
"""
import csv,json,copy,hashlib,math
from pathlib import Path
from collections import defaultdict,Counter
D=Path(__file__).resolve().parent;ROOT=D.parents[2];OLD=ROOT/'engineering/electronics/upper-petal-prototype/ulp02'
FIT=ROOT/'docs/engineering/sources/final-petal-board-fit-analysis.json';fit=json.loads(FIT.read_text())
base=json.loads((OLD/'netlist.json').read_text());fpbase=json.loads((OLD/'footprint-constraints.json').read_text());regbase=json.loads((OLD/'register-plan.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n')
def csvsave(p,rows):
 with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
# mechanical X,Y; theta is the prior generator projection angle after backside flip.
placement={'U1':(56,0,90),'J1':(44.975,0,90),
 'C1':(50,-5.5,180),'C2':(50,-7.8,180),'C3':(50,.2,0),'C6':(50,-1.7,0),
 'C4':(65.2,-1.8,180),'C7':(62.2,-1.8,180),'C5':(63,3.5,180),'C8':(65.8,3.5,180),'C9':(69.8,-5.5,0),
 'R1':(65.3,1.8,180),'R2':(34,0,0),'R3':(37.2,0,0),'R4':(55,7.2,0),'R5':(51.8,7.2,0),
 'R6':(61.4,7.2,0),'R7':(58.2,7.2,0),'R8':(66.8,5.5,0),'R9':(70,5.5,0),'TH1':(66,0,0)}
lower_placement=dict(placement, C4=(68,-3,180), C7=(68,-5.3,180), C5=(67.3,3.8,180), C8=(70.2,5.5,180), C9=(29.5,2.5,0), R1=(36.8,2.5,180), R2=(33.3,0,0), R3=(29.5,0,0), R8=(36.8,-2.5,0), R9=(29.5,-2.5,0))
upper_placement=dict(placement, U1=(80,0,90), C3=(70.5,.2,0), C6=(70.3,-1.7,0), C5=(90,4.2,180), C4=(90,-6.4,180), C7=(93,-6.4,180), C8=(93,-3.5,180), R1=(93,3,180), R3=(85,9,0), R4=(88.2,9,0), R5=(91.4,9,0), R6=(94.6,9,0), R7=(90,-1.8,0), TH1=(93,0,0), R8=(96,0,0), R9=(99,0,0), C9=(102,0,0))
mountpads=[{'pad':i+1,'xy_mm':[-5.625+1.25*i,1.85],'size_mm':[.6,1.7]} for i in range(10)]+[{'pad':'M1','xy_mm':[-7.475,-1.35],'size_mm':[1,2.7]},{'pad':'M2','xy_mm':[7.475,-1.35],'size_mm':[1,2.7]}]
source=next(s for s in fit['manufacturer_sources'] if s['id']=='JST-GH')
interface={'revision':'FPL-01','status':'engineering candidate; catalogue references, no controlled tolerance or mated vendor CAD',
 'header':'SM10B-GHS-TB(LF)(SN)','housing':'GHR-10V-S','terminal':'SSHL-002T-P0.2','source':source,
 'mounting_side_frame':'u right, v up in JST mounting-side drawing; header pin1 upper-left; wire exit -v',
 'header_body_uv_bounds_mm':[[-7.875,-2.45],[7.875,1.6]],'mated_reference_uv_bounds_mm':[[-7.875,-5.55],[7.875,1.6]],
 'mount_pads':mountpads,'footprint_origin_mechanical_xyz_mm':[44.975,0,3.6],
 'transform':'X=44.975+v; Y=u; Z=3.6-h, h away from mounting PCB face',
 'native_transform':'mechanical LED/global PCB mapping Xboard=X, Yboard=40-Y; native front footprint (u,-v), then KiCad Flip LEFT_RIGHT and -90 degree orientation',
 'mated_reference_xyz_bounds_mm':[[39.425,-7.875,-.75],[46.575,7.875,3.6]],
 'land_mechanical_xy_bounds_mm':[[42.275,-7.975],[47.675,7.975]],
 'projected_pads':[dict(p,mechanical_xy_mm=[44.975+p['xy_mm'][1],p['xy_mm'][0]],mechanical_size_xy_mm=list(reversed(p['size_mm']))) for p in mountpads],
 'wire_exit_mechanical_direction':[-1,0,0],'unknowns':['controlled dimensional tolerances','wire exit z and bend radius','mating/unmating translation/access','true latch/mated CAD','supplier crimp qualification'],
 'thermal_bridge_candidate':{'bare_backside_region_xy_mm':[[62,-7],[66,-3]],'PCB_bottom_z_mm':3.6,'metal_floor_z_mm':1.9,'gap_mm':1.7,'size_mm':[4,4],'status':'no components/paste/signal copper/vias inside B-side region; B-side GND copper under mask, six-layer board with reserved In2 GND reference; exact 0.8mm fabrication stackup unconfirmed. Insulating bridge material/compression/metal pedestal not designed; no direct IC pressure.'},
 'high_capacitor_recesses_candidate':[{'ref':r,'center_xy_mm':list(placement[r][:2]),'plan_envelope_xy_mm':[[placement[r][0]-1.7,placement[r][1]-.975],[placement[r][0]+1.7,placement[r][1]+.975]],'package_height_max_mm':1.45,'solder_height_assumption_mm':.1,'assembled_bottom_z_mm':2.05,'floor_z_for_025_gap_mm':1.8} for r in ['C1','C2']],
 'assembly_height_plan_A':{'PCB_z_mm':[3.6,4.4],'front_package_max_mm':.8,'solder_height_assumption_mm':.1,'LED_top_z_mm':5.3,'diffuser_bottom_z_mm':6,'mix_gap_mm':.7,'outer_face_z_mm':6.6,'not_included':'PCB/fixture/insulator/solder/optics tolerance and deflection; original pocket is unchanged'},
 'four_petal_baseline_W':2.264,'thermal_validation':'not measured'}
save(D/'mechanical-interface-candidate.json',interface)
for typ in ['UPPER','LOWER']:
 out=D/typ.lower();out.mkdir(exist_ok=True);(out/'kicad/checks').mkdir(parents=True,exist_ok=True)
 panel=fit['boards'][typ];dots=[];active_placement=upper_placement if typ=='UPPER' else lower_placement
 for i,p in enumerate(panel['candidate_grid']['dots'],1):
  sw=p['sw_provisional'];xs=sorted({v['x'] for v in panel['candidate_grid']['dots'] if v['sw_provisional']==sw});ix=xs.index(p['x'])
  if typ=='UPPER':
   cs=7*ix+int((p['y']+12)/4) if ix<2 else 14+int((p['y']+4)/4) if ix==2 else (15 if p['y']<0 else 17)
  else:
   if sw==0 and p['x']<38:cs=10 if p['x']==30 else 11
   else:
    ix=sorted(x for x in xs if x>=38).index(p['x'])
    cs=5*ix+int((p['y']+8)/4) if ix<2 else 10+int((p['y']+4)/4)
  dots.append({'ref':f'D{i}','x_mm':p['x'],'y_mm':p['y'],'sw':sw,'cs':cs,'side':'F','rotation_deg':0,'cathode_pin':1,'anode_pin':2,'dot_index':18*sw+cs,'dc_address':f'0x{0x100+18*sw+cs:03X}','pwm_low_address':f'0x{0x200+2*(18*sw+cs):03X}'})
 assert len(dots)==(130 if typ=='UPPER' else 42)
 assert len({p['dot_index'] for p in dots})==len(dots)
 comps=copy.deepcopy([c for c in base['components'] if not c['ref'].startswith('D')]);pins=copy.deepcopy([p for p in base['pins'] if not p['ref'].startswith('D')])
 active_cs={p['cs'] for p in dots};active_sw={p['sw'] for p in dots}
 for p in pins:
  if p['ref']=='U1' and p['pin_name'].startswith(('CS','SW')):
   n=p['pin_name'];p['net']=n if int(n[2:]) in (active_cs if n.startswith('CS') else active_sw) else None
 for c in comps:
  x,y,rot=active_placement[c['ref']];c.update(x_mm=x,y_mm=y,projection_rotation_deg=rot,selection_status='FPL01-engineering-candidate-not-released')
  if c['ref']=='J1':c.update(manufacturer_part_number='SM10B-GHS-TB(LF)(SN)',value='10pin GH side-entry',footprint='JST_GH_10_SIDE',notes='Bottom; projection theta+90; originX44.975; mated-body centerX43; wire exit root -X; catalogue reference only')
 ctemplate=next(c for c in base['components'] if c['ref']=='D1')
 for p in dots:
  c=copy.deepcopy(ctemplate);c.update(ref=p['ref'],x_mm=p['x_mm'],y_mm=p['y_mm'],projection_rotation_deg=0,notes=f'FPL-01 {typ}; SW{p["sw"]}/CS{p["cs"]}; fit-study coordinates unchanged',selection_status='FPL01-engineering-candidate-not-released');comps.append(c)
  pins.extend([{'ref':p['ref'],'pin':'1','pin_name':'K','net':f'CS{p["cs"]}','electrical_role':'passive'},{'ref':p['ref'],'pin':'2','pin_name':'A','net':f'SW{p["sw"]}','electrical_role':'passive'}])
 nets=defaultdict(list)
 for p in pins:
  if p['net']:nets[p['net']].append({'ref':p['ref'],'pin':p['pin']})
 assert all(len(v)>1 for v in nets.values())
 assert len({(p['ref'],p['pin']) for p in pins})==len(pins)
 csvsave(out/'bom.csv',comps);csvsave(out/'pin-net.csv',pins);csvsave(out/'led-placement-reference.csv',dots)
 save(out/'netlist.json',{'revision':'FPL-01','panel':typ,'format':'source pin-level netlist; native XML export separately checked','components':comps,'pins':pins,'nets':dict(nets),'no_connect_pins':[p for p in pins if p['net'] is None]})
 fp=copy.deepcopy(fpbase);del fp['JST_GH_10_TOP'];fp['JST_GH_10_SIDE']={'pads':mountpads,'body_bounds_mount_uv_mm':[[-7.875,-2.45],[7.875,1.6]],'source':source['url'],'status':'catalogue reference verified; native flip must match mechanical-interface-candidate.json; controlled model not obtained'}
 fp['routing']['layers_candidate']=6;fp['routing']['stackup_status']='0.8mm six-layer engineering envelope only; dielectric/copper construction and tolerance must be agreed with fabricator';fp['routing']['contact_reserve']={'replaced':'actual FPL outline/mount and thermal keepouts'};fp['routing']['unresolved']='new board routing/checks; original ULP-02 checks do not apply';save(out/'footprint-constraints.json',fp)
 installed={p['dot_index'] for p in dots};masks=[0]*33
 for p in dots:masks[3*p['sw']+p['cs']//8]|=1<<(p['cs']%8)
 dc=[255 if i in installed else 0 for i in range(198)];reg=copy.deepcopy(regbase);reg.update(revision='FPL-01',panel=typ,installed_LED_count=len(dots),active_CS=sorted(active_cs),active_SW=sorted(active_sw),scan_rows_configured=11)
 for op in reg['operations']:
  if op['register']=='0x043':op.update(bytes=masks,reason=f'only {len(dots)} fitted FPL-01 {typ} sites ON')
  if op['register']=='0x100':op.update(bytes=dc)
 assert sum(bin(x).count('1') for x in masks)==len(dots)
 save(out/'register-plan.json',reg)
 budget=copy.deepcopy(panel['power']);budget.update(board_outline_reference_mm=panel['polygon_xy_mm'],mounts_xy_mm=panel['mounts_xy_mm'],mount_hole_mm=2.4,all_copper_keepout_radius_mm=3.25,mechanical_interface='../mechanical-interface-candidate.json',layers=6,thickness_mm=.8,status='FPL-01 planning; no measurements')
 save(out/'mechanical-power-budget.json',budget);save(out/'mapping-revision.json',{'revision':'FPL-01','panel':typ,'source_sha256':sha(FIT),'source':'docs/engineering/sources/final-petal-board-fit-analysis.json','unchanged_fit_study_XY':True,'SW_groups_unchanged':True,'CS_mapping':'fixed physical Y row plus local column slot; special tip/root sites use spare CS channels; provisional packed-row numbering superseded', 'CS_mapping_changes':[{'ref':new['ref'],'x_mm':new['x_mm'],'y_mm':new['y_mm'],'old_cs_provisional':old['cs_provisional'],'cs':new['cs']} for old,new in zip(panel['candidate_grid']['dots'],dots) if old['cs_provisional']!=new['cs']], 'map':dots})
 fw=(OLD/'build_firmware_example.py').read_text().replace('ULP02','FPL01_'+typ).replace('ulp02','fpl01_'+typ.lower()).replace('113',str(len(dots))).replace('ULP-02','FPL-01')
 (out/'build_firmware_example.py').write_text(fw)
 save(out/'sources.json',{'inherited_circuit_sources':json.loads((OLD/'sources.json').read_text()),'connector':source,'input_hashes':{str(p.relative_to(ROOT)):sha(p) for p in [FIT,OLD/'netlist.json',OLD/'footprint-constraints.json',OLD/'register-plan.json']},'checked':'FPL01 replaces GH entry and mapping, not claiming previous native checks apply'})
 print(typ,len(comps),'parts',len(pins),'pins',len(nets),'nets')
