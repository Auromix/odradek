#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Dimension/load screening only. Does not modify LINK01 or generate CAD."""
from pathlib import Path
import csv, hashlib, json, math
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
SOURCE=ROOT/'docs/engineering/sources/r5-slider-hardware01.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
src=json.loads(SOURCE.read_text())
for f,h in src['input_hashes'].items():assert sha(ROOT/f)==h,(f,'changed;review inputs')
link=json.loads((ROOT/'engineering/generated/r5-link01/study.json').read_text())
witness=json.loads((ROOT/'engineering/generated/r5-link01/common90-contact-witness.json').read_text())
F=next(x for x in witness if x['assumed_mu']==.4)['slider_force_including_actual_contact_sign_and_minusZ_material_gravity_N']
rows=[]
for c in src['candidates']:
 for ratio in ([1] if c['id']=='A' else [1,2]):
  p=c['lead_mm']*.001
  for name,v in [('LINK01_quintic',.150),('proposed_7segment_only',.04/(.10+.10+.10))]:
   rows.append(dict(candidate=c['id'],stock_PN=c['exact_stock_PN'],motion=name,motor_to_screw_ratio=ratio,lead_mm=c['lead_mm'],slider_peak_mm_s=v*1000,screw_peak_rpm=v/p*60,motor_peak_rpm=v/p*60*ratio,common90_F_N=F,ideal_screw_static_Nm=F*p/(2*math.pi),ideal_motor_static_Nm=F*p/(2*math.pi*ratio),required_static_kappa_for_motor_budget0p140=F*p/(2*math.pi*ratio*.140),moving_torque_if_eta0p9_Nm=F*p/(2*math.pi*ratio*.9),catalog_3500_floor_speed_only_pass=v/p*60<=3500,static_and_motion_release=False))
