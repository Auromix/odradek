# SPDX-License-Identifier: CC-BY-NC-4.0
"""Source-bound long-arm screening; no physical or production qualification."""
from pathlib import Path
import copy, json, math, sys
import numpy as np
from scipy.optimize import differential_evolution

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]; OUT=HERE/'build'
sys.path.insert(0,str(ROOT/'engineering/arm_a16'))
import common as c
from assembly_sources import collect
sys.path.insert(0,str(ROOT/'engineering/arm_a15/robstride01'))
import study as rs

def frames(layout,q):
    T=np.array(layout['root_transform_mm'],float); f={'world':T.copy()}
    for j,x in zip(layout['joints'],q):
        O=np.eye(4); O[:3,3]=j['offset']; T=T@O; f[j['id']+'.fixed']=T.copy()
        R=np.eye(4); R[:3,:3]=rs.rotations(j['axis'],np.array([x+j['zero_deg']]))[0]
        T=T@R; f[j['id']+'.rotor']=T.copy()
    O=np.eye(4); O[:3,3]=layout.get('flange_from_J7_mm',[110,0,0]); f['flange']=T@O
    return f

def torque(layout,q,payload,budget):
    # Keep the legacy calculation unchanged; changing the flange adds exactly
    # the payload moment at its new position. Component COMs are not shortened.
    tau=rs.batch_gravity(layout,q,payload,budget)
    delta=np.array(layout.get('flange_from_J7_mm',[110,0,0]))-[110,0,0]
    if np.any(delta):
        R=np.broadcast_to(np.eye(3),(len(q),3,3)).copy(); axes=[]
        for i,j in enumerate(layout['joints']):
            axes.append(np.einsum('nij,j->ni',R,j['axis']))
            R=R@rs.rotations(j['axis'],q[:,i]+j['zero_deg'])
        moment=np.cross(np.einsum('nij,j->ni',R,delta)/1000,[0,0,-9.81*payload])
        for i in range(7):tau[:,i]-=np.einsum('ni,ni->n',axes[i],moment)
    return tau

def source_budget():
    path=ROOT/'engineering/arm_a17/build/style01/manifest.json'; d=json.loads(path.read_text())
    rows,sources,_=collect(last='skins06'); rows=[x for x in rows if x['id'] not in d['replaces_only']]+d['parts']
    assert len(rows)==541
    sources[str(path.relative_to(ROOT))]=c.sha(path)
    for p in d['parts']:
        f=path.parent/'step'/(p['id']+'.step');sources[str(f.relative_to(ROOT))]=c.sha(f)
    budget=[dict(id=x['id'],owner=x['owner'],frame=x['frame'],mass_kg=x['mass_kg'],com_mm=x['com_mm']) for x in rows]
    for owner,mass,com in [(3,.1,[170,0,11]),(4,.08,[92.5,62,11]),(7,.06,[65,0,0]),(2,.25,[45,-80,0])]:
        budget.append(dict(id=f'allowance-{owner}',owner=owner,frame=f'J{owner}.rotor',mass_kg=mass,com_mm=com))
    return budget,sources

def geometry(q2,a,b,fx):
    a/=1000;b/=1000;fx/=1000;th=np.radians(q2)
    A=a*b;B=-a*fx;C=a*a+b*b+fx*fx
    length=np.sqrt(C+2*A*np.cos(th)+2*B*np.sin(th));lever=(A*np.sin(th)-B*np.cos(th))/length
    lo,hi=np.radians([-60,110]);phase=np.arctan2(B,A)
    probes=[lo,hi]+[phase+k*np.pi for k in range(-2,3) if lo<=phase+k*np.pi<=hi]
    values=np.sqrt(C+2*A*np.cos(probes)+2*B*np.sin(probes))
    return length,lever,float(min(values)*1000),float(max(values)*1000)

