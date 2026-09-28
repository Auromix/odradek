#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""R5-FOLDED-DRIVE01 read-only-input engineering screen; not production CAD."""
from pathlib import Path
import csv,json,hashlib,math
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(n,v):(OUT/n).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def table(n,v):
 with (OUT/n).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(v[0]));w.writeheader();w.writerows(v)
PITCH=.003;TEETH=30;DP=PITCH*TEETH/math.pi;R=DP/2;BELT=.180;C=(BELT-PITCH*TEETH)/2
N=3200;V=N/60*TEETH*PITCH;TAU=.140;SF=2;LBF=4.4482216152605
M=.078;TMIN=2.4*LBF;speed_kft_min=V*196.8503937/1000
Tcalc=1.21*(TAU*SF)/DP+M*speed_kft_min**2*LBF;T0=max(TMIN,Tcalc);T0HI=1.1*T0
# TC below uses catalogue 3 g / 180 mm mass as a separate conservative dynamic illustration.
TC=.003/BELT*V*V
loads=[]
for T in [TMIN,T0,T0HI,14*LBF]:
 for torque in [TAU,TAU*SF]:
  for rpm in [0,3200]:
   vel=rpm/60*TEETH*PITCH;tc=.003/BELT*vel*vel;delta=torque/R;radial=2*(T+tc)
   z1,z2,zb=3.,35.,22.55
   loads.append(dict(static_tension_per_span_N=T,torque_Nm=torque,rpm=rpm,tension_difference_N=delta,tight_span_N=T+tc+delta/2,slack_span_N=T+tc-delta/2,radial_resultant_N=radial,bearing_rear_radial_N=radial*(z2-zb)/(z2-z1),bearing_front_radial_N=radial*(zb-z1)/(z2-z1),direct_motor_assumed_load_offset_mm=15.05,direct_motor_equal_moment_at5mm_N=radial*15.05/5,scope='equal pulleys, parallel spans, quasi-static elastic equal-tension-split model; no shock/tracking/unknown tension error'))
table('tension-and-bearing-loads.csv',loads)
# Original geometric proxies. These are deliberately not manufacturer weights.
def annulus(OD,ID,L,rho):
 m=math.pi/4*(OD*OD-ID*ID)*L*1e-9*rho
 return m,m*(OD*OD+ID*ID)*1e-6/8
# Entire flanged section treated at max flange diameter. Fairloc slots and teeth not subtracted.
pm1,pj1=annulus(32.2,6,13.5,2700);pm2,pj2=annulus(19.5,6,7.5,2700)
shaft_m,shaft_j=annulus(6,0,48.5,7850);shoulder_m,shoulder_j=annulus(9,0,3,7850)
Jp=pj1+pj2;mp=pm1+pm2;Js=shaft_j+shoulder_j;ms=shaft_m+shoulder_m
Jbelt=.003*R*R;Jcouplings_ref=2*3.4e-7
Jextra=2*Jp+2*Js+Jbelt+Jcouplings_ref
rows=list(csv.DictReader((ROOT/'engineering/generated/r5-motion02/seven_segment-cycle.csv').open()));t=np.array([float(r['t_s']) for r in rows]);n=np.array([float(r['motor_rpm']) for r in rows]);alpha=np.array([float(r['slider_accel_m_s2'])*2*math.pi/.0025 for r in rows]);w=n*2*math.pi/60
base=np.array([float(r['minus_Z_motor_torque_friction_Nm']) for r in rows]);base_ideal=np.array([float(r['minus_Z_motor_torque_ideal_Nm']) for r in rows]);sensitivity=[]
for label,J in [('zero_added',0),('explicit_5e-6',5e-6),('explicit_10e-6',1e-5),('mixed_catalogue_proxy_NOT_bound',Jextra)]:
 torque=base+J*alpha;power=(base_ideal+J*alpha)*w
 sensitivity.append(dict(scenario=label,added_rotating_equivalent_J_kg_m2=J,peak_torque_plus_motor_friction_Nm=float(max(abs(torque))),RMS_torque_plus_motor_friction_Nm=float(np.sqrt(np.trapezoid(torque*torque,t))),ideal_braking_energy_J=float(np.trapezoid(np.maximum(-power,0),t)),additional_peak_kinetic_energy_J=float(.5*J*max(w*w)),scope='adds only stated rotating J; screw, slider, rods, carrier, bearing friction and belt losses absent; not actual installed demand'))
