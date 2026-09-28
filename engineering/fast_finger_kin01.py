#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""FAST-KIN01: auditable empty-cycle and parametric contact sizing, not a motor rating."""
from pathlib import Path
import csv, hashlib, json, math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['svg.hashsalt']='FAST-KIN01'
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'engineering/generated/fast-finger-kin01'
BASE=ROOT/'engineering/generated/head-mass04/mass-properties.json'
G=9.80665;T=.5;SAMPLES=20001
NOTICE='Odradek — Auromix contributors (https://github.com/Auromix/odradek)'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
integ=lambda y,x:float(np.trapezoid(y,x))
def save(n,d): (OUT/n).write_text(json.dumps(d,indent=2)+'\n')
def csvout(n,rows):
 with (OUT/n).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def profiles(t,delta,kind):
 first=t<=T;u=np.where(first,t,t-T);direction=np.where(first,-1.,1.)
 if kind=='quintic':
  v=u/T;s=10*v**3-15*v**4+6*v**5;sd=(30*v**2-60*v**3+30*v**4)/T;sdd=(60*v-180*v**2+120*v**3)/T**2
 else:
  ta=.1;acc=1/(ta*(T-ta));vm=1/(T-ta)
  s=np.where(u<ta,.5*acc*u**2,np.where(u<=T-ta,.5*acc*ta**2+vm*(u-ta),1-.5*acc*(T-u)**2))
  sd=np.where(u<ta,acc*u,np.where(u<=T-ta,vm,acc*(T-u)))
  sdd=np.where(u<ta,acc,np.where(u<=T-ta,0.,-acc))
 return delta*np.where(first,1-s,s),delta*direction*sd,delta*direction*sdd

