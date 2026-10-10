# SPDX-License-Identifier: CC-BY-NC-4.0
"""Fresh uniform-CAD mass/gravity screen; not a measured payload rating."""
from pathlib import Path
import sys,json,math
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'engineering/arm_a16'))
import common as c
import gravity as prior
from assembly_sources import collect
OUT=HERE/'build/style01';rs=prior.rs

def main():
    d=json.loads((OUT/'manifest.json').read_text());rows,sources,_=collect(last='skins06')
    rows=[x for x in rows if x['id'] not in d['replaces_only']]+d['parts']
    assert len(rows)==541
    budget=[dict(id=x['id'],owner=x['owner'],frame=x['frame'],mass_kg=x['mass_kg'],com_mm=x['com_mm']) for x in rows]
    for owner,mass,com in [(3,.1,[170,0,11]),(4,.08,[92.5,62,11]),(7,.06,[65,0,0]),(2,.25,[45,-80,0])]:
        budget.append(dict(id=f'allowance-{owner}',owner=owner,frame=f'J{owner}.rotor',mass_kg=mass,com_mm=com))
    q=np.array(list(c.L['poses'].values())+[[j['limits_deg'][0]+rs.halton(k,b)*(j['limits_deg'][1]-j['limits_deg'][0]) for j,b in zip(c.L['joints'],[2,3,5,7,11,13,17])] for k in range(1,4097)],float)
    torques=rs.batch_gravity(c.L,q,3,budget)
    errors=[]
    def potential(v):
        F=c.frames(v)
        bodies=budget+[dict(frame=j['id']+'.fixed',mass_kg=j['mass_kg'],com_mm=j['motor_center']) for j in c.L['joints']]
        return sum(x['mass_kg']*9.81*(F[x['frame']]@np.r_[x['com_mm'],1])[2]/1000 for x in bodies)+3*9.81*(F['J7.rotor']@np.array([110,0,0,1]))[2]/1000
    for v in list(c.L['poses'].values())+[[23,55,35,-85,68,24,42]]:
        t=rs.batch_gravity(c.L,np.array([v],float),3,budget)[0]
        for i in range(7):
            a=v.copy();b=v.copy();h=1e-4;a[i]+=h;b[i]-=h
            errors.append(abs((potential(a)-potential(b))/(2*math.radians(h))-t[i]))
    assert max(errors)<1e-6
    own=sum(x['mass_kg'] for x in rows);motor=sum(j['mass_kg'] for j in c.L['joints'])
    refs=[rs.SPECS[j['model']]['zero_speed_reference_Nm'] for j in c.L['joints']]
    maxima=np.max(abs(torques),axis=0).tolist()
    report=dict(revision=d['revision'],manifest_sha256=c.sha(OUT/'manifest.json'),sources=sources,layout=c.L,
      own_CAD_and_nominal_hardware_mass_kg=own,catalogue_motor_mass_kg=motor,undeveloped_allowance_kg=.49,
      estimated_bare_mass_kg=own+motor+.49,external_flange_load_kg=3,flange_J7_local_mm=[110,0,0],
      sampled_abs_max_Nm=maxima,catalogue_zero_speed_reference_Nm=refs,sample_count=len(q),virtual_work_max_error_Nm=max(errors),
      raw_shoulder_screen_pass=maxima[1]<refs[1],production_release=False,
      limitations='Uniform prototype CAD, nominal hardware envelopes, unmeasured motor-CG proxies and0.49kg unfinished allowances.4099 unfiltered configurations are not a certified reachable workspace. No gas-spring/bracket, thermal, dynamic, metal strength or3kg rating qualified.')
    (OUT/'physics.json').write_text(json.dumps(report,indent=2)+'\n')
    print('A17_PHYSICS',report['estimated_bare_mass_kg'],maxima,'raw shoulder pass',report['raw_shoulder_screen_pass'],flush=True)

if __name__=='__main__':main()
