#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""B04 service PCB source contract. No firmware; no arm power routing."""
from pathlib import Path
import json,csv,math
D=Path(__file__).resolve().parent
C=[];P=[]
URL={
 'TI':'https://www.ti.com/lit/ds/symlink/lm5164.pdf',
 'EVM':'https://www.ti.com/lit/pdf/SNVU620',
 'MC2':'https://www.phoenixcontact.com/en-gb/products/pcb-header-mc-15-2-g-381-1803277',
 'MC4':'https://www.phoenixcontact.com/en-nl/products/pcb-header-mc-15-4-g-381-1803293',
 'MC2mate':'https://www.phoenixcontact.com/us/products/1803578/pdf',
 'MC4mate':'https://www.phoenixcontact.com/en-us/products/pcb-plug-mc-15-4-st-381-1803594',
 'XH':'https://www.jst-mfg.com/product/pdf/eng/eXH.pdf',
 'OPTO':'https://www.vishay.com/docs/83430/vo617a.pdf',
 'PNP':'https://assets.nexperia.com/documents/data-sheet/BC856_BC857_BC858.pdf',
 'RECT':'https://www.st.com/resource/en/datasheet/stps1h100.pdf',
 'FUSE':'https://www.littelfuse.com/~/media/electronics/datasheets/fuses/littelfuse_fuse_451_453_datasheet.pdf.pdf',
 'TVS':'https://m.littelfuse.com/~/media/electronics/datasheets/tvs_diodes/littelfuse_tvs_diode_smbj_datasheet.pdf.pdf',
 'L':'https://www.coilcraft.com/pdfs/mss1246t.pdf',
 'R':'https://www.yageo.com/upload/media/product/productsearch/datasheet/rchip/PYu-RC_Group_51_RoHS_L.pdf',
 'C22':'https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=CGA6P3X7R1E226M250AE',
 'C220':'https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C1608C0G1H221J080AA',
 'CAP':'https://product.tdk.com/en/search/capacitor/ceramic/mlcc' ,
 'D4148':'https://www.vishay.com/docs/86455/1n4148ws.pdf',
 'LED':'https://www.we-online.com/components/products/datasheet/151031YS06000.pdf'}
def add(ref,value,mpn,fp,uv,rot,pins,source,height,body,notes=''):
 C.append(dict(ref=ref,qty=1,value=value,MPN=mpn,footprint=fp,u_mm=uv[0],v_mm=uv[1],rotation_ccw_deg=rot,height_mm=height,body_mm=body,source_url=URL.get(source,source),notes=notes,status='B04 fabrication-review candidate; not bench validated'))
 for i,t in enumerate(pins):
  if isinstance(t,str):num,name,net,role=str(i+1),str(i+1),t,'passive'
  else:num,name,net,role=t
  P.append(dict(ref=ref,pin=str(num),name=name,net=net,role=role))
def r(ref,value,mpn,uv,net1,net2,rot=0,fp='R0603'):
 add(ref,value,mpn,fp,uv,rot,[net1,net2],'R',.65 if fp=='R0603' else .7,[1.6,.85] if fp=='R0603' else [3.2,1.6] if fp=='R1206' else [6.3,3.2])
def c(ref,value,mpn,uv,n1,n2,rot=0,fp='C0603',h=.9):
 add(ref,value,mpn,fp,uv,rot,[n1,n2],'https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no='+mpn,h,[1.7,.9] if fp=='C0603' else ([3.7,2.8] if mpn=='CGA6P3X7R1E226M250AE' else [3.6,2.8]), 'TDK catalogue maximum body including size tolerance; dielectric DC-bias/loss under actual conditions still requires bench validation')