def shared_master(fingers,t,gravities):
 """Current route: one dimensionless s, not four controlled actuators."""
 s,sd,sdd=profiles(t,1.,'quintic');rows=[];jointrows=[];plots={};contactrows=[]
 for mapping in ['linear_ratio_example','nonlinear_lower_example']:
  Q0=np.zeros(len(t));Ms=np.zeros(len(t));Cs=np.zeros(len(t));fg=[]
  for f in fingers:
   delta=math.radians(f['range_deg']);lower=f['id'] in ['LL','LR'];k=.25 if mapping.startswith('nonlinear') and lower else 0
   q=delta*(s+k/(2*math.pi)*np.sin(2*math.pi*s));fp=delta*(1+k*np.cos(2*math.pi*s));fpp=-delta*k*2*math.pi*np.sin(2*math.pi*s)
   v=fp*sd;acc=fp*sdd+fpp*sd**2;a=np.array(f['axis']);r=np.array(f['COM_from_pivot_home_m']);rq=np.cos(q)[:,None]*r+np.sin(q)[:,None]*np.cross(a,r)+(1-np.cos(q))[:,None]*(a@r)*a
   J=f['J_axis_kg_m2'];Ms+=J*fp**2;Cs+=J*fp*fpp*sd**2;Q0+=J*acc*fp;fg.append((f,fp,rq));jointrows.append(dict(mapping=mapping,finger=f['id'],peak_speed_deg_s=float(np.degrees(max(abs(v)))),peak_accel_rad_s2=float(max(abs(acc))),fprime_min=float(min(fp)),fprime_max=float(max(fp)),fdoubleprime_abs_max=float(max(abs(fpp)))))
  assert np.max(abs(Q0-(Ms*sdd+Cs)))<1e-12
  for gname,gv in gravities.items():
   Qg=np.zeros(len(t))
   for f,fp,rq in fg:Qg+=(np.cross(rq,f['mass_kg']*np.array(gv))@np.array(f['axis']))*fp
   Q=Q0-Qg;P=Q*sd
   for beta in [90,120,180,360]:
    rad=math.radians(beta);rows.append(dict(mapping=mapping,gravity_head=gname,actuator_type='rotary_master',master_full_stroke_deg=beta,linear_stroke_mm=None,peak_speed_rpm=float(max(abs(rad*sd))*60/(2*math.pi)),peak_speed_mm_s=None,peak_accel_rad_s2=float(max(abs(rad*sdd))),peak_accel_mm_s2=None,peak_torque_Nm=float(max(abs(Q/rad))),RMS_torque_Nm=math.sqrt(integ((Q/rad)**2,t)),peak_axial_force_N=None,RMS_axial_force_N=None,peak_positive_mechanical_power_W=float(max(P)),peak_braking_mechanical_power_W=float(max(-P)),positive_mechanical_work_J=integ(np.maximum(P,0),t),braking_mechanical_work_J=integ(np.maximum(-P,0),t)))
   for stroke in [20,30,50]:
    meter=stroke/1000;rows.append(dict(mapping=mapping,gravity_head=gname,actuator_type='axial_master',master_full_stroke_deg=None,linear_stroke_mm=stroke,peak_speed_rpm=None,peak_speed_mm_s=float(max(abs(stroke*sd))),peak_accel_rad_s2=None,peak_accel_mm_s2=float(max(abs(stroke*sdd))),peak_torque_Nm=None,RMS_torque_Nm=None,peak_axial_force_N=float(max(abs(Q/meter))),RMS_axial_force_N=math.sqrt(integ((Q/meter)**2,t)),peak_positive_mechanical_power_W=float(max(P)),peak_braking_mechanical_power_W=float(max(-P)),positive_mechanical_work_J=integ(np.maximum(P,0),t),braking_mechanical_work_J=integ(np.maximum(-P,0),t)))
   if gname=='minus_Z':plots[mapping]=(Q,Ms,Cs,P)
 # Static necessary four-contact comparison, equal balanced normals; no assertion
 # that the yet-undesigned linkage realizes these lever arms or all four contacts.
 delta_sum=sum(math.radians(f['range_deg']) for f in fingers)
 for mu in [.2,.4,.8]:
  N=2*2*G/(4*mu);Ft=2*2*G/4
  for lever in [.06,.08,.10,.12,.15]:
   Qnormal=N*lever*delta_sum;Qlow=max(0,N*lever-Ft*.03)*delta_sum;Qhigh=(N*lever+Ft*.03)*delta_sum
   for beta in [90,120,180,360]:
    rad=math.radians(beta);contactrows.append(dict(assumed_mu=mu,normal_moment_arm_mm=lever*1000,actuator_type='rotary_master',master_full_stroke_deg=beta,linear_stroke_mm=None,generalized_normal_force_J=Qnormal,normal_component_torque_Nm=Qnormal/rad,total_torque_lower_bound_Nm_assuming_tangent_arm30mm=Qlow/rad,total_torque_upper_at_minimum_normal_Nm_assuming_tangent_arm30mm=Qhigh/rad,normal_component_axial_force_N=None))
   for stroke in [20,30,50]:contactrows.append(dict(assumed_mu=mu,normal_moment_arm_mm=lever*1000,actuator_type='axial_master',master_full_stroke_deg=None,linear_stroke_mm=stroke,generalized_normal_force_J=Qnormal,normal_component_torque_Nm=None,total_torque_lower_bound_Nm_assuming_tangent_arm30mm=None,total_torque_upper_at_minimum_normal_Nm_assuming_tangent_arm30mm=None,normal_component_axial_force_N=Qnormal/(stroke/1000)))
 # Independent example of contact mismatch and elastic branches, normal-only toy.
 spring=[];gaps=np.array([0,.5,1,1.5]);Ntarget=2*2*G/(4*.4);limit=4*Ntarget
 for k in [5,20,100]:
  lo=0.;hi=30.
  for _ in range(80):
   x=(lo+hi)/2
   if sum(k*np.maximum(x-gaps,0))>limit:hi=x
   else:lo=x
  loads=k*np.maximum((lo+hi)/2-gaps,0);needed_x=max(gaps)+Ntarget/k
  spring.append(dict(assumed_branch_stiffness_N_mm=k,assumed_initial_gaps_mm=gaps.tolist(),global_sum_normal_limit_N=limit,closure_travel_at_limit_mm=(lo+hi)/2,branch_forces_at_limit_N=loads.tolist(),contacts_active_at_limit=int(sum(loads>1e-8)),travel_to_reach_target_on_last_contact_mm=needed_x,first_contact_force_when_last_reaches_target_N=k*needed_x,status='illustrative independent normal-compliance model only; not proposed material stiffness or actual contact Jacobian'))
 # Current single-drive conversion and one concrete inertial candidate family.
 electrical=[];drive=[];drive_electrical=[]
 Jinput=4.8e-6+1.96e-7+8e-9 # rotor +3-stage input-with-pinion maximum +encoder
 for mapping,(Q,M,C,P) in plots.items():
  for em,er in [(.7,.5),(.9,.8)]:
   bus=np.where(P>=0,P/em,P*er);positive=integ(np.maximum(bus,0),t);ret=integ(np.maximum(-bus,0),t)
   electrical.append(dict(mapping=mapping,gravity_head='minus_Z',motoring_efficiency_assumed=em,regen_efficiency_assumed=er,positive_energy_J=positive,returned_energy_J=ret,net_average_W_at1Hz=positive-ret,positive_peak_W=float(max(bus)),return_peak_W=float(max(-bus)),only_baseline_finger_inertia=True,stall_copper_and_idle_losses_excluded=True))
  for beta,gear in [(120,66),(180,50),(360,50)]:
   rad=math.radians(beta);Jref=Jinput*gear**2;extraQ=Jref*rad**2*sdd;totalP=(Q+extraQ)*sd;equivalent=(Q+extraQ)/rad
   drive.append(dict(mapping=mapping,gravity_head='minus_Z',motor='3274G024BP4',gearhead='32GPT HT',encoder='IE3-1024L',gear_ratio_for_calculation=gear,master_full_stroke_deg=beta,input_total_J_kg_m2=Jinput,output_referred_additional_J_kg_m2=Jref,peak_motor_speed_rpm=float(max(abs(rad*sd)))*gear*60/(2*math.pi),exceeds_7000rpm_continuous_input=float(max(abs(rad*sd)))*gear*60/(2*math.pi)>7000,exceeds_9000rpm_intermittent_input=float(max(abs(rad*sd)))*gear*60/(2*math.pi)>9000,ideal_peak_motor_equivalent_torque_Nm=float(max(abs(equivalent)))/gear,ideal_RMS_motor_equivalent_torque_Nm=math.sqrt(integ((equivalent/gear)**2,t)),extra_rotor_gear_encoder_peak_kinetic_energy_J=.5*Jref*rad**2*max(sd**2),total_positive_mechanical_work_J=integ(np.maximum(totalP,0),t),total_braking_work_J=integ(np.maximum(-totalP,0),t),total_positive_mechanical_peak_W=float(max(totalP)),total_braking_mechanical_peak_W=float(max(-totalP)),scope='conditional inertia example; gearbox efficiencies/friction and thermal losses absent; rotor-equivalent torque is NOT gearbox output-shaft load; no selected motor claim'))
   assert abs(integ(totalP,t))<1e-10
   for em,er in [(.7,.5),(.9,.8)]:
    bus=np.where(totalP>=0,totalP/em,totalP*er);positive=integ(np.maximum(bus,0),t);ret=integ(np.maximum(-bus,0),t)
    drive_electrical.append(dict(mapping=mapping,gravity_head='minus_Z',master_full_stroke_deg=beta,gear_ratio_for_calculation=gear,input_total_J_kg_m2=Jinput,motoring_efficiency_assumed=em,regen_efficiency_assumed=er,positive_energy_J=positive,returned_energy_J=ret,net_average_W_at1Hz=positive-ret,positive_peak_W=float(max(bus)),return_peak_W=float(max(-bus)),conditional_C_F_24to28V_if_one_cycle_all_return_stored=2*ret/(28**2-24**2),scope='one central drive with motor/gear-input/encoder inertia; hypothetical lumped mechanical-to-bus power conversion; not actual gearbox or motor efficiency; no standstill copper, idle, controller or lighting loss'))
 csvout('single-master-electrical-scenarios.csv',electrical);csvout('single-master-drive-inertia-example.csv',drive);csvout('single-master-drive-electrical-scenarios.csv',drive_electrical)
 csvout('single-master-motion.csv',rows);csvout('single-master-joint-derivatives.csv',jointrows);csvout('single-master-contact.csv',contactrows);save('contact-compliance-example.json',spring)
 fig,axs=plt.subplots(2,2,figsize=(12,7),sharex=True)
 for mapping,arr in plots.items():
  Q,M,C,P=arr
  for ax,y in zip(axs.flat,[Q,M,C,P]):ax.plot(t,y,label=mapping)
 for ax,label in zip(axs.flat,['Generalized drive force Qs [J]','Equivalent inertia Ms [kg m²]','Nonlinear C term [J]','Mechanical power [W]']):ax.set_ylabel(label);ax.grid(alpha=.2)
 axs[0,0].legend(fontsize=8);axs[1,0].set_xlabel('Cycle time [s]');axs[1,1].set_xlabel('Cycle time [s]');fig.suptitle('FAST-KIN01 | CURRENT route: one master coordinate s\nFour linked petals; legacy finger inertia; gravity along head −Z');fig.tight_layout();fig.savefig(OUT/'single-master.svg',metadata={'Date':None});fig.savefig(OUT/'single-master.png',dpi=150);plt.close(fig)
 return dict(active_route='one central motor, four mechanically coupled petals',coordinate='s dimensionless:0 open,1 closed; Qs has units joule per unit s; it is not a physical shaft torque until divided by master angle in radians',linear_map='q_i=Delta_i*s; upperDelta109deg,lower122deg',nonlinear_illustration='upper same; lower q=Delta*(s+0.25*sin(2*pi*s)/(2*pi)); illustration only, not synthesized fourbar',equations=['qdot_i=fprime_i*sdot','qddot_i=fprime_i*sddot+fdoubleprime_i*sdot²','Ms=sum(Ji*fprime_i²)','Qs=Ms*sddot+sum(Ji*fprime_i*fdoubleprime_i)*sdot²-sum(tau_gravity_i*fprime_i)','theta=beta*s => torque=Qs/beta; x=L*s => force=Qs/L'],metadata='Real linkage masses, constraints, singularity and contact Jacobians remain to be synthesized; four fingers do not have independent commanded forces',compliance_examples=spring)

