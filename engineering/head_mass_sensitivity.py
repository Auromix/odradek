# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Explicit heavier-head scenarios without changing the R4-layout-03 baseline."""
import copy
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import minimize

from arm_screening import arm_parameters
from kinematics import Arm
from review_arm_screening import reference_gravity, triangle_bounds

ROOT=Path(__file__).resolve().parents[1]


def main():
    path=ROOT/'engineering/parameters/r4-layout.json';p=json.loads(path.read_text())
    model=arm_parameters(p);arm=Arm(model);lo,hi=arm.limits.T
    rng=np.random.default_rng(4517)
    horizontal=np.deg2rad([0,90,0,0,0,0,0])
    samples=np.vstack([rng.uniform(lo,hi,(15000,7)),horizontal,np.zeros(7),
                       np.deg2rad(list(p['poses_deg'].values()))])
    rows=[]
    for mass,offset,l5 in [(2.,[0,0,0],.5),(3.5,[0,0,0],.85),(4.,[0,0,0],.85),
                           (4.5,[0,0,0],.85),(4.5,[0,50,0],.85)]:
        pp=copy.deepcopy(p);pp['link_budgets_kg'][4]=l5
        m=arm_parameters(pp,mass)
        head=next(b for b in m['bodies'] if b['id']=='head_budget')
        head['com_home_m']=(np.asarray(head['com_home_m'])+np.asarray(offset)*.001).tolist()
        gravity,_=reference_gravity(m,samples)
        bounds,_=triangle_bounds(m);maxima=np.max(abs(gravity),axis=0)
        witnesses=np.array([samples[np.argmax(abs(gravity[:,i]))] for i in range(7)])
        # Multi-start local maximization improves witnesses; not a global proof.
        for i in range(1,7):
            ranked=np.argsort(abs(gravity[:,i]))[-3:]
            for idx in ranked:
                sign=np.sign(gravity[idx,i]) or 1.
                def objective(q):return -sign*reference_gravity(m,np.atleast_2d(q))[0][0,i]
                sol=minimize(objective,samples[idx],method='L-BFGS-B',bounds=list(zip(lo,hi)),
                             options={'maxiter':120,'ftol':1e-12,'gtol':1e-7})
                effort=abs(reference_gravity(m,np.atleast_2d(sol.x))[0][0,i])
                if effort>maxima[i]:maxima[i]=effort;witnesses[i]=sol.x
        a=Arm(m);check=np.array([a.gravity_compensation(q)[i] for i,q in enumerate(witnesses)])
        independent_error=float(np.max(abs(abs(check)-maxima)))
        assert independent_error<1e-8
        assert np.all(maxima<=bounds+1e-7)
        rated=np.array([j['rated_torque_Nm'] for j in p['joints']])
        extra_radius_budget_Nm=mass*9.80665*.05
        rows.append({'head_mass_kg':mass,'head_com_offset_from_old_budget_mm':offset,
                     'head_com_home_mm':(np.array(head['com_home_m'])*1000).tolist(),
                     'L5_mass_budget_kg':l5,'model_total_kg_including_fixed_J1_and_object':sum(b['mass_kg'] for b in m['bodies']),
                     'search_sample_count':len(samples),'optimized_witness_abs_gravity_Nm':maxima.tolist(),
                     'witness_q_deg_by_joint':np.rad2deg(witnesses).tolist(),
                     'triangle_bound_Nm':bounds.tolist(),
                     'horizontal_pose_gravity_Nm':reference_gravity(m,np.atleast_2d(horizontal))[0][0].tolist(),
                     'rated_torque_Nm':rated.tolist(),'rated_minus_witness_Nm':(rated-maxima).tolist(),
                     'witness_exceeds_catalog_rated':(maxima>rated).tolist(),
                     'triangle_bound_exceeds_catalog_rated':(bounds>rated).tolist(),
                     'independent_witness_check_error_Nm':independent_error,
                     'additional_50mm_head_com_uncertainty_scalar_bound_Nm':extra_radius_budget_Nm})
    output=ROOT/'docs/engineering/analysis/head-mass-sensitivity.json'
    report={'revision':'R4-HEAD-MASS-01','baseline_parameter_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'status':'mass sensitivity only; baseline unchanged; not an actuator qualification',
            'method':'15005 seeded samples then three L-BFGS-B starts per joint and independent Arm witness check',
            'payload_net_kg':2.,'cases':rows,
            'assumptions':['head 3.5/4/4.5 kg responds to support02 planning, not weighed assemblies',
                           'L5 0.85 kg is provisional allowance above 0.728 kg original metal candidate, not final fastener rollup',
                           'last scenario has arbitrary +50 mm transverse COM offset; not a measured total-head COM',
                           'other link masses and all module COM proxies stay at baseline',
                           'mass increase does not include a necessary rear-interface extension or new tip position',
                           'witness poses have not been qualified for collision, harness or task reachability',
                           'local optimum and sample maxima are lower bounds on worst modeled effort',
                           'triangle bound over rating alone is inconclusive; an over-rating witness is a counterexample within this model',
                           'running catalog rating is not installed zero-speed/thermal rating',
                           'no acceleration, friction, manipulation reaction or brake qualification']}
    output.write_text(json.dumps(report,indent=2)+'\n')
    fig,ax=plt.subplots(figsize=(10,5),layout='constrained');x=np.arange(1,8);w=.14
    for k,row in enumerate(rows):
        label=f'{row["head_mass_kg"]:g} kg head'+(' + 50 mm Y COM' if any(row['head_com_offset_from_old_budget_mm']) else '')
        ax.bar(x+(k-2)*w,row['optimized_witness_abs_gravity_Nm'],w,label=label)
    ax.plot(x,rows[0]['rated_torque_Nm'],'kD--',label='Catalog running torque')
    ax.set(xticks=x,xticklabels=[f'J{i}' for i in x],ylabel='Static joint effort / Nm',
           title='Heavier-head sensitivity — unqualified witness poses; no dynamic margin')
    ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8)
    fig.savefig(output.with_suffix('.png'),dpi=160);plt.close(fig)
    for r in rows:print(r['head_mass_kg'],r['head_com_offset_from_old_budget_mm'],
                       np.round(r['optimized_witness_abs_gravity_Nm'],3).tolist(),
                       r['witness_exceeds_catalog_rated'])


if __name__=='__main__':main()
