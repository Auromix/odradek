#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Known carrier mass/inertia and conditional return tuning, before first event.

No writes outside generated/r5-passive02. Springs/dampers are mathematical
candidates, not selected or tested hardware. Not a full hybrid simulation.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import numpy as np
from scipy.interpolate import BPoly
from scipy.integrate import solve_ivp, cumulative_trapezoid

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/r5-passive02'
FORM_PATH=ROOT/'engineering/generated/r5-petal-form02/study.json'
CARRIER_PATH=ROOT/'engineering/generated/r5-carrier01/parts-manifest.json'
FORM=json.loads(FORM_PATH.read_text())
CARRIER=json.loads(CARRIER_PATH.read_text())
OLD=json.loads((ROOT/'engineering/generated/r5-passive01/study.json').read_text())
CABLE=json.loads((ROOT/'engineering/electronics/r5-cable-hardware01/budget.json').read_text())
G=9.80665
S_MAX=.06
FOLD=.025
CO=np.array([0,0,378.998876,0,0,188.755374,387.828233,244.417517,0,0])/1000
VEL=BPoly(CO[:,None],[0,.5]);POS=VEL.antiderivative();ACC=VEL.derivative()
ROTOR=[r for r in CARRIER['parts'] if r['group']=='rotor']
M_TRANSLATE=sum(r['mass_kg'] for r in CARRIER['parts'] if r['group'] in ['carrier','bearing'])
CFS=next(r for r in ROTOR if r['id']=='IKO_CFS4')
CFS_PROXY_J=CFS['inertia_COM_part_axes_kg_m2'][1][1]
CFS_J_MAX=CFS['outer_ring_spin_sensitivity_upper_bound_kg_m2']
BEARING_CO_ROTATING_J_MAX=sum(r['mass_kg']*.0095**2 for r in CARRIER['parts'] if r['group']=='bearing')


def dump(name,obj):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')


def combine(pieces):
    mass=sum(p[0] for p in pieces)
    com=sum(m*np.asarray(c) for m,c,I in pieces)/mass
    inertia=np.zeros((3,3))
    for m,c,I in pieces:
        d=np.asarray(c)-com
        inertia+=np.asarray(I)+m*((d@d)*np.eye(3)-np.outer(d,d))
    return dict(mass_kg=mass,COM_hinge_m=com.tolist(),inertia_COM_hinge_axes_kg_m2=inertia.tolist(),I_hinge_y_kg_m2=float(inertia[1,1]+mass*(com[0]**2+com[2]**2)))


def pieces(kind,legacy=False):
    p=FORM['parts'][kind]['known_material_subtotal']
    out=[(p['mass_kg'],np.array(p['COM_local_m'])-[0,0,.0035],np.array(p['inertia_COM_local_axes_kg_m2']))]
    if not legacy:
        out += [(r['mass_kg'],np.array(r['COM_part_m']),np.array(r['inertia_COM_part_axes_kg_m2'])) for r in ROTOR]
    return out


MODELS={(k,l):combine(pieces(k,l)) for k in ['upper','lower'] for l in [False,True]}


def command(t,direction='opening'):
    tt=.5-t if direction=='opening' else t
    sign=-1 if direction=='opening' else 1
    return float(POS(tt)),sign*float(VEL(tt)),float(ACC(tt))


def fold(s):
    w=np.clip(np.asarray(s)/FOLD,0.,1.)
    q=np.pi/2*(10*w**3-15*w**4+6*w**5)
    dq=np.pi/2*30*w*w*(1-w)**2/FOLD
    ddq=np.pi/2*60*w*(1-w)*(1-2*w)/FOLD**2
    return q,dq,ddq


