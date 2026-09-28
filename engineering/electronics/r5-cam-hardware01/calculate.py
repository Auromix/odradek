#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Independent planar cam force reconstruction; no writes to frozen STAGE/FORM."""
from pathlib import Path
import json,csv,hashlib,math
import numpy as np
from scipy.special import comb
from scipy.integrate import cumulative_trapezoid
P=Path(__file__).resolve().parent;ROOT=P.parents[2];G=9.80665
STPATH=ROOT/'engineering/generated/r5-stage01/study.json';FORMPATH=ROOT/'engineering/generated/r5-petal-form02/study.json'
ST=json.loads(STPATH.read_text());FORM=json.loads(FORMPATH.read_text())
A=.008;PH=-np.pi/4;RMIN=.031;RF=.066;RO=.091;SPAN=RO-RF;RAD=.004;WIDTH=.004;Eeff=210e9/(2*(1-.3**2))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(name,v):(P/name).write_text(json.dumps(v,ensure_ascii=False,indent=2,default=lambda a:a.tolist() if isinstance(a,np.ndarray) else a.item())+'\n')
def csvout(name,rows):
 with (P/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def poly(t,timing):
 u=np.where(t<=.5,1-2*t,2*t-1);sgn=np.where(t<=.5,-1.,1.)
 if timing=='bernstein9':
  b=np.array(ST['synchronous_bernstein_dynamics']['bernstein_speed_mm_s'])/1000
  def bas(n):return np.array([comb(n,i)*u**i*(1-u)**(n-i) for i in range(n+1)]).T
  s=bas(10)@np.r_[0,.05*np.cumsum(b)];sd=sgn*(bas(9)@b);sdd=bas(8)@(18*np.diff(b))
 else:
  s=.06*(10*u**3-15*u**4+6*u**5);sd=sgn*.12*30*u**2*(1-u)**2;sdd=.24*60*u*(1-u)*(1-2*u)
 return RO-s,-sd,-sdd

def path(R):
 u=np.clip((RO-R)/SPAN,0,1)
 q=np.pi/2*(10*u**3-15*u**4+6*u**5)
 qr=-np.pi/2*30*u**2*(1-u)**2/SPAN
 qrr=np.pi/2*60*u*(1-u)*(1-2*u)/SPAN**2
 ph=q+PH
 c=np.column_stack((R+A*np.cos(ph),.020+A*np.sin(ph)))
 cR=np.column_stack((1-A*np.sin(ph)*qr,A*np.cos(ph)*qr))
 cRR=np.column_stack((-A*np.cos(ph)*qr**2-A*np.sin(ph)*qrr,-A*np.sin(ph)*qr**2+A*np.cos(ph)*qrr))
 v=np.linalg.norm(cR,axis=1);normal=np.column_stack((-cR[:,1],cR[:,0]))/v[:,None]
 h=A*np.cos(ph)/v;k=(cR[:,0]*cRR[:,1]-cR[:,1]*cRR[:,0])/v**3
 return q,qr,qrr,c,cR,cRR,normal,h,k

def material(kind):
 f=FORM['parts'][kind]['known_material_subtotal'];m=f['mass_kg'];x,y,z=np.array(f['COM_local_m'])-[0,0,.0035];Ic=f['inertia_COM_local_axes_kg_m2'][1][1]
 return m,x,y,z,Ic,Ic+m*(x*x+z*z)

summaries=[];all_series={}
for timing in ['quintic','bernstein9']:
 t=np.linspace(0,1,40001);R,Rd,Rdd=poly(t,timing);q,qr,qrr,c,cR,cRR,n,h,k=path(R)
 qd=qr*Rd;qdd=qrr*Rd**2+qr*Rdd;foldload=[];power_total=np.zeros(len(t));Etotal=np.zeros(len(t));pathsum=np.zeros(len(t));drows=[];fdchecks={}
 for kind in ['upper','lower']:
  m,x,y,z,Ic,J=material(kind);aa=-x*np.sin(q)-z*np.cos(q);bb=x*np.cos(q)-z*np.sin(q)
  ar=Rdd+aa*qdd-bb*qd**2;az=bb*qdd+aa*qd**2
  rn=R+x*np.cos(q)-z*np.sin(q);zn=.020+x*np.sin(q)+z*np.cos(q)
  num_ar=np.gradient(np.gradient(rn,t),t);num_az=np.gradient(np.gradient(zn,t),t)
  fdchecks[kind]=dict(max_abs_error_m_s2=max(max(abs(num_ar[5:-5]-ar[5:-5])),max(abs(num_az[5:-5]-az[5:-5]))),peak_analytic_acceleration_m_s2=max(np.hypot(ar,az)),sample_step_s=float(t[1]-t[0]),method='second central finite differences of independent COM positions; five endpoint samples omitted; piecewise C2 transition samples retained')
  tau_inertia=J*qdd+m*aa*Rdd;tau_gravity=m*G*bb;tau=tau_inertia+tau_gravity
  N=tau/h;N_g=tau_gravity/h;N_i=tau_inertia/h
  # Pure rolling spin for the loaded wall; spin relative to turning stud is relevant to bearing.
  speed=np.linalg.norm(cR,axis=1)*Rd
  omega_outer=-np.sign(N)*speed/RAD;omega_relative=omega_outer-qd
  rpm_conservative=(abs(speed)/RAD+abs(qd))*60/(2*np.pi)
  # Curved-track Hertz screening; not a manufacturer curved-track load rating.
  Reff=RAD*(1+np.sign(N)*RAD*k)
  Reff_worst=RAD*(1-RAD*abs(k));assert min(Reff_worst)>0
  hertz=np.sqrt(abs(N)*Eeff/(np.pi*WIDTH*Reff))
  track_proxy=799*(WIDTH/.005)*(Reff_worst/RAD)
  qforce=-m*ar+N*n[:,0] # closing coordinate s=-R
  pathsum+=2*qforce
  E=.5*m*((Rd+aa*qd)**2+(bb*qd)**2)+.5*Ic*qd**2+m*G*(.020+x*np.sin(q)+z*np.cos(q));Etotal+=2*E
  power_total+=2*qforce*(-Rd)
  peak=int(np.argmax(abs(N)));peakdyn=int(np.argmax(abs(N_i)));peakg=int(np.argmax(abs(N_g)))
  def at(i):return dict(time_s=t[i],R_mm=R[i]*1000,q_deg=np.degrees(q[i]))
  summary=dict(timing=timing,kind=kind,mass_kg=m,I_hinge_kgm2=J,maximum_abs_total_follower_N=max(abs(N)),signed_total_range_N=[min(N),max(N)],total_peak_at=at(peak),maximum_abs_inertial_only_N=max(abs(N_i)),inertial_peak_at=at(peakdyn),maximum_abs_gravity_only_N=max(abs(N_g)),gravity_peak_at=at(peakg),peak_outer_ring_absolute_rpm=max(abs(omega_outer))*60/(2*np.pi),peak_loaded_wall_relative_rpm=max(abs(omega_relative))*60/(2*np.pi),peak_both_wall_relative_rpm_bound=max(rpm_conservative),peak_hertz_contact_MPa=max(hertz)/1e6,minimum_conservative_curved_track_proxy_N=min(track_proxy),max_load_over_curved_track_proxy=max(abs(N)/track_proxy),max_dynamic_factor1p5_load_over_curved_track_proxy=max(1.5*abs(N)/track_proxy),maximum_hinge_reaction_N=max(np.hypot(m*ar-N*n[:,0],m*az+m*G-N*n[:,1])),includes=['known FORM02 material','radial-hinge translation acceleration coupling','head gravity minusZ'],excludes=['roller/stud/arm/fasteners/LED/PCB/cable mass','friction and slip','slot-clearance impact','contact during moving cycle','root-carrier mechanism inertia','passive differential non-synchrony'])
  summaries.append(summary)
  all_series[(timing,kind)]=dict(t=t,R=R,q=q,N=N,Ng=N_g,Ni=N_i,track_proxy=track_proxy,rpm_bound=rpm_conservative,hertz=hertz)
  for i in range(0,len(t),20):drows.append(dict(timing=timing,kind=kind,time_s=t[i],R_mm=1000*R[i],q_deg=np.degrees(q[i]),Rdot_m_s=Rd[i],Rddot_m_s2=Rdd[i],qdot_rad_s=qd[i],qddot_rad_s2=qdd[i],lever_m=h[i],signed_cam_N=N[i],gravity_cam_N=N_g[i],inertial_cam_N=N_i[i],curve_kappa_per_m=k[i],loaded_wall_relative_rpm=omega_relative[i]*60/(2*np.pi),both_wall_relative_rpm_bound=rpm_conservative[i],effective_loaded_wall_radius_mm=1000*Reff[i],hertz_MPa=hertz[i]/1e6,conservative_track_load_proxy_N=track_proxy[i],branch_path_force_N=qforce[i]))
 csvout(timing+'-single-petal-cycle.csv',drows)
 work=cumulative_trapezoid(power_total,t,initial=0)
 target=ST['synchronous_path_dynamics' if timing=='quintic' else 'synchronous_bernstein_dynamics']['peak_ideal_path_force_N']
 assert abs(max(abs(pathsum))-target)<1e-8
 assert max(abs(work-(Etotal-Etotal[0])))<1e-5
 summaries.append(dict(timing=timing,check='whole-path reconstructed from2upper+2lower',peak_path_force_N=max(abs(pathsum)),source_peak_path_force_N=target,work_energy_residual_J=max(abs(work-(Etotal-Etotal[0]))),independent_COM_acceleration_FD=fdchecks))
# All static gripping cases are q90 on straight part, not the no-load curved fold.
static=[];rootreactions=[]
for kind in ['upper','lower']:
 m,x,y,z,Ic,J=material(kind);lever=A/math.sqrt(2)
 for mu in [.2,.3,.4,.6]:
  Nobj=2*2*G/(4*mu);Ft=2*2*G/4
  for xc in [.035,.065,.095]:
   for friction in [0,Ft]:
    tau=xc*Nobj-.006*friction-m*G*z;Nc=tau/lever
    f0=math.hypot(Nobj,Nc-friction-m*G)
    r=dict(kind=kind,mu_assumed=mu,payload_kg=2,gravity_factor=2,contacts=4,contact_local_x_mm=1000*xc,contact_face_offset_mm=6,object_normal_N=Nobj,object_on_finger_downward_friction_N=friction,vertical_equilibrium_case=bool(friction),normal_only_moment_Nm=xc*Nobj,gravity_drive_moment_Nm=-m*G*z,total_cam_moment_Nm=tau,follower_force_N=Nc,root_total_radial_reaction_N=f0,CFS4_C0_safety_ratio=1120/abs(Nc),CFS4_structural_max_ratio=919/abs(Nc),flat_track_catalogue_ratio_40HRC=799/abs(Nc),flat_track_width4mm_Hertz_proxy_ratio=799*.8/abs(Nc),flat_track_Hertz_MPa=math.sqrt(abs(Nc)*Eeff/(math.pi*WIDTH*RAD))/1e6,scope='q90 centered4contacts; zero friction rows isolate normal load and are not a supported vertical object; x95 is sensitivity not verified lower contact footprint')
    static.append(r)
    if mu==.4 and xc==.065 and friction==Ft:
     for b,ycam in [(.015,v) for v in [.022,.025,.027,.030]]+[(.0165,.0325),(.016,.032)]:
      Fz=friction+m*G-Nc;Mx=ycam*Nc-y*m*G
      nearZ=(Fz-Mx/b)/2;farZ=(Fz+Mx/b)/2
      near=math.hypot(Nobj/2,nearZ);far=math.hypot(Nobj/2,farZ)
      mirroredMx=ycam*Nc+y*m*G
      mirroredNear=math.hypot(Nobj/2,(Fz-mirroredMx/b)/2);mirroredFar=math.hypot(Nobj/2,(Fz+mirroredMx/b)/2)
      rootreactions.append(dict(kind=kind,bearing_center_span_mm=2000*b,cam_center_lateral_y_mm=ycam*1000,follower_N=Nc,near_bearing_r_N=-Nobj/2,near_bearing_z_N=nearZ,far_bearing_r_N=-Nobj/2,far_bearing_z_N=farZ,near_resultant_N=near,far_resultant_N=far,SKF607slash8_C0_ratio=950/max(near,far),near_resultant_mirrored_COM_same_positive_cam_y_N=mirroredNear,far_resultant_mirrored_COM_same_positive_cam_y_N=mirroredFar,worst_same_chirality_C0_ratio=950/max(near,far,mirroredNear,mirroredFar),moment_balance_residual_Nm=(-b*farZ+b*nearZ+Mx),scope='static coplanar centered object; canonicalright plus reflected COM with cam kept positiveY; actual3D assembly and bearing retention not released'))
csvout('static-grip-scenarios.csv',static);csvout('split-root-reaction-sensitivity.csv',rootreactions)
Rgrid=np.linspace(.031,.091,120001);q,qr,qrr,c,cR,cRR,n,h,k=path(Rgrid)
geometry=dict(numerical_curvature_min_mm=1000/max(abs(k)),minimum_cam_torque_lever_mm=1000*min(h),follower_D_mm=8,slot_width_candidate_mm=8.05,slot_width_is_not_released=True,offset_inner_radius_nominal_min_mm=1000/max(abs(k))-4.025,local_offset_regularity_margin=1-.004025*max(abs(k)),min_effective_Hertz_radius_for_either_wall_mm=4*(1-.004*max(abs(k))),external_clearance_only_half_play_deg_at_nominal_D=math.degrees(.000025/min(h)),class0_mean_OD_interval_mm=[7.992,8],external_clearance_only_half_play_deg_at_low_mean_D=math.degrees(.000029/min(h)),scope='dense numerical geometry; not interval proof or dimensional tolerance stack')
geometry['carrier8p3_comparison']=dict(slot_width_mm=8.3,nominal_external_half_gap_mm=.15,offset_inner_radius_nominal_min_mm=1000/max(abs(k))-4.15,local_offset_regularity_margin=1-.00415*max(abs(k)),linearized_half_play_deg=math.degrees(.00015/min(h)),scope='separate carrier geometry candidate communicated by carrier agent; not a frozen cross-model fit proof')
rejected=[dict(part='IKO CFS3',D_mm=6,C0_N=611,maximum_allowable_static_N=484,reason='normal-only282N staticC0 factor2.17<chosen high-accuracy screening3; keeping placeholder size is not the selection criterion'),dict(part='IKO CFES6B (family minimum illustrative only, not selected)',D_mm=16,reason='stock eccentric follower family minimumOD16; radius8 exceeds original minimum pitch curvature5.454. Cannot substitute into frozen slot; no miniature8mmstock eccentric/preload variant verified.')]
budget=dict(revision='R5-CAM-HARDWARE01',status='CFS4 candidate for detailed single-petal carrier; no manufacturing release',license='CC-BY-NC-4.0',input_hashes={str(p.relative_to(ROOT)):sha(p) for p in [STPATH,FORMPATH,ROOT/'engineering/r5_stage01.py']},script_sha256=sha(__file__),dynamics=summaries,static_grip_cases=static,root_reaction_sensitivity=rootreactions,geometry=geometry,chosen_follower='IKO CFS4, caged high-carbon-steel cylindrical outer ring; class0; included M4nut',chosen_root_bearing='SKF607/8-2Z pair as conditional root support only; shaft/retention still custom',rejected_or_not_selected=rejected,load_terms_not_conflated=True,manufacturing_release=False)
dump('budget.json',budget)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none','svg.hashsalt':'R5-CAM-HARDWARE01'})
fig,ax=plt.subplots(2,2,figsize=(12,7.5));fig.suptitle('R5-CAM-HARDWARE01 / per-petal cam forces and rolling-speed screen')
for row,timing in enumerate(['quintic','bernstein9']):
 for kind in ['upper','lower']:
  a=all_series[(timing,kind)];ax[row,0].plot(a['t'],a['N'],label=kind);ax[row,1].plot(a['t'],a['rpm_bound'],label=kind)
 ax[row,0].set(title=timing+' / signed no-load follower reaction',xlabel='Time [s]',ylabel='Cam force [N]')
 ax[row,1].set(title=timing+' / both-wall relative-spin bound',xlabel='Time [s]',ylabel='Relative bearing speed [rpm]')
 for a in ax[row]:a.legend();a.grid(alpha=.2)
fig.tight_layout();fig.savefig(P/'single-petal-loads.svg',metadata={'Date':None});fig.savefig(P/'single-petal-loads.png',dpi=160);plt.close(fig)
print(json.dumps({'dynamics':summaries,'geometry':geometry,'nominal_static':[r for r in static if r['mu_assumed']==.4 and r['contact_local_x_mm']==65]},indent=2))