add('J1','20-55V SERVICE','1803277','MC2',[8,12],0,['VIN_RAW','GND'],'MC2',7.25,[9.2,9.01],'mate1803578; insertion towards+u; removal-u; not motor power')
add('J2','24V isolated status','1803293','MC4',[8,25],0,['FIELD_RUN_P','FIELD_RUN_N','FIELD_FAULT_P','FIELD_FAULT_N'],'MC4',7.25,[9.2,16.63],'mate1803594; each channel has independent return; no MCU GPIO direct connection')
add('J3','REMOTE LEDS','S4B-XH-A(LF)(SN)','XH4',[73,21],0,['GND','LED_PWR_A','LED_RUN_A','LED_FAULT_A'],'XH',6.1,[11.7,12.4],'mateXHP-4; four SXH-001T-P0.6 contacts; externally mounted bare LEDs, max3mA/channel')
add('F1','250mA 125VDC','0451.250MRL','F2410',[17,12],0,['VIN_RAW','VIN_FUSED'],'FUSE',2.6,[6.1,2.69],'50A interrupt @125VDC is component data; prospective branch fault current must be <=50A; upstream protected branch required')
add('D1','100V reverse block','STPS1H100A','SMA',[25,12],180,[('1','K','VIN_DIODE','passive'),('2','A','VIN_FUSED','passive')],'RECT',2.45,[4.6,2.95])
r('R1','10R 1W','RC2512FK-0710RL',[24,18],'VIN_DIODE','VIN_PROT',0,'R2512')
add('D2','58V standoff TVS','SMBJ58A','SMB',[17,18],90,[('1','K','VIN_PROT','passive'),('2','A','GND','passive')],'TVS',2.44,[4.57,3.94],'transient candidate only; not regeneration absorber; published clamp93.6V leaves limited100V margin; actual overshoot test required')
c('C1','2.2u 100V','CGA6N3X7R2A225K230AB',[31,17],'VIN_PROT','GND',90,'C1210',2.5)
c('C2','2.2u 100V','CGA6N3X7R2A225K230AB',[31,12],'VIN_PROT','GND',90,'C1210',2.5)
add('U1','LM5164DDAR','LM5164DDAR','TI_DDA8',[39,16],0,[('1','GND','GND','power_in'),('2','VIN','VIN_PROT','power_in'),('3','EN_UVLO','UVLO','input'),('4','RON','RON','input'),('5','FB','FB','input'),('6','PGOOD','PGOOD','open_collector'),('7','BST','BST','power_in'),('8','SW','SW','power_out'),('9','EP','GND','passive')],'TI',1.75,[4.9,3.98])
c('C3','2.2n 50V C0G','C1608C0G1H222J080AA',[45,17.435],'BST','SW',90)
add('L1','68uH shielded','MSS1246T-683MLB','MSS1246T',[54,16],0,['SW','V5'],'L',4.8,[12.3,12.3],'I_sat20%=2.26A; actual loss/temperature not yet measured')
c('C4','22u 25V X7R','CGA6P3X7R1E226M250AE',[64,14],'V5','GND',90,'C1210',2.8)
c('C5','22u 25V X7R','CGA6P3X7R1E226M250AE',[64,19],'V5','GND',90,'C1210',2.8)
r('R2','41.2k','RC0603FR-0741K2L',[34,8],'RON','GND',90)
r('R3','158k','RC0603FR-07158KL',[45,9],'V5','FB')
r('R4','49.9k','RC0603FR-0749K9L',[40,9],'FB','GND')
r('R5','1M','RC0603FR-071ML',[25,6],'VIN_PROT','UVLO')
r('R6','90.9k','RC0603FR-0790K9L',[30,6],'UVLO','GND')
r('R7','220k','RC0603FR-07220KL',[50,6],'SW','RIPPLE')
c('C6','3.3n 100V X7R','CGA3E2X7R2A332K080AA',[55,6],'RIPPLE','V5')
c('C7','220p 50V C0G','C1608C0G1H221J080AA',[45,5],'RIPPLE','FB')
r('R8','47k','RC0603FR-0747KL',[39,24],'V5','PGOOD')
# Each field domain remains galvanically separate from local GND and from the other field return.
for k,(name,v) in enumerate([('RUN',28),('FAULT',39)]):
 n=10+6*k; uref='U'+str(2+k); qref='Q'+str(1+k)
 r('R'+str(n),'1.5k 0.25W','RC1206FR-071K5L',[15,v],f'FIELD_{name}_P',f'FIELD_{name}_MID',0,'R1206')
 r('R'+str(n+1),'1.5k 0.25W','RC1206FR-071K5L',[21,v],f'FIELD_{name}_MID',f'FIELD_{name}_A',0,'R1206')
 add('D'+str(3+k),'opto reverse clamp','1N4148WS-E3-08','SOD323',[21,v+4],0,[('1','K',f'FIELD_{name}_A','passive'),('2','A',f'FIELD_{name}_N','passive')],'D4148',1.1,[1.8,1.35])
 add(uref,'VO617A-3','VO617A-3','DIP4',[27,v],0,[('1','A',f'FIELD_{name}_A','passive'),('2','K',f'FIELD_{name}_N','passive'),('3','E','GND','passive'),('4','C',f'{name}_OC','open_collector')],'OPTO',4.55,[9.91,4.83],'CTR100..200%@IF5mA,VCE5V,25C; use~.45mA output load; temperature/aging test remains')
 r('R'+str(n+2),'10k','RC0603FR-0710KL',[43,v],f'{name}_OC',f'{name}_BASE')
 r('R'+str(n+3),'47k','RC0603FR-0747KL',[49,v+3],f'{name}_BASE','V5')
 add(qref,'BC857B PNP','BC857B,215','SOT23',[50,v],0,[('1','B',f'{name}_BASE','passive'),('2','E','V5','passive'),('3','C',f'{name}_DRIVE','passive')],'PNP',1.1,[3.0,1.4])
 r('R'+str(n+4),'2.2k LED limit','RC0603FR-072K2L',[58,v],f'{name}_DRIVE',f'LED_{name}_A')
