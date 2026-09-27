# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Hybrid LINK56-CAD / heavier-head static and anchored-base sensitivity."""
from pathlib import Path
import copy,hashlib,json
import numpy as np
from scipy.optimize import minimize
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from candidate_mass_model import candidate_model, link56_bodies
from kinematics import Arm
from review_arm_screening import reference_gravity, triangle_bounds
from build_base_study import LEG_RADIUS, G, E

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/candidate-loads'


def lumped_rigid_body(bodies):
    mass=sum(b['mass_kg'] for b in bodies);com=sum(b['mass_kg']*np.array(b['com_home_m']) for b in bodies)/mass
    tensor=np.zeros((3,3))
    for b in bodies:
        delta=np.array(b['com_home_m'])-com;R=np.array(b['orientation_home'])
        tensor+=R@np.array(b['inertia_com_kg_m2'])@R.T+b['mass_kg']*(np.eye(3)*(delta@delta)-np.outer(delta,delta))
    return {'id':'L56_lumped','mass_kg':mass,'preceding_joints':5,'com_home_m':com.tolist(),
            'orientation_home':np.eye(3).tolist(),'inertia_com_kg_m2':tensor.tolist()}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    pp=ROOT/'engineering/parameters/r4-layout.json';p=json.loads(pp.read_text())
    bp=ROOT/'engineering/generated/base-study/evidence.json';base=json.loads(bp.read_text())['loads']
    sample_model,source_info=candidate_model(p,4.5);arm=Arm(sample_model);lo,hi=arm.limits.T
    rng=np.random.default_rng(4517)
    samples=np.vstack([rng.uniform(lo,hi,(15000,7)),np.deg2rad([0,90,0,0,0,0,0]),np.zeros(7),np.deg2rad(list(p['poses_deg'].values()))])
    pieces=[b for b in sample_model['bodies'] if b['id'].startswith('L56_')]
    lump=lumped_rigid_body(pieces);lm=copy.deepcopy(sample_model);lm['bodies']=[b for b in lm['bodies'] if not b['id'].startswith('L56_')]+[lump]
    la=Arm(lm)
    gravity_error=max(float(np.max(abs(arm.gravity_compensation(q)-la.gravity_compensation(q)))) for q in samples[:12])
    mass_error=max(float(np.max(abs(arm.mass_matrix(q)-la.mass_matrix(q)))) for q in samples[:12])
    assert gravity_error<1e-10 and mass_error<1e-10
    rows=[]
    for mass,offset in [(2.,[0,0,0]),(3.5,[0,0,0]),(4.,[0,0,0]),(4.5,[0,0,0]),(4.5,[0,50,0])]:
        model,_=candidate_model(p,mass,offset);a=Arm(model)
        gravity,(_,_,_,states)=reference_gravity(model,samples);bound=triangle_bounds(model)[0]
        maxima=np.max(abs(gravity),axis=0);witness=np.array([samples[np.argmax(abs(gravity[:,i]))] for i in range(7)])
        for i in range(1,7):
            for idx in np.argsort(abs(gravity[:,i]))[-3:]:
                sign=np.sign(gravity[idx,i]) or 1.
                sol=minimize(lambda q:-sign*reference_gravity(model,np.atleast_2d(q))[0][0,i],samples[idx],
                             method='L-BFGS-B',bounds=list(zip(lo,hi)),options={'maxiter':120,'ftol':1e-12,'gtol':1e-7})
                effort=abs(reference_gravity(model,np.atleast_2d(sol.x))[0][0,i])
                if effort>maxima[i]:maxima[i]=effort;witness[i]=sol.x
        error=max(abs(abs(a.gravity_compensation(q)[i])-maxima[i]) for i,q in enumerate(witness));assert error<1e-8
        assert np.all(maxima<=bound+1e-8)
        total_mass=sum(b['mass_kg'] for b in model['bodies'])
        upstream=sum(b['mass_kg']*G*np.linalg.norm(np.array(b['com_home_m'])[:2]) for b in model['bodies'] if b['preceding_joints']<=1)
        base_bound=float(bound[1]+upstream)
        vector=sum(np.cross(point,b['mass_kg']*np.array([0,0,-G])) for b,point in states)
        sampled_base=np.linalg.norm(vector[:,:2],axis=1);assert sampled_base.max()<=base_bound+1e-8
        uncertainty=2*G*.1+mass*G*.05+.1*G*.15
        design=1.5*(base_bound+uncertainty)
        vertical=1.5*G*(total_mass+base['base_original_mass_kg']+.5)
        fpost=vertical/4+design*1000/(2*LEG_RADIUS)
        area=base['post_area_net_major_diameter_mm2'];I=base['post_I_net_mm4'];span=base['plate_strip_span_mm']
        ecc=base['post_support_top']['radial_eccentricity_mm']+base['post_support_bottom']['radial_eccentricity_mm']
        rated=np.array([j['rated_torque_Nm'] for j in p['joints']])
        rows.append({'head_mass_kg':mass,'head_COM_offset_mm':offset,'arm_model_mass_including_object_and_J1_kg':total_mass,
            'witness_max_abs_gravity_Nm':maxima.tolist(),'witness_q_deg_by_joint':np.rad2deg(witness).tolist(),
            'triangle_bound_Nm':bound.tolist(),'catalog_rated_Nm':rated.tolist(),
            'witness_over_rated':(maxima>rated).tolist(),'triangle_over_rated':(bound>rated).tolist(),
            'independent_gravity_error_Nm':float(error),'base':{
                'nominal_overturning_bound_Nm':base_bound,'sample_max_overturning_Nm':float(sampled_base.max()),
                'sample_worst_q_deg':np.rad2deg(samples[sampled_base.argmax()]).tolist(),
                'added_COM_uncertainty_Nm':uncertainty,'study_multiplier':1.5,
                'study_design_moment_Nm':design,'study_vertical_budget_N':vertical,
                'post_equal_stiffness_max_abs_N':fpost,'J1_fixed_M4_equal_stiffness_N':vertical/8+design*1000/(4*51),
                'anchor_equal_stiffness_tension_no_gravity_relief_N':design*1000*np.sqrt(2)/(4*110),
                'single_anchor_110mm_lever_example_N':design*1000/110,
                'post_nominal_axial_eccentric_stress_MPa':fpost/area+fpost*ecc*12/I,
                'plate_strip_sensitivity_stress_MPa':6*fpost*span/(24*16**2),
                'plate_strip_sensitivity_deflection_mm':fpost*span**3/(3*E*(24*16**3/12))}})
    report={'revision':'CANDIDATE-LOADS-01','baseline_sha256':hashlib.sha256(pp.read_bytes()).hexdigest(),
        'base_study_sha256':hashlib.sha256(bp.read_bytes()).hexdigest(),'link56':source_info,
        'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'mass_helper_sha256':hashlib.sha256((ROOT/'engineering/candidate_mass_model.py').read_bytes()).hexdigest(),
        'replacement_bodies':pieces,'equivalent_rigid_body':lump,
        'rigid_body_equivalence_regression':{'poses':12,'gravity_max_error_Nm':gravity_error,'mass_matrix_max_error_kg_m2':mass_error},
        'search_samples':len(samples),'cases':rows,'manufacturing_release':False,
        'limits':['Only six LINK56 solids use CAD-derived mass/COM/inertia; 0.1kg local reserve remains a proxy',
            'Head masses/COM and other five connections remain assumptions; no new tip/interface offsets included',
            'Base COM budgets: object 100mm, head additional 50mm, 0.1kg local reserve 150mm; not all uncertainty bounded',
            '0.5kg base/general hardware reserve is separate from LINK56 0.1kg allowance',
            'No collision/task/harness validation of sampled or optimized poses',
            'Local witness maximum is not a global proof; running rating does not establish zero-speed thermal capacity',
            'Base equal-stiffness loads and strip stresses omit prying/preload/contact separation/local concentration',
            'No dynamic, contact, fatigue, thread stripping, anchor/table capacity or brake qualification']}
    (OUT/'study.json').write_text(json.dumps(report,indent=2)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained');x=np.arange(2,8);w=.15
    for k,row in enumerate(rows):
        label=f'{row["head_mass_kg"]:g} kg'+(' +50Y' if any(row['head_COM_offset_mm']) else '')
        axes[0].bar(x+(k-2)*w,row['witness_max_abs_gravity_Nm'][1:],w,label=label)
    axes[0].plot(x,rows[0]['catalog_rated_Nm'][1:],'kD--',label='Catalog running rating')
    axes[0].set(xticks=x,xlabel='Joint number',ylabel='Gravity effort / Nm',title='LINK56 CAD mass replaces old link budget');axes[0].legend(fontsize=7);axes[0].grid(axis='y',alpha=.2)
    labels=[f'{r["head_mass_kg"]:g}kg'+('+50Y' if any(r['head_COM_offset_mm']) else '') for r in rows]
    xx=np.arange(len(rows));axes[1].bar(xx-.17,[r['base']['nominal_overturning_bound_Nm'] for r in rows],.34,label='Nominal global bound')
    axes[1].bar(xx+.17,[r['base']['study_design_moment_Nm'] for r in rows],.34,label='Added budgets then x1.5')
    axes[1].set(xticks=xx,xticklabels=labels,ylabel='Base moment / Nm',title='Anchored-base sensitivity / no dynamic terms');axes[1].legend(fontsize=8);axes[1].grid(axis='y',alpha=.2)
    fig.savefig(OUT/'candidate-loads.png',dpi=150);plt.close(fig)
    print('L56 COM/mm',source_info['metal_COM_home_mm'],'equivalence errors',gravity_error,mass_error)
    for row in rows:print(row['head_mass_kg'],row['head_COM_offset_mm'],np.round(row['witness_max_abs_gravity_Nm'],3).tolist(), 'base',round(row['base']['study_design_moment_Nm'],3), 'plate',round(row['base']['plate_strip_sensitivity_stress_MPa'],3))

if __name__=='__main__':main()
