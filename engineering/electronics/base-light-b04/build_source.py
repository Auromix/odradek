#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Original four-net front indicator module; geometry contract is explicit."""
from pathlib import Path
import json,csv,hashlib
D=Path(__file__).resolve().parent
URL='https://www.we-online.com/components/products/datasheet/150120AS75000.pdf'
def dump(f,v):(D/f).write_text(json.dumps(v,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
components=[];pins=[]
for i,u,net,label in [(1,13,'LED_PWR_A','POWER'),(2,25,'LED_RUN_A','RUN'),(3,37,'LED_FAULT_A','FAULT')]:
 ref='D'+str(i);components.append(dict(ref=ref,value=label+' AMBER',MPN='150120AS75000',footprint='WE_150120AS75000',u_mm=u,v_mm=6,side='F',source_url=URL))
 pins.extend([dict(ref=ref,pin='1',name='K',role='passive',net='GND'),dict(ref=ref,pin='2',name='A',role='passive',net=net)])
components.append(dict(ref='J1',value='SOLDER HARNESS',MPN='PCB_FEATURE',footprint='Wire4_Back',u_mm=25,v_mm=2.5,side='B',source_url=''))
for i,n in enumerate(['GND','LED_PWR_A','LED_RUN_A','LED_FAULT_A']):pins.append(dict(ref='J1',pin=str(i+1),name=n,role='passive',net=n))
for i,u in [(1,3),(2,47)]:components.append(dict(ref='H'+str(i),value='M2 NPTH',MPN='PCB_FEATURE',footprint='Mount_M2_R3',u_mm=u,v_mm=6,side='F',source_url=''))
dump('netlist.json',dict(revision='BASE-LIGHT-B04-01',components=components,pins=pins,nets=sorted(set(p['net'] for p in pins))))
with (D/'bom.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=components[0].keys());w.writeheader();w.writerows(components)
with (D/'pin-net.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=pins[0].keys());w.writeheader();w.writerows(pins)
contract=dict(revision='BASE-LIGHT-B04-01',stage='native ECAD/nominal assembly review; not optical or production validation',coordinates=dict(local='u,v,w; PCB bottom w0; physical +u,+v,+w',to_global='x=u-25,y=v+235,z=w+28',native_KiCad='x=u,y=12-v; PCB top F.Cu'),PCB=dict(size_mm=[50,12,1.6],global_min_mm=[-25,235,28],global_max_mm=[25,247,29.6]),mounts=[dict(ref='H'+str(i),uv_mm=[u,6],global_xyz_mm=[u-25,241,28],drill_mm=2.2,keepout_radius_mm=3,requirement='no copper or non-mount component within R3') for i,u in [(1,3),(2,47)]],LEDs=[dict(ref=c['ref'],role=c['value'].split()[0],MPN=c['MPN'],center_uv_mm=[c['u_mm'],6],center_global_xy_mm=[c['u_mm']-25,241],optical_axis=[0,0,1],cathode='left / -u / pin1',land_centers_relative_uv_mm=[[-1.5,0],[1.5,0]],land_size_mm=[1.4,1.6],nominal_body_mm=[3.2,1.6,.68],specified_width_height_max_mm=[1.7,.78],XY_planning_box_mm=[3.4,1.7],solder_planning_mm=.1,body_global_z_mm=[29.7,30.48],source='Wurth p1; length3.2 nominal with general tolerance;3.4 selected planning envelope') for c in components if c['ref'].startswith('D')],window=dict(shape='38x6 capsule; root-owned',global_xy_bbox_mm=[[-19,238],[19,244]],top_z_mm=37,zone_intent='POWER left, RUN middle, FAULT right; not uniformity proof'),harness=dict(type='four backside solder lands; no on-board plug',J1_pads=[dict(pin=str(i+1),net=n,center_uv_mm=[19+4*i,2.5],center_global_xy_mm=[-6+4*i,237.5],size_mm=[2.5,3],layer='B.Cu') for i,n in enumerate(['GND','LED_PWR_A','LED_RUN_A','LED_FAULT_A'])],service_board_ref='base-b04 J3',service_pin_order=['GND','LED_PWR_A','LED_RUN_A','LED_FAULT_A'],mate='JST XHP-4',contacts='4 x SXH-001T-P0.6',wire_target='26AWG stranded, insulation OD1.0..1.5mm; exact wire PN and final cut length not frozen',exit_vector=[0,-1,0],local_reservation_global_min_mm=[-8,225,25],local_reservation_global_max_mm=[8,239.5,28],reservation_status='planning space including solder and wire; not full routed harness or manufacturer bend limit',assembly='solder wires before installing board; mechanical strain relief on lamp box; unplug service J3 before removing lamp module'),electrical=dict(no_onboard_resistors=True,upstream_limit_resistors_ohm=2200,upstream_refs=dict(POWER='R22',RUN='R14',FAULT='R20'),supply_V_nominal=5,nominal_current_at_Vf2_mA=3/2200*1000,conditional_current_upper_bound_mA=5.1/(2200*.99)*1000,current_bound_assumptions='V5<=5.1V measured at board, 2.2k -1%, Vf>=0 and switch drop>=0; not a regulator tolerance proof',brightness='20mA catalogue flux does not rate brightness at ~1.3mA; test actual guide and ambient light'),not_included=['root-owned guide/box/fixing screws','whole harness path or shell interference check','optical cross-talk, photometry, temperature and electrical bench qualification'])
dump('mechanical-interface.json',contract)
source_paths=['connector-contract.json','netlist.json','kicad/base-b04.kicad_sch','kicad/base-b04.kicad_pcb']
dump('upstream-inputs.json',dict(files=[dict(path='../base-b04/'+p,sha256=sha(D.parent/'base-b04'/p)) for p in source_paths],consumption='read-only; front module replaces the earlier external 3mm LED candidate only; service circuit unchanged'))
print('source and mechanical contract ready')
