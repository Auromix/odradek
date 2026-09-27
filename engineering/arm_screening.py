# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Gravity screening of stated mass/COM assumptions, not motor qualification."""
import json
from pathlib import Path
import numpy as np
from kinematics import Arm

ROOT=Path(__file__).resolve().parents[1]


def arm_parameters(p,head_mass=None,payload_offset=None):
    joints=[{**j,'origin_m':(np.array(j['origin_mm'])*.001).tolist()} for j in p['joints']]
    bodies=[]
    for i,j in enumerate(joints):
        z=np.asarray(j['axis'],dtype=float);x=np.array([1.,0,0])
        if abs(x@z)>.99:x=np.array([0.,1,0])
        x-=x@z*z;x/=np.linalg.norm(x);R=np.column_stack([x,np.cross(z,x),z])
        m=j['mass_kg'];r=j['diameter_mm']*.0005;L=j['length_mm']*.001
        # Full module mass assigned to its upstream housing. True rotor split
        # and inertia are unavailable; this is only a static gravity screen.
        centre=np.array(j['origin_m'])-np.array(j['axis'])*(L/2-.002)
        inertia=np.diag([m*(3*r*r+L*L)/12]*2+[m*r*r/2])
        bodies.append({'id':j['id']+'_mass_proxy','mass_kg':m,'preceding_joints':i,
                       'com_home_m':centre.tolist(),'orientation_home':R.tolist(),
                       'inertia_com_kg_m2':inertia.tolist()})
        a=np.array(j['origin_m'])
        b=np.array(joints[i+1]['origin_m']) if i<6 else np.array(p['head']['mount_origin_mm'])*.001
        m=p['link_budgets_kg'][i];L=max(np.linalg.norm(b-a),.02)
        bodies.append({'id':f'L{i+1}_budget','mass_kg':m,'preceding_joints':i+1,
                       'com_home_m':((a+b)/2).tolist(),
                       'inertia_com_kg_m2':np.diag([m*L*L/12]*3).tolist()})
    tcp=np.array(p['head']['tcp_home_mm'])*.001
    com=np.array(p['head']['head_com_home_mm'])*.001
    m=p['head_budget_kg'] if head_mass is None else head_mass
    bodies.append({'id':'head_budget','mass_kg':m,'preceding_joints':7,'com_home_m':com.tolist(),
                   'inertia_com_kg_m2':np.diag([m*.08**2/2]*3).tolist()})
    object_com=tcp+(np.zeros(3) if payload_offset is None else payload_offset)
    bodies.append({'id':'net_object','mass_kg':p['payload_net_kg'],'preceding_joints':7,'com_home_m':object_com.tolist(),
                   'inertia_com_kg_m2':np.diag([p['payload_net_kg']*.04**2/6]*3).tolist()})
    T=np.eye(4);T[:3,3]=tcp
    return {'joints':joints,'bodies':bodies,'tool_home_transform':T.tolist(),'gravity_m_s2':[0,0,-9.80665]}


def main():
    p=json.loads((ROOT/'engineering/parameters/r4-layout.json').read_text());rng=np.random.default_rng(704)
    base=arm_parameters(p);arm=Arm(base);lo,hi=arm.limits.T
    samples=rng.uniform(lo,hi,(1500,7))
    samples=np.vstack([samples,np.deg2rad(list(p['poses_deg'].values()))])
    reports=[]
    for hmass in p['head_mass_sensitivity_kg']:
        a=Arm(arm_parameters(p,hmass))
        gravity=np.array([a.gravity_compensation(q) for q in samples])
        maxima=np.max(abs(gravity),axis=0)
        reports.append({'head_mass_kg':hmass,'sample_count':len(samples),
                        'sampled_abs_max_gravity_Nm':maxima.tolist(),
                        'sampled_worst_q_deg_by_joint':[np.rad2deg(samples[np.argmax(abs(gravity[:,i]))]).tolist() for i in range(7)],
                        'rated_over_sampled_gravity_ratio':[None if t<1e-8 else j['rated_torque_Nm']/t for j,t in zip(p['joints'],maxima)]})
    # Triangle inequality bounds joint-to-COM distance for every configuration
    # of this stated point-mass model. They include no material uncertainty.
    bounds=np.zeros(7)
    for b in base['bodies']:
        n=b['preceding_joints']
        for i in range(n):
            path=sum(np.linalg.norm(np.array(base['joints'][k+1]['origin_m'])-base['joints'][k]['origin_m']) for k in range(i,n-1))
            path+=np.linalg.norm(np.array(b['com_home_m'])-base['joints'][n-1]['origin_m'])
            bounds[i]+=b['mass_kg']*9.80665*path
    # J1 is vertical in the gravity frame for all configurations, exactly zero.
    if np.allclose(base['joints'][0]['axis'],[0,0,1]):bounds[0]=0.
    reach=np.linalg.norm(np.array(p['head']['tcp_home_mm'])-p['joints'][1]['origin_mm'])
    result={'revision':p['revision'],'status':'screening only: no collision, cable, inertia, thermal or holding-brake qualification',
            'nominal_home_shoulder_to_tcp_distance_mm':reach,
            'actuator_mass_total_kg':sum(j['mass_kg'] for j in p['joints']),
            'modeled_total_mass_including_fixed_J1_and_object_kg':sum(b['mass_kg'] for b in base['bodies']),
            'joint_ids':[j['id'] for j in p['joints']],
            'rated_output_torque_Nm':[j['rated_torque_Nm'] for j in p['joints']],
            'head_sensitivity':reports,
            'all_configuration_triangle_bound_at_2kg_head_Nm':bounds.tolist(),
            'model':base,
            'limits':['full module housing COM uses its geometric midpoint, not vendor COM',
                      'link COM and mass are budgets, not final CAD integrals',
                      'static gravity excludes acceleration, contact, friction and off-axis payload beyond specified COM',
                      'sampled maxima are not global maxima; triangle bounds apply only to stated point-mass assumptions',
                      'no claim that all sampled configurations are mechanically or cable reachable',
                      'drive rated running torque is not guaranteed zero-speed holding torque']}
    out=ROOT/'docs/engineering/analysis/arm-gravity-screening.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['model','head_sensitivity']},indent=2))
    for r in reports:print(r['head_mass_kg'],np.round(r['sampled_abs_max_gravity_Nm'],3).tolist())


if __name__=='__main__':main()
