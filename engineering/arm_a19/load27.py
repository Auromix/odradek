# SPDX-License-Identifier: CC-BY-NC-4.0
"""Current root wrench and passive-assist lower bound; no supplier guarantee."""
from pathlib import Path
import sys,json,csv
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/assembly25'
sys.path.insert(0,str(HERE));import wrist16 as w
c=w.c;f=w.f
def main():
    path=OUT/'manifest.json';d=json.loads(path.read_text());L=d['layout'];budget=d['budget']
    q=np.array(list(L['poses'].values())+[[j['limits_deg'][0]+f.rs.halton(k,b)*(j['limits_deg'][1]-j['limits_deg'][0]) for j,b in zip(L['joints'],[2,3,5,7,11,13,17])] for k in range(1,4097)],float)
    # Whole supported arm above J2 mounting face includes fixed motor weight.
    bodies=[p for p in budget if p['frame'].startswith('J') and int(p['frame'][1])>=2]+[dict(id=j['id'],frame=j['id']+'.fixed',mass_kg=j['mass_kg'],com_mm=j['motor_center']) for j in L['joints'][1:]]
    origin=np.array([0,68.5,114.]);loads=[]
    for v in q:
        F=f.frames(L,v);J=np.linalg.inv(F['J1.rotor']);force=np.zeros(3);moment=np.zeros(3)
        for p in bodies+[dict(frame='flange',mass_kg=3,com_mm=[0,0,0])]:
            xyz=(J@F[p['frame']]@np.r_[p['com_mm'],1])[:3];G=J[:3,:3]@np.array([0,0,-9.81*p['mass_kg']]);force+=G;moment+=np.cross(xyz-origin,G)
        loads.append(np.r_[force,moment])
    loads=np.array(loads);indices={int(np.argmax(np.linalg.norm(loads[:,3:],axis=1)))}|{int(np.argmax(abs(loads[:,i]))) for i in [3,4,5]};cases=[]
    for i in sorted(indices):
        v=q[i];F=f.frames(L,v);J=np.linalg.inv(F['J1.rotor']);axis=(J@F['J2.fixed'])[:3,:3]@np.array([0,1,0]);fixed_moment=0.
        for p in bodies:
            if p['frame']!='J2.fixed':continue
            xyz=(J@F[p['frame']]@np.r_[p['com_mm'],1])[:3];G=J[:3,:3]@np.array([0,0,-9.81*p['mass_kg']]);fixed_moment+=np.dot(np.cross(xyz-origin,G),axis)/1000
        err=abs(np.dot(loads[i,3:],axis)/1000-fixed_moment+f.torque(L,np.array([v]),3,budget)[0,1]);assert err<1e-8
        cases.append(dict(id=f'current-gravity-pose-{i}',q_deg=v.tolist(),force_N=loads[i,:3].tolist(),moment_Nmm=loads[i,3:].tolist(),J2_virtual_work_error_Nm=float(err)))
    sbudget=budget+[dict(id='assist-mass-allowance',owner=2,frame='J2.rotor',mass_kg=.30,com_mm=[60,0,30])]
    def at(angle):
        v=q.copy();v[:,1]=angle;return np.concatenate([f.torque(L,v,p,sbudget)[:,1] for p in [0,3]])
    A=at(0);B=at(90);assert np.max(abs(at(35)-A*np.cos(np.radians(35))-B*np.sin(np.radians(35))))<1e-9
    table=[]
    for angle in range(-60,111):
        t=A*np.cos(np.radians(angle))+B*np.sin(np.radians(angle));low=float(t.min());high=float(t.max());table.append(dict(J2_deg=angle,raw_min_Nm=low,raw_max_Nm=high,ideal_assist_midpoint_Nm=-(low+high)/2,minimum_possible_worst_residual_Nm=(high-low)/2))
    with (OUT/'J2-ideal-passive-limit27.csv').open('w') as fp:
        writer=csv.DictWriter(fp,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
    worst=max(table,key=lambda r:r['minimum_possible_worst_residual_Nm'])
    root=json.loads((HERE/'build/root22/manifest.json').read_text())
    result=dict(revision='A19-CURRENT-LOAD27',source_assembly_sha256=c.sha(path),source_root_manifest_sha256=c.sha(HERE/'build/root22/manifest.json'),sample_count=len(q),payload_kg=3,mount_origin_J1_rotor_mm=origin.tolist(),gravity_load_cases=cases,material=root['material'],passive_assist_lower_bound=worst,assist_extra_full_moving_allowance_kg=.30,unfiltered_other_joint_samples=len(q),ideal_torque_is_real_hardware=False,production_release=False,limits=['This load set updates wrist/root own assembly mass, but all structure remains prototype plastic-density budget.','Any J2-only passive torque cannot beat half the sample torque interval, even with ideal unrestricted force. This is a lower bound, not a realizable spring.','Actual passively assisted design needs measured force/hysteresis/temperature, linkage geometry and bracket loads; no spring is selected by this table.','No dynamic, braking, collision stop, metal-mass update or physical qualification.'])
    (OUT/'load27.json').write_text(json.dumps(result,indent=2)+'\n');print('LOAD27',worst,flush=True)
if __name__=='__main__':main()
