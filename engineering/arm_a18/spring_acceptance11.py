# SPDX-License-Identifier: CC-BY-NC-4.0
"""Derive a required measured strut-force window, never invent supplier curves."""
from pathlib import Path
import sys,json,csv,math
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build'
sys.path.insert(0,str(HERE));import feasibility01 as f

def main():
    old=OUT/'feasibility01.json';report=json.loads(old.read_text())
    budget,sources=f.source_budget();assert sources==report['sources']
    budget.append(dict(id='additional-spring-brackets',owner=2,frame='J2.rotor',mass_kg=.15,com_mm=[55,0,0]))
    q=np.array(list(f.c.L['poses'].values())+[[j['limits_deg'][0]+f.rs.halton(k,b)*(j['limits_deg'][1]-j['limits_deg'][0]) for j,b in zip(f.c.L['joints'],[2,3,5,7,11,13,17])] for k in range(1,4097)],float)
    def tau_at(theta):
        v=q.copy();v[:,1]=theta
        return np.array([f.torque(f.c.L,v,p,budget)[:,1] for p in [0,3]])
    A=tau_at(0);B=tau_at(90);errors=[]
    for angle in [-60,35,110]:errors.append(float(np.max(abs(tau_at(angle)-(A*np.cos(np.radians(angle))+B*np.sin(np.radians(angle)))))))
    assert max(errors)<1e-9
    candidate=next(x for x in report['counterbalance_candidates'] if x['model']=='01625025')
    limit=22.8;rows=[];impossible=[]
    for angle in range(-60,111):
        t=A*np.cos(np.radians(angle))+B*np.sin(np.radians(angle))
        length,lever,_,_=f.geometry(np.array([angle]),candidate['a_mm'],candidate['b_mm'],candidate['fixed_pin_x_mm'])
        k=float(lever[0]);minimum=float(t.min());maximum=float(t.max())
        if abs(k)<1e-9:
            lower=0.;upper=None;possible=minimum>=-limit and maximum<=limit
        else:
            x=(-limit-t)/k;y=(limit-t)/k
            lower=max(0.,float(np.max(np.minimum(x,y))));upper=float(np.min(np.maximum(x,y)));possible=upper>=lower
        if not possible:impossible.append(angle)
        rows.append(dict(J2_deg=angle,eye_length_mm=float(length[0]*1000),assist_lever_m=k,
          sampled_raw_min_Nm=minimum,sampled_raw_max_Nm=maximum,
          ideal_q2_only_compensator_lower_bound_Nm=(maximum-minimum)/2,
          required_measured_force_min_N=lower,required_measured_force_max_N=upper,feasible_for_sampled_other_joints=possible))
    with (OUT/'spring-required-force11.csv').open('w') as fp:
        writer=csv.DictWriter(fp,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    out=dict(revision='A18-SPRING-ACCEPTANCE11',baseline_sha256=f.c.sha(old),sources=sources,
      chosen_numerical_candidate=candidate,not_a_purchase_selection=True,provisional_motor_residual_limit_Nm=limit,
      angular_rows=len(rows),other_joint_samples=len(q),payload_cases_kg=[0,3],trigonometric_reconstruction_error_Nm=max(errors),
      impossible_rows=impossible,force_curve_confirmed=False,brackets_and_dynamic_collisions_confirmed=False,
      notes=['Force windows are requirements on the actual extension/compression curves at every operating temperature, not an offered supplier curve.',
      'Do not use nominalF1 alone. Include force tolerance, temperature, friction, ageing and installation error within these windows.',
      'Only other-joint sample set and1-degree shoulder rows are bounded; whole continuous coupled workspace and accelerations are not qualified.',
      'The ideal scalar compensator lower bound is a diagnostic for the sampled set, not an attainable gas-spring guarantee.',
      '22.8Nm is an engineering screen based on80% of catalogue28.5. Enclosed holding torque requires physical thermal qualification.',
      'Spring pin dimensions must not be released before moving brackets/strut clear the J1 stator support and J2/J3 cases.'],production_release=False)
    (OUT/'spring-acceptance11.json').write_text(json.dumps(out,indent=2)+'\n')
    print('SPRING11',len(rows),'rows','impossible',impossible,'reconstruction',max(errors),flush=True)
    for angle in [0,30,60,90,110]:
        print('FORCE11',next(x for x in rows if x['J2_deg']==angle),flush=True)

if __name__=='__main__':main()