def coeff(s,kind,extra=0.,legacy=False,spin='rigid_proxy',bearing_j=0.):
    p=MODELS[kind,legacy];m=p['mass_kg'];x,_,z=p['COM_hinge_m'];I=p['inertia_COM_hinge_axes_kg_m2'][1][1]
    q,qs,qss=fold(s)
    A=-x*np.sin(q)-z*np.cos(q);B=x*np.cos(q)-z*np.sin(q)
    vr=-1+A*qs;vz=B*qs
    ar=-B*qs**2+A*qss;az=A*qs**2+B*qss
    H=m*(vr*vr+vz*vz)+I*qs*qs+extra+(0 if legacy else M_TRANSLATE)
    Hp=2*m*(vr*ar+vz*az)+2*I*qs*qss
    gravity=m*G*vz
    if not legacy and spin!='rigid_proxy':
        # Remove the already counted rigid CFS central inertia before replacement.
        H-=CFS_PROXY_J*qs*qs;Hp-=2*CFS_PROXY_J*qs*qss
        if spin=='all_mass_ring_bound':
            a=.008;phi=q-np.pi/4;r=.004
            # Roller center follows [R+a*cos(phi), zroot+a*sin(phi)].
            cr=-1-a*np.sin(phi)*qs;cz=a*np.cos(phi)*qs
            crr=-a*np.cos(phi)*qs**2-a*np.sin(phi)*qss
            czz=-a*np.sin(phi)*qs**2+a*np.cos(phi)*qss
            H+=CFS_J_MAX*(cr*cr+cz*cz)/r**2
            Hp+=2*CFS_J_MAX*(cr*crr+cz*czz)/r**2
        elif spin=='all_mass_stud_bound':
            H+=CFS_J_MAX*qs*qs;Hp+=2*CFS_J_MAX*qs*qss
        elif spin!='zero_central_spin':raise ValueError(spin)
    H+=bearing_j*qs*qs;Hp+=2*bearing_j*qs*qss
    return H,Hp,gravity


def forces(s,v,kind,param,**kw):
    h,hp,g=coeff(s,kind,**kw)
    f,k,c=param
    return h,.5*hp*v*v+g+f+k*s+c*v


def run(params=((5.,30.,.2),(5.,30.,.2)),direction='opening',extra=0.,legacy=False,spin='rigid_proxy',bearing_j=0.,rtol=2e-8,step=.001,dense_count=1601):
    kw=dict(extra=extra,legacy=legacy,spin=spin,bearing_j=bearing_j)
    def state(t,y):
        u,v,a=command(t,direction);d,dv=y
        sU,sL=u+d,u-d;vU,vL=v+dv,v-dv
        hu,bu=forces(sU,vU,'upper',params[0],**kw);hl,bl=forces(sL,vL,'lower',params[1],**kw)
        da=((hl-hu)*a+bl-bu)/(hu+hl)
        T=hu*(a+da)+bu
        return sU,sL,vU,vL,da,T
    def fun(t,y):return [y[1],state(t,y)[4]]
    def opening_stop(t,y):return min(state(t,y)[:2])+1e-8
    def closing_stop(t,y):return .06000001-max(state(t,y)[:2])
    def slack(t,y):return state(t,y)[5]
    events=[opening_stop,closing_stop,slack]
    for e in events:e.terminal=True;e.direction=-1
    sol=solve_ivp(fun,(0,.5),[0.,0.],method='DOP853',rtol=rtol,atol=1e-11,max_step=step,events=events,dense_output=True)
    times=np.linspace(0,sol.t[-1],dense_count)
    val=np.array([state(t,y) for t,y in zip(times,sol.sol(times).T)])
    event=next((n for n,t in zip(['opening_stop','closing_stop','slack'],sol.t_events) if len(t)),'command_end')
    end=val[-1]
    normal_stop='opening_stop' if direction=='opening' else 'closing_stop'
    unmet=float(max(end[:2]) if direction=='opening' else S_MAX-min(end[:2]))
    out=dict(direction=direction,params_upper=dict(preload_N=params[0][0],k_N_m=params[0][1],c_N_s_m=params[0][2]),params_lower=dict(preload_N=params[1][0],k_N_m=params[1][1],c_N_s_m=params[1][2]),extra_translation_each_kg=extra,legacy_bare_petal=legacy,CFS_spin_scenario=spin,bearing_corotating_J_kg_m2=bearing_j,event=event,stop_time_s=float(sol.t[-1]),end_s_mm=(end[:2]*1000).tolist(),end_v_m_s=end[2:4].tolist(),max_pair_difference_mm=float(max(abs(val[:,0]-val[:,1]))*1000),remaining_other_branch_mm=max(0,unmet*1000),T_min_N=float(min(val[:,5])),T_max_N=float(max(val[:,5])),arrived_at_intended_stop=event==normal_stop,complete_cycle_qualified=False)
    out['damping_energy_before_event_J']=float(np.trapezoid(2*params[0][2]*val[:,2]**2+2*params[1][2]*val[:,3]**2,times))
    out['peak_total_damper_power_before_event_W']=float(max(2*params[0][2]*val[:,2]**2+2*params[1][2]*val[:,3]**2))
    out['ideal_input_work_before_event_J']=float(np.trapezoid(4*val[:,5]*np.array([command(t,direction)[1] for t in times]),times))
    return out,dict(times=times,values=val,sol=sol,state=state,kw=kw,params=params,direction=direction)