r('R22','2.2k LED limit','RC0603FR-072K2L',[66,24],'V5','LED_PWR_A')
# Bare surface test pads have no separately procured part.
for j,(name,uv) in enumerate([('GND',[64,34]),('V5',[69,34]),('VIN_PROT',[35,22]),('PGOOD',[44,24])]):
 add('TP'+str(j+1),name,'PCB_FEATURE','TP',uv,0,[name],URL['TI'],0,[1.5,1.5],'fabricated copper test pad; no purchased component')
for j,uv in enumerate([(5,5),(75,5),(75,45),(5,45)]):add('H'+str(j+1),'M3 NPTH R3.5 clear','PCB_FEATURE','M3',uv,0,[],URL['TI'],0,[7,7],'no copper, no electrical grounding through mount')

def dump(p,x):(D/p).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def csvout(p,rows):
 with (D/p).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
net={}
for p in P:
 if p['net'] is not None:net.setdefault(p['net'],[]).append([p['ref'],p['pin']])
assert all(len(nodes)>1 for nodes in net.values()),[n for n,x in net.items() if len(x)<2]
dump('netlist.json',dict(revision='B04-SERVICE01',components=C,pins=P,nets=net))
csvout('bom.csv',C);csvout('pin-net.csv',P)
dump('sources.json',dict(revision='B04-SERVICE01',checked='2026-09-30',primary_sources=URL,notes='Official catalogues are part evidence, not system qualification; vendor PDFs not redistributed. Footprints authored from dimensional data.',changes=[dict(ref='C3',old='2.2nF X7R ±10%',new='C1608C0G1H222J080AA C0G ±5%; keeps1.5..2.5nF across selected tolerance planning'),dict(ref='C7',old='C1608C0G1H181J080AA 180pF obsolete',new='C1608C0G1H221J080AA 220pF production; TI Eq26 minimum158.2pF'),dict(ref='C4/C5',old='TMK325B7226KMHT non-preferred reference',new='CGA6P3X7R1E226M250AE production; max3.7x2.8x2.8mm'),dict(ref='calculation',issue='initial RON frequency conversion1000x low',fix='source formula now2.5e9 with R inOhm; independent Eq15 kOhm/kHz and volt-second audit')],dimension_evidence=dict(input_caps='TDK max3.6x2.8x2.5mm; land gap2.2, pad1.1x2.5mm',output_caps='TDK max3.7x2.8x2.8mm; same land',U1='TI DDA8 pin9 EP; bodymax5.0x4.0x1.7 and leadspan6.2 reference',XH='JST eXH side-entry4way14.3 projection/6.1 height reference; model reserves7.0 height',MC='Phoenix straight-mated catalogue18.7 projection11.1 height reference')))
buck=dict(Vout_nom=1.2*(1+158/49.9),fsw_Hz=1.2*(1+158/49.9)*2.5e9/41200,L_H=68e-6,RA_Ohm=220e3,CA_F=3.3e-9,CB_F=220e-12)
fs=buck['fsw_Hz'];vo=buck['Vout_nom'];assert 250e3<fs<350e3
# Independent units audit: TI Eq15 R[kOhm]=Vout*2500/f[kHz].
assert abs(fs/1000-vo*2500/41.2)<1e-8
buck['cases']=[dict(Vin=vi,ton_ns=vo/vi/fs*1e9,deltaIL_A=vo*(1-vo/vi)/fs/68e-6,Ipeak_at_025A=.25+vo*(1-vo/vi)/fs/68e-6/2,FB_ripple_V=(vo/vi/fs)*(vi-vo)/(220e3*3.3e-9)) for vi in [18,20,48,55]]
buck.update(CA_min_F=10/(fs*(158e3*49.9e3/(158e3+49.9e3))),CB_min_75us_F=75e-6/(3*158e3),UVLO_on_nom_V=1.5*(1+1e6/90.9e3),UVLO_off_nom_V=1.4*(1+1e6/90.9e3),bootstrap_nom_F=2.2e-9,bootstrap_tolerance_fraction=.05,bootstrap_temp_fraction_planning=.003,bootstrap_min_F=2.2e-9*.95*.997,bootstrap_max_F=2.2e-9*1.05*1.003,input_C_nom_F=4.4e-6,input_hotplug_E_55V_J=.5*4.4e-6*55**2,input_hotplug_I2t_10ohm_A2s=4.4e-6*55**2/20,input_R_loss_at_100mA_W=.1,efficiency_test_threshold_for_2W_input_at_1p25W_out=.625,measured=False)
dump('calculation.json',dict(buck=buck,status_input=dict(V_high_range=[18,30],V_low_max=2,Rs_each=[1500,1500],IF_min_at18V_Vf1p65_mA=(18-1.65)/3030*1000,IF_max30V_Vf0_mA=30/2970*1000,resistor_each_worst30V_W=(30/2970)**2*1515,external_status_power_max_two_W=2*30**2/2970,optocoupler_CTR_margin_not_fulltemperature_guarantee=True),limits=['No 2W current limiter:2W is design/acceptance budget; fuse is250mA,notpowerlimiter','No whole-arm power/regen/stop function','0.25A output only at testpads under supervised bench load; J3 is resistor-limited LED output only','No production or enclosure EMC/temperature qualification']))
# Mechanical bounds to be populated from actual native footprint placements; fixed connector contract.
dump('connector-contract.json',dict(revision='B04-SERVICE01',coordinates='u/v board mm, z=0 PCB bottom; native KiCad x=u,y=50-v',PCB=dict(size_mm=[80,50,1.6],origin_assembly_mm=[-40,-2,23]),connectors=[dict(ref='J1',pin1_uv=[8,12],pin_step_uv=[0,3.81],pins=['48V_SERVICE','RETURN'],removal_vector=[-1,0,0],header_uv_box=[[0,9.4],[9.2,18.41]],mated_uv_box=[[-9.5,9.4],[9.2,18.41]],mated_z_mm=[1.6,12.7],through_pin_lowest_z_mm=-1.8,plug='1803578',retention='friction only; harness strain relief required'),dict(ref='J2',pin1_uv=[8,25],pin_step_uv=[0,3.81],pins=['RUN+','RUN-','FAULT+','FAULT-'],removal_vector=[-1,0,0],header_uv_box=[[0,22.4],[9.2,39.03]],mated_uv_box=[[-9.5,22.4],[9.2,39.03]],mated_z_mm=[1.6,12.7],through_pin_lowest_z_mm=-1.8,plug='1803594',retention='friction only; harness strain relief required'),dict(ref='J3',pin1_uv=[73,21],pin_step_uv=[0,2.5],pins=['LED common cathode GND','POWER anode current-limited','RUN anode current-limited','FAULT anode current-limited'],removal_vector=[1,0,0],header_uv_box=[[70.7,18.55],[82.2,30.95]],mated_uv_box=[[70.7,18.55],[87.3,30.95]],mated_z_mm=[1.6,8.6],through_pin_lowest_z_mm=-1.8,plug='XHP-4',contacts='4x SXH-001T-P0.6',retention='XH friction lock; not a latch-released positive lock')],notes=['Connector dimensions are catalogue references; mating housing tolerance not provided as controlled max. Add assembly tolerance margin.','Do not infer externalLED installed geometry from this board package.','mated MC18.7mm total,11.1mm installed height; XH14.3mm assembly projection from PCBpin line,6.1mm height; exact CAD mating verification remains.']))
print('B04',len(C),'components',len(P),'pins',len(net),'nets')
