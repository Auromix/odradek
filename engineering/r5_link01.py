#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""R5-LINK01 nominal slider/crank synthesis. Reference mechanism, not load release.

All geometric input/output is mm and radians unless the field names say otherwise.
Dynamics explicitly converts the axial Jacobian to rad/m. No parent generator runs.
"""
from pathlib import Path
import argparse,csv,hashlib,json,math,re
import numpy as np
from scipy.optimize import least_squares,brentq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/r5-link01'
FORM=ROOT/'engineering/generated/r5-petal-form01/study.json'
DRIVE=ROOT/'engineering/electronics/fast-drive01/budget.json'
DRIVE_SOURCE=ROOT/'docs/engineering/sources/fast-drive01.json'
G=9.80665
plt.rcParams.update({'svg.hashsalt':'R5-LINK01','svg.fonttype':'none','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
integ=lambda y,t:float(np.trapezoid(y,t))
def save(name,data): (OUT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def csvout(name,rows):
 with (OUT/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def figsave(fig,name):
 fig.tight_layout();fig.savefig(OUT/(name+'.svg'),metadata={'Date':None});fig.savefig(OUT/(name+'.png'),dpi=150);plt.close(fig)

def direct(q,p):
 """x(q), dx/dq, d²x/dq², rod radial/axial projection for rear-rod branch."""
 a=p['crank_mm'];L=p['rod_mm'];psi=p['phase_rad']+np.asarray(q);u=p['root_radius_mm']-p['slider_ear_radius_mm']+a*np.cos(psi)
 disc=L*L-u*u
 if np.any(disc<=0):raise ValueError('rod cannot reach, or axial branch tangent')
 w=np.sqrt(disc);s=np.sin(psi);c=np.cos(psi)
 x=a*s-w;D=a*c-a*u*s/w;E=-a*s-a*u*c/w+a*a*L*L*s*s/w**3
 return x,D,E,u,w

def inverse(x,p):
 """Explicit continuous negative-acos branch; q=0 at specified open pose."""
 x=np.asarray(x);d=p['root_radius_mm']-p['slider_ear_radius_mm'];a=p['crank_mm'];L=p['rod_mm'];rho=np.sqrt(d*d+x*x)
 argument=(L*L-d*d-a*a-x*x)/(2*a*rho)
 if np.any(abs(argument)>1+1e-12):raise ValueError('unreachable x')
 psi=-np.arccos(np.clip(argument,-1,1))-np.arctan2(x,d)
 return psi-p['phase_rad']

def synthesize(q_closed_deg=105,x_open_mm=-80,x_closed_mm=-40,rod_mm=72.5,root_radius_mm=60,slider_ear_radius_mm=20):
 """Solve crank radius+phase for caller-specified endpoints. Not a branch certificate.

