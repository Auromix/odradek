# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Independent STAGE01 review. Does not import or modify the implementation."""
from pathlib import Path
import csv,hashlib,itertools,json,math
import numpy as np
from scipy.special import betainc
from scipy.optimize import brentq
from scipy.integrate import cumulative_trapezoid
ROOT=Path(__file__).resolve().parents[1];FORM_DIR=ROOT/'engineering/generated/r5-petal-form02';S=ROOT/'engineering/generated/r5-stage01';W=S/'independent-review';W.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((FORM_DIR/'parameters.json').read_text());f=json.loads((FORM_DIR/'study.json').read_text());st=json.loads((S/'study.json').read_text());fr=json.loads((FORM_DIR/'radial-study.json').read_text())
for rel,h in st['source_hashes'].items():assert sha(ROOT/rel)==h,rel
for r in fr['containment']:
 assert sha(FORM_DIR/r['source_step'])==r['source_sha256']
 assert r['outside_convex_prism_mm3']<1e-4
info={'UR':('upper',1,45),'UL':('upper',-1,135),'LL':('lower',-1,225),'LR':('lower',1,315)}
B=8.;phase=-np.pi/4
# Integrate normalized beta(3,3) density instead of copying the builder's quintic.
def Q(R):return np.pi/2*betainc(3,3,np.clip((91-np.asarray(R))/25,0,1))
def dQ(R):
 u=np.clip((91-np.asarray(R))/25,0,1);return -np.pi/2*30*u*u*(1-u)**2/25

def point(R,q):return np.stack([np.asarray(R)+B*np.cos(np.asarray(q)+phase),20+B*np.sin(np.asarray(q)+phase)],axis=-1)
def axis(phi):
 t=math.radians(phi);return np.array([math.cos(t),math.sin(t),0]),np.array([-math.sin(t),math.cos(t),0])

rank=[]
for R in np.linspace(31,91,1201):
 q=Q(R);v=q+phase;prime=dQ(R);dq=np.array([-B*np.sin(v),B*np.cos(v)]);dt=np.array([1-B*np.sin(v)*prime,B*np.cos(v)*prime]);J=np.column_stack([dq,-dt]);det=np.linalg.det(J);expected=B*np.cos(v);assert abs(det-expected)<1e-12
 rank.append(dict(R_mm=float(R),determinant_mm_per_rad=float(det),analytic_det_mm_per_rad=float(expected)))
# Actual R differs from the independent groove parameter in the alternate branch.
tau=60.;qalt=1.5*np.pi-Q(tau);Ralt=tau+2*B*np.cos(Q(tau)+phase);alt=point(Ralt,qalt)-point(tau,Q(tau));assert max(abs(alt))<1e-12
altbranch=dict(groove_parameter_mm=tau,actual_root_radius_mm=float(Ralt),alternative_q_deg=float(np.degrees(qalt)),nominal_q_at_actual_R_deg=float(np.degrees(Q(Ralt))),closure_residual_mm=alt.tolist(),within_actual_R_range=True,within_assumed_q0to90=False,formula='q_alt=270deg-q(tau); R_alt=tau+2*a*cos(q(tau)-45deg). Plus 360deg periodic branches if unlimited rotation.')
alpha=float(st['cam']['pressure_angle_max']['value']);sensitivity=8*math.cos(math.radians(alpha));clearance=dict(assumed_diametral_gap_mm=.3,normal_center_play_mm=.15,minimum_first_order_normal_q_sensitivity_mm_per_rad=sensitivity,first_order_q_half_play_deg=math.degrees(.15/sensitivity),scope='Linearized at zero-clearance nominal branch; not a guaranteed finite tolerance bound or a chosen bearing preload.')
# Global XY projection bound for ANY independent R>=31, q in0..90.
# rho=R+x cosq-(z-3.5)sinq >= R-6 since x>=0, cosq>=0,
# (z-3.5)<=6 and sinq<=1. y is unchanged by the hinge rotation.
cert=[];sample_min_slack=1e9
for aa,bb in itertools.combinations(info,2):
 ka,ha,pa=info[aa];kb,hb,pb=info[bb];ea,ta=axis(pa);eb,tb=axis(pb);n=(ea-eb)/np.linalg.norm(ea-eb);ya=np.array(p[ka]['outline_knots_mm'])[:,1]*ha;yb=np.array(p[kb]['outline_knots_mm'])[:,1]*hb
 assert n@ea>0 and n@eb<0
 def gap(Ra,Rb):return (Ra-6)*(n@ea)-(Rb-6)*(n@eb)+min(ya*(n@ta))-max(yb*(n@tb))
 row=dict(pair=[aa,bb],unit_normal=n.tolist(),all_independent_R_ge31_q0to90_gap_mm=float(gap(31,31)),both_fold_R_ge66_gap_mm=float(gap(66,66)),A_fold_B_radial_gap_mm=float(gap(66,31)),A_radial_B_fold_gap_mm=float(gap(31,66)));assert row['all_independent_R_ge31_q0to90_gap_mm']>0;cert.append(row)
 # independent 3D Rodrigues samples to catch frame/sign errors in the proof
 for fid,Rlo in [(aa,31),(bb,31)]:
  kind,hand,phi=info[fid];er,et=axis(phi);coords=np.array([[x,y*hand,z] for x,y in p[kind]['outline_knots_mm'] for z in [0.,9.5]])-[0,0,3.5];initial=coords[:,0,None]*er+coords[:,1,None]*et+coords[:,2,None]*[0,0,1.];a=-et;K=np.array([[0,-a[2],a[1]],[a[2],0,-a[0]],[-a[1],a[0],0.]])
  for q in np.radians([0,15,30,45,60,75,90]):
   rot=np.eye(3)+np.sin(q)*K+(1-np.cos(q))*(K@K);v=initial@rot.T+Rlo*er+[0,0,20];rho=v@er;slack=float(min(rho)-(Rlo-6));assert slack>-1e-10;sample_min_slack=min(sample_min_slack,slack)
