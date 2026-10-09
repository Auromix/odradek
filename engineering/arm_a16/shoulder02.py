# SPDX-License-Identifier: CC-BY-NC-4.0
"""Optimize only two ordinary gas-spring pin locations, not a new mechanism."""
import json,sys,numpy as np
from scipy.optimize import differential_evolution
import common as c
sys.path.insert(0,str(c.ROOT/'engineering/arm_a15/robstride01'));import study as rs

def main():
    D=json.loads((c.OUT/'gravity.json').read_text());assert D['layout']==c.L
    for src in D['sources']:assert c.sha(c.ROOT/src['path'])==src['sha256']
    budget=D['prototype_CAD_and_allowance_ledger'];named=list(c.L['poses'].values())
    q=np.array(named+[[j['limits_deg'][0]+rs.halton(k,b)*(j['limits_deg'][1]-j['limits_deg'][0]) for j,b in zip(c.L['joints'],[2,3,5,7,11,13,17])] for k in range(1,4097)],float)
    raw=np.array([rs.batch_gravity(c.L,q,p,budget)[:,1] for p in [0,3]])
    angle=np.radians(q[:,1]);sin=np.sin(angle);cos=np.cos(angle)
    def geometry(a,b,fx=0):
        A=a*b;B=-a*fx;C=a*a+b*b+fx*fx
        length=np.sqrt(C+2*A*cos+2*B*sin);lever=(A*sin-B*cos)/length
        # All stationary points plus endpoints prove the pin-eye length range
        # over the continuous interval; force/workspace still only sampled.
        lo,hi=np.radians([-60,110]);phase=np.arctan2(B,A)
        probes=[lo,hi]+[phase+k*np.pi for k in range(-2,3) if lo<=phase+k*np.pi<=hi]
        values=np.sqrt(C+2*A*np.cos(probes)+2*B*np.sin(probes))
        return length,lever,float(min(values)),float(max(values))
    def worst(x):
        a,b,F=x[:3];fx=x[3] if len(x)>3 else 0;a/=1000;b/=1000;fx/=1000;length,lever,lo,hi=geometry(a,b,fx)
        if lo<.166 or hi>.258:return 1000+10000*(max(0,.166-lo)+max(0,hi-.258))
        comp=(.264-length)/.1;result=0
        for progression in [1,1.6]:
            for temp in [0,50]:
                for tol in [.9,1.1]:
                    for friction in [-30,30]:
                        force=F*(1+(progression-1)*comp)*(1+.0035*(temp-20))*tol+friction
                        result=max(result,float(np.max(abs(raw+force*lever))))
        return result
    simple=differential_evolution(worst,[(42,92),(164,216),(50,420)],seed=1602,tol=1e-8,maxiter=160,polish=True)
    result=differential_evolution(worst,[(42,92),(164,216),(50,420),(-20,20)],seed=1603,tol=1e-8,maxiter=220,polish=True)
    a,b,F,fx=map(float,result.x);length,lever,lo,hi=geometry(a/1000,b/1000,fx/1000)
    fixed=np.array([fx,-80,c.L['joints'][1]['offset'][2]-b,1.])
    moving=np.array([a,-80,0,1.]);length_errors=[];lever_errors=[]
    def fk_length(v):
        frames=c.frames(v)
        return np.linalg.norm((frames['J1.rotor']@fixed-frames['J2.rotor']@moving)[:3])/1000
    for i in [0,1,2,3,len(q)-1]:
        v=q[i].tolist();length_errors.append(abs(fk_length(v)-length[i]))
        plus=v.copy();minus=v.copy();h=1e-4;plus[1]+=h;minus[1]-=h
        derivative=(fk_length(plus)-fk_length(minus))/(2*np.radians(h))
        lever_errors.append(abs(derivative+lever[i]))
    assert max(length_errors)<1e-9 and max(lever_errors)<1e-8
    record=dict(revision='A16-SHOULDER02-CONVENTIONAL-PINS',layout=c.L,gravity_sha256=c.sha(c.OUT/'gravity.json'),
      sample_count=len(q),payload_cases_kg=[0,3],a_mm=a,b_mm=b,fixed_pin_x_mm=fx,candidate_F1_N=F,
      aligned_pin_comparison=dict(a_mm=float(simple.x[0]),b_mm=float(simple.x[1]),F1_N=float(simple.x[2]),worst_Nm=float(simple.fun)),
      fixed_pin_J1_rotor_mm=[fx,-80,c.L['joints'][1]['offset'][2]-b],moving_pin_J2_rotor_mm=[a,-80,0],
      analytic_eye_length_full_J2_interval_mm=[float(lo*1000),float(hi*1000)],
      independent_FK_length_max_error_mm=float(max(length_errors)*1000),
      independent_virtual_work_lever_max_error_m=float(max(lever_errors)),
      assumed_force_envelope_worst_shoulder_Nm=float(worst(result.x)),zero_speed_catalogue_reference_Nm=28.5,
      assumed_static_envelope_below_reference=bool(worst(result.x)<28.5),
      conventional_structure='Same single100mm-stroke catalogue gas spring and two ordinary pinned brackets. No cam, gear, differential or parallel motors.',
      limits=['Pin brackets, rod articulation, side loading, frame stress and whole-spring collisions are not designed or checked.',
       'F1 range50..420, eye length264+/-2, stroke100 inherited from the A15 SUSPA source; force progression1..1.6,0..50C,F1+/-10%,friction+/-30N are proposed test assumptions, not supplier guarantees.',
       'The static extremum is over unfiltered discrete4099 poses and two payload cases, not the full continuous workspace or dynamics.',
       'Full-interval pin-eye length clearance only. Body diameter15, rod6, eye/pin hardware and brackets still require source geometry and physical trial.',
       'Enclosed motor thermal holding capacity, actual COM, spring hysteresis and power-loss holding remain unqualified. No load or production release.'],
      production_release=False,selection_frozen=False)
    (c.OUT/'shoulder02.json').write_text(json.dumps(record,indent=2)+'\n');print('SIMPLE_PINS',a,b,F,'WORST',record['assumed_force_envelope_worst_shoulder_Nm'],'LENGTH',record['analytic_eye_length_full_J2_interval_mm'],flush=True)

if __name__=='__main__':main()
