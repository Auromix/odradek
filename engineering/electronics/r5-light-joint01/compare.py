# SPDX-License-Identifier: CC-BY-NC-4.0
# Attribution: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""R5-LIGHT-JOINT01: catalog masses and frozen-geometry gravity sensitivity.

This does not establish new interfaces, new joint COMs, feasible motion, motor
static thermal rating, or a replacement release. Original CAD/model untouched.
"""
from pathlib import Path
import sys,json,hashlib,copy,csv
import numpy as np
from scipy.stats import qmc
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'engineering'))
from r5_body01 import transforms,effort,triangle,pointbody,aggregate_by_attachment
OUT=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    src=ROOT/'docs/engineering/sources/r5-light-joint01.json';catalog=read(src)
    path=ROOT/'engineering/generated/r5-body01/body-only-model.json';original=read(path)
    prior=read(ROOT/'engineering/generated/r5-body01/study.json')
    joints=original['joints'];mods={x['short_model']:x for x in catalog['candidate_models']}
    chosen=['eRob90I V6']*3+['eRob80I V6']*2+['eRob70I V5']*2
    masses=[mods[x]['with_brake_mass_kg'] for x in chosen]
    replaced=copy.deepcopy(original['bodies']);changes=[]
    for i,newmass in enumerate(masses):
        b=next(b for b in replaced if b['id']==f'J{i+1}_mass_proxy')
        changes.append(dict(axis=f'J{i+1}',old_model=joints[i]['model'],candidate=chosen[i],old_mass_kg=b['mass_kg'],new_mass_kg=newmass,delta_kg=newmass-b['mass_kg'],preceding_joints=b['preceding_joints'],UNCHANGED_PROXY_com_home_m=b['com_home_m']))
        b['mass_kg']=newmass
    bounds=np.deg2rad([j['limit_deg'] for j in joints])
    u=qmc.Sobol(5,scramble=True,seed=501).random_base2(15)
    qs=np.zeros((len(u),7));qs[:,1:6]=qmc.scale(u,bounds[1:6,0],bounds[1:6,1])
    cache=transforms(joints,qs);flange=np.array(joints[6]['origin_m']);scenarios=[]
    for tcp in [.15,.20]:
        load=[pointbody('parameter_head_1p5kg',1.5,flange+[0,0,.1]),pointbody('net_object_2kg',2,flange+[0,0,tcp])]
        for name,bodies in [('RH_frozen',original['bodies']),('eRob_mass_only_frozen_COM',replaced)]:
            allb=bodies+load;v,bend=effort(joints,aggregate_by_attachment(allb),qs,cache)
            upper=triangle(joints,allb);sample=np.max(abs(v),axis=0)
            assert np.all(sample<=upper+1e-8)
            scenarios.append(dict(model=name,head_mass_kg=1.5,head_COM_offset_mm=100,TCP_offset_mm=tcp*1000,net_payload_kg=2,sampled_abs_max_gravity_Nm=sample.tolist(),all_configuration_triangle_bound_Nm=upper.tolist(),sampled_base_overturning_magnitude_Nm=float(np.linalg.norm(bend[:,:2],axis=1).max()),sampled_witness_q_deg=np.rad2deg(qs[np.argmax(abs(v),axis=0)]).tolist()))
    old=sum(j['mass_kg'] for j in joints);new=sum(masses)
    out=dict(revision='R5-LIGHT-JOINT01',status='catalog shortlist and mass-only sensitivity; no hardware replacement release',source_hashes={str(p.relative_to(ROOT)):sha(p) for p in [src,path,ROOT/'engineering/r5_body01.py',ROOT/'engineering/generated/r5-body01/study.json']},script_sha256=sha(Path(__file__)),catalog_mass_plan=changes,total_modules_kg=dict(RH=old,eRob_all_brake=new,reduction=old-new,reduction_percent=100*(old-new)/old),original_fixed_planning_kg=prior['mass']['fixed_base_original_metal_kg']+prior['mass']['fixed_J1_catalog_kg'],original_moving_planning_kg=prior['mass']['moving_planning_kg'] if 'moving_planning_kg' in prior['mass'] else sum(b['mass_kg'] for b in original['bodies'] if b['preceding_joints']>0),replacement_fixed_planning_kg=prior['mass']['fixed_base_original_metal_kg']+masses[0],replacement_moving_planning_kg=sum(b['mass_kg'] for b in replaced if b['preceding_joints']>0),sampling=dict(count=len(qs),sequence='Sobol scrambled 5D seed501',angles='same mathematical joint box as R5-BODY01; q1/q7 zero symmetry',collision_filtered=False,global_maximum=False),scenarios=scenarios,not_updated=['origins','joint axes','link CAD','link masses','old RH COM proxy positions','rotating/fixed internals split','COM inertia tensors'],limits=['mass-only sensitivity is not an eRob assembled arm model','catalog continuous gear torque and motor static input torque are distinct','new mounting interfaces and actual COM transforms require rework','no environmental/temperature/holding test performed'])
    (OUT/'comparison.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    with (OUT/'module-mass-plan.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(changes[0]));w.writeheader();w.writerows(changes)
    rows=[]
    for r in scenarios:
        for i in range(7):rows.append(dict(model=r['model'],TCP_offset_mm=r['TCP_offset_mm'],axis=f'J{i+1}',sampled_abs_max_gravity_Nm=r['sampled_abs_max_gravity_Nm'][i],triangle_upper_bound_Nm=r['all_configuration_triangle_bound_Nm'][i]))
    with (OUT/'static-mass-sensitivity.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps({k:out[k] for k in ['total_modules_kg','replacement_fixed_planning_kg','replacement_moving_planning_kg','scenarios']},indent=2))
if __name__=='__main__':main()
