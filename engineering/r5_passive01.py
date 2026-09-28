#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Ideal taut differential before first stop/slack; not a complete head simulation."""
from pathlib import Path
import json
import hashlib, csv
import numpy as np
from scipy.interpolate import BPoly
from scipy.integrate import solve_ivp

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/r5-passive01'
FORM=json.loads((ROOT/'engineering/generated/r5-petal-form02/study.json').read_text())
co=np.array([0,0,378.998876,0,0,188.755374,387.828233,244.417517,0,0])/1000
vel=BPoly(co[:,None],[0,.5]);pos=vel.antiderivative();acc=vel.derivative()
def command(t):
    tt=.5-t
    return float(pos(tt)), -float(vel(tt)), float(acc(tt))

def coeff(s,kind,carrier):
    w=np.clip(s/.025,0.,1.)
    q=np.pi/2*(10*w**3-15*w**4+6*w**5)
    qs=np.pi/2*30*w*w*(1-w)**2/.025
    qss=np.pi/2*60*w*(1-w)*(1-2*w)/.025**2
    p=FORM['parts'][kind]['known_material_subtotal'];m=p['mass_kg']
    x,y,z=np.array(p['COM_local_m'])-[0,0,.0035];I=p['inertia_COM_local_axes_kg_m2'][1][1]
    A=-x*np.sin(q)-z*np.cos(q);B=x*np.cos(q)-z*np.sin(q)
    vr=-1+A*qs;vz=B*qs
    ar=-B*qs**2+A*qss;az=A*qs**2+B*qss
    H=m*(vr*vr+vz*vz)+I*qs*qs+carrier
    Hp=2*m*(vr*ar+vz*az)+2*I*qs*qss
    G=m*9.80665*vz
    return H,Hp,G

def run(k,c,pre=5.,carrier=.05,rtol=1e-9,step=.0002):
    def state(t,y):
        u,v,a=command(t);d,dv=y
        su,sl=u+d,u-d;vu,vl=v+dv,v-dv
        hu,hpu,gu=coeff(su,'upper',carrier);hl,hpl,gl=coeff(sl,'lower',carrier)
        bu=.5*hpu*vu*vu+gu+pre+k*su+c*vu
        bl=.5*hpl*vl*vl+gl+pre+k*sl+c*vl
        da=((hl-hu)*a+bl-bu)/(hu+hl)
        T=hu*(a+da)+bu
        return su,sl,da,T
    def fun(t,y): return [y[1],state(t,y)[2]]
    def low(t,y):return min(state(t,y)[:2])+1e-8
    def high(t,y):return .06000001-max(state(t,y)[:2])
    def slack(t,y):return state(t,y)[3]
    for f in [low,high,slack]:f.terminal=True;f.direction=-1
    sol=solve_ivp(fun,(0,.5),[0.,0.],method='DOP853',rtol=rtol,atol=1e-12,max_step=step,events=[low,high,slack],dense_output=True)
    times=np.linspace(0,sol.t[-1],2001);val=np.array([state(t,y) for t,y in zip(times,sol.sol(times).T)])
    out=dict(k_N_mm=k/1000,c_N_s_m=c,preload_N=pre,carrier_each_kg=carrier,stop_time_s=sol.t[-1],event=next((n for n,t in zip(['open_stop','closed_stop','slack'],sol.t_events) if len(t)),'end'),max_upper_lower_diff_mm=max(abs(val[:,0]-val[:,1]))*1000,end_s_mm=(val[-1,:2]*1000).tolist(),T_min_N=min(val[:,3]),T_max_N=max(val[:,3]))
    return out, (times,val,sol)

def full_four(k,c,pre,carrier,end):
    """Separate 4-coordinate constrained equations, no reduced delta RHS."""
    def rhs(t,y):
        s=y[:4];v=y[4:];hh=[];bb=[]
        for si,vi,kind in zip(s,v,['upper','upper','lower','lower']):
            h,hp,g=coeff(si,kind,carrier);hh.append(h)
            bb.append(.5*hp*vi**2+g+pre+k*si+c*vi)
        hh=np.array(hh);bb=np.array(bb)
        tension=(4*command(t)[2]+sum(bb/hh))/sum(1/hh)
        return np.r_[v,(tension-bb)/hh]
    return solve_ivp(rhs,(0,end),[.06]*4+[0.]*4,method='DOP853',rtol=1e-10,atol=1e-13,max_step=.0001,dense_output=True)

