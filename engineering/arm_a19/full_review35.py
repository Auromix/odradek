# SPDX-License-Identifier: CC-BY-NC-4.0
"""All current arm part pairs; no inheritance of old-old collision results."""
from pathlib import Path
import sys,json
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/assembly25'
sys.path.insert(0,str(HERE));import wrist16 as w
from vendor import interfaces
c=w.c;g=c.cad;r=w.r

def permitted(shape,p,target):
 if p.get('intentional_heatset_target')==target['id']:
  z=p['heatset_zone_mm'];return shape.cut(g.ring(z['p'],z['n'],z['outer_diameter']/2,z['pilot_diameter']/2,z['length']))
 if p.get('intentional_thread_motor') and target['id'].startswith(p['intentional_thread_motor']+'-supplier-'):
  z=p['thread_zone_mm'];n=np.array(z['n']);return shape.cut(g.cyl(np.array(z['p'])-n*z['depth'],n,z['diameter']/2,z['depth']))
 return shape

def main():
 path=OUT/'manifest.json';d=json.loads(path.read_text());L=d['layout'];items=[];sources={str(path.relative_to(ROOT)):c.sha(path)}
 for p in d['parts']:
  f=ROOT/p['step_path'];assert c.sha(f)==p['step_sha256'];items.append((p,r.load(f)));sources[p['step_path']]=c.sha(f)
 vendor=json.loads((c.OUT/'vendor-audit.json').read_text());native_sources={}
 for m in vendor['motors']:
  if m['joint']=='J5':
   # Re-derive rigid source transform in memory; do not rewrite native cache.
   parent=next(x for x in vendor['motors'] if x['joint']=='J1');T=np.array(w.interface()['T_joint_from_raw_mm'])@np.linalg.inv(np.array(interfaces()[0]['T_joint_from_raw_mm']))
   assert np.max(abs(T[:3,:3].T@T[:3,:3]-np.eye(3)))<1e-10
   for tag,fr in [('stator','fixed'),('external-output','rotor')]:
    f=c.CACHE/'vendor'/('J1-'+tag+'.step');assert c.sha(f)==parent['cache_step_sha256'][tag];s=r.load(f);mapped=c.transform(s,T);assert abs(mapped.Volume()-s.Volume())<1e-5
    items.append((dict(id='J5-supplier-'+tag,frame='J5.'+fr),mapped));native_sources['J5-'+tag]=dict(source=str(f.relative_to(ROOT)),sha256=c.sha(f),T_from_source=T.tolist())
   continue
  for tag,fr in [('stator','fixed'),('external-output','rotor')]:
   f=c.CACHE/'vendor'/(m['joint']+'-'+tag+'.step');assert c.sha(f)==m['cache_step_sha256'][tag];items.append((dict(id=m['joint']+'-supplier-'+tag,frame=m['joint']+'.'+fr),r.load(f)));native_sources[m['joint']+'-'+tag]=dict(source=str(f.relative_to(ROOT)),sha256=c.sha(f))
 poses=[dict(name=name,q_deg=q) for name,q in L['poses'].items()]
 for k in range(1,17):poses.append(dict(name=f'coupled-{k}',q_deg=[j['limits_deg'][0]+w.f.rs.halton(k,b)*(j['limits_deg'][1]-j['limits_deg'][0]) for j,b in zip(L['joints'],[2,3,5,7,11,13,17])]))
 # Extra current governing gravity load poses are checked rather than silently
 # assuming load-maximizing configurations are executable.
 loads=json.loads((OUT/'load27.json').read_text())
 for case in loads['gravity_load_cases']:
  if case['q_deg'] not in [p['q_deg'] for p in poses]:poses.append(dict(name=case['id'],q_deg=case['q_deg']))
 cache={};hits=[];checks=[]
 for pose in poses:
  F=w.f.frames(L,pose['q_deg']);world=[c.transform(s,F[p['frame']]) for p,s in items];bounds=np.array([r.bounds(s) for s in world]);count=0;fresh=0;local_hits=[]
  for i,(a,sa) in enumerate(items):
   lower=np.maximum(bounds[i,:3],bounds[i+1:,:3]);upper=np.minimum(bounds[i,3:],bounds[i+1:,3:]);js=np.flatnonzero(np.all(upper-lower>1e-5,axis=1))+i+1
   for j in js:
    b,sb=items[j];relative=np.linalg.inv(F[a['frame']])@F[b['frame']];key=(a['id'],b['id'],tuple(np.round(relative,8).flat));count+=1
    if key not in cache:
     pa=permitted(sa,a,b);pb=permitted(sb,b,a);cache[key]=r.common_volume(c.transform(pa,F[a['frame']]),c.transform(pb,F[b['frame']]));fresh+=1
    v=cache[key]
    if v>.08:
     hit=dict(pose=pose['name'],a=a['id'],b=b['id'],volume_mm3=v);hits.append(hit);local_hits.append(hit);print('FULL35_HIT',hit,flush=True)
  rec=dict(name=pose['name'],q_deg=pose['q_deg'],all_arm_part_count=len(items),positive_bbox_pairs=count,new_exact_pairs=fresh,hits=len(local_hits),minimum_world_Z_mm=float(bounds[:,2].min()));checks.append(rec);print('FULL35_POSE',rec,flush=True)
  (OUT/'full-review35-progress.json').write_text(json.dumps(dict(source_assembly_sha256=c.sha(path),checks=checks,hits=hits,complete=False),indent=2)+'\n')
 report=dict(revision='A19-ALL-ARM-PAIRS35',source_sha256=sources,native_sources=native_sources,source_checker_sha256=c.sha(Path(__file__)),layout=L,checks=checks,hits=hits,sampled_all_arm_pairs_clear=not hits,exact_distinct_pairs=len(cache),production_release=False,scope='All562 current own rows and14 actual native partitions, all pair combinations including old-old. Only explicit thread/press annulus volumes removed.21 finite configurations; excludes canonical base internals, continuous sweep, tolerances, real wires and physical qualification.')
 (OUT/'full-review35.json').write_text(json.dumps(report,indent=2)+'\n');print('FULL35_DONE',len(poses),len(cache),len(hits),flush=True)
if __name__=='__main__':main()