def static_load(params):
    # Opposite pairs UR/LL and UL/LR each contain one upper and one lower.
    results=[]
    required=2*2*G/(4*.4)
    leaf=CABLE['combinations']['leaf_upgrade']['conditional_T_ceiling_N_at_term_eta1_and_guideline10']
    second=CABLE['combinations']['secondary_upgrade']['conditional_T_ceiling_N_at_term_eta1_and_guideline10']
    phi=np.radians([45,135,225,315]);er=np.c_[np.cos(phi),np.sin(phi)]
    for orientation in [0,90]:
        si=np.array([.060,.025,.060,.025] if orientation==0 else [.025,.060,.025,.060])
        pars=[params[0],params[0],params[1],params[1]]
        spring=np.array([p[0]+p[1]*s for p,s in zip(pars,si)])
        t=required+max(spring);normals=t-spring
        residual=-np.sum(normals[:,None]*er,axis=0)
        results.append(dict(box_orientation_offset_deg=orientation,finger_order=['UR','UL','LL','LR'],contact_s_mm=(si*1000).tolist(),required_normal_each_lower_bound_N=required,spring_each_N=spring.tolist(),normal_each_N=normals.tolist(),unbalanced_XY_normal_force_N=residual.tolist(),centered_normal_only_force_balance=bool(np.linalg.norm(residual)<1e-9),leaf_tension_N=float(t),second_tier_tension_N=float(2*t),input_force_N=float(4*t),ideal_4mm_lead_hold_Nm=float(4*t*.004/(2*np.pi)),passes_mid50_100_screen=bool(t<=50),passes_CABLE_conditional_bend10_ceiling=bool(t<=leaf and 2*t<=second),terminal_retention_needed_leaf=float(10*t/CABLE['combinations']['leaf_upgrade']['min_break_N']),terminal_retention_needed_secondary=float(20*t/CABLE['combinations']['secondary_upgrade']['min_break_N']),assembly_qualified=False))
    return results


def sync_fit():
    """Fit different spring forces to synchronous dynamic mismatch, both directions.
    Not an ODE qualification: the actual response is integrated separately.
    """
    t=np.linspace(0,.5,501);s=np.array([command(x,'closing')[0] for x in t]);v=np.array([command(x,'closing')[1] for x in t]);a=np.array([command(x,'closing')[2] for x in t])
    hu,hpu,gu=coeff(s,'upper');hl,hpl,gl=coeff(s,'lower')
    # To keep d=0, S_U-S_L=(HL-HU)*a+.5(HL'-HU')v²+GL-GU
    need=(hl-hu)*a+.5*(hpl-hpu)*v*v+gl-gu
    A=np.column_stack([np.ones(len(s)),s])
    fit=np.linalg.lstsq(A,need,rcond=None)[0]
    return dict(delta_preload_U_minus_L_N=float(fit[0]),delta_k_U_minus_L_N_m=float(fit[1]),residual_rms_N=float(np.sqrt(np.mean((A@fit-need)**2))),required_difference_minmax_N=[float(min(need)),float(max(need))]),(s,need,A@fit)