def mass_metric_fd():
    rows=[]
    for kind in ['upper','lower']:
        p=FORM['parts'][kind]['known_material_subtotal'];m=p['mass_kg']
        x,_,z=np.array(p['COM_local_m'])-[0,0,.0035];I=p['inertia_COM_local_axes_kg_m2'][1][1]
        def pose(s):
            w=np.clip(s/.025,0,1);q=np.pi/2*(10*w**3-15*w**4+6*w**5)
            return np.array([.091-s+x*np.cos(q)-z*np.sin(q),.020+x*np.sin(q)+z*np.cos(q)]),q
        errors=[]
        for s in np.linspace(.0002,.0598,157):
            eps=1e-7;pa,qa=pose(s+eps);pb,qb=pose(s-eps)
            vp=(pa-pb)/(2*eps);qp=(qa-qb)/(2*eps)
            h=m*(vp@vp)+I*qp**2
            errors.append(abs(h-coeff(s,kind,0)[0]))
        rows.append(dict(kind=kind,max_H_FD_error_kg=max(errors)))
    assert max(r['max_H_FD_error_kg'] for r in rows)<1e-7
    return rows

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    scenarios=[];base=None
    for carrier in [0,.05,.10]:
        for k,c in [(30,.2),(100,2),(300,5)]:
            row,curve=run(k,c,carrier=carrier);scenarios.append(row)
            if carrier==.05 and k==30:base=(row,curve)
    row,(ts,values,sol)=base;end=sol.t[-1]
    dense=np.linspace(0,end,12001);ys=sol.sol(dense);u=np.array([command(t)[0] for t in dense]);v=np.array([command(t)[1] for t in dense]);sU=u+ys[0];sL=u-ys[0];vU=v+ys[1];vL=v-ys[1]
    full=full_four(30,.2,5,.05,end);fy=full.sol(dense)
    four_error=float(np.max(abs(fy[:4]-np.vstack([sU,sU,sL,sL]))))
    constraint_error=float(np.max(abs(np.sum(fy[:4],axis=0)-4*u)))
    assert four_error<1e-7 and constraint_error<1e-8
    refined,(_,_,refsol)=run(30,.2,5,.05,rtol=1e-11,step=.0001)
    assert abs(refined['stop_time_s']-row['stop_time_s'])<1e-7
    # Energy and first-stop impulse, strictly before contact.
    energy=np.zeros(len(dense));T=np.zeros(len(dense))
    for kind,s,vi in [('upper',sU,vU),('lower',sL,vL)]:
        h,hp,g=coeff(s,kind,.05)
        p=FORM['parts'][kind]['known_material_subtotal'];m=p['mass_kg'];x,_,z=np.array(p['COM_local_m'])-[0,0,.0035]
        w=np.clip(s/.025,0,1);q=np.pi/2*(10*w**3-15*w**4+6*w**5)
        potential=m*9.80665*(.020+x*np.sin(q)+z*np.cos(q))+5*s+.5*30*s*s
        energy+=2*(.5*h*vi*vi+potential)
    hu,hpu,gu=coeff(sU,'upper',.05);hl,hpl,gl=coeff(sL,'lower',.05)
    bu=.5*hpu*vU*vU+gu+5+30*sU+.2*vU
    bl=.5*hpl*vL*vL+gl+5+30*sL+.2*vL
    aa=np.array([command(t)[2] for t in dense]);dd=((hl-hu)*aa+bl-bu)/(hu+hl)
    T=hu*(aa+dd)+bu
    from scipy.integrate import cumulative_trapezoid
    work=cumulative_trapezoid(4*T*v-2*.2*(vU*vU+vL*vL),dense,initial=0)
    residual=float(max(abs(work-(energy-energy[0]))));assert residual<1e-6
    impulse_per_leaf=float(hu[-1]*vL[-1])
    assert vL[-1]<0 and impulse_per_leaf<0
    # Static comparison after q90: N_i=T-(pre+k*s_i), no guide friction.
    grip=[];required=2*2*9.80665/(4*.4)
    for k in [30,100,300,1000]:
        s=np.array([.060,.025,.060,.025]);S=5+k*s;Tg=required+max(S);N=Tg-S
        grip.append(dict(k_N_mm=k/1000,preload_each_N=5.,contact_s_mm=(s*1000).tolist(),leaf_tension_N=float(Tg),second_tier_tension_N=float(2*Tg),input_force_N=float(4*Tg),normal_each_N=N.tolist(),ideal_lead4_hold_Nm=float(4*Tg*.004/(2*np.pi))))
    files=[Path(__file__),ROOT/'engineering/generated/r5-petal-form02/study.json',ROOT/'engineering/generated/r5-stage01/study.json']
    output=dict(revision='R5-PASSIVE01',scope='Before first opening stop in an ideal massless, frictionless, inextensible, taut two-tier differential; carrier masses, springs and viscous damping are hypothetical. Not a simulated complete cycle, fabricated transmission or payload rating.',source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},assumptions=dict(gravity_head=[0,0,-9.80665],one_active_mean_input=True,identical_members_within_upper_lower_pair=True,carrier_mass_is_sensitivity_not_actual=True,omitted=['follower/crank rotational inertia','pulley and rope mass/compliance/friction','actual return hardware','3D asymmetry and arbitrary gravity','stop impact/slack recovery and grasp contacts','final fully closed shape']),scenarios=scenarios,baseline=row,first_stop=dict(stopping_pair='lower',upper_speed_m_s=float(vU[-1]),lower_speed_m_s=float(vL[-1]),upper_remaining_s_mm=float(sU[-1]*1000),lower_q_deg=0.,upper_q_deg=float(np.pi/2*(10*(sU[-1]/.025)**3-15*(sU[-1]/.025)**4+6*(sU[-1]/.025)**5)*180/np.pi),bilateral_maintain_mean_required_tension_impulse_per_leaf_N_s=impulse_per_leaf,tension_impulse_feasible=False,interpretation='Stopping the lower pair at zero velocity while maintaining the prescribed mean velocity would require a negative cable impulse. The taut bilateral model must end; real rope slack/compliance and stop dynamics must be modeled.'),static_rect50x120=grip,review=dict(full_four_coordinate_max_position_difference_m=four_error,full_four_mean_constraint_error_m=constraint_error,timestep_refinement_event_difference_s=abs(refined['stop_time_s']-row['stop_time_s']),work_energy_residual_J=residual,mass_metric_FD=mass_metric_fd()),one_second_qualification=False,manufacturing_release=False)
    (OUT/'study.json').write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n')
    with (OUT/'opening-until-first-event.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['time_s','mean_R_mm','upper_R_mm','lower_R_mm','upper_closing_speed_m_s','lower_closing_speed_m_s','leaf_tension_N'])
        w.writerows(zip(dense[::20],(91-1000*u)[::20],(91-1000*sU)[::20],(91-1000*sL)[::20],vU[::20],vL[::20],T[::20]))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(2,1,figsize=(10,8),sharex=True)
    axs[0].plot(dense,91-1000*u,'k--',label='commanded mean R')
    axs[0].plot(dense,91-1000*sU,label='upper petals');axs[0].plot(dense,91-1000*sL,label='lower petals')
    axs[0].axhline(91,color='#aa3333',ls=':',label='opening stop R91')
    axs[0].set_ylabel('Root radius / mm');axs[0].legend();axs[0].grid(alpha=.2)
    axs[1].plot(dense,T,label='one leaf tension / ideal');axs[1].plot(dense,4*T,label='input force / ideal')
    axs[1].set_ylabel('Force / N');axs[1].set_xlabel('Opening half-cycle time / s');axs[1].legend();axs[1].grid(alpha=.2)
    for ax in axs:ax.axvline(end,color='#aa3333',ls=':');ax.set_xlim(0,.5)
    fig.suptitle('R5-PASSIVE01 / one active mean does not enforce synchronous petals',fontsize=14)
    fig.text(.08,.015,'Stops at first impact/slack event. Carrier 50g each, preload 5N, k=0.03N/mm, c=0.2Ns/m are assumptions.\nNo motion is extrapolated beyond the event; the final fully closed shape and complete 1s cycle remain unqualified.',fontsize=9)
    fig.tight_layout(rect=[0,.065,1,.95]);fig.savefig(OUT/'passive-opening.png',dpi=170);fig.savefig(OUT/'passive-opening.svg');plt.close(fig)
    print(json.dumps(dict(baseline=row,event=output['first_stop'],review=output['review']),indent=2))

if __name__=='__main__':main()