def main():
 OUT.mkdir(parents=True,exist_ok=True);base=json.loads(BASE.read_text());joints={j['id']:j for j in base['finger_joints']};fingers=[]
 for row in base['aggregated_bodies']:
  if row['kinematic_group']!='finger_rotor':continue
  j=joints[row['finger']];a=np.array(j['closing_axis_head']);assert abs(np.linalg.norm(a)-1)<1e-12
  r=np.array(row['com_head_home_m'])-np.array(j['pivot_head_mm'])*.001;m=row['mass_kg'];I=np.array(row['inertia_about_COM_head_axes_kg_m2']);Ij=I+m*((r@r)*np.eye(3)-np.outer(r,r));J=float(a@Ij@a);rp=float(np.linalg.norm(np.cross(a,r)))
  assert not any('P16_envelope' in p for p in row['source'])
  fingers.append(dict(id=row['finger'],mass_kg=m,J_axis_kg_m2=J,COM_from_pivot_home_m=r.tolist(),axis=a.tolist(),COM_perpendicular_radius_m=rp,worst_gravity_Nm=m*G*rp,range_deg=j['range_deg'][1],source_members=row['source']))
 t=np.linspace(0,1,SAMPLES);allseries={};motion=[];kinrows=[];power=[];supply=[]
 gravities={'zero':[0,0,0],'minus_Z':[0,0,-G],'minus_X':[-G,0,0],'minus_Y':[0,-G,0]}
 for kind in ['quintic','trapezoid_ta0p1']:
  signals={}
  for f in fingers:
   delta=math.radians(f['range_deg']);q,v,acc=profiles(t,delta,kind);a=np.array(f['axis']);r=np.array(f['COM_from_pivot_home_m']);rq=np.cos(q)[:,None]*r+np.sin(q)[:,None]*np.cross(a,r)+(1-np.cos(q))[:,None]*(a@r)*a
   signals[f['id']]=(q,v,acc,rq)
   vp=(1.875*delta/T if kind=='quintic' else delta/(T-.1));ap=(10*math.sqrt(3)/3*delta/T**2 if kind=='quintic' else delta/(.1*(T-.1)));jrk=60*delta/T**3 if kind=='quintic' else None
   assert abs(max(abs(v))-vp)<1e-8
   assert abs(q[0]-delta)<1e-12 and abs(q[SAMPLES//2])<1e-12 and abs(q[-1]-delta)<1e-12
   assert max(abs(v[[0,SAMPLES//2,-1]]))<1e-10
   if kind=='quintic':assert max(abs(acc[[0,SAMPLES//2,-1]]))<1e-9
   kinrows.append(dict(profile=kind,finger=f['id'],stroke_deg=f['range_deg'],leg_s=T,peak_speed_rad_s=vp,peak_speed_deg_s=math.degrees(vp),peak_speed_rpm=vp*60/(2*math.pi),peak_accel_rad_s2=ap,peak_accel_deg_s2=math.degrees(ap),peak_piecewise_jerk_rad_s3=jrk,J_axis_kg_m2=f['J_axis_kg_m2'],inertial_torque_peak_Nm=f['J_axis_kg_m2']*ap,all_orientation_inertial_plus_gravity_peak_upper_bound_Nm=f['J_axis_kg_m2']*ap+f['worst_gravity_Nm'],all_orientation_RMS_upper_bound_Nm=f['J_axis_kg_m2']*math.sqrt(integ(acc**2,t))+f['worst_gravity_Nm'],inertial_peak_kinetic_energy_J=.5*f['J_axis_kg_m2']*vp**2))
  for gname,gvec in gravities.items():
   netP=np.zeros(len(t));individual_regen=0.;Etot=np.zeros(len(t));Prows={}
   for f in fingers:
    q,v,acc,rq=signals[f['id']];g=np.array(gvec);tg=np.cross(rq,f['mass_kg']*g)@np.array(f['axis']);tau=f['J_axis_kg_m2']*acc-tg;P=tau*v;netP+=P;individual_regen+=integ(np.maximum(-P,0),t);Etot+=.5*f['J_axis_kg_m2']*v**2-f['mass_kg']*(rq@g);Prows[f['id']]=P
    motion.append(dict(profile=kind,gravity_head=gname,finger=f['id'],peak_abs_torque_Nm=float(max(abs(tau))),RMS_torque_Nm=math.sqrt(integ(tau**2,t)),peak_positive_shaft_power_W=float(max(P)),peak_negative_shaft_power_W=float(min(P)),positive_mechanical_work_J=integ(np.maximum(P,0),t),negative_mechanical_work_magnitude_J=integ(np.maximum(-P,0),t),net_mechanical_work_J=integ(P,t)))
    if gname=='minus_Z':allseries[kind,f['id']]=(q,v,acc,tau,P)
   pos=integ(np.maximum(netP,0),t);neg=integ(np.maximum(-netP,0),t);net=integ(netP,t);deltaE=float(Etot[-1]-Etot[0]);assert abs(net-deltaE)<3e-4
   rec=dict(profile=kind,gravity_head=gname,all_four_positive_peak_W=float(max(netP)),all_four_negative_peak_W=float(min(netP)),common_bus_ideal_positive_work_J=pos,common_bus_ideal_braking_work_J=neg,sum_individual_braking_work_J=individual_regen,net_work_J=net,conservative_energy_change_J=deltaE,quadrature_energy_residual_J=net-deltaE)
   power.append(rec)
   for em,er in [(0.7,0.5),(0.9,0.8)]:
    # Apply losses PER DRIVE before common-bus summation; opposite-sign axes cannot
    # exchange mechanical power without each electrical conversion loss.
    electrical=[np.where(p>=0,p/em,p*er) for p in Prows.values()];bus=np.sum(electrical,axis=0)
    ei=integ(np.maximum(bus,0),t);eb=integ(np.maximum(-bus,0),t)
    supply.append(dict(profile=kind,gravity_head=gname,hypothetical_motoring_efficiency=em,hypothetical_regen_efficiency=er,input_positive_energy_J=ei,common_bus_return_energy_J=eb,individual_drives_return_energy_J=sum(integ(np.maximum(-p,0),t) for p in electrical),net_source_energy_J=ei-eb,net_source_average_W_at_1Hz=ei-eb,positive_power_peak_W=float(max(bus)),DC_bus_return_peak_W=float(max(0,-min(bus))),conditional_C_F_12to14V_if_one_cycle_all_return_stored=2*eb/(14**2-12**2),conditional_C_F_24to28V_if_one_cycle_all_return_stored=2*eb/(28**2-24**2),efficiency_model_is_hypothetical_power_conversion_only=True,stall_copper_idle_switching_and_control_losses_not_included=True))
 # Peak speed and inertia sensitivity does not assume new gear ratio/motor inertia.
 sensitivity=[]
 for f in fingers:
  k=next(x for x in kinrows if x['profile']=='quintic' and x['finger']==f['id'])
  for Jadd in [0,.0001,.001,.005]:
   J=f['J_axis_kg_m2']+Jadd;sensitivity.append(dict(finger=f['id'],added_output_equivalent_J_kg_m2=Jadd,total_J_kg_m2=J,peak_inertial_torque_Nm=J*k['peak_accel_rad_s2'],peak_kinetic_energy_J=.5*J*k['peak_speed_rad_s']**2,gross_inertial_braking_work_per_cycle_J=J*k['peak_speed_rad_s']**2))
 # Necessary force bound for a balanced side grip: not a wrench-feasibility certificate.
 contact=[]
 for n in [2,4]:
  for mu in [.2,.4,.8]:
   for aup in [0,2,5]:
    for lever in [.06,.08,.10,.12,.15]:
     F=2.*2.*(G+aup);N=F/(n*mu)
     contact.append(dict(payload_kg=2,design_factor=2,upward_payload_accel_m_s2=aup,symmetric_active_contacts=n,assumed_mu=mu,normal_force_per_contact_N=N,normal_line_moment_arm_m=lever,torque_for_normal_component_Nm=N*lever,hypothetical_tangential_moment_arm_m=.03,resultant_torque_lower_bound_Nm_if_30mm_tangent_arm=max(0,N*lever-(F/n)*.03),resultant_torque_upper_bound_Nm_at_minimum_N_if_30mm_tangent_arm=N*lever+(F/n)*.03,mean_contact_pressure_kPa_at_100mm2=N/.0001/1000,mean_contact_pressure_kPa_at_300mm2=N/.0003/1000,mean_contact_pressure_kPa_at_600mm2=N/.0006/1000,requirement_status='primary_4contact_2kg' if n==4 else 'comparison_only_not_a_2contact_2kg_requirement',status='necessary normal-force sizing scenario; balanced contacts, no object moment demand; normal-component and explicit 30mm tangential-lever bounds only; not actual mu or actual geometry'))
 # Same-force contact-count derating is a necessary ideal comparison, not a payload rating.
 derating=[]
 for mu in [.2,.4,.8]:
  N4=2*2*G/(4*mu)
  derating.append(dict(assumed_mu=mu,normal_force_per_contact_from_4contact_2kg_N=N4,ideal_4contact_payload_kg=2,ideal_2opposed_contact_payload_kg_at_same_force=2*mu*N4/(2*G),geometry_and_wrench_feasibility_not_proven=True,actual_2contact_rating_kg=None))
 # Left/right symmetric upper35/lower45 radial-normal example: unequal top/bottom
 # normal forces balance XY; all contacts at common height and same object radius.
 asym=[];ratio=math.sin(math.radians(35))/math.sin(math.radians(45))
 for mu in [.2,.4,.8]:
  upper=2*2*G/(2*mu*(1+ratio));lower=ratio*upper
  asym.append(dict(assumed_mu=mu,payload_kg=2,design_factor=2,phi_deg=[35,145,225,315],normal_N_per_upper=upper,normal_N_per_lower=lower,upper_vs_equal4_factor=upper/(2*2*G/(4*mu)),conditional_geometry='radial normals; common contact plane, equal object radius, gravity along Z; no object COM moment'))
 compact=[]
 for f in fingers:
  delta=math.pi/2
  for kind in ['quintic','trapezoid_ta0p1']:
   vp=1.875*delta/T if kind=='quintic' else delta/(T-.1);ap=10*math.sqrt(3)/3*delta/T**2 if kind=='quintic' else delta/(.1*(T-.1))
   compact.append(dict(finger=f['id'],profile=kind,alternative_stroke_deg=90,peak_speed_deg_s=math.degrees(vp),peak_speed_rpm=vp*60/(2*math.pi),peak_accel_rad_s2=ap,body_only_peak_inertial_Nm=f['J_axis_kg_m2']*ap,angular_expression_reduction_deg=f['range_deg']-90,status='unadopted redesigned-mechanism scenario; truncating old q at90 is NOT old full closure'))
 csvout('two-contact-derating.csv',derating);csvout('asymmetric-four-contact-example.csv',asym);csvout('compact-90deg-alternative.csv',compact)
 # Unmeasured stop latency: fast empty motion cannot be taken through contact.
 delay=[]
 for f in fingers:
  v=next(x['peak_speed_rad_s'] for x in kinrows if x['profile']=='quintic' and x['finger']==f['id'])
  for ms in [2,5,10]:delay.append(dict(finger=f['id'],assumed_detection_and_reaction_delay_ms=ms,speed_rad_s=v,coast_angle_deg=math.degrees(v*ms/1000),coast_distance_at_80mm_radius_mm=80*v*ms/1000,additional_braking_distance_excluded=True))
 # Grasp-map rank: two point contacts cannot supply torque along their connecting line.
 def skew(r):x,y,z=r;return np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
 rank=[]
 for n,pts in [(2,[[.04,0,0],[-.04,0,0]]),(4,[[.04,0,0],[-.04,0,0],[0,.04,0],[0,-.04,0]])]:
  W=np.concatenate([np.vstack([np.eye(3),skew(r)]) for r in pts],axis=1);rank.append(dict(contacts=n,locations_m=pts,point_force_grasp_map_rank=int(np.linalg.matrix_rank(W)),rank6_is_necessary_not_friction_force_closure=True))
 assert [x['point_force_grasp_map_rank'] for x in rank]==[5,6]
 csvout('finger-inputs.csv',[{k:v for k,v in f.items() if k not in ['source_members','COM_from_pivot_home_m','axis']} for f in fingers]);csvout('motion-limits.csv',kinrows);csvout('torque-power-scenarios.csv',motion);csvout('common-bus-mechanical-power.csv',power);csvout('efficiency-scenarios.csv',supply);csvout('added-inertia-sensitivity.csv',sensitivity);csvout('contact-scenarios.csv',contact);csvout('contact-delay-scenarios.csv',delay)
 times=[]
 for i in range(0,len(t),20):
  row={'time_s':float(t[i])}
  for (kind,fid),(q,v,acc,tau,P) in allseries.items():
   for label,x in [('q_deg',np.rad2deg(q)),('velocity_rad_s',v),('acceleration_rad_s2',acc),('tau_minusZ_Nm',tau),('power_minusZ_W',P)]:row[kind+'_'+fid+'_'+label]=float(x[i])
  times.append(row)
 csvout('cycle-timeseries.csv',times)
 plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
 fig,axs=plt.subplots(3,2,figsize=(12,9),sharex=True)
 for col,fid in enumerate(['UR','LL']):
  for kind,style in [('quintic','-'),('trapezoid_ta0p1','--')]:
   q,v,acc,tau,P=allseries[kind,fid]
   for row,y in enumerate([np.rad2deg(q),np.rad2deg(v),np.rad2deg(acc)]):axs[row,col].plot(t,y,style,label=kind)
  axs[0,col].set_title(fid+' / '+('upper 109 deg' if fid=='UR' else 'lower 122 deg'));axs[2,col].set_xlabel('Cycle time [s]')
 for ax,label in zip(axs[:,0],['Angle [deg]','Speed [deg/s]','Acceleration [deg/s²]']):ax.set_ylabel(label)
 for ax in axs.flat:ax.grid(alpha=.2)
 axs[0,0].legend();fig.suptitle('FAST-KIN01 | Empty closed → open → closed in 1.0 s\n0.5 s per leg; explicit legacy travel, new contact geometry not frozen');fig.tight_layout();fig.savefig(OUT/'motion-profiles.svg',metadata={'Date':None});fig.savefig(OUT/'motion-profiles.png',dpi=150);plt.close(fig)
 fig,axs=plt.subplots(2,2,figsize=(12,7),sharex=True)
 for fid,col in [('UR',0),('LL',1)]:
  for kind,style in [('quintic','-'),('trapezoid_ta0p1','--')]:
   q,v,acc,tau,P=allseries[kind,fid];axs[0,col].plot(t,tau,style,label=kind);axs[1,col].plot(t,P,style)
  axs[0,col].set_title(fid+' finger body only');axs[1,col].set_xlabel('Cycle time [s]')
 axs[0,0].set_ylabel('Output torque [N m]');axs[1,0].set_ylabel('Output mechanical power [W]');axs[0,0].legend()
 for ax in axs.flat:ax.grid(alpha=.2);ax.axhline(0,color='grey',lw=.5)
 fig.suptitle('FAST-KIN01 | Known finger inertia + gravity along head −Z\nNo P16, motor/gear reflected inertia, bearing/cable friction or electrical losses');fig.tight_layout();fig.savefig(OUT/'torque-power.svg',metadata={'Date':None});fig.savefig(OUT/'torque-power.png',dpi=150);plt.close(fig)
 fig,axs=plt.subplots(1,2,figsize=(12,4.7));muarr=np.linspace(.15,.9,300)
 for n in [4,2]:
  for lever,ls in [(.06,':'),(.10,'-'),(.15,'--')]:axs[0].plot(muarr,2*2*G/(n*muarr)*lever,ls,label=f'{n} contacts, arm {lever*1000:.0f} mm'+(' (comparison)' if n==2 else ''))
 axs[0].set(xlabel='Hypothetical friction coefficient μ',ylabel='Normal-component joint torque [N m]',title='2 kg, factor 2, static; necessary scenario')
 for n in [4,2]:axs[1].plot(muarr,2*2*G/(n*muarr)/.0003/1000,label=f'{n} contacts, 300 mm² each'+(' (comparison)' if n==2 else ''))
 axs[1].set(xlabel='Hypothetical friction coefficient μ',ylabel='Mean contact pressure [kPa]',title='Real area and pressure peaks must be measured')
 for ax in axs:ax.grid(alpha=.2);ax.legend(fontsize=8)
 fig.suptitle('FAST-KIN01 | Contact force, not an asserted material coefficient');fig.tight_layout();fig.savefig(OUT/'contact-scenarios.svg',metadata={'Date':None});fig.savefig(OUT/'contact-scenarios.png',dpi=150);plt.close(fig)
 shared=shared_master(fingers,t,gravities)
 result=dict(single_master=shared,legacy_independent_results_status='historical analysis only; not current requirement for four motors',revision='FAST-KIN01',license='CC-BY-NC-4.0',required_notice=NOTICE,source_hashes={str(BASE.relative_to(ROOT)):sha(BASE)},script_sha256=sha(__file__),requirement='CURRENT: one central motor with mechanically coupled four petals; empty full closed-open-closed <=1s; calculation1s,0.5s per stroke; contact face is lit petal face; force-limit mode after contact',two_contact_policy='primary requirement is four-contact2kg; two-contact cases are comparison/derating, no full2kg requirement assigned',compact_90deg_alternative=compact,asymmetric_contact_example=asym,model_status='initial archived finger_rotor inertial proxy only; new structural illuminated face must be recomputed',excluded=['all old P16 body and slider masses','new linkage and output-stage mass; drive inertia only included in explicitly named conditional example CSV','unweighed electronics','friction, cables, bearing loss','object load during fast empty cycle','complete arm motion coupling'],sample_count=SAMPLES,finger_inputs=fingers,kinematic_limits=kinrows,common_bus_power=power,grasp_rank_examples=rank,checks=dict(unique_rotor_count=len(fingers),no_P16_member_in_rotor_sources=True,closed_open_closed_endpoints=True,zero_endpoint_velocity=True,quintic_zero_endpoint_acceleration=True,maximum_numerical_cycle_energy_residual_J=max(abs(x['quadrature_energy_residual_J']) for x in power)),manufacturing_or_grasp_rating=False)
 sources=[dict(title='Modern Robotics: point-to-point time scaling',url='https://modernrobotics.northwestern.edu/nu-gm-book-resource/9-1-and-9-2-point-to-point-trajectories-part-2-of-2/',used_for='trajectory taxonomy; all numerical coefficients and results derived in this script'),dict(title='Modern Robotics: friction',url='https://modernrobotics.northwestern.edu/nu-gm-book-resource/12-2-1-friction/',used_for='Coulomb contact-cone model, not a coefficient for this design'),dict(title='Modern Robotics: force closure',url='https://modernrobotics.northwestern.edu/nu-gm-book-resource/12-2-3-force-closure/',used_for='wrench feasibility versus contact count; rank examples computed locally')]
 sources += [dict(title='FAULHABER3274 BP4',url='https://www.faulhaber.com/fileadmin/Import/Media/EN_3274_BP4_DFF.pdf',used_for='p1 rotor inertia48gcm²; no purchased/selected combination asserted'),dict(title='FAULHABER32GPT HT',url='https://www.faulhaber.com/fileadmin/Import/Media/EN_32GPT_HT_FCH.pdf',used_for='p1 three-stage input inertia including pinion196gmm² max; continuous/intermittent input7000/9000rpm'),dict(title='FAULHABERIE3-1024L',url='https://www.faulhaber.com/fileadmin/Import/Media/EN_IE3-1024L_DFF.pdf',used_for='p1 magnetic ring inertia0.08gcm²')]
 save('sources.json',dict(review_date='2026-09-27',sources=sources));result['artifact_sha256']={p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='study.json'};save('study.json',result)
 print(json.dumps(dict(revision='FAST-KIN01',finger_count=len(fingers),files=len(result['artifact_sha256'])+1,max_energy_residual_J=result['checks']['maximum_numerical_cycle_energy_residual_J'],kinematic_limits=kinrows),indent=2))
if __name__=='__main__':main()