Returns a nominal rear-crank root, then caller must certify its complete interval.
If geometry is unsuitable ValueError is raised; changing q does not retain clearance.
"""
 delta=math.radians(q_closed_deg);d=root_radius_mm-slider_ear_radius_mm
 def residual(v):
  a,phase=v;psi=np.array([phase,phase+delta]);u=d+a*np.cos(psi);D=rod_mm**2-u*u
  if min(D)<=0:return np.array([100+abs(min(D)),100+abs(min(D))])
  return a*np.sin(psi)-np.sqrt(D)-[x_open_mm,x_closed_mm]
 solutions=[]
 for deg in [-120,-105,-95,-85,-70]:
  sol=least_squares(residual,[20,math.radians(deg)],bounds=([2,math.radians(-170)],[60,math.radians(-5)]),xtol=1e-13,ftol=1e-13,gtol=1e-13,max_nfev=500)
  if np.linalg.norm(sol.fun)<1e-7:
   a,phase=map(float,sol.x)
   if not any(abs(a-z[0])<1e-5 and abs(phase-z[1])<1e-6 for z in solutions):solutions.append((a,phase))
 if not solutions:raise ValueError('no rear-crank endpoint solution found by bounded multistart search; not a global nonexistence proof')
 # Deterministic selection favors phase near -90 degrees. Other roots are not certified.
 a,phase=min(solutions,key=lambda ap:abs(ap[1]+math.pi/2))
 return dict(root_radius_mm=root_radius_mm,slider_ear_radius_mm=slider_ear_radius_mm,rod_mm=rod_mm,crank_mm=a,phase_rad=phase,phase_deg=math.degrees(phase),q_closed_deg=q_closed_deg,x_open_mm=x_open_mm,x_closed_mm=x_closed_mm,endpoint_solution_count=len(solutions))

def synthesize_three_pose(q_closed_deg=105,x_at90_mm=-45.525,x_open_mm=-80,x_closed_mm=-40,root_radius_mm=62,slider_ear_radius_mm=20):
 """Exact 3x3 synthesis; caller must validate rear branch and singularity margins."""
 q=np.radians([0.,90.,q_closed_deg]);x=np.array([x_open_mm,x_at90_mm,x_closed_mm]);d=root_radius_mm-slider_ear_radius_mm
 A=np.column_stack([2*(d*np.cos(q)-x*np.sin(q)),-2*(d*np.sin(q)+x*np.cos(q)),np.ones(3)])
 u,v,K=np.linalg.solve(A,-d*d-x*x);a=math.hypot(u,v);L2=a*a-K
 if L2<=0:raise ValueError('three-pose system does not yield a real positive rod length')
 phase=math.atan2(v,u)
 return dict(root_radius_mm=root_radius_mm,slider_ear_radius_mm=slider_ear_radius_mm,rod_mm=math.sqrt(L2),crank_mm=a,phase_rad=phase,phase_deg=math.degrees(phase),q_closed_deg=q_closed_deg,x_open_mm=x_open_mm,x_closed_mm=x_closed_mm,x_at90_mm=x_at90_mm,method='exact linear 3x3 in crank Cartesian components u,v and K=a²-L²',linear_system_residual_max_mm2=float(max(abs(A@np.array([u,v,K])+d*d+x*x))))

class I:
 """Outward-rounded scalar interval arithmetic for a nominal branch certificate."""
 def __init__(self,lo,hi=None):self.lo=float(lo);self.hi=float(lo if hi is None else hi)
 @staticmethod
 def box(lo,hi):return I(np.nextafter(lo,-np.inf),np.nextafter(hi,np.inf))
 def __add__(s,o):
  o=o if isinstance(o,I) else I(o);return I.box(s.lo+o.lo,s.hi+o.hi)
 __radd__=__add__
 def __neg__(s):return I.box(-s.hi,-s.lo)
 def __sub__(s,o):return s+-asI(o)
 def __rsub__(s,o):return asI(o)+-s
 def __mul__(s,o):
  o=asI(o);a=[s.lo*o.lo,s.lo*o.hi,s.hi*o.lo,s.hi*o.hi];return I.box(min(a),max(a))
 __rmul__=__mul__
 def __truediv__(s,o):
  o=asI(o)
  if o.lo<=0<=o.hi:raise ValueError('interval division through zero')
  return s*I.box(1/o.hi,1/o.lo)
 def sqrt(s):
  if s.lo<=0:raise ValueError('nonpositive discriminant lower bound')
  return I.box(math.sqrt(s.lo),math.sqrt(s.hi))
 def out(s):return [s.lo,s.hi]
def asI(x):return x if isinstance(x,I) else I(x)
def trig(lo,hi,cos=False):
 offset=0 if cos else math.pi/2;fn=math.cos if cos else math.sin;values=[fn(lo),fn(hi)]
 for k in range(math.ceil((lo-offset)/math.pi),math.floor((hi-offset)/math.pi)+1):values.append((-1.)**k)
 return I.box(min(values),max(values))
def certify(p,n=4096):
 qend=math.radians(p['q_closed_deg']);a=p['crank_mm'];L=p['rod_mm'];d=p['root_radius_mm']-p['slider_ear_radius_mm'];bins=[]
 for q0,q1 in zip(np.linspace(0,qend,n+1)[:-1],np.linspace(0,qend,n+1)[1:]):
  lo=p['phase_rad']+q0;hi=p['phase_rad']+q1;s=trig(lo,hi);c=trig(lo,hi,True);u=d+a*c;w=(L*L-u*u).sqrt();D=a*c-a*u*s/w;E=-a*s-a*u*c/w+(a*a*L*L)*s*s/(w*w*w);sinmu=w*D/(a*L)
  bins.append((D,w,sinmu,E,u))
 Dmin=min(z[0].lo for z in bins);Dmax=max(z[0].hi for z in bins);wmin=min(z[1].lo for z in bins);smin=min(z[2].lo for z in bins)
 return dict(method='4096 outward-rounded interval enclosures over nominal q; analytic derivatives, no sampled-sign inference',interval_count=n,dx_dq_mm_rad_certified_interval=[Dmin,Dmax],rod_axial_projection_mm_certified_min=wmin,sin_transmission_angle_certified_min=smin,acute_transmission_angle_deg_certified_min=math.degrees(math.asin(max(-1,min(1,smin)))),monotonic_and_no_dead_point=bool(Dmin>0 and wmin>0),d2x_dq2_mm_rad2_certified_interval=[min(z[3].lo for z in bins),max(z[3].hi for z in bins)],rod_radial_projection_mm_certified_interval=[min(z[4].lo for z in bins),max(z[4].hi for z in bins)],tolerance_included=False)

def frame(phi):
 p=math.radians(phi);er=np.array([math.cos(p),math.sin(p),0.]);et=np.array([-math.sin(p),math.cos(p),0.]);ez=np.array([0.,0.,1.]);return er,et,ez
FINGERS=[('UR','upper',35,1),('UL','upper',145,-1),('LL','lower',225,-1),('LR','lower',315,1)]
def points(p,q,phi):
 er,et,ez=frame(phi);x=direct(q,p)[0];P=p['root_radius_mm']*er;B=P+p['crank_mm']*math.cos(p['phase_rad']+q)*er+p['crank_mm']*math.sin(p['phase_rad']+q)*ez;C=p['slider_ear_radius_mm']*er+x*ez
 return P,B,C

def source_mass():
 data=json.loads(FORM.read_text());out={}
 for kind in ['upper','lower']:
  v=data['parts'][kind]['known_material_subtotal'];r=np.array(v['COM_local_m'])-[0,0,.0035];J=float(v['inertia_COM_local_axes_kg_m2'][1][1]+v['mass_kg']*(r[0]**2+r[2]**2));out[kind]=dict(mass_kg=v['mass_kg'],COM_from_pivot_local_m=r.tolist(),J_hinge_kg_m2=J,scope='R5-PETAL-FORM01 known material only; assumed densities; electronics, fasteners, hinge, crank, rod, slider and drive excluded')
 return out

def continuous_bounds(p,phi):
 """Capsule/endpoint hull AABB over ALL q. Boxes are not swept-solid unions."""
 lo=p['phase_rad'];hi=lo+math.radians(p['q_closed_deg']);rad=p['root_radius_mm']+p['crank_mm']*trig(lo,hi,True);z=p['crank_mm']*trig(lo,hi);er,et,ez=frame(phi)
 bp=[(rad*er[0]).out(),(rad*er[1]).out(),z.out()];P=p['root_radius_mm']*er;C0=p['slider_ear_radius_mm']*er+[0,0,p['x_open_mm']];C1=p['slider_ear_radius_mm']*er+[0,0,p['x_closed_mm']]
 def hull(other,radius):
  return [[min(bp[i][0],*[v[i] for v in other])-radius for i in range(3)],[max(bp[i][1],*[v[i] for v in other])+radius for i in range(3)]]
 return dict(crank_pin_continuous_bbox_mm=[[a[0] for a in bp],[a[1] for a in bp]],rod_diameter5_capsule_continuous_bbox_mm=hull([C0,C1],2.5),crank_diameter8_capsule_continuous_bbox_mm=hull([P],4),method='exact sine/cosine critical-point extrema; moving rod contained in endpoint convex hull, expanded isotropically by reference radius',scope='reference rods/cranks only, no clevis, bearings, bolt heads, petal, camera, LED display, motor or cable')

def generate(params):
 OUT.mkdir(parents=True,exist_ok=True);mass=source_mass();cert={k:certify(p) for k,p in params.items()};assert all(x['monotonic_and_no_dead_point'] for x in cert.values());curves=[];summaries={};xgrid=np.linspace(-80,-40,2001)
 for kind,p in params.items():
  q=inverse(xgrid,p);xx,D,E,u,w=direct(q,p);qp=1/D;qpp=-E/D**3;assert max(abs(xx-xgrid))<1e-10;assert abs(q[0])<1e-10 and abs(math.degrees(q[-1])-p['q_closed_deg'])<1e-9
  error=max(abs((inverse(xgrid+1e-4,p)-inverse(xgrid-1e-4,p))/(2e-4)-qp));assert error<1e-8
  for i in range(0,len(q),2):curves.append(dict(kind=kind,slider_z_mm=xgrid[i],q_deg=math.degrees(q[i]),dq_dx_rad_mm=qp[i],d2q_dx2_rad_mm2=qpp[i],dx_dq_mm_rad=D[i],rod_angle_to_Z_deg=math.degrees(math.atan2(u[i],w[i])),acute_transmission_angle_deg=math.degrees(math.asin(min(1,abs(w[i]*D[i]/(p['crank_mm']*p['rod_mm'])))))))
  summaries[kind]=dict(q_open_deg=math.degrees(q[0]),q_closed_deg=math.degrees(q[-1]),qprime_open_rad_m=float(qp[0]*1000),qprime_closed_rad_m=float(qp[-1]*1000),closed_vs_open_torque_gain_at_same_branch_axial_force=float(D[-1]/D[0]),closed_dx_dq_mm_rad=float(D[-1]),maximum_dx_dq_mm_rad=float(max(D)),angle_at_maximum_dx_dq_deg=float(math.degrees(q[np.argmax(D)])),maximum_rod_angle_to_Z_deg=float(np.degrees(max(np.arctan2(u,w)))),finite_difference_first_derivative_error_rad_mm=error,common90_slider_z_mm=float(direct(math.pi/2,p)[0]),contact90_dq_dx_rad_m=float(1000/direct(math.pi/2,p)[1]),contact90_vs_open_torque_gain_at_same_branch_axial_force=float(direct(math.pi/2,p)[1]/D[0]))
 csvout('kinematics.csv',curves)
 # Endpoints are scalable inputs. Each new synthesis gets a full-domain certificate.
 scan=[]
 for deg in range(90,121,5):
  try:
   p=synthesize(deg,root_radius_mm=62);c=certify(p,1024);scan.append(dict(q_target_deg=deg,crank_mm=p['crank_mm'],phase_deg=p['phase_deg'],monotonic=c['monotonic_and_no_dead_point'],certified_min_transmission_deg=c['acute_transmission_angle_deg_certified_min'],passes_reference_transmission25deg=c['acute_transmission_angle_deg_certified_min']>=25,closed_dq_dx_rad_m=float(1000/direct(math.radians(deg),p)[1]),status='nominal endpoint solution; no petal closure/contact check'))
  except ValueError as e:scan.append(dict(q_target_deg=deg,crank_mm=None,phase_deg=None,monotonic=False,certified_min_transmission_deg=None,passes_reference_transmission25deg=False,closed_dq_dx_rad_m=None,status=str(e)))
 csvout('closure-angle-synthesis-scan.csv',scan)
 three_scan=[]
 for xm in sorted(set(np.arange(-55,-42,.25).tolist()+[-45.525])):
  row=dict(common90_slider_z_mm=xm)
  for kind,end in [('upper',105),('lower',113)]:
   try:
    p=synthesize_three_pose(end,xm);c=certify(p,512);row.update({kind+'_crank_mm':p['crank_mm'],kind+'_rod_mm':p['rod_mm'],kind+'_phase_deg':p['phase_deg'],kind+'_Dmin_mm_rad':c['dx_dq_mm_rad_certified_interval'][0],kind+'_transmission_min_deg':c['acute_transmission_angle_deg_certified_min'],kind+'_monotonic':c['monotonic_and_no_dead_point']})
   except ValueError:row.update({kind+'_crank_mm':None,kind+'_rod_mm':None,kind+'_phase_deg':None,kind+'_Dmin_mm_rad':None,kind+'_transmission_min_deg':None,kind+'_monotonic':False})
  three_scan.append(row)
 csvout('three-pose-common90-scan.csv',three_scan)
 comparisons=[]
 for pair in [(105,95),(105,113),(109,122)]:
  for kind,deg in zip(['upper','lower'],pair):
   try:
    p=synthesize(deg,root_radius_mm=62);c=certify(p,1024);x90=float(direct(math.pi/2,p)[0]);row=dict(pair=f'{pair[0]}/{pair[1]}',kind=kind,crank_mm=p['crank_mm'],phase_deg=p['phase_deg'],rod_mm=p['rod_mm'],root_radius_mm=62,q_target_deg=deg,x_at90_mm=x90,certified_min_dx_dq_mm_rad=c['dx_dq_mm_rad_certified_interval'][0],certified_min_transmission_deg=c['acute_transmission_angle_deg_certified_min'],monotonic=c['monotonic_and_no_dead_point'],status='two endpoint fit only; no shared90 guarantee; NOT primary candidate')
   except ValueError as exc:row=dict(pair=f'{pair[0]}/{pair[1]}',kind=kind,crank_mm=None,phase_deg=None,rod_mm=72.5,root_radius_mm=62,q_target_deg=deg,x_at90_mm=None,certified_min_dx_dq_mm_rad=None,certified_min_transmission_deg=None,monotonic=False,status=str(exc))
   comparisons.append(row)
 csvout('two-pose-comparisons.csv',comparisons)
 # Explicit reject: a crank phase that encounters a toggle inside the requested range.
 bad=dict(root_radius_mm=62,slider_ear_radius_mm=20,rod_mm=params['upper']['rod_mm'],crank_mm=20.,phase_rad=-math.pi,phase_deg=-180.,q_closed_deg=100.)
 qtoggle=brentq(lambda q:float(direct(q,bad)[1]),0,math.radians(100));badx=direct(qtoggle,bad)[0]
 rejected=dict(parameters=bad,reason='dx/dq changes sign: non-monotonic assembly branch with internal dead point; cannot use one-valued q(x)',toggle_q_deg=math.degrees(qtoggle),toggle_slider_z_mm=float(badx),dx_dq_open_mm_rad=float(direct(0,bad)[1]),dx_dq_end_mm_rad=float(direct(math.radians(100),bad)[1]))
 # Cycle is full closed -> open -> full closed, 0.5s each leg.
 t=np.linspace(0,1,20001);first=t<=.5;u=np.where(first,t,t-.5)/.5;h=u**3*(10+u*(-15+6*u));hd=30*u*u*(1-u)**2/.5;hdd=60*u*(1-u)*(1-2*u)/.5**2
 s=np.where(first,1-h,h);sd=np.where(first,-hd,hd);sdd=np.where(first,-hdd,hdd);x=-80+40*s;xd=.04*sd;xdd=.04*sdd;state={};motion=[]
 for kind,p in params.items():
  q=inverse(x,p);_,D,E,_,_=direct(q,p);qp=1000/D;qpp=-1e6*E/D**3;v=qp*xd;acc=qp*xdd+qpp*xd*xd;state[kind]=(q,qp,qpp,v,acc)
  motion.append(dict(kind=kind,q_stroke_deg=p['q_closed_deg'],peak_speed_deg_s=float(max(abs(np.degrees(v)))),peak_accel_rad_s2=float(max(abs(acc))),peak_accel_if_wrongly_drop_qdoubleprime_rad_s2=float(max(abs(qp*xdd))),body_J_kg_m2=mass[kind]['J_hinge_kg_m2'],body_inertial_peak_torque_Nm=float(max(abs(mass[kind]['J_hinge_kg_m2']*acc))),scope='R5 known material only; new mechanism inertia excluded'))
 # Multi-body virtual work; use actual R5 material COM, mirrored left Y, not old P16 mass.
 forces={};powerrows=[];Ms=np.zeros(len(t));Cs=np.zeros(len(t))
 for _,kind,_,_ in FINGERS:
  q,qp,qpp,v,acc=state[kind];J=mass[kind]['J_hinge_kg_m2'];Ms+=J*qp**2;Cs+=J*qp*qpp*xd**2
 inertial=np.zeros(len(t))
 for _,kind,_,_ in FINGERS:inertial+=mass[kind]['J_hinge_kg_m2']*state[kind][4]*state[kind][1]
 assert max(abs(inertial-(Ms*xdd+Cs)))<1e-10
 for name,g in [('zero',[0,0,0]),('minus_Z',[0,0,-G]),('minus_X',[-G,0,0]),('minus_Y',[0,-G,0])]:
  F=inertial.copy();Etot=np.zeros(len(t))
  for fid,kind,phi,mirror in FINGERS:
   q,qp,qpp,v,acc=state[kind];m=mass[kind]['mass_kg'];er,et,ez=frame(phi);rx,ry,rz=mass[kind]['COM_from_pivot_local_m'];ry*=mirror
   rq=(rx*np.cos(q)-rz*np.sin(q))[:,None]*er+ry*et+(rx*np.sin(q)+rz*np.cos(q))[:,None]*ez;axis=-et;tg=np.cross(rq,m*np.array(g))@axis;F-=tg*qp;Etot+=.5*mass[kind]['J_hinge_kg_m2']*v*v-m*(rq@np.array(g))
  P=F*xd;residual=integ(P,t)-float(Etot[-1]-Etot[0]);assert abs(residual)<1e-9;forces[name]=F
  powerrows.append(dict(gravity_head=name,peak_slider_force_abs_N=float(max(abs(F))),RMS_slider_force_N=math.sqrt(integ(F*F,t)),positive_mechanical_work_J=integ(np.maximum(P,0),t),braking_mechanical_work_J=integ(np.maximum(-P,0),t),positive_mechanical_peak_W=float(max(P)),braking_mechanical_peak_W=float(max(-P)),cycle_energy_residual_J=residual))
 csvout('motion.csv',motion);csvout('empty-slider-load.csv',powerrows)
 times=[]
 for i in range(0,len(t),20):
  row=dict(t_s=float(t[i]),slider_z_mm=float(x[i]),slider_velocity_mm_s=float(xd[i]*1000),slider_accel_mm_s2=float(xdd[i]*1000),equivalent_mass_kg=float(Ms[i]),nonlinear_force_N=float(Cs[i]),empty_force_minusZ_N=float(forces['minus_Z'][i]))
  for k,(q,qp,qpp,v,a) in state.items():row.update({k+'_q_deg':float(math.degrees(q[i])),k+'_velocity_rad_s':float(v[i]),k+'_accel_rad_s2':float(a[i])})
  times.append(row)
 csvout('cycle.csv',times)
 # Real direct-screw candidate numbers; efficiency is an explicit sensitivity.
 p_lead=.0025;Jm=4.8e-6+8e-9;omega=2*math.pi*xd/p_lead;alpha=2*math.pi*xdd/p_lead;dr=[]
 for slider_m in [0,.10,.20]:
  for Jscrew in [0,1e-6,5e-6]:
   for name,F0 in forces.items():
    F=F0+slider_m*xdd;tau=F*p_lead/(2*math.pi)+(Jm+Jscrew)*alpha;P=tau*omega
    for eta in [1,.65,.85]:
     conservative=abs(F)*p_lead/(2*math.pi*eta)+(Jm+Jscrew)*abs(alpha)
     dr.append(dict(gravity_head=name,assumed_slider_mass_kg=slider_m,assumed_screw_coupler_rotating_J_kg_m2=Jscrew,lead_mm=2.5,motor_gear_ratio=1,motor='3274G024BP4 + IE3-1024L',motor_encoder_J_kg_m2=Jm,peak_motor_rpm=float(max(abs(omega))*60/(2*math.pi)),assumed_motion_efficiency=eta,peak_motor_torque_absolute_sum_bound_Nm=float(max(conservative)),RMS_motor_torque_absolute_sum_bound_Nm=math.sqrt(integ(conservative**2,t)),ideal_signed_motor_peak_torque_Nm=float(max(abs(tau))),ideal_motor_positive_work_J=integ(np.maximum(P,0),t),ideal_motor_braking_work_J=integ(np.maximum(-P,0),t),scope='screw rotating inertia and slider mass are sensitivity inputs, not catalogue values; unknown friction and actual efficiency still absent'))
 csvout('direct-screw-dynamic-sensitivity.csv',dr)
 # Four equal balanced side contacts are only an explicit contact load scenario.
 contacts=[];wrenches=[];closedstate={k:direct(math.radians(p['q_closed_deg']),p) for k,p in params.items()}
 for mu in [.2,.4,.8]:
  for lever in [40,60,80,100,120,150]:
   N=2*2*G/(4*mu);Ft=2*2*G/4;Fn=0.;FU=0.;FL=0.;guide=np.zeros(3);rods=[]
   for fid,kind,phi,mirror in FINGERS:
    _,D,_,ur,wr=closedstate[kind];qp=1000/D;m=mass[kind];rx,ry,rz=m['COM_from_pivot_local_m'];grav=m['mass_kg']*G*math.hypot(rx,rz)
    normal=N*lever/1000;upper=normal+Ft*.03+grav;lower=max(0,normal-Ft*.03-grav);Fn+=normal*qp;FU+=upper*qp;FL+=lower*qp;Frod=upper*qp*params[kind]['rod_mm']/wr;radial=upper*qp*ur/wr;er=frame(phi)[0];guide+=radial*er;rods.append(Frod)
   torque=FU*p_lead/(2*math.pi);contacts.append(dict(payload_kg=2,contact_count=4,design_factor=2,assumed_mu=mu,normal_moment_arm_mm=lever,tangent_moment_arm_mm=30,normal_per_contact_N=N,normal_only_slider_force_N=float(Fn),slider_force_lower_N_with_tangent_gravity_bounds=float(FL),slider_force_upper_N_with_tangent_gravity_bounds=float(FU),ideal_screw_motor_holding_torque_upper_Nm=float(torque),minimum_static_transfer_kappa_for_0p140Nm_motor_budget=float(torque/.140),catalogue_motor_0p140Nm_is_graph_estimate_not_certified_head_limit=True,maximum_rod_compression_N_at_upper_bound=float(max(rods)),resultant_slider_lateral_reaction_upper_scenario_N=float(np.linalg.norm(guide)),kinematic_contact_pose='all fingers at reference full-closed angle; actual object contact may occur earlier and is NOT proven'))
   if mu==.4 and lever==60:wrenches.append(dict(assumed_mu=mu,normal_moment_arm_mm=lever,rod_compression_by_UR_UL_LL_LR_N=[float(z) for z in rods],slider_lateral_reaction_vector_N=guide.tolist(),scope='simultaneous positive per-finger upper torque scenario; not interval bound on arbitrary independently signed gravity/tangential reactions'))
 csvout('contact-screw-demand.csv',contacts);save('guide-load-example.json',wrenches)
 # Conditional root-provided common-90 sphere: radius56, centerZ65; face offset6.
 # Distinct upper/lower normal magnitudes cancel XY because phi is not central-symmetric.
 contact90=[];ratio=math.sin(math.radians(35))/math.sin(math.radians(45));center=np.array([0.,0.,.065])
 for mu in [.2,.4,.8]:
  Nu=2*2*G/(2*mu*(1+ratio));Nl=ratio*Nu;Fslider=0.;Qnormal=0.;guide=np.zeros(3);objforce=np.zeros(3);objmoment=np.zeros(3);details=[]
  for fid,kind,phi,mirror in FINGERS:
   N=Nu if kind=='upper' else Nl;Ft=mu*N;er,et,ez=frame(phi);point=.056*er+center;P=.062*er;object_force=-N*er+Ft*ez
   objforce+=object_force;objmoment+=np.cross(point-center,object_force)
   required_tau=-float(np.dot(np.cross(point-P,-object_force),-et))
   m=mass[kind];rz=m['COM_from_pivot_local_m'][2];gravity_required=-m['mass_kg']*G*rz
   _,D,_,ur,wr=direct(math.pi/2,params[kind]);fp=1000/D;Fbranch=(required_tau+gravity_required)*fp;rod=Fbranch*params[kind]['rod_mm']/wr;guide+=Fbranch*ur/wr*er
   Fslider+=Fbranch;Qnormal+=N*.065*fp
   details.append(dict(finger=fid,normal_N=N,tangent_N=Ft,required_contact_hinge_torque_Nm=required_tau,gravity_hinge_torque_Nm=gravity_required,dq_dx_rad_m=float(fp),slider_axial_contribution_N=float(Fbranch),rod_compression_N=float(rod)))
  force_res=objforce-[0,0,2*2*G];assert np.linalg.norm(force_res)<1e-10 and np.linalg.norm(objmoment)<1e-10
  tau=Fslider*.0025/(2*math.pi)
  contact90.append(dict(assumed_mu=mu,payload_kg=2,design_factor=2,contact_pose_q_deg=90,slider_z_mm=params['upper']['x_at90_mm'],sphere_radius_mm=56,sphere_center_head_mm=[0,0,65],normal_moment_arm_mm=65,tangent_moment_arm_mm=6,normal_only_slider_force_N=float(Qnormal),slider_force_including_actual_contact_sign_and_minusZ_material_gravity_N=float(Fslider),ideal_direct_screw_motor_static_torque_Nm=float(tau),required_static_kappa_for_motor_budget0p140Nm=float(tau/.140),force_balance_residual_N=force_res.tolist(),moment_balance_residual_Nm=objmoment.tolist(),slider_lateral_reaction_magnitude_N=float(np.linalg.norm(guide)),branches=details,scope='conditional exact point-contact wrench witness on common90 planes; finite petal face containment/collision is separate root study; friction coefficient unmeasured; no allowance for contact-position/force errors, rod friction or unknown parts'))
 save('common90-contact-witness.json',contact90)
 csvout('common90-contact-summary.csv',[{k:v for k,v in row.items() if k not in ['branches','force_balance_residual_N','moment_balance_residual_Nm']} for row in contact90])
 # Reference geometry and continuous radial-plane separation, not complete assembly collision proof.
 bounds={fid:continuous_bounds(params[k],phi) for fid,k,phi,_ in FINGERS};clear=[]
 for i,(fid,k,phi,_) in enumerate(FINGERS):
  for fid2,k2,phi2,_ in FINGERS[i+1:]:
   delta=abs((phi2-phi+180)%360-180);lower=2*20*math.sin(math.radians(delta)/2)-8
   clear.append(dict(pair=[fid,fid2],azimuth_separation_deg=delta,reference_rod_crank_cross_branch_clearance_lower_bound_mm=lower,method='all centerline points have radius>=20 and fixed radial plane; minimum XY distance of two rays outside radius20 minus two conservative radius4 capsules',includes='reference rods and crank bars only; slider common joints intentionally excluded'))
 # Nominal geometry snapshots: cylinders with arbitrary reference radii, not manufactured joints.
 cad=export_reference(params)
 # Plots.
 fig,axs=plt.subplots(2,2,figsize=(12,8))
 for kind,p in params.items():
  q=inverse(xgrid,p);_,D,E,ur,wr=direct(q,p);axs[0,0].plot(xgrid,np.degrees(q),label=kind);axs[0,1].plot(xgrid,1000/D,label=kind);axs[1,0].plot(xgrid,-1e6*E/D**3,label=kind);axs[1,1].plot(xgrid,np.degrees(np.arcsin(np.clip(wr*D/(p['crank_mm']*p['rod_mm']),-1,1))),label=kind)
 for ax,label in zip(axs.flat,['Finger angle [deg]','dq/dx [rad/m]','d²q/dx² [rad/m²]','Acute transmission angle [deg]']):ax.set_ylabel(label);ax.set_xlabel('Slider Z [mm]');ax.grid(alpha=.2);ax.legend()
 fig.suptitle('R5-LINK01 | True slider + fixed-length rods + offset cranks\nNominal rear branch; no linear mimic approximation');figsave(fig,'kinematics')
 fig,axs=plt.subplots(3,1,figsize=(11,9),sharex=True)
 for kind,(q,qp,qpp,v,acc) in state.items():axs[0].plot(t,np.degrees(q),label=kind);axs[1].plot(t,np.degrees(v),label=kind);axs[2].plot(t,acc,label=kind)
 for ax,label in zip(axs,['Finger angle [deg]','Finger speed [deg/s]','Finger acceleration [rad/s²]']):ax.set_ylabel(label);ax.grid(alpha=.2);ax.legend()
 axs[-1].set_xlabel('Closed → open → closed time [s]');fig.suptitle('R5-LINK01 | 0.5 s quintic slider stroke per direction\nFinger acceleration includes q″(x) · xdot²');figsave(fig,'motion')
 fig,axs=plt.subplots(1,2,figsize=(12,6))
 for ax,(kind,p) in zip(axs,params.items()):
  for xp,c in zip([-80,-45.525,-40],['#2166ac','#888888','#d6604d']):
   q=float(inverse(xp,p));P,B,C=points(p,q,0);ax.plot([P[0],B[0]],[P[2],B[2]],color=c,lw=5);ax.plot([C[0],B[0]],[C[2],B[2]],color=c,lw=2,label=f'q={math.degrees(q):.1f}°');ax.scatter([P[0],B[0],C[0]],[P[2],B[2],C[2]],color=c,s=25)
  ax.plot([20,20],[-80,-40],color='#222',ls='--');ax.set(xlabel='Radial coordinate [mm]',ylabel='Head Z / forward [mm]',title=kind,aspect='equal');ax.grid(alpha=.2);ax.legend()
 fig.suptitle('R5-LINK01 | Reference linkage centerlines\nSame slider range; fixed pivots R62; exact common 90° pose; reference bar sizes only');figsave(fig,'mechanism-side')
 result=dict(revision='R5-LINK01',license='CC-BY-NC-4.0',required_notice='Odradek — Auromix contributors (https://github.com/Auromix/odradek)',scope='nominal single-DOF no-contact mechanism; real nonlinear kinematics, not complete head/grip/manufacturing release',parameters=params,coordinate_contract=dict(head_Z='forward',root_plane_Z_mm=0,root_radius_mm=62,azimuths_deg={f:phi for f,k,phi,m in FINGERS},petal_local_hinge_mm=[0,0,3.5],petal_basis_at_open='local +X=er,+Y=et,+Z=ez; point=P+Rot(-et,q)*(x*er+y*et+(z-3.5)*ez)',positive_q_axis='-et, petal tip folds toward +Z',crank_pin='P+a*cos(phase+q)*er+a*sin(phase+q)*ez',slider_pin='20*er+x*ez; x=-80 open,-40 reference closed',left_petal_material='left silhouette may mirror local Y, but no electronic board is reflected by this transform'),branch_certificate=cert,kinematic_summary=summaries,motion_summary=motion,known_material_inputs=mass,empty_slider_load=powerrows,peak_slider_speed_mm_s=float(max(abs(xd))*1000),peak_slider_accel_mm_s2=float(max(abs(xdd))*1000),rejected_configuration=rejected,continuous_reference_bounds=bounds,reference_cross_branch_separation=clear,reference_cad=cad,common90_contact_witness=contact90,source_hashes={str(p.relative_to(ROOT)):sha(p) for p in [FORM,DRIVE,DRIVE_SOURCE]},script_sha256=sha(__file__),missing=['actual petal closure/object contacts','series elasticity or passive differential after first contact','rod/crank/slider/guide/hinge electronics mass and friction','controlled bearings, fasteners, screw end machining, static transfer and thermal performance','complete cameras/display/body/actuator swept interference','manufacturing tolerances, rod buckling, pin-bearing and fatigue substantiation'],manufacturing_release=False,grasp_2kg_pass=False)
 result['artifact_sha256']={p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='study.json'};save('study.json',result)
 print(json.dumps(dict(parameters=params,summary=summaries,motion=motion,common90_mu04=next(c for c in contact90 if c['assumed_mu']==.4),source_mass=mass,study_sha256=sha(OUT/'study.json')),indent=2))

def export_reference(params):
 import cadquery as cq
 data=[]
 def cyl(A,B,r):
  v=np.array(B)-A;return cq.Solid.makeCylinder(r,float(np.linalg.norm(v)),cq.Vector(*A),cq.Vector(*v))
 for name,s in [('open',0),('mid',.5),('contact90',(-45.525+80)/40),('closed',1)]:
  shapes=[];rows=[];x=-80+40*s
  # Shared annular carriage is a reference placeholder, no guide or screw nut interface.
  ring=cq.Workplane('XY').workplane(offset=x-3).circle(25).circle(10).extrude(6).val();shapes.append(ring);rows.append(dict(name='slider_reference_annulus',representation='unvalidated R10..25, thickness6 placeholder'))
  for fid,k,phi,_ in FINGERS:
   p=params[k];q=float(inverse(x,p));P,B,C=points(p,q,phi);er,et,ez=frame(phi)
   for pn,A,Bb,r in [('rod',C,B,2.5),('crank',P,B,4),('fixed_pivot',P-5*et,P+5*et,3)]:
    obj=cyl(A,Bb,r);assert obj.isValid();shapes.append(obj);rows.append(dict(name=fid+'_'+pn,start_mm=A.tolist(),end_mm=Bb.tolist(),reference_radius_mm=r,volume_mm3=float(obj.Volume())))
  compound=cq.Compound.makeCompound(shapes);cq.exporters.export(compound,str(OUT/('R5-LINK01-'+name+'-reference.step')));cq.exporters.export(compound,str(OUT/('R5-LINK01-'+name+'-reference.stl')),tolerance=.08,angularTolerance=.15);step=OUT/('R5-LINK01-'+name+'-reference.step');txt=step.read_text();txt=re.sub(r"(FILE_NAME\('[^']*','?)[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]+",lambda match:match.group(1)+'2026-09-27T00:00:00',txt);step.write_text(txt);data.append(dict(pose=name,slider_Z_mm=x,solids=len(shapes),valid=compound.isValid(),parts=rows))
 return data

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--three-pose',nargs=6,type=float,metavar=('Q_CLOSED','X_AT90','X_OPEN','X_CLOSED','ROOT_R','SLIDER_R'),help='print exact three-pose synthesis and nominal certificate only');ap.add_argument('--synthesize',nargs=6,type=float,metavar=('Q_DEG','X_OPEN','X_CLOSED','ROD','ROOT_R','SLIDER_R'),help='print only nominal crank/phase synthesis, without regenerating default outputs');a=ap.parse_args()
 if a.three_pose:
  p=synthesize_three_pose(*a.three_pose);print(json.dumps(dict(parameters=p,certificate=certify(p)),indent=2))
 elif a.synthesize:
  p=synthesize(*a.synthesize);print(json.dumps(dict(parameters=p,certificate=certify(p)),indent=2))
 else:generate({'upper':synthesize_three_pose(105),'lower':synthesize_three_pose(113)})