with (OUT/'operating-points.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
# Pure shaft mode and Euler calculations from KSS A815/816; deliberately use170mm
# even though final fixed/supported bearing center span should be shorter.
shaft=[]
for c in src['candidates']:
 d=c['root_diameter_mm']*.001;L=.170;E=2.08e11;rho=7850;A=math.pi*d*d/4;I=math.pi*d**4/64
 for label,lam,n in [('fixed_supported',3.927,2),('fixed_free',1.875,.25)]:
  shaft.append(dict(candidate=c['id'],support_assumption=label,span_mm=L*1000,root_mm=d*1000,critical_allowable_rpm_with_factor0p8=.8*60/(2*math.pi)*lam**2*math.sqrt(E*I/(rho*A))/L**2,buckling_N_with_factor0p5=.5*n*math.pi**2*E*I/L**2,yield_screen_N=98e6*A,scope='uniform root shaft only; ignores local journal bending, real support compliance, recirculator and high acceleration'))
# Conservative material-volume proxies, NOT supplier masses or tolerance maxima.
# Entire nominal screw lies in d9.5 cylinder; nut fits complete flange cylinder.
masses=[]
for c in src['candidates']:
 for L in [c['stock_total_length_mm'],130]:
  d=.0095;l=L*.001;m=7850*math.pi*d*d/4*l;J=m*d*d/8
  mn=7850*math.pi*(c['nut_flange_nominal_outer_diameter_mm']*.001)**2/4*(c['nut_overall_axial_length_mm']*.001)
  masses.append(dict(candidate=c['id'],shaft_total_mm=L,shaft_full_enclosing_cylinder_steel_mass_kg=m,shaft_full_enclosing_cylinder_J_kg_m2=J,nut_full_flange_cylinder_steel_mass_kg=mn,condition='nominal envelope,assumed uniform7850kg/m3,no bracket/locknut/coupler/fasteners; not catalogmass or manufactured upper tolerance bound'))
# common90 rod resultants about slider center. Compression pushes slider back.
row=next(x for x in witness if x['assumed_mu']==.4);force=np.zeros(3);moment=np.zeros(3)
phis={'UR':35,'UL':145,'LL':225,'LR':315};detail=[]
for b in row['branches']:
 fid=b['finger'];kind='upper' if fid[0]=='U' else 'lower';p=link['parameters'][kind];phi=math.radians(phis[fid]);er=np.array([math.cos(phi),math.sin(phi),0]);ez=np.array([0.,0.,1.]);q=math.pi/2;psi=p['phase_rad']+q;u=p['root_radius_mm']-p['slider_ear_radius_mm']+p['crank_mm']*math.cos(psi);w=math.sqrt(p['rod_mm']**2-u*u);fz=b['slider_axial_contribution_N'];ff=-fz*(u/w*er+ez);rr=.02*er;mm=np.cross(rr,ff);force+=ff;moment+=mm;detail.append(dict(finger=fid,pin_m=rr.tolist(),force_on_slider_N=ff.tolist(),moment_Nm=mm.tolist()))
assert abs(force[2]+F)<1e-9
assert abs(np.linalg.norm(force[:2])-row['slider_lateral_reaction_magnitude_N'])<1e-9
spacing=.035;guideforce=-force.copy();guideforce[2]=0
# Moments of the rod forces are cancelled by differential transverse guide forces.
reaction_top=guideforce/2+np.array([-moment[1]/spacing,moment[0]/spacing,0]);reaction_bottom=guideforce-reaction_top
resid=moment+np.cross(np.array([0.,0.,spacing/2]),reaction_top)+np.cross(np.array([0.,0.,-spacing/2]),reaction_bottom)
assert np.linalg.norm(resid)<1e-9
# Collinear load nominal layout lower footprint budgets: not collision proof.
geometry=dict(selected_short_screw_total_mm=130,original_A_total_mm=170,nominal_direct_train_length_mm=90.8+13+(23-2*6.5)+130,original_A_direct_train_length_mm=90.8+13+(23-2*6.5)+170,nominal_direct_train_formula='motor+encoder L1 + motor shaft13 + coupling tip gap(23-2*6.5) + screw total; excludes tolerance/cables/cover/front stroke structure',thread_clearance_A_mm=80-16-40,thread_clearance_B_mm=79-28-40,guide_rail_mm=115,guide_block_center_distance_mm=35,guide_block_total_span_mm=35+28.9,guide_remaining_end_margins_each_mm=(115-(35+28.9)-40)/2,proposed_parallel_motor_screw_min_axis_distance_mm=16+17.5+1,parallel_bare_width_lower_mm=16+(16+17.5+1)+17.5,parallel_case='rectangular MSU width35 andmotorOD32,1mm nominal gap along width; excludes pulley/cover/camera; not an assembled CAD certificate',catalog_common_support_guide_mass_kg=(50+32+2*16)/1000+.38*.115)
result=dict(revision='R5-SLIDER-HARDWARE01',source_sha256=sha(SOURCE),script_sha256=sha(__file__),input_hashes=src['input_hashes'],static_point_scope=row['scope'],operating_points=rows,shaft_screens=shaft,nominal_mass_inertia_proxies=masses,common90_guide=dict(pin_forces=detail,rod_resultant_N=force.tolist(),rod_moment_about_slider_center_Nm=moment.tolist(),transverse_guide_reaction_N=guideforce.tolist(),two_blocks_separation_mm=35,block_positiveZ_reaction_N=reaction_top.tolist(),block_negativeZ_reaction_N=reaction_bottom.tolist(),moment_balance_residual_Nm=resid.tolist(),screw_antirotation_torque_ideal_Nm=F*.0025/(2*math.pi),scope='this112mm sphere/mu.4/SF2 only; assumes guide force plane through slider center. Real guide offset/fasteners/crossloads/friction and screw reaction torque distribution must be checked'),geometry_budgets=geometry,manufacturing_release=False,grasp_2kg_certified=False)
(OUT/'budget.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'F':F,'geometry':geometry,'shaft':shaft,'guide':result['common90_guide'],'mass':masses},indent=2))
