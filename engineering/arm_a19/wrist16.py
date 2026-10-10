# SPDX-License-Identifier: CC-BY-NC-4.0
"""Actual unscaled RS03 J5 fit study, isolated from issued A18 layout."""
from pathlib import Path
import copy,json,sys,math
import numpy as np
import cadquery as cq
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'engineering/arm_a18'))
import feasibility01 as f
sys.path.insert(0,str(ROOT/'engineering/arm_a16'))
import skeleton_review as r
from vendor import interfaces
from hardware01 import points
c=f.c;g=c.cad;OUT=HERE/'build/wrist16';CACHE=ROOT/'work/arm-a19/vendor16'
L=copy.deepcopy(c.L);L['id']='A19-J5-RS03-FIT16'
L['joints'][4].update(model='RS03',mass_kg=.9,length_mm=56.6,motor_center=[0,68.3,0])
L['status']='candidate; exact changed-part review required; not production'
if '--J6-x' in sys.argv:
    value=float(sys.argv[sys.argv.index('--J6-x')+1]);L['joints'][5]['offset']=[value,0,0]
    OUT=HERE/f'build/wrist16-offset{value:g}';L['id']+=f'-J6X{value:g}'

def interface():
    inf=copy.deepcopy(interfaces()[4]);m=c.SRC['models']['RS03']
    D=np.eye(4);D[:3,:3]=np.column_stack([inf['u'],inf['v'],inf['n']]);D[:3,3]=inf['out_mm']
    inf.update(model='RS03',model_source=m,fixed_mm=(np.array(inf['out_mm'])-np.array(inf['n'])*2.5).tolist(),T_joint_from_raw_mm=(D@np.linalg.inv(m['interface_frame']['T_raw_from_interface_mm'])).tolist())
    return inf

def motor():
    CACHE.mkdir(parents=True,exist_ok=True);inf=interface()
    old=interfaces()[0];T=np.array(inf['T_joint_from_raw_mm'])@np.linalg.inv(old['T_joint_from_raw_mm'])
    assert np.max(abs(T[:3,:3].T@T[:3,:3]-np.eye(3)))<1e-10
    audit=json.loads((c.OUT/'vendor-audit.json').read_text());src=next(x for x in audit['motors'] if x['joint']=='J1')
    rows=[]
    for tag,frame in [('stator','J5.fixed'),('external-output','J5.rotor')]:
        path=c.CACHE/'vendor'/('J1-'+tag+'.step');assert c.sha(path)==src['cache_step_sha256'][tag]
        original=r.load(path);s=c.transform(original,T);assert abs(s.Volume()-original.Volume())<1e-5
        target=CACHE/('J5-'+tag+'.step');cq.exporters.export(s,str(target))
        rows.append((dict(id='J5-supplier-'+tag,frame=frame),s))
    return rows,dict(source_raw_sha256=src['source_sha256'],source_url=src['source_url'],linear_scale=1,interface=inf,cache_sha256={p.name:c.sha(p) for p in CACHE.glob('*.step')})

def main():
    OUT.mkdir(parents=True,exist_ok=True);newmotor,audit=motor()
    path=ROOT/'engineering/arm_a18/build/assembly12.json';d=json.loads(path.read_text())
    assert d['layout']==c.L
    excluded=[p['id'] for p in d['parts'] if 'J5' in p['id'] or 'wrist-pitch-yaw-L' in p['id']]
    # Existing J5 module is absent only in this preliminary fit study, never
    # hidden in a purported whole-body manufacturing package.
    items=[(p,r.load(ROOT/p['step_path'])) for p in d['parts'] if p['id'] not in excluded]
    oldvendor=json.loads((c.OUT/'vendor-audit.json').read_text())
    for m in oldvendor['motors']:
        if m['joint']=='J5':continue
        for tag,fr in [('stator','fixed'),('external-output','rotor')]:
            file=c.CACHE/'vendor'/(m['joint']+'-'+tag+'.step');assert c.sha(file)==m['cache_step_sha256'][tag]
            items.append((dict(id=m['joint']+'-supplier-'+tag,frame=m['joint']+'.'+fr),r.load(file)))
    q=[dict(name=name,q=value) for name,value in L['poses'].items()]
    for index in [3,4,5]:
        lo,hi=L['joints'][index]['limits_deg']
        for value in np.linspace(lo,hi,math.ceil((hi-lo)/10)+1):
            pose=L['poses']['reference'].copy();pose[index]=float(value);q.append(dict(name=f'J{index+1}-{value:.3f}',q=pose))
    for k in range(1,33):q.append(dict(name=f'coupled-{k}',q=[j['limits_deg'][0]+f.rs.halton(k,b)*(j['limits_deg'][1]-j['limits_deg'][0]) for j,b in zip(L['joints'],[2,3,5,7,11,13,17])]))
    cache={};hits=[];checks=[]
    for pose in q:
        F=f.frames(L,pose['q']);world=[(p,c.transform(s,F[p['frame']])) for p,s in newmotor+items]
        fresh=0
        for i in range(len(newmotor)):
            a,s=world[i]
            for b,t in world[len(newmotor):]:
                if not r.overlap(s,t):continue
                rel=np.linalg.inv(F[a['frame']])@F[b['frame']];key=(a['id'],b['id'],tuple(np.round(rel,8).flat))
                if key not in cache:cache[key]=r.common_volume(s,t);fresh+=1
                if cache[key]>.08:hits.append(dict(pose=pose['name'],a=a['id'],b=b['id'],volume_mm3=cache[key]))
        checks.append(dict(name=pose['name'],q_deg=pose['q'],new_exact_pairs=fresh))
        print('RS03_FIT',pose['name'],fresh,'total_hits',len(hits),flush=True)
    report=dict(revision='A19-RS03-NATIVE-FIT16',layout=L,base_context=c.base_context(),assembly_source_sha256=c.sha(path),motor=audit,excluded_for_reconstruction=excluded,checks=checks,hits=hits,sampled_clear=not hits,scope='Changed native J5 only vs A18 own parts except explicitly removed old J5 module plus twelve unchanged supplier partitions. No new brackets/cowls/wires or continuous motion.',production_release=False)
    (OUT/'native-fit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('FIT16_DONE',len(q),len(cache),'pairs',len(hits),'hits',flush=True)
if __name__=='__main__':main()