assert abs(min(x['all_independent_R_ge31_q0to90_gap_mm'] for x in cert)-4/np.sqrt(2))<1e-10
# Rectangular box45: side-normal supports are W/2,H/2,W/2,H/2.
rectangle=dict(width_mm=50.,depth_mm=120.,yaw_deg=45.,required_R_mm=[31.,66.,31.,66.],rigid_common_R_feasible=False,at_first_contact_common_R_mm=66.,late_pair_remaining_gap_mm=35.,at_late_pair_contact_common_R_mm=31.,early_pair_rigid_penetration_mm=35.,spring_N_per_mm=10.,conditional_extra_early_pair_force_N=350.)
A=np.array([[1,1,0,0,-2,0,0],[0,0,1,1,0,-2,0],[0,0,0,0,1,1,-2]],float);assert np.linalg.matrix_rank(A)==3
Ri=np.array(rectangle['required_R_mm']);yA=(Ri[0]+Ri[1])/2;yB=(Ri[2]+Ri[3])/2;u=(yA+yB)/2;v=np.r_[Ri,yA,yB,u];assert max(abs(A@v))<1e-12
# Force via virtual work: all zero-sum branch motions at fixed u require
# equal branch generalized forces. Then P=sum(F_i*dRi)=4*N*du.
N=2*2*9.80665/(4*.4);force=np.full(4,N);null=np.array([[1,-1,0,0],[0,1,-1,0],[0,0,1,-1]],float);assert max(abs(null@force))<1e-12
lever=dict(constraint_rank=int(np.linalg.matrix_rank(A)),coordinates=7,configuration_DOF=4,prescribed_input_remaining_passive_DOF=3,rectangle_solution=dict(Ri_mm=Ri.tolist(),yA_mm=yA,yB_mm=yB,u_mm=u,first_tier_branch_offsets_mm=[-17.5,17.5,-17.5,17.5]),branch_relative_difference_mm=35.,pulley_center_stroke_determined=False,conditional_equal_branch_generalized_force_N=N,conditional_input_force_N=4*N,limits='Taut massless inextensible cables, parallel strands, frictionless massless pulleys, free travel. At radial q90 only, branch generalized force equals radial object normal. During folding it also drives hinge rotation. Slack, unequal preload/friction/inertia/endstops invalidate simple equal-force equilibrium; sum constraint never guarantees synchronous R_i.')
# Independent timing: beta integral for quintic, scipy piecewise Bernstein
# polynomial integration for the frozen speed coefficients, no builder imports.
from scipy.interpolate import BPoly
coeff=np.array(st['synchronous_bernstein_dynamics']['bernstein_speed_mm_s'])/1000
velocity_poly=BPoly(coeff[:,None],[0.,.5]);integral_poly=velocity_poly.antiderivative()
assert abs(float(integral_poly(.5)-integral_poly(0))-.06)<1e-14

def path(t,mode):
 t=np.mod(np.asarray(t),1.)
 if mode=='bernstein9':
  v=np.where(t<=.5,.5-t,t-.5);return integral_poly(v)-integral_poly(0)
 u=np.where(t<=.5,2*t,2*t-1);v=betainc(3,3,u);return .06*np.where(t<=.5,1-v,v)
