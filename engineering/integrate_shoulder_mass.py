# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Add LINK12 CAD inertia without rerunning unchanged downstream gravity search."""
from pathlib import Path
import json,hashlib,copy
import numpy as np
import cadquery as cq
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from candidate_mass_model import candidate_model
from recalculate_candidate_loads import lumped_rigid_body
from kinematics import Arm
from build_base_study import LEG_RADIUS,G,E

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'engineering/generated/candidate-loads-02'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def link12_bodies():
    folder=ROOT/'engineering/generated/link12-study';p=folder/'part-placements.json';placement=json.loads(p.read_text())
    e=json.loads((folder/'evidence.json').read_text());bodies=[];hashes={str(p.relative_to(ROOT)):sha(p),str((folder/'evidence.json').relative_to(ROOT)):sha(folder/'evidence.json')}
    for name,v in placement['instances'].items():
        path=folder/(v['part_id']+'.step');assert sha(path)==e['export_checks'][v['part_id']]['sha256'][path.name]
        s=cq.importers.importStep(str(path)).val();assert s.isValid() and len(s.Solids())==1
        pr=GProp_GProps();BRepGProp.VolumeProperties_s(s.wrapped,pr);m=pr.Mass()*2.7e-6
        local=np.array([pr.CentreOfMass().X(),pr.CentreOfMass().Y(),pr.CentreOfMass().Z()]);T=np.array(v['T_world_from_part_mm']);world=(T@np.r_[local,1])[:3]
        I=np.array([[pr.MatrixOfInertia().Value(i,j) for j in [1,2,3]] for i in [1,2,3]])*2.7e-12
        assert abs(m-v['mass_kg_6061'])<1e-8 and np.max(abs(world-v['estimated_COM_world_mm']))<1e-5 and np.linalg.eigvalsh(I).min()>0
        assert v['preceding_joints']==1
        bodies.append({'id':'L12_'+name,'mass_kg':m,'preceding_joints':1,'com_home_m':(world*.001).tolist(),
            'orientation_home':T[:3,:3].tolist(),'inertia_com_kg_m2':I.tolist(),'mass_source':str(path.relative_to(ROOT))})
        hashes[str(path.relative_to(ROOT))]=sha(path)
    mass=sum(b['mass_kg'] for b in bodies);com=sum(b['mass_kg']*np.array(b['com_home_m']) for b in bodies)/mass
    bodies.append({'id':'L12_fastener_reserve','mass_kg':.2,'preceding_joints':1,'com_home_m':com.tolist(),
        'orientation_home':np.eye(3).tolist(),'inertia_com_kg_m2':(np.eye(3)*.2*.05**2/6).tolist(),
        'mass_source':'Unweighed 0.20kg reserve at metal COM with 50mm cube inertia proxy'})
    return bodies,{'metal_mass_kg':mass,'reserve_mass_kg':.2,'metal_COM_home_mm':(com*1000).tolist(),'source_hashes':hashes}

def yaw_inertia(b):
    R=np.array(b.get('orientation_home',np.eye(3)));I=R@np.array(b['inertia_com_kg_m2'])@R.T;c=np.array(b['com_home_m'])
    return float(I[2,2]+b['mass_kg']*(c[0]**2+c[1]**2))

