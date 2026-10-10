# SPDX-License-Identifier: CC-BY-NC-4.0
"""Ordinary single-strut pin clocking over source-bound current arm masses."""
from pathlib import Path
import sys,json,math
import numpy as np
from scipy.optimize import differential_evolution
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'engineering/arm_a18'));import feasibility01 as f

def geometry(theta,ax,az,b,fx):
    ax,az,b,fx=np.array([ax,az,b,fx])/1000
    A=b*ax+fx*az;B=b*az-fx*ax;C=ax*ax+az*az+b*b+fx*fx
    th=np.radians(theta);L=np.sqrt(C+2*A*np.cos(th)+2*B*np.sin(th));k=(A*np.sin(th)-B*np.cos(th))/L
    low,high=np.radians([-60,110]);phase=np.arctan2(B,A)
    probes=[low,high]+[phase+i*np.pi for i in range(-2,3) if low<=phase+i*np.pi<=high]
    lengths=np.sqrt(C+2*A*np.cos(probes)+2*B*np.sin(probes))*1000
    return L,k,float(min(lengths)),float(max(lengths))

def current():
    path=ROOT/'engineering/arm_a18/build/assembly12.json';data=json.loads(path.read_text())
    for name,h in data['source_sha256'].items():assert f.c.sha(ROOT/name)==h
    budget=[dict(id=p['id'],owner=p['owner'],frame=p['frame'],mass_kg=p['mass_kg'],com_mm=p['com_mm']) for p in data['parts']]
    for owner,mass,com in [(3,.1,[170,0,11]),(4,.08,[92.5,62,11]),(7,.06,[65,0,0]),(2,.25,[45,-80,0])]:
        budget.append(dict(id=f'allowance-{owner}',owner=owner,frame=f'J{owner}.rotor',mass_kg=mass,com_mm=com))
    # Independent extra full-moving lump, deliberately not an actual strut mass.
    budget.append(dict(id='new-pin-and-strut-extra-allowance',owner=2,frame='J2.rotor',mass_kg=.30,com_mm=[60,0,30]))
    q=np.array(list(f.c.L['poses'].values())+[[j['limits_deg'][0]+f.rs.halton(k,base)*(j['limits_deg'][1]-j['limits_deg'][0]) for j,base in zip(f.c.L['joints'],[2,3,5,7,11,13,17])] for k in range(1,4097)],float)
    def at(a):
        v=q.copy();v[:,1]=a
        return np.concatenate([f.torque(f.c.L,v,p,budget)[:,1] for p in [0,3]])
    A=at(0);B=at(90)
    assert max(float(np.max(abs(at(a)-A*np.cos(np.radians(a))-B*np.sin(np.radians(a))))) for a in [-60,35,110])<1e-9
    return data,path,budget,q,A,B

def main():
    data,path,budget,q,A,B=current();theta=np.linspace(-60,110,341)
    raw=A[:,None]*np.cos(np.radians(theta))+B[:,None]*np.sin(np.radians(theta));lo=raw.min(axis=0);hi=raw.max(axis=0)
    catalogue=[('01625024',206.5,60,80,750,18.5),('01625025',246.5,80,80,750,18.5),
       ('01625082',256.5,90,80,750,18.5),('01625026',286.5,100,80,750,18.5),('01625043',283,95,100,1200,22)]
    results=[]
    for model,extended,stroke,Fmin,Fmax,diameter in catalogue:
        lower=extended-stroke+6;upper=extended-6
        def objective(x):
            radius,alpha,b,F,fx=x;ax=radius*np.cos(np.radians(alpha));az=radius*np.sin(np.radians(alpha))
            length,lever,Lmin,Lmax=geometry(theta,ax,az,b,fx)
            if Lmin<lower or Lmax>upper:return 1000+10*(max(0,lower-Lmin)+max(0,Lmax-upper))
            compression=(extended-length*1000)/stroke
            F_lo=F*.93*.9-30;F_hi=F*(1+.6*compression)*1.105*1.1+30
            return float(np.max(np.abs(np.array([lo+F_lo*lever,lo+F_hi*lever,hi+F_lo*lever,hi+F_hi*lever]))))
        best=None
        for seed in [19015,19016]:
            r=differential_evolution(objective,[(25,95),(-55,55),(110,194),(Fmin,Fmax),(-65,65)],seed=seed,maxiter=240,popsize=14,tol=2e-7,polish=True)
            if best is None or r.fun<best.fun:best=r
        radius,alpha,b,F,fx=map(float,best.x);ax=radius*np.cos(np.radians(alpha));az=radius*np.sin(np.radians(alpha))
        length,lever,Lmin,Lmax=geometry(theta,ax,az,b,fx)
        checks=[]
        for angle in [-60,0,35,90,110]:
            v=f.c.L['poses']['reference'].copy();v[1]=angle;frames=f.frames(f.c.L,v)
            fixed=frames['J1.rotor']@np.array([fx,62,114-b,1.]);moving=frames['J2.rotor']@np.array([ax,62,az,1.])
            analytic=geometry(np.array([angle]),ax,az,b,fx);error=abs(np.linalg.norm((fixed-moving)[:3])-analytic[0][0]*1000)
            assert error<1e-6
            h=1e-4;lp=geometry(np.array([angle+h]),ax,az,b,fx)[0][0];lm=geometry(np.array([angle-h]),ax,az,b,fx)[0][0]
            assert abs((lp-lm)/(2*np.radians(h))+analytic[1][0])<1e-8
            checks.append(dict(q2_deg=angle,FK_length_error_mm=float(error)))
        rec=dict(model=model,extended_length_mm=extended,stroke_mm=stroke,body_diameter_mm=diameter,F1_N=F,
            moving_pin_J2_xz_mm=[ax,az],moving_pin_radius_mm=radius,moving_pin_phase_deg=alpha,
            fixed_pin_J1_xz_mm=[fx,114-b],fixed_pin_world_Z_mm=279-b,
            full_J2_analytic_eye_length_mm=[Lmin,Lmax],allowed_eye_length_mm=[lower,upper],
            sampled_robust_residual_J2_Nm=float(best.fun),below_22_8_design_screen=bool(best.fun<=22.8),
            checks=checks,assembly_verified=False,purchase_selected=False)
        results.append(rec);print('PIN15',rec,flush=True)
    out=dict(revision='A19-SHOULDER15-PIN-PHASE',source_assembly_sha256=f.c.sha(path),layout=f.c.L,source_sha256=data['source_sha256'],
      candidate_results=results,other_joint_samples=len(q),payload_cases_kg=[0,3],q2_grid_step_deg=.5,
      assumptions=dict(extra_full_moving_mass_kg=.3,progression=[1,1.6],temperature_C=[0,50],F1_tolerance=[.9,1.1],friction_N=[-30,30]),
      supplier_force_guarantee=False,production_release=False,
      source_web=['https://www.suspa.com/global/products/gas-struts/gas-struts-type-16-2/','https://www.suspa.com/global/products/gas-struts/gas-struts-type-16-4/'],
      scope='Simple straight single strut and offset pin tab; no extra linkage. Pin phase searched, actual brackets and continuous coupled collisions pending.')
    (OUT/'shoulder15.json').write_text(json.dumps(out,indent=2)+'\n')

if __name__=='__main__':main()
