# SPDX-License-Identifier: CC-BY-NC-4.0
"""Changed-part exact finite fit checks. Never inherit old motor/layout checks."""
from pathlib import Path
import itertools,json,sys
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE));import wrist16 as w
c=w.c;g=c.cad;r=w.r

def main():
    root_mode='--root' in sys.argv
    integrated='--integrated' in sys.argv
    shell_mode='--shell' in sys.argv or integrated
    directory=HERE/'build/assembly25' if integrated else (HERE/('build/root22' if '--thick' in sys.argv else 'build/root17-gusset') if root_mode else HERE/('build/wrist-shell21' if shell_mode else 'build/wrist-core19'))
    path=directory/'manifest.json';D=json.loads(path.read_text());L=D['layout']
    oldpath=ROOT/'engineering/arm_a18/build/assembly12.json';old=json.loads(oldpath.read_text())
    if root_mode:
        new=D.get('parts',[dict(id=D['part_id'],frame='J1.rotor',step_path=D['step_path'])]);removed=D.get('replaces_only',['A16-C04-J2-mount-plate'])
    else:new=D['parts'];removed=D.get('replaces_only',D.get('removed_part_ids',[]))
    extra_sources=[]
    if shell_mode and not integrated:
        core=json.loads((HERE/'build/wrist-core19/manifest.json').read_text());assert D['layout']==core['layout']
        assert D['source_core_sha256']==c.sha(HERE/'build/wrist-core19/manifest.json')
        new=core['parts']+new;removed=core['replaces_only']+removed
        extra_sources.append(HERE/'build/wrist-core19/manifest.json')
    if integrated:
        new=[p for p in D['parts'] if p['id'] in D['added_part_ids']]
        removed=D['removed_part_ids']
        extra_sources=[ROOT/p for p in D['source_manifests_sha256']]
    rows=[dict(p) for p in old['parts'] if p['id'] not in removed]
    if not root_mode:
        for p in rows:
            if p.get('intentional_heatset_target')=='A16-C06-fore-spine-and-J5-ring':p['intentional_heatset_target']='A19-S19-fore-spine-RS03-ring'
    items=[(p,r.load(ROOT/p['step_path'])) for p in new+rows]
    motor=json.loads((c.OUT/'vendor-audit.json').read_text())
    newmotor=[]
    for m in motor['motors']:
        if not root_mode and m['joint']=='J5':
            newmotor,audit=w.motor();continue
        for tag,fr in [('stator','fixed'),('external-output','rotor')]:
            file=c.CACHE/'vendor'/(m['joint']+'-'+tag+'.step');assert c.sha(file)==m['cache_step_sha256'][tag]
            items.append((dict(id=m['joint']+'-supplier-'+tag,frame=m['joint']+'.'+fr),r.load(file)))
    if not root_mode:items=newmotor+items
    nnew=len(new)+(2 if not root_mode else 0)
    # Four existing J6 insert pilot descriptors are retained in their new
    # location. A nominal press annulus is the only permitted subtraction.
    poses=[dict(name=name,q_deg=q) for name,q in L['poses'].items()]
    for k in range(1,27):poses.append(dict(name=f'coupled-{k}',q_deg=[j['limits_deg'][0]+w.f.rs.halton(k,b)*(j['limits_deg'][1]-j['limits_deg'][0]) for j,b in zip(L['joints'],[2,3,5,7,11,13,17])]))
    if root_mode or integrated:
        for value in np.arange(-60,111,5):
            q=L['poses']['reference'].copy();q[1]=float(value);poses.append(dict(name=f'J2-{value}',q_deg=q))
    if not root_mode:
        for idx in [4,5]:
            lo,hi=L['joints'][idx]['limits_deg']
            for value in np.linspace(lo,hi,int((hi-lo)/5)+1):
                q=L['poses']['reference'].copy();q[idx]=float(value);poses.append(dict(name=f'J{idx+1}-{value:.3f}',q_deg=q))
    quick='--quick' in sys.argv
    if quick:poses=[p for p in poses if p['name'] in ['idle','reference','J5-130.000','J6--60.000','J6-60.000']]
    hits=[];cache={};checks=[]
    def permitted(shape,p,target):
        if p.get('intentional_heatset_target')==target['id']:
            z=p['heatset_zone_mm'];zone=g.ring(z['p'],z['n'],z['outer_diameter']/2,z['pilot_diameter']/2,z['length']);return shape.cut(zone)
        if p.get('intentional_thread_motor') and target['id'].startswith(p['intentional_thread_motor']+'-supplier-'):
            z=p['thread_zone_mm'];n=np.array(z['n']);zone=g.cyl(np.array(z['p'])-n*z['depth'],n,z['diameter']/2,z['depth']);return shape.cut(zone)
        return shape
    sources={str(oldpath.relative_to(ROOT)):c.sha(oldpath),str(path.relative_to(ROOT)):c.sha(path)}
    sources.update({str(p.relative_to(ROOT)):c.sha(p) for p in extra_sources})
    for p in new+rows:sources[p['step_path']]=c.sha(ROOT/p['step_path'])
    for pose in poses:
        F=w.f.frames(L,pose['q_deg']);world=[(p,c.transform(s,F[p['frame']])) for p,s in items];fresh=0;count=0
        for i in range(nnew):
            a,s=world[i]
            for j in range(i+1,len(items)):
                b,t=world[j]
                if a['id'].startswith('J5-supplier-') and b['id'].startswith('J5-supplier-'):continue
                if not r.overlap(s,t):continue
                rel=np.linalg.inv(F[a['frame']])@F[b['frame']];key=(a['id'],b['id'],tuple(np.round(rel,8).flat))
                if key not in cache:
                    local_a=permitted(items[i][1],a,b);local_b=permitted(items[j][1],b,a)
                    cache[key]=r.common_volume(c.transform(local_a,F[a['frame']]),c.transform(local_b,F[b['frame']]));fresh+=1
                if cache[key]>.08:
                    hit=dict(pose=pose['name'],a=a['id'],b=b['id'],volume_mm3=cache[key]);hits.append(hit);count+=1;print('CHANGED_HIT',hit,flush=True)
        checks.append(dict(name=pose['name'],q_deg=pose['q_deg'],fresh_exact_pairs=fresh,hits=count))
        if fresh or count:print('REVIEW20',pose['name'],fresh,count,flush=True)
    out=dict(source_sha256=sources,layout=L,checks=checks,hits=hits,changed_pair_sampled_clear=not hits,exact_distinct_pairs=len(cache),removed=removed,scope='Only new parts (and native J5 for wrist mode) vs remaining A18 own assembly and exact supplier partitions, plus new-new pairs. Finite poses, no base shell, continuous sweep, tolerance, dynamic harness or physical fit.',production_release=False)
    (directory/('review20-quick.json' if quick else 'review20.json')).write_text(json.dumps(out,indent=2)+'\n');print('REVIEW20_DONE',len(poses),len(hits),flush=True)
if __name__=='__main__':main()