def main():
    OUT.mkdir(parents=True,exist_ok=True);budget,sources=source_budget();base=c.base_context()
    q=np.array(list(c.L['poses'].values())+[[j['limits_deg'][0]+rs.halton(k,b)*(j['limits_deg'][1]-j['limits_deg'][0]) for j,b in zip(c.L['joints'],[2,3,5,7,11,13,17])] for k in range(1,4097)],float)
    raw=torque(c.L,q,3,budget)
    previous=json.loads((ROOT/'engineering/arm_a17/build/style01/physics.json').read_text())
    error=float(np.max(abs(np.max(abs(raw),axis=0)-previous['sampled_abs_max_Nm'])))
    assert error<1e-10
    wrists=[];virtual_errors=[]
    for flange_x,j7_offset in [(110,75),(95,75),(85,75),(75,75),(85,65),(75,65)]:
        layout=copy.deepcopy(c.L);layout['flange_from_J7_mm']=[flange_x,0,0];layout['joints'][6]['offset']=[j7_offset,0,0]
        t=torque(layout,q,3,budget);maxima=np.max(abs(t),axis=0).tolist()
        def potential(v):
            f=frames(layout,v); bodies=budget+[dict(frame=j['id']+'.fixed',mass_kg=j['mass_kg'],com_mm=j['motor_center']) for j in layout['joints']]
            return sum(x['mass_kg']*9.81*(f[x['frame']]@np.r_[x['com_mm'],1])[2]/1000 for x in bodies)+3*9.81*f['flange'][2,3]/1000
        for v in [list(c.L['poses'].values())[1],[23,55,35,-85,68,24,42]]:
            exact=torque(layout,np.array([v],float),3,budget)[0]
            for i in range(7):
                a=v.copy();b=v.copy();h=1e-4;a[i]+=h;b[i]-=h
                virtual_errors.append(abs((potential(a)-potential(b))/(2*math.radians(h))-exact[i]))
        wrists.append(dict(flange_x_mm=flange_x,J6_to_J7_mm=j7_offset,sampled_max_Nm=maxima,
          assembly_verified=False,limitation='Existing carrier/ports/COMs retained for conservative comparison, not a compact CAD assembly. Bearing pair retained; no native bearing rating assumed.'))
    assert max(virtual_errors)<1e-6
    # Add a common conservative allowance to all counterbalance candidates,
    # including the twin-strut case. This is not a weighed strut assembly.
    sbudget=budget+[dict(id='additional-spring-brackets',owner=2,frame='J2.rotor',mass_kg=.15,com_mm=[55,0,0])]
    spring_raw=np.array([torque(c.L,q,p,sbudget)[:,1] for p in [0,3]])
    candidates=[]
    # L +/-2 plus 4 mm reserve at both ends. F1 is PER STRUT.
    for model,count,L,stroke,fmin,fmax,diam in [('01625011',1,264,100,50,420,15),('01625025',1,246.5,80,80,750,18.5),('01625011',2,264,100,50,420,15)]:
        lower=L-stroke+6;upper=L-6
        def objective(x):
            a,b,F,fx=x;length,lever,lo,hi=geometry(q[:,1],a,b,fx)
            if lo<lower or hi>upper:return 1000+10*(max(0,lower-lo)+max(0,hi-upper))
            comp=(L-length*1000)/stroke
            force_lo=count*(F*.93*.9-30)
            force_hi=count*(F*(1+.6*comp)*1.105*1.1+30)
            return float(max(np.max(abs(spring_raw+force_lo*lever)),np.max(abs(spring_raw+force_hi*lever))))
        result=differential_evolution(objective,[(25,95),(130,194),(fmin,fmax),(-25,25)],seed=1801,tol=2e-7,maxiter=180,popsize=12,polish=True)
        a,b,F,fx=map(float,result.x);length,lever,lo,hi=geometry(q[:,1],a,b,fx)
        errs=[];der=[]
        # Symmetric side-plane position does not change length or generalized
        # torque. No lateral packaging or bracket feasibility is asserted.
        fixed=np.array([fx,-62,114-b,1]);moving=np.array([a,-62,0,1])
        def fk_length(v):
            f=frames(c.L,v);return np.linalg.norm((f['J1.rotor']@fixed-f['J2.rotor']@moving)[:3])/1000
        for k in [0,1,2,4098]:
            v=q[k].tolist();errs.append(abs(fk_length(v)-length[k]));p=v.copy();m=v.copy();h=1e-4;p[1]+=h;m[1]-=h
            der.append(abs((fk_length(p)-fk_length(m))/(2*math.radians(h))+lever[k]))
        assert max(errs)<1e-9 and max(der)<1e-8
        rec=dict(model=model,quantity=count,catalogue_extended_length_mm=L,stroke_mm=stroke,body_diameter_mm=diam,
          a_mm=a,b_mm=b,fixed_pin_x_mm=fx,F1_per_strut_N=F,
          fixed_pin_world_height_mm=279-b,analytic_eye_length_full_J2_mm=[lo,hi],allowed_eye_length_mm=[lower,upper],
          sampled_robust_abs_max_J2_Nm=float(result.fun),below_28_5_reference=bool(result.fun<28.5),below_22_8_design_target=bool(result.fun<22.8),
          FK_length_max_error_mm=max(errs)*1000,virtual_work_lever_max_error_m=max(der),assembly_verified=False)
        candidates.append(rec);print('SPRING',model,count,'J2',result.fun,'pins',a,b,fx,'F1',F,flush=True)
    report=dict(revision='A18-FEASIBILITY01',base_context=base,layout=c.L,sources=sources,
      baseline_A17_max_error_Nm=error,virtual_work_max_error_Nm=max(virtual_errors),
      raw_torques_Nm=np.max(abs(raw),axis=0).tolist(),sample_count=len(q),wrist_comparisons=wrists,counterbalance_candidates=candidates,
      assumptions=dict(payload_cases_kg=[0,3],progression=[1,1.6],temperature_C=[0,50],thermal_coefficient_per_C=.0035,F1_factor=[.9,1.1],friction_per_strut_N=[-30,30],additional_moving_allowance_kg=.15,fixed_pin_min_world_Z_mm=85),
      sources_web=['https://www.suspa.com/global/products/gas-struts/gas-struts-type-16-1','https://www.suspa.com/global/products/gas-struts/gas-struts-type-16-2/'],
      force_envelope_is_supplier_guarantee=False,production_release=False,
      limits=['4099 unfiltered configurations, not collision-qualified or continuous workspace.','Spring body/clevis/bracket collision, side load, fatigue and force/hysteresis are unqualified.','Catalogue torque reference is not an enclosed thermal holding rating.','Wrist shortening is a parametric moment comparison only; existing connector depth prevents automatic CAD shortening.'])
    (OUT/'feasibility01.json').write_text(json.dumps(report,indent=2)+'\n')
    print('WRISTS',[(x['flange_x_mm'],x['J6_to_J7_mm'],x['sampled_max_Nm'][4]) for x in wrists],flush=True)

if __name__=='__main__':main()