def mass_audit():
    checks=[]
    for kind in ['upper','lower']:
        errH=[];errHp=[];errG=[]
        for s in np.linspace(.00011,.05989,181):
            eps=1e-7;Hfd=0.;Gfd=0.
            def pose(center,z):
                q=fold(z)[0];co,si=np.cos(q),np.sin(q)
                rot=np.array([[co,0,-si],[0,1,0],[si,0,co]])
                return np.array([.091-z,0,.020])+rot@np.array(center),q
            for m,com,I in pieces(kind):
                rp,qp=pose(com,s+eps);rm,qm=pose(com,s-eps)
                vel=(rp-rm)/(2*eps);w=(qp-qm)/(2*eps)
                Hfd+=m*(vel@vel)+I[1,1]*w*w
                Gfd+=m*G*vel[2]
            Hfd+=M_TRANSLATE
            h,hp,g=coeff(s,kind)
            hfdp=(coeff(s+eps,kind)[0]-coeff(s-eps,kind)[0])/(2*eps)
            errH.append(abs(Hfd-h));errHp.append(abs(hp-hfdp));errG.append(abs(g-Gfd))
        checks.append(dict(kind=kind,individual_piece_FD_H_max_error_kg=max(errH),FD_Hprime_max_error_kg_m=max(errHp),individual_piece_FD_gravity_max_error_N=max(errG)))
    assert max(x['individual_piece_FD_H_max_error_kg'] for x in checks)<1e-7
    assert max(x['FD_Hprime_max_error_kg_m'] for x in checks)<2e-5
    left_models={}
    for kind in ['upper','lower']:
        pp=pieces(kind);m,c,I=pp[0];D=np.diag([1,-1,1]);pp[0]=(m,D@c,D@I@D)
        left_models[kind]=combine(pp)
        assert np.isclose(left_models[kind]['I_hinge_y_kg_m2'],MODELS[kind,False]['I_hinge_y_kg_m2'],atol=1e-15)
    source_steps={r['source_step']:hashlib.sha256((CARRIER_PATH.parent/r['source_step']).read_bytes()).hexdigest()==r['sha256'] for r in CARRIER['parts']}
    assert all(source_steps.values())
    guides=sum(r['mass_kg'] for r in CARRIER['parts'] if r['group']=='guide')*4
    moving=sum(MODELS[k,False]['mass_kg']*2 for k in ['upper','lower'])+4*M_TRANSLATE
    parent=json.loads((CARRIER_PATH.parent/'mass-summary.json').read_text())
    total=parent['states'][0]['known_mass_kg']
    assert abs(moving+guides-total)<1e-9
    return dict(coordinates='Hinge-relative +X radial,+Y tangent,+Z front; rotation about -Y. FORM02 alone translated by -3.5mmZ; carrier manifest is already hinge-relative.',canonical_right_models={k:MODELS[k,False] for k in ['upper','lower']},left_petal_mirrored_but_internal_C4_not_mirrored_models=left_models,carrier_only_translation_each_kg=M_TRANSLATE,rotor_hardware_each_kg=sum(r['mass_kg'] for r in ROTOR),moving_known_mass_four_branches_kg=moving,fixed_guide_mass_four_kg=guides,sum_matches_CARRIER01_mass_kg=total,geometry_checks=checks,source_STEP_hashes_match=source_steps,uniform_envelope_proxy_rotor_parts=[r['id'] for r in ROTOR if r['inertia_is_uniform_envelope_proxy']],unidentified_spin=dict(CFS_baseline_central_J_kg_m2=CFS_PROXY_J,CFS_total_mass_radius_bound_J_kg_m2=CFS_J_MAX,bearing_corotating_inner_ring_only_bound_J_kg_m2=BEARING_CO_ROTATING_J_MAX,warning='The co-rotating-bearing sensitivity does not bound ball/cage independent spin. CFS bounds assume all4g lies within4mm of its own axis. No actual ring/stud split measured.'))