def com_at_s(s,m,phi,hand):
 R=91-1000*np.asarray(s);q=Q(R);er,et=axis(phi);x,y,z=np.array(m['COM_local_m'])-[0,0,.0035];y*=hand
 return ((R*.001+x*np.cos(q)-z*np.sin(q))[...,None]*er+y*et+(.02+x*np.sin(q)+z*np.cos(q))[...,None]*[0,0,1.])
def D1(fn,t,h):return (-fn(t+2*h)+8*fn(t+h)-8*fn(t-h)+fn(t-2*h))/(12*h)
def D2(fn,t,h):return (-fn(t+2*h)+16*fn(t+h)-30*fn(t)+16*fn(t-h)-fn(t-2*h))/(12*h*h)
def evaluate(times,mode,dt=1e-5):
 ds=1e-7;P=lambda t:path(t,mode);R=lambda t:91-1000*P(t)
 ss=P(times);sd=D1(P,times,dt);sdd=D2(P,times,dt);qd=D1(lambda t:Q(R(t)),times,dt);qdd=D2(lambda t:Q(R(t)),times,dt);qs=D1(lambda s:Q(91-1000*s),ss,ds);Force=np.zeros(len(times));E=np.zeros(len(times));gvec=np.array([0,0,-9.80665])
 for fid,(kind,hand,phi) in info.items():
  m=f['parts'][kind]['known_material_subtotal'];mass=m['mass_kg'];er,et=axis(phi);a=-et;K=np.array([[0,-a[2],a[1]],[a[2],0,-a[0]],[-a[1],a[0],0.]])
  fun=lambda t:com_at_s(P(t),m,phi,hand);c=fun(times);vel=D1(fun,times,dt);acc=D2(fun,times,dt);J=D1(lambda s:com_at_s(s,m,phi,hand),ss,ds)
  localI=np.array(m['inertia_COM_local_axes_kg_m2']);M=np.diag([1,hand,1]);localI=M@localI@M;B0=np.column_stack([er,et,[0.,0.,1.]]);q=Q(R(times));rot=np.eye(3)[None,:,:]+np.sin(q)[:,None,None]*K+(1-np.cos(q))[:,None,None]*(K@K);T=rot@B0;Iw=T@localI@np.swapaxes(T,1,2);omega=qd[:,None]*a;alph=qdd[:,None]*a;L=np.einsum('nij,nj->ni',Iw,omega);torque=np.einsum('nij,nj->ni',Iw,alph)+np.cross(omega,L)
  Force+=mass*np.sum((acc-gvec)*J,axis=1)+np.sum(torque*(qs[:,None]*a),axis=1)
  E+=.5*mass*np.sum(vel*vel,axis=1)+.5*np.sum(omega*L,axis=1)-mass*(c@gvec)
 return dict(s=ss,sd=sd,sdd=sdd,qd=qd,qdd=qdd,Force=Force,E=E)
def audit_timing(mode,csvfile,summary):
 rows=list(csv.DictReader((S/csvfile).open()));times=np.array([float(x['time_s']) for x in rows]);ev=evaluate(times,mode);err=abs(ev['Force']-np.array([float(r['ideal_path_force_N']) for r in rows]));mask=(times>6e-6)&(times<1-6e-6)&(abs(times-.5)>6e-6);assert max(err[mask])<.003
 qderr=max(abs(ev['qd']-np.array([float(r['q_speed_rad_s']) for r in rows])));qdd_err=max(abs(ev['qdd']-np.array([float(r['q_accel_rad_s2']) for r in rows])));assert qderr<1e-6 and qdd_err<.002
 coarse_fd=evaluate(times,mode,2e-5);fdrefinement_force_change=float(max(abs(coarse_fd['Force']-ev['Force'])));assert fdrefinement_force_change<.005
 dense_t=np.linspace(0,1,40001);de=evaluate(dense_t,mode);work=cumulative_trapezoid(de['Force']*de['sd'],dense_t,initial=0);enerr=max(abs(work-(de['E']-de['E'][0])));assert enerr<2e-6
 peaks=dict(peak_speed_mm_s=max(abs(de['sd']))*1000,peak_accel_m_s2=max(abs(de['sdd'])),peak_q_speed_deg_s=np.degrees(max(abs(de['qd']))),peak_q_accel_rad_s2=max(abs(de['qdd'])),peak_ideal_path_force_N=max(abs(de['Force'])),RMS_ideal_path_force_N=np.sqrt(np.trapezoid(de['Force']**2,dense_t)))
 peakerrors={k:float(abs(v-summary[k])) for k,v in peaks.items()};assert max(peakerrors.values())<.003
 # Exact time reversal is about mid-cycle; no passive-differential implication.
 reversal_error=max(abs(path(dense_t,mode)-path(1-dense_t,mode)));assert reversal_error<1e-14
 return dict(source=csvfile,sample_count=len(rows),dense_peak_sample_count=len(dense_t),finite_time_step_s=1e-5,finite_path_step_m=1e-7,independent_method='Direct 3D COM acceleration and full reflected/rotated inertia Newton-Euler torque, projected onto numerical virtual-work Jacobians. Timing uses scipy beta integral or BPoly antiderivative; no implementation imports.',finite_difference_step_halving_force_change_N=fdrefinement_force_change,max_force_error_interior_N=float(max(err[mask])),max_force_error_all_including_reversal_N=float(max(err)),max_angular_velocity_error_rad_s=float(qderr),max_angular_acceleration_error_rad_s2=float(qdd_err),independent_work_energy_residual_J=float(enerr),dense_peak_values={k:float(v) for k,v in peaks.items()},peak_absolute_errors=peakerrors,time_reversal_position_error_m=float(reversal_error),nominal_material_mass_kg=f['four_petal_known_material_subtotal_kg'],scope='Imposed synchronous bare petals only; no hardware/differential synchronization qualification.')
