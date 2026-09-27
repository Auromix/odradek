# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Normal-load coupling sensitivity and direct minimum shared torque cap.

Existence of friction-cone equilibrium is not realizability by a single
compliant finger or qualification of a motor/gearbox.
"""
from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from grasp_screening import solve_grasp
from finite_pad_contacts import grouped_contact_regression

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'engineering/generated/pad-loadsharing'


def inputs(case):
    items=[d['components'][k] for d in case['fingers'] for k in ['pad_minus','pad_plus']]
    points=np.array([p['point_head_mm'] for p in items])*.001;com=points.mean(0);com[:2]=0
    return dict(points=points,normals=[p['normal_on_object'] for p in items],
        jacobians=[p['jacobian_m_per_rad'] for p in items],com=com,wrench=[0,0,-39.2266,0,0,0],
        minimum_normal_N=1.,contact_to_joint=np.repeat(np.arange(4),2))


def threshold(kwargs):
    lo,hi=0.,8.;high=solve_grasp(torque_limit=[hi]*4,**kwargs)
    if not high['feasible']:return {'feasible_up_to_8Nm':False}
    for _ in range(24):
        mid=(lo+hi)/2;ans=solve_grasp(torque_limit=[mid]*4,**kwargs)
        if ans['feasible']:hi=mid;high=ans
        else:lo=mid
    assert high['max_force_balance_residual_N']<1e-5 and high['max_moment_balance_residual_Nm']<1e-5
    return {'feasible_up_to_8Nm':True,'infeasible_lower_bracket_Nm':lo,
            'feasible_upper_bracket_Nm':hi,'witness_at_upper_bracket':high,
            'numerical_note':'LP feasibility tolerance means bracket is numerical, not an exact analytic load bound'}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    path=ROOT/'engineering/generated/contact02-study/study.json';d=json.loads(path.read_text());rows=[]
    for c in d['contact_cases']:
        if c['z_limits_mm'] is not None or c['diameter_mm'] not in [30,50,80,100,120]:continue
        data=inputs(c)
        for mu in [.3,.4,.6]:
            for ratio in [None,.25,.5,1.,2.,4.]:
                constraints=None if ratio is None else [(i,i+1,ratio) for i in range(0,8,2)]
                kw={**data,'mu':mu,'normal_ratio_constraints':constraints}
                bounds=threshold(kw)
                row={'diameter_mm':c['diameter_mm'],'mu':mu,'paired_Nminus_over_Nplus':ratio,**bounds}
                if c['diameter_mm']==80 and mu==.4:
                    row['specified_cap_checks']=[{'cap_Nm':cap,**solve_grasp(torque_limit=[cap]*4,**kw)} for cap in [3.,3.145,3.33,3.5,3.515,3.7]]
                rows.append(row)
    # Pair ratio 2 and 1/2 are left/right mirrors for the symmetric workpiece.
    mirror=[]
    for dia in [30,50,80,100,120]:
        for mu in [.3,.4,.6]:
            a=next(r for r in rows if r['diameter_mm']==dia and r['mu']==mu and r['paired_Nminus_over_Nplus']==2)
            b=next(r for r in rows if r['diameter_mm']==dia and r['mu']==mu and r['paired_Nminus_over_Nplus']==.5)
            assert a['feasible_up_to_8Nm']==b['feasible_up_to_8Nm']
            if a['feasible_up_to_8Nm']:
                err=abs(a['feasible_upper_bracket_Nm']-b['feasible_upper_bracket_Nm']);assert err<2e-6;mirror.append(err)
    # Default API preserves the already committed unsplit / shared-axis checks.
    regression=grouped_contact_regression()
    default_errors=[]
    for c in d['contact_cases']:
        if c['z_limits_mm'] is not None or not c['all_four_paired_pads_first']:continue
        for old in c.get('conditional_grasps',[]):
            result=solve_grasp(**inputs(c),mu=old['mu'],torque_limit=[old['cap_Nm']]*4)
            assert result['feasible']==old['feasible']
            if result['feasible']:default_errors.append(abs(result['normal_total_N']-old['normal_total_N']))
    assert max(default_errors)<1e-8
    report={'revision':'PAD-LOADSHARING-01','inputs_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [path,Path(__file__),ROOT/'engineering/grasp_screening.py']},
        'cases':rows,'checks':{'mirror_max_threshold_error_Nm':max(mirror),'default_normal_sum_error_N':max(default_errors),'original_grouped_contact_regression':regression},
        'meaning_of_ratio':'normal force of pad_minus divided by pad_plus on each rigid finger; all fingers use same ratio case',
        'limits':['Equal or fixed-ratio paired normals are sensitivity assumptions, not a measured pad compliance law',
            'Actual force distribution, contact deformation and attainable controller equilibria remain unknown',
            'Default LP first minimizes total normal force then peak joint torque among those optima; its witness is not a minimum torque capacity',
            'This study directly bisects a common four-axis cap; supports no actuator efficiency, self-weight, thermal or dynamic qualification',
            'No pressure upper bound, pad attachment or material strength constraint is included',
            'Eight contacts still map to four shared actuator torque limits'],
        'manufacturing_release':False}
    (OUT/'study.json').write_text(json.dumps(report,indent=2)+'\n')
    fig,axes=plt.subplots(1,3,figsize=(13,4),layout='constrained')
    for ax,mu in zip(axes,[.3,.4,.6]):
        for ratio,label in [(None,'Free normal sharing'),(1.,'Paired 1:1'),(2.,'Paired 2:1'),(4.,'Paired 4:1')]:
            rr=[r for r in rows if r['mu']==mu and r['paired_Nminus_over_Nplus']==ratio]
            ax.plot([r['diameter_mm'] for r in rr],[r.get('feasible_upper_bracket_Nm',float('nan')) for r in rr],marker='o',label=label)
        ax.axhline(3.515,color='#923b34',ls='--',label='3.7 Nm x 95%')
        ax.set(xlabel='Cylinder diameter / mm',ylabel='Minimum common cap / Nm',title=f'Assumed friction mu = {mu:g}',xlim=(25,125),xticks=[30,50,80,100,120]);ax.grid(alpha=.2)
    axes[0].legend(fontsize=7)
    fig.suptitle('Shared torque / normal distribution sensitivity; missing points = no solution up to 8 Nm')
    fig.savefig(OUT/'loadsharing.png',dpi=150);plt.close(fig)
    for r in rows:
        if r['diameter_mm']==80 and r['mu']==.4:print(r['paired_Nminus_over_Nplus'],r.get('feasible_upper_bracket_Nm'))
    print('default/mirror regression',report['checks'])

if __name__=='__main__':main()