table('added-inertia-sensitivity.csv',sensitivity)
# Nominal folded datums; no current head coordinate transformation is implied.
layout=dict(coordinate='Z from rear cartridge towards screw travel; axes parallel +Z; screw axis X0,Y0; motor axis X45,Y0; millimetres',axis_distance_mm=45,adjustment_design_window_mm=[42,48],pulley_nominal=dict(z_range_mm=[8.5,29.1],hub_range_mm=[8.5,16],belt_pitch_plane_z_mm=22.55,maximum_flange_diameter_mm=32.2,maximum_length_mm=21.0),jackshaft=dict(nominal_z_range_mm=[-3,48.5],pulley_seat_mm=[8.5,29.1],rear_journal_mm=[0,6],front_journal_mm=[32,38],coupling_seat_mm=[42,48.5],nominal_diameter_mm=6,shoulder_diameter_mm=9,shoulder_range_mm=[-3,0],bearing_fit='TBD after rotating ring load/clearance study; not h6 automatically',pulley_and_coupler_fit='6 h6 candidate; Fairloc surface and clamp test pending',axial_retention='rear locating bearing shoulder + unresolved retainer; front bearing floating outer ring; no bearing preload assigned'),bearings_z_ranges_mm=[[0,6],[32,38]],couplers_z_mm=[42,65],motor=dict(shaft_tip_z_mm=58.5,mounting_face_z_mm=71.5,body_rear_z_mm=162.3,body_diameter_mm=32),screw=dict(shaft_tip_z_mm=58.5,diameter4p5_shoulder_z_mm=66.0,thread_M6_start_z_mm=66.0,thread_M6_end_z_mm=73.0,bearing_diameter6_shoulder_z_mm=88.5,end_z_for130request_mm=188.5,end_z_for170stock_mm=228.5,nominal_coupling_insertion_mm=6.5,gap_coupler_to4p5shoulder_mm=1.0,locknut_outer_face_z_mm=None,locknut_note='7.5 mm shaft segment is not verified locknut free-space; actual MSU assembly datum/tool clearance remains open'),reference_rear_cartridge_limit_z_mm=-5,nominal_component_union_width_mm=78.5,nominal_component_union_height_mm=32,nominal_component_union_depth_130_mm=193.5,nominal_component_union_depth_170_mm=233.5,optional_guard_allowance_mm=3,guarded_reference_box_130_mm=[84.5,38,199.5],scope='only listed axial-chain references; excludes rail, nut ear bridge, real supports/retainers/tools/wiring, central camera/display and carrier; not a fitted head envelope')
# KSS primary IGES surfaces: native shaft shoulder -14.5; nut front +7.5.
# Inference assumes the screw shoulder seats on that bearing-pair face.
layout['screw'].update(locknut_outer_face_z_mm=66.5,
 locknut_note='Nominal inference from hashed KSS MSU6C IGES, 130 faces / no solids: shoulder native -14.5, nut front +7.5; assembled gap not tolerance-qualified',
 nominal_coupler_to_locknut_gap_mm=1.5,
 MSU_native_to_local='X=x_native, Y=y_native, Z=74-z_native; surface reference only',
 MSU_body_z_mm=[74,91],MSU_locknut_z_mm=[66.5,71.5],
 MSU_bearing_pair_z_mm=[77,88.5],MSU_collar_z_mm=[71.5,77])
