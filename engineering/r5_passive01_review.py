# SPDX-License-Identifier: CC-BY-NC-4.0
"""Independent pre-event numerical review; not physical cycle qualification."""
from pathlib import Path
import json, hashlib, math
import numpy as np
from numpy.polynomial import Polynomial as P
from scipy.integrate import solve_ivp, simpson
R=Path(__file__).resolve().parents[1]
OUT=R/'engineering/generated/r5-passive01'
FORM=json.loads((R/'engineering/generated/r5-petal-form02/study.json').read_text())
REFERENCE=json.loads((R/'engineering/generated/r5-passive01/study.json').read_text())
# Independently construct degree9 Bernstein as a power polynomial, without BPoly.
c=np.array([0,0,378.998876,0,0,188.755374,387.828233,244.417517,0,0])*.001
w=P([0,2]); speed=sum((ci*math.comb(9,i)*w**i*(1-w)**(9-i) for i,ci in enumerate(c)),P([0]))
distance=speed.integ(); accel=speed.deriv()
qpoly=P([0,0,0,10,-15,6])*(np.pi/2)
q1=qpoly.deriv();q2=q1.deriv()
def command(t):
    return distance(.5-t)-distance(0),-speed(.5-t),accel(.5-t)
def geom(s,kind):
    p=FORM['parts'][kind]['known_material_subtotal'];m=p['mass_kg'];I=p['inertia_COM_local_axes_kg_m2'][1][1]
    X,_,Z=np.asarray(p['COM_local_m'])-[0,0,.0035]
    if s<=0:q,dq=0.,0.
    elif s>=.025:q,dq=np.pi/2,0.
    else:q,dq=qpoly(s/.025),q1(s/.025)/.025
    rot=np.array([[np.cos(q),-np.sin(q)],[np.sin(q),np.cos(q)]])
    pr=rot@np.array([X,Z]);v=np.array([-1.,0.])+np.array([-pr[1],pr[0]])*dq
    h=m*(v@v)+I*dq*dq+.05
    g=m*9.80665*v[1]
    pose=np.array([.091-s,.020])+pr
    return h,g,pose,q

def hgb(s,v,kind):
    h,g,_,_=geom(s,kind)
    eps=1e-7
    hp=(geom(s+eps,kind)[0]-geom(s-eps,kind)[0])/(2*eps)
    b=.5*hp*v*v+g+5.+30*s+.2*v
    return h,b

def rhs(t,y):
    s=y[:4];v=y[4:];H=[];B=[]
    for si,vi,k in zip(s,v,['upper','upper','lower','lower']):
        h,b=hgb(si,vi,k);H.append(h);B.append(b)
    H=np.array(H);B=np.array(B)
    # solve bordered linear system instead of parent multiplier/reduced formula
    A=np.zeros((5,5));A[:4,:4]=np.diag(H);A[:4,4]=-1.;A[4,:4]=1.
    result=np.linalg.solve(A,np.r_[-B,4*command(t)[2]])
    return np.r_[v,result[:4]]

def stop(t,y):return min(y[:4])  # exact nominal stop, no parent's10nm offset
stop.direction=-1;stop.terminal=True
initial=np.r_[np.repeat(command(0)[0],4),np.repeat(command(0)[1],4)]
sol=solve_ivp(rhs,[0,.5],initial,method='DOP853',max_step=.0003,rtol=2e-10,atol=1e-12,events=stop,dense_output=True)
t=float(sol.t[-1]);y=sol.y[:,-1];U,V,A=command(t)
hu,bu=hgb(y[0],y[4],'upper');hl,bl=hgb(y[2],y[6],'lower')
vUplus=2*V; deltaU=vUplus-y[4]; J=hu*deltaU
stop_impulse=-hl*y[6]-J
# Energy audit with independently evaluated physical pose and Simpson integration.
ts=np.linspace(0,t,8001);ys=sol.sol(ts);power=[];energy=[];tension=[];constraint=[]
for ti,yi in zip(ts,ys.T):
    si=yi[:4];vi=yi[4:];ai=rhs(ti,yi)[4:]
    e=0.;tt=[]
    for sj,vj,aj,k in zip(si,vi,ai,['upper','upper','lower','lower']):
        h,g,pos,q=geom(sj,k);_,bj=hgb(sj,vj,k)
        m=FORM['parts'][k]['known_material_subtotal']['mass_kg']
        e+=.5*h*vj*vj+m*9.80665*pos[1]+5*sj+.5*30*sj*sj
        tt.append(h*aj+bj)
    ten=np.mean(tt)
    energy.append(e);power.append(ten*sum(vi)-.2*(vi@vi));tension.append(ten)
    constraint.append(sum(si)-4*command(ti)[0])
