#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""R5-MOTION02: exact seven-segment trajectory with frozen LINK01 geometry.

Read-only parent inputs. No hardware, controller or CAD is modified.
NumPy/SciPy/Matplotlib required. Run from any cwd; writes only generated/r5-motion02.
"""
from pathlib import Path
import csv, hashlib, importlib.util, json, math
import numpy as np
from scipy.integrate import cumulative_trapezoid
from scipy.optimize import brentq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/r5-motion02'
LINK=ROOT/'engineering/generated/r5-link01/study.json'
SCRIPT=ROOT/'engineering/r5_link01.py'
G=9.80665; LEAD=.0025; JM=4.808e-6; KT=.0281; C0=.00204; CV=.000000924; RLL=.253
DURATIONS=np.array([.05,.10,.05,.10,.05,.10,.05]); SIGNS=np.array([1,0,-1,0,-1,0,1])
EDGES=np.r_[0,np.cumsum(DURATIONS)]
STROKE=.040
GRAVITY={'zero':[0,0,0],'minus_Z':[0,0,-G],'minus_X':[-G,0,0],'minus_Y':[0,-G,0]}
plt.rcParams.update({'svg.hashsalt':'R5-MOTION02','svg.fonttype':'none','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
integ=lambda y,t:float(np.trapezoid(y,t))
def dump(name,data): (OUT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def table(name,rows):
 with (OUT/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def figure(fig,name):
 fig.tight_layout();fig.savefig(OUT/(name+'.svg'),metadata={'Date':None});fig.savefig(OUT/(name+'.png'),dpi=150);plt.close(fig)
def propagated(jerk_scale):
 """Exact polynomial integration of each constant-jerk interval, positive leg."""
 states=[[0.,0.,0.]]
 for dt,sign in zip(DURATIONS,SIGNS):
  x,v,a=states[-1]; j=jerk_scale*sign
  states.append([x+v*dt+a*dt**2/2+j*dt**3/6,v+a*dt+j*dt**2/2,a+j*dt])
 return np.array(states)
JERK=STROKE/propagated(1)[-1,0]
BOUNDARY=propagated(JERK)
def leg7(t):
 t=np.asarray(t);idx=np.clip(np.searchsorted(EDGES,t,side='right')-1,0,6);u=t-EDGES[idx];s=BOUNDARY[idx];j=JERK*SIGNS[idx]
 return s[...,0]+s[...,1]*u+s[...,2]*u*u/2+j*u**3/6,s[...,1]+s[...,2]*u+j*u*u/2,s[...,2]+j*u,j

def trajectory(name,t):
 t=np.asarray(t);opening=t<=.5;u=np.where(opening,t,t-.5);sgn=np.where(opening,-1.,1.)
 if name=='seven_segment': z,v,a,j=leg7(u)
 else:
  h=u/.5;z=STROKE*h**3*(10+h*(-15+6*h));v=STROKE*30*h*h*(1-h)**2/.5
  a=STROKE*60*h*(1-h)*(1-2*h)/.5**2;j=STROKE*(60-360*h+360*h*h)/.5**3
 # Analytic zero boundary states are restored exactly after floating-point evaluation.
 endpoint=np.isclose(t,0,rtol=0,atol=1e-14)|np.isclose(t,.5,rtol=0,atol=1e-14)|np.isclose(t,1,rtol=0,atol=1e-14)
 v=np.where(endpoint,0.,v);a=np.where(endpoint,0.,a)
 return np.where(opening,-.040-z,-.080+z),sgn*v,sgn*a,sgn*j

def gravity_torque(kind,q,phi,mirror,masses,g,frame):
 m=masses[kind];er,et,ez=frame(phi);rx,ry,rz=m['COM_from_pivot_local_m'];rq=(rx*np.cos(q)-rz*np.sin(q))[:,None]*er+(mirror*ry)*et+(rx*np.sin(q)+rz*np.cos(q))[:,None]*ez
 tg=np.cross(rq,m['mass_kg']*np.array(g))@(-et)
 U=-m['mass_kg']*(rq@np.array(g))
 return tg,U

def evaluate(name,t,link,parameters,masses):
 x,v,a,j=trajectory(name,t);states={};M=np.zeros(len(t));C=np.zeros(len(t));inertial=np.zeros(len(t));KE=np.zeros(len(t))
 for kind,p in parameters.items():
  q=link.inverse(x*1000,p);_,D,E,_,_=link.direct(q,p);qp=1000/D;qpp=-1e6*E/D**3;qd=qp*v;qdd=qp*a+qpp*v*v
  states[kind]=dict(q=q,qp=qp,qpp=qpp,qd=qd,qdd=qdd)
  J=masses[kind]['J_hinge_kg_m2'];M+=2*J*qp**2;C+=2*J*qp*qpp*v*v;inertial+=2*J*qdd*qp;KE+=J*qd*qd
 omega=2*math.pi*v/LEAD;alpha=2*math.pi*a/LEAD;n=60*v/LEAD;fr=(C0+CV*abs(n))*np.sign(v)
 out=dict(t=t,x=x,v=v,a=a,j=j,states=states,equivalent_M=M,nonlinear_C=C,inertial_F=inertial,omega=omega,alpha=alpha,rpm=n,fr=fr,KE_petal=KE,gravity={})
 assert max(abs(inertial-(M*a+C)))<1e-9
 for label,g in GRAVITY.items():
  F=inertial.copy();U=np.zeros(len(t));ftau={}
  for fid,kind,phi,mirror in link.FINGERS:
   s=states[kind];tg,Ui=gravity_torque(kind,s['q'],phi,mirror,masses,g,link.frame)
   tau=masses[kind]['J_hinge_kg_m2']*s['qdd']-tg;ftau[fid]=tau;F-=tg*s['qp'];U+=Ui
  tau=F*LEAD/(2*math.pi)+JM*alpha;em=tau+fr;P=tau*omega;Pem=em*omega;E=KE+U+.5*JM*omega*omega
  out['gravity'][label]=dict(F=F,tau=tau,em=em,P=P,Pem=Pem,E=E,U=U,finger_tau=ftau)
 return out

def stats(d,g):
 t=d['t'];v=d['gravity'][g];I=v['em']/KT;P=v['P'];Pem=v['Pem'];rms=lambda y:math.sqrt(integ(y*y,t)/(t[-1]-t[0]))
 return dict(trajectory=d['name'],gravity_head=g,peak_slider_velocity_mm_s=float(max(abs(d['v']))*1000),peak_slider_accel_m_s2=float(max(abs(d['a']))),peak_slider_jerk_m_s3=float(max(abs(d['j']))),peak_motor_rpm=float(max(abs(d['rpm']))),RMS_motor_rpm=rms(d['rpm']),peak_slider_force_N=float(max(abs(v['F']))),RMS_slider_force_N=rms(v['F']),ideal_peak_motor_torque_Nm=float(max(abs(v['tau']))),ideal_RMS_motor_torque_Nm=rms(v['tau']),with_motor_friction_peak_torque_Nm=float(max(abs(v['em']))),with_motor_friction_RMS_torque_Nm=rms(v['em']),catalogue_equivalent_peak_current_A=float(max(abs(I))),catalogue_equivalent_RMS_current_A=rms(I),ideal_positive_energy_J=integ(np.maximum(P,0),t),ideal_braking_energy_J=integ(np.maximum(-P,0),t),ideal_positive_peak_power_W=float(max(P)),ideal_braking_peak_power_W=float(max(-P)),with_motor_friction_positive_energy_J=integ(np.maximum(Pem,0),t),with_motor_friction_braking_energy_J=integ(np.maximum(-Pem,0),t),motor_friction_energy_J=integ(d['fr']*d['omega'],t),conditional_mean_copper_W_if_Ieq_is_phase_amplitude=.75*RLL*rms(I)**2,conditional_mean_copper_W_if_Ieq_is_phase_RMS=1.5*RLL*rms(I)**2,peak_motor_rotor_encoder_kinetic_energy_J=float(max(.5*JM*d['omega']**2)),maximum_cumulative_energy_audit_error_J=float(max(abs(cumulative_trapezoid(P,t,initial=0)-(v['E']-v['E'][0])))),cycle_energy_residual_J=integ(P,t)-float(v['E'][-1]-v['E'][0]))

def independent_q(x,p):
 """Independent scalar rod-length closure, no LINK01 inverse or derivatives."""
 d=(p['root_radius_mm']-p['slider_ear_radius_mm'])/1000;a=p['crank_mm']/1000;L=p['rod_mm']/1000;phase=p['phase_rad']
 def closure(q):return (d+a*math.cos(q+phase))**2+(a*math.sin(q+phase)-x)**2-L*L
 # Extension around endpoints supports central finite differences; same negative-Z rod branch.
 return brentq(closure,-.02,math.radians(p['q_closed_deg'])+.02,xtol=5e-15)

def independent_audit(link,params,mass,series):
 report=[];h=1e-6
 def q5(x,p):
  vals=np.array([independent_q(x+k*h,p) for k in [-2,-1,0,1,2]])
  first=(vals[0]-8*vals[1]+8*vals[3]-vals[4])/(12*h)
  second=(-vals[0]+16*vals[1]-30*vals[2]+16*vals[3]-vals[4])/(12*h*h)
  return vals[2],first,second
 for kind,p in params.items():
  e0=[];e1=[];e2=[]
  for x in np.linspace(-.08,-.04,129):
   q,qp,qpp=q5(x,p);ql=float(link.inverse(x*1000,p));_,D,E,_,_=link.direct(ql,p)
   e0.append(abs(q-ql));e1.append(abs(qp-1000/D));e2.append(abs(qpp+1e6*E/D**3))
  report.append(dict(check='independent rod closure and five-point spatial derivatives',kind=kind,step_m=h,positions=129,maximum_q_error_rad=max(e0),maximum_qprime_error_rad_m=max(e1),maximum_qdoubleprime_error_rad_m2=max(e2)))
 # Independent Lagrange force: M computed from numerical q', U from Cartesian COM.
 def MU(x,g):
  qs={k:q5(x,p) for k,p in params.items()};M=0.;U=0.
  for fid,kind,phi,mirror in link.FINGERS:
   m=mass[kind];q,qp,_=qs[kind];rx,ry,rz=m['COM_from_pivot_local_m'];ph=math.radians(phi)
   r=np.array([(rx*math.cos(q)-rz*math.sin(q))*math.cos(ph)-mirror*ry*math.sin(ph),(rx*math.cos(q)-rz*math.sin(q))*math.sin(ph)+mirror*ry*math.cos(ph),rx*math.sin(q)+rz*math.cos(q)])
   M+=m['J_hinge_kg_m2']*qp*qp;U-=m['mass_kg']*np.dot(r,g)
  return M,U
 for name,d in series.items():
  indices=np.linspace(0,len(d['t'])-1,81,dtype=int)
  for label,g in GRAVITY.items():
   errors=[]
   for i in indices:
    x=d['x'][i];a=d['a'][i];v=d['v'][i];vals=[MU(x+k*h,g) for k in [-2,-1,0,1,2]]
    Mp=(vals[0][0]-8*vals[1][0]+8*vals[3][0]-vals[4][0])/(12*h);Up=(vals[0][1]-8*vals[1][1]+8*vals[3][1]-vals[4][1])/(12*h)
    errors.append(abs(vals[2][0]*a+.5*Mp*v*v+Up-d['gravity'][label]['F'][i]))
   report.append(dict(check='independent finite-difference Lagrange force',trajectory=name,gravity_head=label,points=len(indices),maximum_force_error_N=max(errors)))
  # Independent time-domain differentiation, excluding jerk boundaries and endpoints.
  dt=d['t'][1]-d['t'][0];mask=(d['t']>2*dt)&(d['t']<1-2*dt)
  edges=np.r_[EDGES,EDGES+.5] if name=='seven_segment' else np.array([0,.5,1])
  for edge in edges:mask&=abs(d['t']-edge)>3*dt
  for kind in params:
   q=d['states'][kind]['q'];qd=(np.roll(q,2)-8*np.roll(q,1)+8*np.roll(q,-1)-np.roll(q,-2))/(12*dt)
   qdd=(-np.roll(q,2)+16*np.roll(q,1)-30*q+16*np.roll(q,-1)-np.roll(q,-2))/(12*dt*dt)
   report.append(dict(check='five-point time derivatives away from joins',trajectory=name,kind=kind,step_s=float(dt),maximum_qdot_error_rad_s=float(max(abs(qd[mask]-d['states'][kind]['qd'][mask]))),maximum_qddot_error_rad_s2=float(max(abs(qdd[mask]-d['states'][kind]['qdd'][mask])))))
 return report

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 spec=importlib.util.spec_from_file_location('r5_link01_readonly',SCRIPT);link=importlib.util.module_from_spec(spec);spec.loader.exec_module(link)
 source=json.loads(LINK.read_text());params=source['parameters'];masses=source['known_material_inputs']
 # Bound on .5 s duration and nonzero end state is tested at full machine precision.
 assert abs(sum(DURATIONS)-.5)<1e-14 and abs(BOUNDARY[-1,0]-.04)<1e-14 and max(abs(BOUNDARY[-1,1:]))<1e-14
 t=np.linspace(0,1,40001);series={};rows=[];fingerrows=[];convergence=[];boundary=[]
 for name in ['quintic','seven_segment']:
  d=evaluate(name,t,link,params,masses);d['name']=name;series[name]=d
  fine=evaluate(name,np.linspace(0,1,80001),link,params,masses);fine['name']=name
  for g in GRAVITY:
   s=stats(d,g);sf=stats(fine,g);rows.append(s)
   convergence.append(dict(trajectory=name,gravity_head=g,samples=40001,finer_samples=80001,peak_torque_change_Nm=abs(s['ideal_peak_motor_torque_Nm']-sf['ideal_peak_motor_torque_Nm']),RMS_torque_change_Nm=abs(s['ideal_RMS_motor_torque_Nm']-sf['ideal_RMS_motor_torque_Nm']),braking_energy_change_J=abs(s['ideal_braking_energy_J']-sf['ideal_braking_energy_J']),maximum_cumulative_energy_error_J=s['maximum_cumulative_energy_audit_error_J']))
  for kind,st in d['states'].items():
   fr=dict(trajectory=name,kind=kind,maximum_speed_deg_s=float(max(abs(np.degrees(st['qd'])))),maximum_accel_rad_s2=float(max(abs(st['qdd']))),maximum_body_inertial_torque_Nm=float(max(abs(masses[kind]['J_hinge_kg_m2']*st['qdd']))),maximum_missing_nonlinear_accel_term_rad_s2=float(max(abs(st['qpp']*d['v']**2))))
   for g in GRAVITY:
    for fid,typ,_,_ in link.FINGERS:
     if typ==kind:fr[g+'_'+fid+'_peak_total_torque_Nm']=float(max(abs(d['gravity'][g]['finger_tau'][fid])))
   fingerrows.append(fr)
  for edge in sorted(set(np.r_[EDGES,EDGES+.5].tolist())):
   if edge>1+1e-12:continue
   xx,vv,aa,jj=trajectory(name,np.array([edge]));boundary.append(dict(trajectory=name,t_s=float(edge),x_mm=float(xx[0]*1000),v_mm_s=float(vv[0]*1000),a_m_s2=float(aa[0]),j_right_or_endpoint_m_s3=float(jj[0])))
  times=[]
  for i in range(0,len(t),20):
   r=dict(t_s=float(t[i]),slider_z_mm=float(d['x'][i]*1000),slider_velocity_mm_s=float(d['v'][i]*1000),slider_accel_m_s2=float(d['a'][i]),slider_jerk_m_s3=float(d['j'][i]),motor_rpm=float(d['rpm'][i]),equivalent_mass_kg=float(d['equivalent_M'][i]),nonlinear_force_N=float(d['nonlinear_C'][i]))
   for kind,s in d['states'].items():r.update({kind+'_q_deg':float(math.degrees(s['q'][i])),kind+'_velocity_rad_s':float(s['qd'][i]),kind+'_acceleration_rad_s2':float(s['qdd'][i])})
   for g,gs in d['gravity'].items():r.update({g+'_slider_force_N':float(gs['F'][i]),g+'_motor_torque_ideal_Nm':float(gs['tau'][i]),g+'_motor_torque_friction_Nm':float(gs['em'][i]),g+'_catalogue_equivalent_current_A':float(gs['em'][i]/KT),g+'_ideal_power_W':float(gs['P'][i])})
   times.append(r)
  table(name+'-cycle.csv',times)
 # Finger tables are rectangular despite different finger IDs by kind.
 keys=list(dict.fromkeys(k for r in fingerrows for k in r));fingerrows=[{k:r.get(k) for k in keys} for r in fingerrows]
 table('comparison.csv',rows);table('finger-motion.csv',fingerrows);table('boundary-states.csv',boundary);table('convergence.csv',convergence)
 seg=[]
 for i in range(7):seg.append(dict(segment=i+1,start_s=float(EDGES[i]),duration_s=float(DURATIONS[i]),jerk_m_s3=float(SIGNS[i]*JERK),x_start_mm=float(BOUNDARY[i,0]*1000),v_start_mm_s=float(BOUNDARY[i,1]*1000),a_start_m_s2=float(BOUNDARY[i,2]),x_end_mm=float(BOUNDARY[i+1,0]*1000),v_end_mm_s=float(BOUNDARY[i+1,1]*1000),a_end_m_s2=float(BOUNDARY[i+1,2])))
 table('positive-leg-segments.csv',seg)
 # Unknown screw/coupler inertia and slider mass remain explicit sensitivities.
 sens=[]
 for name,d in series.items():
  for mass in [0,.1,.2]:
   for Js in [0,5e-7,1e-6,1.5e-6]:
    for eta in [1,.65,.85]:
     F=d['gravity']['minus_Z']['F']+mass*d['a'];tau=F*LEAD/(2*math.pi)+(JM+Js)*d['alpha'];fr=d['fr'];con=abs(F)*LEAD/(2*math.pi*eta)+(JM+Js)*abs(d['alpha'])+abs(fr)
     sens.append(dict(trajectory=name,gravity_head='minus_Z',assumed_slider_mass_kg=mass,assumed_screw_coupler_J_kg_m2=Js,assumed_dynamic_efficiency=eta,peak_absolute_sum_torque_bound_Nm=float(max(con)),RMS_absolute_sum_torque_bound_Nm=math.sqrt(integ(con*con,t)),signed_ideal_peak_torque_Nm=float(max(abs(tau))),signed_ideal_RMS_torque_Nm=math.sqrt(integ(tau*tau,t)),ideal_braking_energy_J=integ(np.maximum(-tau*d['omega'],0),t),scope='unmeasured sensitivity inputs; absolute-sum bound is not actual RMS; efficiency is not static kappa'))
 table('missing-hardware-sensitivity.csv',sens)
 regen=[];current=[]
 for r in rows:
  E=r['ideal_braking_energy_J']
  for C in [.001,.0047,.010]:regen.append(dict(trajectory=r['trajectory'],gravity_head=r['gravity_head'],lumped_entire_cycle_braking_J=E,assumed_initial_bus_V=24,assumed_capacitance_F=C,lossless_lumped_bus_V=math.sqrt(24**2+2*E/C),scope='mechanical energy-only illustration; not bus capture prediction or stop sizing'))
  current.append(dict(trajectory=r['trajectory'],gravity_head=r['gravity_head'],catalogue_equivalent_peak_A=r['catalogue_equivalent_peak_current_A'],catalogue_equivalent_RMS_over_cycle_A=r['catalogue_equivalent_RMS_current_A'],phase_peak_if_Ieq_means_amplitude_A=r['catalogue_equivalent_peak_current_A'],phase_RMS_envelope_peak_if_Ieq_means_amplitude_A=r['catalogue_equivalent_peak_current_A']/math.sqrt(2),phase_peak_if_Ieq_means_phase_RMS_A=r['catalogue_equivalent_peak_current_A']*math.sqrt(2),phase_RMS_envelope_peak_if_Ieq_means_phase_RMS_A=r['catalogue_equivalent_peak_current_A'],condition='alternative conventions, not a physical confidence interval; phase reference remains unverified'))
 table('regeneration-sensitivity.csv',regen);table('current-convention-sensitivity.csv',current)
 audit=independent_audit(link,params,masses,series);dump('independent-audit.json',audit)
 checks=[]
 def check(name,ok,details):checks.append(dict(name=name,pass_=bool(ok),details=details));assert ok,name
 check('seven segment exact displacement/time/endpoint velocity/acceleration',abs(BOUNDARY[-1,0]-.04)<1e-14 and max(abs(BOUNDARY[-1,1:]))<1e-14 and abs(EDGES[-1]-.5)<1e-14,BOUNDARY[-1].tolist())
 check('derived jerk and maxima agree with proposed numbers',abs(JERK-160/9)<1e-12 and abs(max(BOUNDARY[:,1])-2/15)<1e-12 and abs(max(BOUNDARY[:,2])-8/9)<1e-12,dict(jerk=JERK,vmax=max(BOUNDARY[:,1]),amax=max(BOUNDARY[:,2])))
 for name,d in series.items():
  check(name+' correct full-cycle endpoints',max(abs(d['x'][[0,20000,40000]]-[-.04,-.08,-.04]))<1e-12 and max(abs(d['v'][[0,20000,40000]]))<1e-12 and max(abs(d['a'][[0,20000,40000]]))<1e-12,'closed -> open -> closed; zero velocity and acceleration at all three')
  # Trapezoidal integration deliberately independent of analytic x(t).
  vi=cumulative_trapezoid(d['a'],t,initial=0);xi=d['x'][0]+cumulative_trapezoid(d['v'],t,initial=0)
  check(name+' numerical integration',max(abs(vi-d['v']))<1e-7 and max(abs(xi-d['x']))<1e-9,dict(velocity_error_m_s=float(max(abs(vi-d['v']))),position_error_m=float(max(abs(xi-d['x'])))))
 for r in audit:
  if 'maximum_q_error_rad' in r:ok=r['maximum_q_error_rad']<1e-11 and r['maximum_qprime_error_rad_m']<1e-6 and r['maximum_qdoubleprime_error_rad_m2']<.02
  elif 'maximum_force_error_N' in r:ok=r['maximum_force_error_N']<1e-4
  else:ok=r['maximum_qdot_error_rad_s']<1e-7 and r['maximum_qddot_error_rad_s2']<1e-4
  check(r['check']+' '+r.get('trajectory','')+' '+r.get('kind',r.get('gravity_head','')),ok,r)
 for r in convergence:check('grid convergence '+r['trajectory']+' '+r['gravity_head'],r['peak_torque_change_Nm']<1e-6 and r['RMS_torque_change_Nm']<1e-7 and r['braking_energy_change_J']<1e-6 and r['maximum_cumulative_energy_error_J']<1e-6,r)
 # Complete round trip energy balance; no conservative mechanism can create net cycle work.
 for r in rows:check('energy balance '+r['trajectory']+' '+r['gravity_head'],abs(r['cycle_energy_residual_J'])<1e-9 and abs(r['with_motor_friction_positive_energy_J']-r['with_motor_friction_braking_energy_J']-r['motor_friction_energy_J'])<1e-9,r['cycle_energy_residual_J'])
 fig,axs=plt.subplots(4,1,figsize=(9,10),sharex=True)
 for name,d in series.items():
  label='Quintic (reference)' if name=='quintic' else 'Seven-segment candidate'
  for ax,y in zip(axs,[d['x']*1000,d['rpm'],d['a'],d['j']]):ax.plot(t,y,label=label,lw=1.5)
 for ax,lab in zip(axs,['Slider Z (mm)','Motor speed (rpm)','Slider accel. (m/s²)','Slider jerk (m/s³)']):ax.set_ylabel(lab);ax.grid(alpha=.25)
 axs[1].axhline(3500,color='#a83a33',ls=':',label='3500 rpm catalogue range lower end');axs[1].axhline(-3500,color='#a83a33',ls=':');axs[0].legend();axs[1].legend(fontsize=8,loc='upper right');axs[-1].set_xlabel('Cycle time (s)');fig.suptitle('R5-MOTION02 | Frozen LINK01 | 40 mm per 0.5 s | No dwell');figure(fig,'trajectory-comparison')
 fig,axs=plt.subplots(3,2,figsize=(12,10),sharex=True)
 for name,d in series.items():
  label='Quintic' if name=='quintic' else 'Seven-segment'
  for col,kind in enumerate(params):
   s=d['states'][kind];axs[0,col].plot(t,np.degrees(s['q']),label=label);axs[1,col].plot(t,np.degrees(s['qd']));axs[2,col].plot(t,s['qdd'])
 for col,k in enumerate(params):axs[0,col].set_title(k.capitalize());axs[2,col].set_xlabel('Cycle time (s)')
 for row,lab in enumerate(['Angle (deg)','Speed (deg/s)','Accel. (rad/s²)']):
  for col in range(2):axs[row,col].set_ylabel(lab);axs[row,col].grid(alpha=.25)
 axs[0,0].legend();fig.suptitle('Actual nonlinear q(x); upper 105°, lower 113°');figure(fig,'finger-comparison')
 fig,axs=plt.subplots(3,1,figsize=(9,8),sharex=True)
 for name,d in series.items():
  g=d['gravity']['minus_Z'];lab='Quintic' if name=='quintic' else 'Seven-segment'
  axs[0].plot(t,g['F'],label=lab);axs[1].plot(t,g['em']*1000);axs[2].plot(t,g['P'])
 for ax,lab in zip(axs,['Known petal axial force (N)','Motor torque + friction (mNm)','Ideal shaft power (W)']):ax.set_ylabel(lab);ax.grid(alpha=.25)
 axs[0].legend();axs[-1].set_xlabel('Cycle time (s)');fig.suptitle('Head gravity −Z | Known petals + motor/encoder | Screw/links excluded');figure(fig,'dynamics-comparison')
 sources=[]
 for name,url,local,pages in [
  ('KSS technical description','https://kssballscrew.com/us/pdf/catalog/BS_Technical_Description.pdf','../../work/r5-slider-hardware01/kss_technical.pdf','A816 / PDF p8'),
  ('KSS SG0802.5 catalogue','https://kssballscrew.com/us/pdf/catalog/A219.pdf','../../work/r5-slider-hardware01/kss_sg0802p5.pdf','A219'),
  ('FAULHABER 3274 BP4','https://www.faulhaber.com/fileadmin/Import/Media/EN_3274_BP4_DFF.pdf','../../work/fast-drive01/3274.pdf','p1'),
  ('FAULHABER IE3-1024 L','https://www.faulhaber.com/fileadmin/Import/Media/EN_IE3-1024L_DFF.pdf','../../work/fast-drive01/IE3L.pdf','p1'),
  ('FAULHABER brushless technical information','https://eshop.faulhaber.com/media/39/ea/a1/1755094024/EN_TI_BRUSHLESS_DC-MOTORS.pdf','../../work/r5-head-servo01/faul-bldc-ti.pdf','current and torque definitions')]:
  sources.append(dict(title=name,url=url,pages=pages,sha256=sha(ROOT/local) if (ROOT/local).exists() else None,retrieved='2026-09-27'))
 study=dict(revision='R5-MOTION02',license='CC-BY-NC-4.0',required_notice='Odradek — Auromix contributors (https://github.com/Auromix/odradek)',status='numerical trajectory candidate; no hardware acceptance',script_sha256=sha(__file__),input_hashes={str(p.relative_to(ROOT)):sha(p) for p in [LINK,SCRIPT,ROOT/'engineering/generated/r5-petal-form01/study.json',ROOT/'engineering/generated/r5-link01/common90-contact-summary.csv',ROOT/'engineering/electronics/r5-slider-hardware01/budget.json']},official_sources=sources,geometry=params,known_material_inputs=masses,trajectory=dict(positive_leg_duration_s=.5,full_cycle_duration_s=1,stroke_m=.04,segment_durations_s=DURATIONS.tolist(),jerk_signs=SIGNS.tolist(),jerk_m_s3=JERK,peak_velocity_m_s=float(max(BOUNDARY[:,1])),peak_acceleration_m_s2=float(max(BOUNDARY[:,2])),smoothness='C2 position; jerk has finite steps. No endpoint dwell.'),motor=dict(model='3274G024BP4',encoder='IE3-1024 L',direct_lead_m=LEAD,rotor_encoder_J_kg_m2=JM,Kt_catalogue_Nm_per_A=KT,current_normalization='catalogue equivalent only; phase RMS vs amplitude is unresolved; do not use as controller current setting',friction=dict(C0_Nm=C0,Cv_Nm_per_rpm=CV,zero_speed='set to zero at isolated zero-velocity samples; static friction uncharacterized'),phase_to_phase_R_ohm_at22C=RLL),comparison=rows,finger_motion=fingerrows,scope={'included':['four R5-PETAL-FORM01 known-material inertias and gravity','nonlinear LINK01 Jacobian and second derivative','3274 rotor + IE3 magnet inertia','optional catalogue motor friction estimate'],'excluded':['screw/coupler rotating inertia and actual efficiency','nut/slider/guide/rod/crank/hinge mass and friction','electronics, fasteners and cable inertia','gripped objects and contact force control','bridge and winding inductive dynamics','measured thermal installation and supplier acceleration approval'],'continuous_1Hz_thermal_duty_confirmed_by_user':False,'all_orientation_envelope':False,'gravity_scenarios':'zero,-Z,-X,-Y are four explicit fixed head orientations; moving base inertial loads excluded'},catalogue_screen=dict(screw='SG0802.5-129R170C5 candidate with support-end machining handled separately',catalogue_circulator_speed_range_rpm=[3500,4000],seven_segment_peak_rpm=3200,lower_range_end_margin_rpm=300,lower_range_end_margin_fraction=300/3500,quintic_peak_rpm=3600,conclusion='seven-segment below catalogue range lower end only; actual operating limit depends on acceleration/environment and smaller critical-speed limit',critical_speed_and_support='R5-SLIDER-HARDWARE01; not certified here'),holding=dict(reference_only='112 mm sphere, four q90 finite faces, mu=.4, force factor2; NOT full 50–120 mm box/bottle range',slider_force_N=287.17126214932495,ideal_motor_torque_Nm=.11426181471250892,unchanged_by_empty_trajectory=True),manufacturing_release=False,hardware_qualification=False)
 dump('study.json',study)
 dump('verification.json',dict(revision='R5-MOTION02',documentation_sha256=sha(ROOT/'docs/engineering/r5-motion02.md'),passed=all(c['pass_'] for c in checks),checks=checks,numerical_grid_points=40001,convergence_grid_points=80001,extrema='sampled with grid convergence; no continuous-interval extrema certificate',artifact_sha256={p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='verification.json'}))
 print(json.dumps({'comparison_minus_Z':[r for r in rows if r['gravity_head']=='minus_Z'],'checks':len(checks),'passed':True},indent=2))
if __name__=='__main__':main()