layout['pulley_nominal']['belt_pitch_plane_basis']='planning midpoint of L-minus-hub section; actual flange/face location and tracking are not controlled here'
layout['pulley_nominal']['conservative_load_z_interval_mm']=[16,29.1]
layout['jackshaft'].update(shaft_shoulder_fillet_max_mm=.3,
 shoulder_source='SKF 626-2Z abutment da 8.4..9.4, ra<=0.3; chosen 9 is provisional',
 unsupported_end_coupler_screw_access='TBD; housing and tool not designed')
dump('layout-parameters.json',layout)
nominal_known=.325+.0135+.050+.032+2*.016+.115*.38+4*.0088+.003
mass=dict(known_catalogue_or_typical_subtotal_kg=nominal_known,known_scope='3274, typical IE3, MSU6C/6CS, two MGN9C and115mm rail, four626-2Z, catalogue180mm belt',coupler_max_bore_reference_kg=.0184,not_actual_pair_weight=True,pulley_geometric_proxy_each_kg=mp,jackshaft_geometric_proxy_each_kg=ms,screw130_geometric_proxy_kg=.0723353,nut_geometric_proxy_kg=.082961,illustrative_sum_with_references_and_proxies_kg=nominal_known+.0184+2*mp+2*ms+.0723353+.082961,excluded=['jackshaft housings and motor plate','retainers/fasteners/tension adjustment','covers/cables','custom nut-to-ears plate','four rods/cranks and fingers','camera/display/electronics','actual tolerances/materials/grease variation'],whole_head_mass_kg=None)
inputpaths=['engineering/generated/r5-motion02/study.json','engineering/generated/r5-motion02/seven_segment-cycle.csv','engineering/electronics/r5-slider-hardware01/budget.json']
budget=dict(revision='R5-FOLDED-DRIVE01',license='CC-BY-NC-4.0',required_notice='Odradek — Auromix contributors (https://github.com/Auromix/odradek)',status='one conditional parallel-axis candidate; interfaces and custom supports not released',script_sha256=sha(__file__),input_hashes={s:sha(ROOT/s) for s in inputpaths},ratio=1,belt=dict(catalogue_code='Gates 180-3MGT3-6 / 9400-53250; SDP/SI catalogue-defined A36R53M060060 equivalent GT3',pitch_mm=3,teeth=60,width_mm=6,length_mm=180,catalogue_mass_kg=.003,live_stock_verified=False),pulley=dict(part='SDP/SI A 6D53M030DF0906',quantity=2,teeth=30,pitch_diameter_exact_mm=DP*1000,catalogue_rounded_pitch_diameter_mm=28.7,bore_mm=6,overall_length_mm=20.6,overall_length_tolerance_mm=.4,body_S_mm=12.9,hub_projection_mm=7.5,hub_OD_mm=19.1,hub_OD_tolerance_mm=.4,flange_OD_mm=31.8,flange_OD_tolerance_mm=.4,clamp='M3 Fairloc; part-specific slip torque and tightening value still unverified',mass_kg=None),tension=dict(assumed_static_motor_torque_Nm=TAU,screening_service_factor=SF,design_torque_Nm=TAU*SF,formula='T0=max(minimum,1.21*Qdesign/Dpitch + M*(belt_speed_ft_min/1000)^2*lbf_to_N)',minimum_span_N=TMIN,formula_span_N=Tcalc,proposed_initial_span_screen_interval_N=[T0,T0HI],not_a_released_setting=True,pitch_speed_m_s=V,wrap_each_deg=180,teeth_in_mesh_each=15,maximum_radial_screen_N=2*(T0HI+TC),general_table14lb_per_span_radial_N=28*LBF),belt_capacity_screen=dict(catalogue_30T_3200rpm_base6mm_Nm=1.96,length_factor_180mm=.85,corrected_Nm=1.96*.85,design_torque_Nm=.28,qualification='tabular running torque screen only; no zero-speed holding, reversal fatigue or registration guarantee'),motor_direct_rejection=dict(catalogue_radial_N=50,catalogue_rpm=3000,catalogue_offset_mm=5,proposed_direct_belt_offset_mm=15.05,equal_moment_equivalent_at5mm_N=2*(T0HI+TC)*15.05/5,actual3200rpm_allowance_verified=False,stock_pulley_bore6_fits_motor5=False,stock_pulley_bore6_fits_screw4p5=False,conclusion='direct-stock installation rejected; custom thin pulley cannot inherit this stock part or load approval'),main_load_path='belt -> two independent jackshafts -> four626-2Z -> custom bearing bridge; flexible couplers only transmit torque to motor and supported screw; residual coupling reactions remain',bearing_screen=dict(model='SKF626-2Z',d_D_B_mm=[6,19,6],C_N=2340,C0_N=950,limiting_rpm=40000,catalogue_mass_kg=.0088,rear_center_z_mm=3,front_center_z_mm=35,pulley_load_z_mm=22.55,maximum_rear_N=2*(T0HI+TC)*(35-22.55)/32,maximum_front_N=2*(T0HI+TC)*(22.55-3)/32,scope='nominal static beam reactions only; bearing fit/preload/life/housing deflection excluded'),MSU_boundary='MSU6C still carries screw axial load; direct belt radial reaction removed in ideal main architecture; residual coupling reaction and exact locknut clearance unclosed',layout=layout,mass=mass,extra_inertia=dict(pulley_proxy_each_kg_m2=Jp,jackshaft_proxy_each_kg_m2=Js,belt_equivalent_J_kg_m2=Jbelt,couplings_max_bore_reference_J_kg_m2=Jcouplings_ref,mixed_proxy_total_kg_m2=Jextra,not_an_actual_or_guaranteed_upper_bound=True),inertia_sensitivity=sensitivity,manufacturing_release=False,full_head_fit_confirmed=False,static_hold_0140Nm_guaranteed=False)
budget['MSU_boundary']='MSU6C still carries screw axial load; ideal double-jackshaft path removes belt radial reaction. Primary IGES yields nominal1.5mm coupler/nut gap; tolerances, retention, tool access and residual coupling reaction remain unclosed.'
F=budget['tension']['maximum_radial_screen_N'];a=.01955;b=.01245;l=a+b;E=210e9;I=math.pi*.006**4/64
budget['bearing_screen']['conservative_any_load_within_flanged_section_max_N']=F*max((35-16)/32,(29.1-3)/32)
budget['jackshaft_plain_beam_screen']=dict(span_m=l,load_N=F,assumed_E_Pa=E,
 max_bending_moment_Nm=F*a*b/l,bending_stress_MPa=32*(F*a*b/l)/(math.pi*.006**3)/1e6,
 load_point_deflection_mm=F*a*a*b*b/(3*E*I*l)*1000,
 scope='plain6mm shaft/simply-supported bearings; excludes shoulders, fits, fatigue, torque, carrier deflection and dynamics; not strength approval')
budget['nominal_inline_comparison']=dict(request130_inline_mm=243.8,folded_reference_mm=193.5,reduction_mm=50.3,
 scope='same130mm screw request; folded support rear planning datum-5; real carrier/guard/retention/limits omitted')
dump('budget.json',budget)
assert abs(C-.045)<1e-14 and abs(V-4.8)<1e-12
assert all(r['slack_span_N']>0 for r in loads if r['static_tension_per_span_N']>=T0)
assert budget['bearing_screen']['maximum_front_N']<20
assert budget['motor_direct_rejection']['equal_moment_equivalent_at5mm_N']>50
print(json.dumps({'centre_mm':C*1000,'tension':budget['tension'],'bearing':budget['bearing_screen'],'mass':mass,'added_J':Jextra,'dynamic':sensitivity[-1]},indent=2))