def independent_four_check(params,direction,curve):
    end=float(curve['times'][-1]);kw=curve['kw']
    def rhs(t,y):
        h=[];b=[]
        for s,v,k,par in zip(y[:4],y[4:],['upper','upper','lower','lower'],[params[0],params[0],params[1],params[1]]):
            hi,bi=forces(s,v,k,par,**kw);h.append(hi);b.append(bi)
        mat=np.zeros((5,5));mat[:4,:4]=np.diag(h);mat[:4,4]=-1;mat[4,:4]=1
        z=np.linalg.solve(mat,np.r_[-np.array(b),4*command(t,direction)[2]])
        return np.r_[y[4:],z[:4]]
    u,v,_=command(0,direction)
    sol=solve_ivp(rhs,(0,end),[u]*4+[v]*4,method='DOP853',rtol=2e-10,atol=1e-12,max_step=.0002,dense_output=True)
    ts=np.linspace(0,end,8001);ys=sol.sol(ts);d=curve['sol'].sol(ts)
    u=np.array([command(t,direction)[0] for t in ts]);v=np.array([command(t,direction)[1] for t in ts])
    state=np.vstack([u+d[0],u+d[0],u-d[0],u-d[0]])
    error=float(np.max(abs(ys[:4]-state)))
    constraint=float(np.max(abs(ys[:4].sum(axis=0)-4*u)))
    energy=np.zeros(len(ts));power=np.zeros(len(ts));tens=[]
    for t_index,(ti,yi) in enumerate(zip(ts,ys.T)):
        acc=rhs(ti,yi)[4:];t_each=[]
        for s,vi,ai,kind,par in zip(yi[:4],yi[4:],acc,['upper','upper','lower','lower'],[params[0],params[0],params[1],params[1]]):
            h,b=forces(s,vi,kind,par,**kw);t_each.append(h*ai+b)
            mp=MODELS[kind,kw['legacy']];m=mp['mass_kg'];x,_,z=mp['COM_hinge_m'];q=fold(s)[0]
            potential=m*G*(.020+x*np.sin(q)+z*np.cos(q))+par[0]*s+.5*par[1]*s*s
            energy[t_index]+=.5*h*vi*vi+potential
            power[t_index]-=par[2]*vi*vi
        tension=np.mean(t_each);tens.append(tension);power[t_index]+=tension*sum(yi[4:])
    work=cumulative_trapezoid(power,ts,initial=0)
    residual=float(max(abs(work-(energy-energy[0]))))
    assert error<2e-7 and constraint<1e-8 and residual<2e-6
    return dict(full_four_bordered_mass_solve_max_position_error_m=error,sum_position_constraint_error_m=constraint,work_energy_max_residual_J=residual,end_energy_change_J=float(energy[-1]-energy[0]),end_net_work_J=float(work[-1]))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--search-only',action='store_true');args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    fit,_=sync_fit();print('sync-fit',fit,flush=True)
    initial=[]
    for extra in [0,.05,.10]:
        for k,c in [(30,.2),(100,2),(300,5)]:
            par=((5.,float(k),float(c)),)*2
            row,_=run(par,extra=extra);row['static_box']=static_load(par)
            initial.append(row)
    dump('initial-mass-baselines.json',initial)
    print('baseline',initial[0],flush=True)
    candidates=[]
    # Candidate values are bounded engineering variables. No new hardware SKU.
    for pre in [5.,10.,15.]:
        for k in [30.,100.,250.,350.]:
            for c in [.2,2.,5.,10.,20.,40.]:
                for fit_weight in [0.,1.]:
                    df=fit['delta_preload_U_minus_L_N']*fit_weight
                    dk=fit['delta_k_U_minus_L_N_m']*fit_weight
                    par=((pre+df/2,k+dk/2,c),(pre-df/2,k-dk/2,c))
                    if min(par[0][:2]+par[1][:2])<0:continue
                    loads=static_load(par)
                    if not all(x['passes_CABLE_conditional_bend10_ceiling'] for x in loads):continue
                    rr=[run(par,direction=d,step=.002,rtol=1e-6,dense_count=301)[0] for d in ['opening','closing']]
                    # Both endpoints/early initial reversal are explicit failures.
                    score=sum(r['max_pair_difference_mm']+2*r['remaining_other_branch_mm']+100*(.5-r['stop_time_s'])+(200 if not r['arrived_at_intended_stop'] else 0) for r in rr)
                    candidates.append(dict(params=par,score=score,runs=rr,static_box=loads))
    candidates.sort(key=lambda x:x['score'])
    # Explicit asymmetric stiffness/damping search. Equal preloads avoid an
    # immediate opening-stop conflict when closing starts from all s=0 at rest.
    for pre in [5.,10.]:
        for k in [200.,300.,350.]:
            for dk in [-100.,0.,100.]:
                for c in [40.,80.,120.]:
                    for dc in [-40.,0.,40.]:
                        par=((pre,k+dk/2,c+dc/2),(pre,k-dk/2,c-dc/2))
                        loads=static_load(par)
                        if not all(x['passes_CABLE_conditional_bend10_ceiling'] for x in loads):continue
                        rr=[run(par,direction=d,step=.002,rtol=1e-6,dense_count=301)[0] for d in ['opening','closing']]
                        score=sum(r['max_pair_difference_mm']+2*r['remaining_other_branch_mm']+100*(.5-r['stop_time_s'])+(200 if not r['arrived_at_intended_stop'] else 0) for r in rr)
                        candidates.append(dict(params=par,score=score,runs=rr,static_box=loads))
    candidates.sort(key=lambda x:x['score'])
    # One predefined local refinement only; no unbounded optimizer.
    for dk in [-20.,0.,20.]:
        for dc in [-8.,0.,8.]:
            par=((10.,300.+dk/2,80.+dc/2),(10.,300.-dk/2,80.-dc/2))
            loads=static_load(par)
            if not all(x['passes_CABLE_conditional_bend10_ceiling'] for x in loads):continue
            rr=[run(par,direction=d,step=.002,rtol=1e-6,dense_count=301)[0] for d in ['opening','closing']]
            score=sum(r['max_pair_difference_mm']+2*r['remaining_other_branch_mm']+100*(.5-r['stop_time_s'])+(200 if not r['arrived_at_intended_stop'] else 0) for r in rr)
            candidates.append(dict(params=par,score=score,runs=rr,static_box=loads))
    unique={tuple(tuple(p) for p in x['params']):x for x in candidates}
    candidates=sorted(unique.values(),key=lambda x:x['score'])
    dump('candidate-search.json',dict(bounds=dict(preload_common_N=[5,15],k_common_N_m=[30,350],damping_common_N_s_m=[.2,120],difference_weights=[0,1],second_search_delta_k_N_m=[-100,0,100],second_search_delta_c_N_s_m=[-40,0,40],local_refinement_delta_k_N_m=[-20,0,20],local_refinement_delta_c_N_s_m=[-8,0,8]),synchronous_force_fit=fit,objective='sum over opening/closing: max_difference_mm+2*unmet_mm+100*(.5-event_time_s)+200*wrong_first_event',candidates=candidates))
    print('best',json.dumps(candidates[0],indent=2),flush=True)
    if args.search_only:return
    finalize(initial,candidates,fit)


