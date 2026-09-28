#!/usr/bin/env python3
"""R5-HEAD-SERVO01: reproduce electrical demand; does not modify mechanical inputs.
SPDX-License-Identifier: CC-BY-NC-4.0
Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""
from pathlib import Path
import csv, hashlib, json, math
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
IN=ROOT/'engineering/generated/r5-link01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(n,o):(OUT/n).write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n')
def table(n,rows):
 with (OUT/n).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def trap(y,t):return sum((a+b)*(tb-ta)/2 for a,b,ta,tb in zip(y[:-1],y[1:],t[:-1],t[1:]))
rows=list(csv.DictReader((IN/'cycle.csv').open()));t=[float(r['t_s']) for r in rows]
p=.0025;J=4.808e-6;C0=.00204;Cv=.000000924;Kt=.0281;Rll=.253
cycle=[]
for r in rows:
 v=float(r['slider_velocity_mm_s'])/1000;a=float(r['slider_accel_mm_s2'])/1000;F=float(r['empty_force_minusZ_N'])
 omega=2*math.pi*v/p;alpha=2*math.pi*a/p;n=omega*60/(2*math.pi)
 tau=F*p/(2*math.pi)+J*alpha
 fr=(C0+Cv*abs(n))*(1 if v>0 else -1 if v<0 else 0)
 cycle.append(dict(t_s=float(r['t_s']),slider_z_mm=float(r['slider_z_mm']),motor_rpm=n,omega_rad_s=omega,alpha_rad_s2=alpha,empty_force_minusZ_N=F,ideal_motor_torque_Nm=tau,estimated_motor_friction_Nm=fr,torque_with_motor_friction_Nm=tau+fr,ideal_shaft_power_W=tau*omega,power_with_motor_friction_W=(tau+fr)*omega,catalogue_equivalent_current_A=(tau+fr)/Kt))
table('cycle-demand.csv',cycle)
P=[r['ideal_shaft_power_W'] for r in cycle];Pf=[r['power_with_motor_friction_W'] for r in cycle];tau=[r['ideal_motor_torque_Nm'] for r in cycle];tf=[r['torque_with_motor_friction_Nm'] for r in cycle]
Ep=trap([max(x,0) for x in P],t);Er=-trap([min(x,0) for x in P],t)
base=dict(peak_rpm=max(abs(r['motor_rpm']) for r in cycle),peak_alpha_rad_s2=max(abs(r['alpha_rad_s2']) for r in cycle),ideal_peak_Nm=max(map(abs,tau)),ideal_rms_Nm=math.sqrt(trap([x*x for x in tau],t)),ideal_positive_work_J=Ep,ideal_braking_work_J=Er,ideal_positive_peak_W=max(P),ideal_braking_peak_W=-min(P),with_catalogue_motor_friction_peak_Nm=max(map(abs,tf)),with_catalogue_motor_friction_rms_Nm=math.sqrt(trap([x*x for x in tf],t)),with_catalogue_motor_friction_positive_work_J=trap([max(x,0) for x in Pf],t),with_catalogue_motor_friction_braking_work_J=-trap([min(x,0) for x in Pf],t),motor_friction_energy_J=trap([b-a for a,b in zip(P,Pf)],t),rotor_plus_encoder_peak_kinetic_energy_J=.5*J*(2*math.pi*3600/60)**2,encoder_channel_frequency_Hz=1024*3600/60,encoder_quadrature_edges_per_s=4096*3600/60,motor_electrical_frequency_Hz=2*3600/60)
contact=[]
for r in csv.DictReader((IN/'common90-contact-summary.csv').open()):contact.append(r)
# Catalogue torque-equivalent only: neither vendor's phase-current normalization is inferred.
static=[]
for k in [1,.9,.8161558193794077,.7,.5]:
 T=.1142618147131171/k;Ieq=(T+C0)/Kt
 static.append(dict(static_transfer_kappa_assumed=k,shaft_hold_torque_Nm=T,catalogue_equivalent_current_A=Ieq,conditional_copper_W_if_Ieq_is_phase_amplitude=.75*Rll*Ieq**2,conditional_copper_W_if_Ieq_is_phase_RMS=1.5*Rll*Ieq**2,scope='112mm sphere only; mu .4 and SF2; current convention UNRESOLVED; not current-setting instruction'))
table('hold-sensitivity.csv',static)
regen=[]
for C in [.001,.0047,.01]:
 regen.append(dict(assumed_C_F=C,assumed_initial_bus_V=24,assumed_return_energy_J=Er,result_bus_V=math.sqrt(24**2+2*Er/C),scope='whole-cycle braking energy deliberately lumped into one event; not worst-case stop sizing; no losses or other loads'))
table('regen-capacitor-sensitivity.csv',regen)
summary=dict(revision='R5-HEAD-SERVO01',license='CC-BY-NC-4.0',required_notice='Odradek — Auromix contributors (https://github.com/Auromix/odradek)',status='engineering candidates; not energized wiring/manufacturing release',requirements={'empty_close_open_close_s':1,'slider_travel_mm':40,'leg_time_s':.5,'priority_objects':'boxes and bottles/cans, approximately 50–120 mm grasp width','range_load_bound_completed':False},model={'motor':'3274G024BP4','encoder':'IE3-1024 L','direct_screw_lead_mm':2.5,'motor_encoder_inertia_kg_m2':J,'known_four_petal_material_mass_kg':.242488036745,'gravity_head':'minus Z','motor_friction_model':'C0 + Cv*abs(rpm); applied against velocity; zero at exactly zero speed; estimate only','C0_Nm':C0,'Cv_Nm_per_rpm':Cv,'excluded':['screw/coupler inertia','slider/rod/crank/hinge mass and friction','new electronics and fasteners','actual screw efficiency','gripped-object dynamics','motor current-normalization calibration','temperature rise and actual thermal installation'],'catalogue_Kt_Nm_per_A':Kt,'Kt_phase_RMS_or_amplitude':'not established by the retrieved primary text; do not compare derived A directly with Elmo phase RMS','R_phase_to_phase_ohm_at22C':Rll},demand=base,conditional_contact={'object':'112mm sphere center Z65 at four q90 finite faces','friction_mu_assumed':.4,'force_design_factor':2,'payload_kg':2,'slider_force_N':287.171262149,'ideal_hold_input_Nm':.1142618147131171,'static_transfer_needed_if_net_shaft_torque_budget_Nm_014':.1142618147131171/.140,'not_whole_50_120mm_range_bound':True},regeneration={'whole_cycle_braking_energy_J':Er,'min_C_F_for_lumped_energy_24_to28V':2*Er/(28**2-24**2),'actual_regen_solution':'TBD; supply sink/chopper/capacitor must be validated, not TVS-only','stop_energy_bound':'TBD after all inertia, load orientation and stop path'},native_network={'joint_slaves':7,'head_servo_slaves':1,'head_io_slaves':1,'total':9,'note':'assumes existing separate head I/O slave; not old 4-servo or P16 architecture'},inputs=[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in [IN/'study.json',IN/'cycle.csv',IN/'common90-contact-summary.csv',IN/'direct-screw-dynamic-sensitivity.csv']],generated_by='engineering/electronics/r5-head-servo01/build.py')
summary['reference_braking_work_J_finer_R5_LINK01_grid']=.8407698102076219
summary['braking_work_reintegration_error_J']=base['ideal_braking_work_J']-.8407698102076219
assert abs(summary['braking_work_reintegration_error_J'])<1e-4
assert abs(base['peak_rpm']-3600)<1e-8
assert abs(Ep-Er)<1e-10
dump('study.json',summary)
print(json.dumps(base,indent=2))
