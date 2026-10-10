# SPDX-License-Identifier: CC-BY-NC-4.0
"""Explicit incremental proof after whole-arm scan exposed old elbow screws."""
from pathlib import Path
import sys,json
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/assembly25';BASE=OUT/'baselines'
sys.path.insert(0,str(HERE));import full_review35 as v
from vendor import interfaces
w=v.w;c=v.c;r=v.r

def main():
 current=OUT/'manifest.json';d=json.loads(current.read_text());oldpath=BASE/'assembly25-v25.json';old=json.loads(oldpath.read_text());fullpath=BASE/'full-review35-v25.json';basefull=json.loads(fullpath.read_text());changedpath=BASE/'review20-v25.json';basechanged=json.loads(changedpath.read_text());hardwarepath=HERE/'build/hardware43/manifest.json';h=json.loads(hardwarepath.read_text())
 assert basefull['source_sha256'][str(current.relative_to(ROOT))]==c.sha(oldpath)==h['source_baseline_assembly_sha256']
 assert basechanged['source_sha256'][str(current.relative_to(ROOT))]==c.sha(oldpath)
 assert d['layout']==old['layout']==basefull['layout']==basechanged['layout']
 oldmaps={p['id']:p for p in old['parts']};newmaps={p['id']:p for p in d['parts']};changed={p['id']for p in h['parts']};removed=set(h['replaces_only']);unchanged=set(oldmaps)-removed
 assert unchanged==set(newmaps)-changed and not(removed&set(newmaps))
 for id in unchanged:
  a,b=oldmaps[id],newmaps[id]
  for key in ['frame','owner','step_path','step_sha256','intentional_thread_motor','thread_zone_mm','intentional_heatset_target','heatset_zone_mm']:assert a.get(key)==b.get(key),(id,key)
 # Every old full-scan hit must involve a removed part; no waiver survives.
 assert not[h for h in basefull['hits']if h['a']in unchanged and h['b']in unchanged]
 assert basechanged['changed_pair_sampled_clear'] and not basechanged['hits']
 sources={str(current.relative_to(ROOT)):c.sha(current),str(oldpath.relative_to(ROOT)):c.sha(oldpath),str(fullpath.relative_to(ROOT)):c.sha(fullpath),str(changedpath.relative_to(ROOT)):c.sha(changedpath),str(hardwarepath.relative_to(ROOT)):c.sha(hardwarepath)}
 items=[]
 for p in d['parts']:
  f=ROOT/p['step_path'];assert c.sha(f)==p['step_sha256'];sources[p['step_path']]=c.sha(f);items.append((p,r.load(f)))
 native_sources=basefull['native_sources']
 for key,proof in native_sources.items():
  file=ROOT/proof['source'];assert c.sha(file)==proof['sha256'];s=r.load(file)
  if 'T_from_source'in proof:s=c.transform(s,np.array(proof['T_from_source']))
  j=key.split('-')[0];tag=key[len(j)+1:];items.append((dict(id=j+'-supplier-'+tag,frame=j+('.fixed'if tag=='stator'else '.rotor')),s))
 poses=[];seen=set()
 def add(name,q):
  key=tuple(np.round(q,10))
  if key not in seen:poses.append(dict(name=name,q_deg=q));seen.add(key)
 for record in basefull['checks']+basechanged['checks']:add(record['name'],record['q_deg'])
 for q4 in np.arange(-145,136,2):
  q=d['layout']['poses']['reference'].copy();q[3]=float(q4);add(f'J4-grid-{q4}',q)
 indexes=[i for i,(p,s)in enumerate(items)if p['id']in changed];cache={};hits=[];checks=[]
 for pose in poses:
  F=w.f.frames(d['layout'],pose['q_deg']);world=[c.transform(s,F[p['frame']])for p,s in items];bb=np.array([r.bounds(s)for s in world]);fresh=0;tested=set();local=[]
  for i in indexes:
   for j in np.flatnonzero(np.all(np.minimum(bb[i,3:],bb[:,3:])-np.maximum(bb[i,:3],bb[:,:3])>1e-5,axis=1)):
    if i==j or tuple(sorted((i,int(j))))in tested:continue
    tested.add(tuple(sorted((i,int(j)))));a,sa=items[i];b,sb=items[j];rel=np.linalg.inv(F[a['frame']])@F[b['frame']];key=(a['id'],b['id'],tuple(np.round(rel,8).flat))
    if key not in cache:
     cache[key]=r.common_volume(c.transform(v.permitted(sa,a,b),F[a['frame']]),c.transform(v.permitted(sb,b,a),F[b['frame']]));fresh+=1
    if cache[key]>.08:
     hit=dict(pose=pose['name'],a=a['id'],b=b['id'],volume_mm3=cache[key]);local.append(hit);hits.append(hit);print('REVIEW44_HIT',hit,flush=True)
  checks.append(dict(name=pose['name'],q_deg=pose['q_deg'],fresh_exact_pairs=fresh,hits=len(local)))
  if fresh or local:print('REVIEW44',pose['name'],fresh,len(local),flush=True)
 report=dict(revision='A19-ELBOW-INCREMENTAL-REVIEW44',source_sha256=sources,source_checker_sha256=c.sha(Path(__file__)),source_checker_file='review44.py',native_sources=native_sources,layout=d['layout'],current_own_rows=len(d['parts']),current_supplier_partitions=len(native_sources),unchanged_rows=len(unchanged),removed_ids=sorted(removed),new_ids=sorted(changed),baseline_full_pose_count=len(basefull['checks']),baseline_changed_pose_count=len(basechanged['checks']),checks=checks,hits=hits,exact_distinct_new_pairs=len(cache),old_hit_replaced=basefull['hits'],changed_pair_sampled_clear=not hits,production_release=False,scope='Fresh12 changed hardware vs every current own/native row, union of old21 all-pair and134 changed-part poses plus141 J4 positions. Unchanged STEP/frame/thread/press metadata equality proven. Reconstructs current whole-arm21 poses by inheritance of only unchanged pairs; does NOT claim whole-arm clearance at every other sampled pose, continuous sweep, base internals, tolerances or wires.')
 (OUT/'review44.json').write_text(json.dumps(report,indent=2)+'\n')
 if not hits:
  alias=dict(report,checks=basechanged['checks'],delta_report_sha256=c.sha(OUT/'review44.json'),scope='Current134 changed-part scope reconstructed from old134 source-identical unchanged pairs and fresh hardware44 delta at every matching pose. See review44 for exact inheritance and limits.')
  (OUT/'review20.json').write_text(json.dumps(alias,indent=2)+'\n')
  wholechecks=[dict(name=p['name'],q_deg=p['q_deg'],all_arm_part_count=len(items),hits=0,inherited_source_identical_pairs=True,baseline_historical_hit_count=p['hits'])for p in basefull['checks']]
  whole=dict(report,checks=wholechecks,delta_report_sha256=c.sha(OUT/'review44.json'),sampled_all_arm_pairs_clear=True,exact_distinct_pairs=basefull['exact_distinct_pairs']+len(cache),scope='Current21 all-arm poses reconstructed from original all-pair35 scan for source-identical unchanged pairs plus fresh12-row hardware delta44. Original collision pair removed and rechecked with replacements. Computation total includes historical removed rows; not a fresh all-current pair sweep. No continuous/base-internal/tolerance/wire or physical qualification.')
  (OUT/'full-review35.json').write_text(json.dumps(whole,indent=2)+'\n')
 print('REVIEW44_DONE',len(poses),len(cache),len(hits),flush=True)
if __name__=='__main__':main()