def finalize(initial,candidates,fit):
    mass=mass_audit();dump('mass-model.json',mass)
    comparison=[]
    for i,(mc,k,c) in enumerate((mc,k,c) for mc in [0.,.05,.10] for k,c in [(30.,.2),(100.,2.),(300.,5.)]):
        legacy,_=run(((5.,k,c),)*2,extra=mc,legacy=True,rtol=2e-10,step=.0002)
        new,_=run(((5.,k,c),)*2,extra=mc,rtol=2e-10,step=.0002)
        old=OLD['scenarios'][i]
        assert abs(legacy['stop_time_s']-old['stop_time_s'])<1e-7
        comparison.append(dict(original_proxy_or_new_extra_translation_kg=mc,k_N_m=k,c_N_s_m=c,original_time_s=old['stop_time_s'],legacy_replay_event_time_error_s=legacy['stop_time_s']-old['stop_time_s'],new_time_s=new['stop_time_s'],original_other_remaining_mm=max(old['end_s_mm']),new_other_remaining_mm=new['remaining_other_branch_mm'],new_T_min_N=new['T_min_N'],new_T_max_N=new['T_max_N'],interpretation='Old: bareFORM02+mc proxy. New: FORM02+knownrotor+known59.584gtranslation+mc extra; mc is not the same physical component. Actual-known baseline uses extra0.'))
    dump('nine-case-comparison.json',comparison)
    best=candidates[0]
    asym=next(x for x in candidates if x['params'][0]!=x['params'][1])
    preload_case=next(x for x in candidates if x['params'][0][0]!=x['params'][1][0])
    choices={'known_mass_baseline':((5.,30.,.2),)*2,'lowest_search_score':best['params'],'best_asymmetric_candidate':asym['params'],'unequal_stiffness_example':((10.,290.,80.),(10.,310.,80.)),'unequal_preload_counterexample':preload_case['params']}
    runs={};curves={};audits={}
    for label,params in choices.items():
        runs[label]=[];curves[label]=[]
        for direction in ['opening','closing']:
            row,curve=run(params,direction=direction,rtol=2e-10,step=.0002,dense_count=8001)
            row['static_box']=static_load(params)
            runs[label].append(row);curves[label].append(curve)
            if label in ['known_mass_baseline','lowest_search_score']:
                audits[label+'_'+direction]=independent_four_check(params,direction,curve)
                fine,_=run(params,direction=direction,rtol=1e-11,step=.0001,dense_count=2001)
                err=abs(fine['stop_time_s']-row['stop_time_s']);assert err<1e-7
                audits[label+'_'+direction]['event_refinement_error_s']=err
    sensitivities=[]
    for spin,bj in [('zero_central_spin',0.),('all_mass_ring_bound',0.),('all_mass_stud_bound',0.),('rigid_proxy',BEARING_CO_ROTATING_J_MAX)]:
        for direction in ['opening','closing']:
            row,_=run(best['params'],direction=direction,spin=spin,bearing_j=bj,rtol=2e-10,step=.0002)
            sensitivities.append(row)
    dump('spin-sensitivities.json',sensitivities)
    # No-slip outer-ring sensitivity is separate from rigid crank rotation.
    ss=np.linspace(0,.06,3001);q,qp,qpp=fold(ss);phi=q-np.pi/4
    center_speed_per_s=np.sqrt((-1-.008*np.sin(phi)*qp)**2+(.008*np.cos(phi)*qp)**2)
    spin_metric=dict(CFS_rotor_model='Baseline includes full4g COM motion plus uniform-envelope centralI*qdot². Alternative cases remove that central term before adding separate ring/stud spin.',ring_absolute_omega_per_sdot_minmax_rad_m=[float(min(center_speed_per_s/.004)),float(max(center_speed_per_s/.004))],qprime_max_rad_m=float(max(qp)),central_inertia_bound_assumption='Jstud>=0,Jring>=0,Jstud+Jring<=4g*(4mm)^2, common roller axis and no slip. Alternatives are sensitivity extremes, not measured internals or complete contact dynamics.',bearing_bound_scope='At most both7.2g bearings assigned to co-rotating inner-ring inertia within9.5mm radius; ball/cage spin and real load/friction remain unidentified.')
    critical=[(r['max_pair_difference_mm'],r['remaining_other_branch_mm']) for x in candidates for r in x['runs']]
    close2=[x for x in candidates if all(r['arrived_at_intended_stop'] and r['max_pair_difference_mm']<=2 and r['remaining_other_branch_mm']<=2 for r in x['runs'])]
    sources=[Path(__file__),FORM_PATH,CARRIER_PATH,CARRIER_PATH.parent/'mass-summary.json',ROOT/'engineering/r5_passive01.py',ROOT/'engineering/generated/r5-passive01/study.json',ROOT/'engineering/generated/r5-stage01/study.json',ROOT/'engineering/electronics/r5-cable-hardware01/budget.json']
    report=dict(revision='R5-PASSIVE02',scope='Known material/envelope mass model; massless taut frictionless two-tier differential; separate half-cycles only until first stop/slack. Not a complete1s qualification.',source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},mass_source='R5-CARRIER01 parts-manifest + FORM02, no duplicated form/guide mass',assumptions=dict(gravity_head_m_s2=[0,0,-G],unselected_spring_and_damper=True,all_halfcycles_start_each_leaf_at_rest=True,opening_start_s_m=.06,closing_start_s_m=0.,event_guard_m=1e-8,rail_slider_mass_missing=True,omitted=['actual rail blocks','pulley/cable inertia, friction and compliance','return component mass and nonlinear force','bearing rolling-element spin','slot clearance/impact/slack recovery','actuator dynamics and force limits','actual electronics/wiring','payload during motion and arbitrary gravity']),runs=runs,original_nine_case_comparison=comparison,search=dict(unique_parameter_sets=len(candidates),synchronous_force_fit=fit,close2mm_screen='study-selected diagnostic only, not user acceptance: both halfcycles max difference<=2mm and other branch remaining<=2mm, with intended first stop',close2mm_count=len(close2),best_score=best['score'],finite_search_not_global_optimum=True),spin=spin_metric,independent_checks=audits,cable_boundary='Static normalthreshold plus returnforce screen only; no terminal/routing qualification. Actual rope limit unknown. Asymmetric returnforces can leave nonzeroXY normal resultant for a centered box.',one_second_qualification=False,manufacturing_release=False)
    dump('study.json',report)
    with (OUT/'baseline-and-candidate.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['candidate','direction','t_s','sU_mm','sL_mm','vU_m_s','vL_m_s','leaf_T_N'])
        for label in ['known_mass_baseline','lowest_search_score']:
            for curve in curves[label]:
                for t,v in zip(curve['times'][::10],curve['values'][::10]):writer.writerow([label,curve['direction'],t,v[0]*1000,v[1]*1000,v[2],v[3],v[5]])
    plot(curves,fit)
    print('FINAL',json.dumps(dict(search_count=len(candidates),close2mm_count=len(close2),mass_moving=mass['moving_known_mass_four_branches_kg'],audit_keys=list(audits))),flush=True)


def plot(curves,fit):
    import matplotlib
    matplotlib.use('Agg')
    matplotlib.rcParams['svg.hashsalt']='R5-PASSIVE02'
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(2,2,figsize=(12,8),sharex='col')
    colors={'known_mass_baseline':'#3676a6','lowest_search_score':'#bc6c20'}
    for label in colors:
        for j,curve in enumerate(curves[label]):
            v=curve['values'];t=curve['times']
            ax[0,j].plot(t,(v[:,0]-v[:,1])*1000,color=colors[label],label=label.replace('_',' '))
            ax[1,j].plot(t,v[:,5],color=colors[label])
            ax[0,j].plot(t[-1],(v[-1,0]-v[-1,1])*1000,'o',color=colors[label])
            ax[1,j].plot(t[-1],v[-1,5],'o',color=colors[label])
    for j,d in enumerate(['Opening half-cycle','Closing half-cycle']):
        ax[0,j].set_title(d);ax[0,j].set_ylabel('Upper - lower stroke / mm');ax[1,j].set_ylabel('Leaf tension / N');ax[1,j].set_xlabel('Time / s')
        for a in ax[:,j]:a.set_xlim(0,.5);a.grid(alpha=.2)
    ax[0,0].legend(fontsize=9)
    fig.suptitle('R5-PASSIVE02 / known carrier mass + bounded return-parameter search')
    fig.text(.05,.012,'Curves end at FIRST stop or slack; no post-impact trajectory is drawn. Same input, different springs/dampers.\nReturn parts, cables, rails and actual electronic mass remain unselected; this is not a full 1 s cycle.',fontsize=9)
    fig.tight_layout(rect=[0,.06,1,.95]);fig.savefig(OUT/'return-comparison.png',dpi=170);fig.savefig(OUT/'return-comparison.svg',metadata={'Date':None});plt.close(fig)


if __name__=='__main__':main()