def main():
    OUT.mkdir(parents=True,exist_ok=True);p=json.loads((ROOT/'engineering/parameters/r4-layout.json').read_text())
    oldpath=ROOT/'engineering/generated/candidate-loads/study.json';old=json.loads(oldpath.read_text())
    assert old['mass_helper_sha256']==sha(ROOT/'engineering/candidate_mass_model.py')
    assert old['generator_sha256']==sha(ROOT/'engineering/recalculate_candidate_loads.py')
    assert old['baseline_sha256']==sha(ROOT/'engineering/parameters/r4-layout.json')
    for file,digest in old['link56']['input_hashes'].items():assert sha(ROOT/file)==digest
    bodies,info=link12_bodies();oldmodel,_=candidate_model(p,4.5);oldbody=next(b for b in oldmodel['bodies'] if b['id']=='L1_budget')
    assert oldbody['preceding_joints']==1 and oldmodel['joints'][0]['axis']==[0,0,1]
    newmodel=copy.deepcopy(oldmodel);newmodel['bodies']=[b for b in newmodel['bodies'] if b['id']!='L1_budget']+bodies
    oldarm=Arm(oldmodel);newarm=Arm(newmodel);lump=lumped_rigid_body(bodies);lump['id']='L12_lumped';lump['preceding_joints']=1
    lm=copy.deepcopy(oldmodel);lm['bodies']=[b for b in lm['bodies'] if b['id']!='L1_budget']+[lump];la=Arm(lm)
    deltaI=sum(yaw_inertia(b) for b in bodies)-yaw_inertia(oldbody);expected=np.zeros((7,7));expected[0,0]=deltaI
    rng=np.random.default_rng(120256);samples=rng.uniform(*newarm.limits.T,(12,7));checks=[]
    for q in samples:
        a=np.max(abs(newarm.gravity_compensation(q)-oldarm.gravity_compensation(q)))
        b=np.max(abs(newarm.mass_matrix(q)-oldarm.mass_matrix(q)-expected))
        c=np.max(abs(newarm.mass_matrix(q)-la.mass_matrix(q)))
        assert max(a,b,c)<1e-9;checks.append({'q_deg':np.rad2deg(q).tolist(),'gravity_difference_Nm':float(a),'analytic_mass_matrix_delta_error_kg_m2':float(b),'lumped_mass_matrix_error_kg_m2':float(c)})
    delta_mass=sum(b['mass_kg'] for b in bodies)-oldbody['mass_kg']
    delta_bound=sum(b['mass_kg']*G*np.linalg.norm(np.array(b['com_home_m'])[:2]) for b in bodies)-oldbody['mass_kg']*G*np.linalg.norm(np.array(oldbody['com_home_m'])[:2])
    basepath=ROOT/'engineering/generated/base-study/evidence.json';assert old['base_study_sha256']==sha(basepath)
    base=json.loads(basepath.read_text())['loads'];rows=[]
    for prior in old['cases']:
        row=copy.deepcopy(prior);row.pop('witness_q_deg_by_joint',None)
        row['arm_model_mass_including_object_and_J1_kg']+=delta_mass
        b=row['base'];b['nominal_overturning_bound_Nm']+=delta_bound;b['added_COM_uncertainty_Nm']+=.2*G*.15
        design=1.5*(b['nominal_overturning_bound_Nm']+b['added_COM_uncertainty_Nm']);vertical=b['study_vertical_budget_N']+1.5*G*delta_mass
        fpost=vertical/4+design*1000/(2*LEG_RADIUS);area=base['post_area_net_major_diameter_mm2'];I=base['post_I_net_mm4'];span=base['plate_strip_span_mm']
        ecc=base['post_support_top']['radial_eccentricity_mm']+base['post_support_bottom']['radial_eccentricity_mm']
        # Old sampled overturning maximum is not updated by adding its bound:
        # the offset vector may align differently. Preserve it only as history.
        b.pop('sample_max_overturning_Nm',None);b.pop('sample_worst_q_deg',None)
        b.update({'study_design_moment_Nm':design,'study_vertical_budget_N':vertical,'post_equal_stiffness_max_abs_N':fpost,
            'J1_fixed_M4_equal_stiffness_N':vertical/8+design*1000/(4*51),
            'anchor_equal_stiffness_tension_no_gravity_relief_N':design*1000*np.sqrt(2)/(4*110),'single_anchor_110mm_lever_example_N':design*1000/110,
            'post_nominal_axial_eccentric_stress_MPa':fpost/area+fpost*ecc*12/I,
            'plate_strip_sensitivity_stress_MPa':6*fpost*span/(24*16**2),'plate_strip_sensitivity_deflection_mm':fpost*span**3/(3*E*(24*16**3/12))})
        rows.append(row)
    result={'revision':'CANDIDATE-LOADS-02','prior_results_sha256':sha(oldpath),'generator_sha256':sha(Path(__file__)),
       'baseline_sha256':old['baseline_sha256'],'link12':info,'replacement_bodies':bodies,'equivalent_rigid_body':lump,
       'mass_increase_vs_LOADS01_kg':delta_mass,'nominal_base_bound_increase_Nm':float(delta_bound),'constant_M11_increase_kg_m2':deltaI,
       'analytic_reason':'New and old L1 bodies depend only on J1; its axis is vertical through x=y=0. Gravity effort is identically zero and the inertia difference is a constant M11 term. All J2-J7 gravity witnesses and triangle bounds are unchanged.',
       'checks':checks,'cases':rows,'manufacturing_release':False,
       'limits':old['limits'][:],
       'new_limits':['LINK12 three solids now have CAD-derived inertia; 0.20kg remains a COM/cube proxy.',
                     'Nine metal solids use CAD integration, other joints/four link budgets/head/payload remain directory values or proxies.',
                     'Additional shoulder reserve COM error budget is 0.20kg at 150mm, without claiming all uncertainties are bounded.',
                     'Downstream gravity searches reused only under the explicit analytic identity; prior base sampled maxima are not copied as current.',
                     'No new head/camera/LED/contact height or rear-interface offsets integrated.']}
    result['limits']=[x for x in old['limits'] if not x.startswith(('Only six','Head masses/COM','Base COM budgets'))]
    result['limits'].append('Base/general 0.5kg, LINK56 0.1kg and LINK12 0.2kg are distinct planning budgets, not weighed fastener assemblies.')
    (OUT/'study.json').write_text(json.dumps(result,indent=2)+'\n')
    print('dMass',delta_mass,'dM11',deltaI,'dBaseBound',delta_bound)
    for r in rows:print(r['head_mass_kg'],r['head_COM_offset_mm'],r['base']['study_design_moment_Nm'],r['base']['post_equal_stiffness_max_abs_N'],r['base']['plate_strip_sensitivity_stress_MPa'])

if __name__=='__main__':main()