work=float(simpson(power,x=ts));deltaE=float(energy[-1]-energy[0])
errs=dict(stop_time_vs_parent_s=t-REFERENCE['baseline']['stop_time_s'],upper_s_vs_parent_m=float(y[0]-REFERENCE['first_stop']['upper_remaining_s_mm']/1000),upper_v_vs_parent_m_s=float(y[4]-REFERENCE['first_stop']['upper_speed_m_s']),lower_v_vs_parent_m_s=float(y[6]-REFERENCE['first_stop']['lower_speed_m_s']),impulse_vs_parent_N_s=J-REFERENCE['first_stop']['bilateral_maintain_mean_required_tension_impulse_per_leaf_N_s'],max_sum_position_constraint_error_m=float(max(abs(np.array(constraint)))),energy_error_J=work-deltaE)
paths=['engineering/r5_passive01.py','engineering/generated/r5-passive01/study.json','engineering/generated/r5-petal-form02/study.json','engineering/generated/r5-stage01/study.json']
report=dict(review='Independent R5-PASSIVE01 mathematical audit',conclusion='PASS within stated hypothetical pre-event model; no substantive sign/factor bug found',input_hashes={p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in paths},independence=['power-polynomial Bernstein construction, no BPoly','4 independent leaf coordinates plus5x5 multiplier solve, no reduced delta RHS','rotated COM Jacobian and finite-difference mass derivative','exact nominal first-opening stop, no10nm offset','independent Simpson work-energy integration'],values=dict(event_time_s=t,upper_s_m=float(y[0]),lower_s_m=float(y[2]),upper_v_m_s=float(y[4]),lower_v_m_s=float(y[6]),mean_v_m_s=V,HU_kg=hu,HL_kg=hl,required_upper_v_after_maintaining_mean_m_s=vUplus,upper_delta_v_m_s=deltaU,tension_impulse_each_leaf_N_s=J,lower_stop_impulse_each_N_s=stop_impulse,tension_range_N=[float(min(tension)),float(max(tension))],energy_change_J=deltaE,input_minus_damping_work_J=work),errors=errs,findings=[dict(severity='informational',text='Parent open-stop event has +1e-8m guard, hence ends at -10nm. Independent exact stop differs about65ns; quoted rounded result unaffected.'),dict(severity='scope',text='Negative required rope impulse rules out continuing the simultaneous hard lower stop plus prescribed mean speed with all ropes taut. It does not predict post-impact slack recovery, or prove complete1s infeasibility for actual hardware.'),dict(severity='scope',text='Spring5N+30N/m*s, viscous.2Ns/m and50g pure translating carrier each are assumptions; dynamic CABLE sizing must use actual routing/masses/return mechanism.')],mathematics=dict(reduced='(HU+HL)*d_ddot=(HL-HU)*u_ddot+bL-bU',impulse='At maintained mean velocity, vUplus=2*u_dot; delta_vU=vLminus; J_each=HU*vLminus<0',multipliers='each leaf T; second tier2T; prescribed mean input4T. Pair multiplicity cancels in reduced d equation.',mass='H=m*||dr_com/ds||^2+I_COM,y*(dq/ds)^2+m_carrier; G=mg*dz_com/ds',force_sign='positive s closes; spring and damping terms enter b=0.5Hprime*v^2+G+pre+k*s+c*v; gravity_head=-Z'),source_files_modified=False)
assert abs(errs['stop_time_vs_parent_s'])<2e-7
assert abs(errs['impulse_vs_parent_N_s'])<1e-5
assert abs(work-deltaE)<1e-6
assert max(abs(np.array(constraint)))<1e-8
assert J<0 and stop_impulse>0
(OUT/'independent-review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'values':report['values'],'errors':errs},indent=2))