dynamic=audit_timing('quintic','synchronous-empty-cycle.csv',st['synchronous_path_dynamics'])
bernstein_dynamic=audit_timing('bernstein9','synchronous-bernstein-cycle.csv',st['synchronous_bernstein_dynamics'])

from scipy.interpolate import PPoly
power_velocity=PPoly.from_bernstein_basis(velocity_poly)
polynomial_extrema={}
for order,label in [(0,'speed_m_s'),(1,'acceleration_m_s2')]:
 polynomial=power_velocity.derivative(order);roots=polynomial.derivative().roots(extrapolate=False);candidates=[0.,.5]+[float(x.real) for x in roots if np.isreal(x) and 0<=x.real<=.5];values=[float(polynomial(x)) for x in candidates];j=int(np.argmax(abs(np.array(values))));polynomial_extrema[label]=dict(maximum_absolute_value=max(abs(np.array(values))),at_closing_time_s=candidates[j],stationary_candidates_s=candidates,method='All in-domain real roots of derivative of the explicit low-degree polynomial, plus endpoints; floating-point root solve, not a rigorous interval bound.')
assert polynomial_extrema['acceleration_m_s2']['maximum_absolute_value']>2.
inputs=[ROOT/'engineering/r5_stage01.py',S/'study.json',S/'synchronous-empty-cycle.csv',S/'synchronous-bernstein-cycle.csv',FORM_DIR/'parameters.json',FORM_DIR/'study.json',FORM_DIR/'radial-study.json']
result=dict(revision='R5-STAGE01-independent-review',input_hashes={str(x.relative_to(ROOT)):sha(x) for x in inputs},script_sha256=sha(Path(__file__)),guide_rank=dict(analytic_determinant='a*cos(q-45deg)',minimum_over_assumed_q0to90_mm_per_rad=8/math.sqrt(2),maximum_mm_per_rad=8.,sample_count=len(rank),chosen_branch_unique_on_q0to90=True,unrestricted_global_assembly_unique=False,alternate_branch_witness=altbranch,clearance=clearance,analytic_pitch_radial_derivative_lower_bound=1-8*(np.pi/2*1.875/25)/np.sqrt(2),pitch_injectivity_argument='q_R magnitude <= (pi/2)*1.875/25; |sin(q-45deg)| <= 1/sqrt2, so dC_r/dR >= 0.33356756 >0. The nominal pitch centerline is globally injective. This does not prove finite slot wall shape or roller clearance.'),mixed_phase_certificate=dict(pairs=cert,global_minimum_gap_mm=min(x['all_independent_R_ge31_q0to90_gap_mm'] for x in cert),mixed_minimum_gap_mm=min(min(x['A_fold_B_radial_gap_mm'],x['A_radial_B_fold_gap_mm']) for x in cert),all_fold_minimum_gap_mm=min(x['both_fold_R_ge66_gap_mm'] for x in cert),independent_Rodrigues_projection_sample_minimum_slack_mm=sample_min_slack,scope='All 28 FORM02-contained bare petal solids; arbitrary independent R>=31 and q0..90. No added screws/root/hub/guide/camera/wire geometry.'),rectangle_counterexample=rectangle,ideal_differential=lever,original_synchronous_dynamics=dynamic,bernstein_synchronous_dynamics=bernstein_dynamic,bernstein_nominal_polynomial_extrema=polynomial_extrema,manufacturing_release=False)
(W/'review.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
