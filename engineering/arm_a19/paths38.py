# SPDX-License-Identifier: CC-BY-NC-4.0
"""Verify simple axial install-later paths for staged tool access."""
from pathlib import Path
import sys,json
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/assembly25'
sys.path.insert(0,str(HERE));import tools37 as t
from vendor import interfaces
w=t.w;c=t.c;r=t.r

def main():
 path=OUT/'manifest.json';d=json.loads(path.read_text());tools=json.loads((OUT/'tools37.json').read_text());assert tools['source_assembly_sha256']==c.sha(path)
 F=w.f.frames(d['layout'],d['layout']['poses']['reference']);items=[(p,r.load(ROOT/p['step_path']))for p in d['parts']];vendor=json.loads((c.OUT/'vendor-audit.json').read_text())
 for m in vendor['motors']:
  if m['joint']=='J5':
   parent=next(x for x in vendor['motors']if x['joint']=='J1');T=np.array(w.interface()['T_joint_from_raw_mm'])@np.linalg.inv(np.array(interfaces()[0]['T_joint_from_raw_mm']))
   for tag,fr in [('stator','fixed'),('external-output','rotor')]:
    p=c.CACHE/'vendor'/('J1-'+tag+'.step');assert c.sha(p)==parent['cache_step_sha256'][tag];items.append((dict(id='J5-supplier-'+tag,frame='J5.'+fr),c.transform(r.load(p),T)))
   continue
  for tag,fr in [('stator','fixed'),('external-output','rotor')]:
   p=c.CACHE/'vendor'/(m['joint']+'-'+tag+'.step');assert c.sha(p)==m['cache_step_sha256'][tag];items.append((dict(id=m['joint']+'-supplier-'+tag,frame=m['joint']+'.'+fr),r.load(p)))
 maps={p['id']:(p,s)for p,s in items};nativeids=set(p['id']for p,s in items if 'supplier-'in p['id']);stages=[]
 for name,bolt,incoming,extra_remove,added,axis,start in [
  ('shoulder-foot-after-J1-output-before-cowl-hardware','A16-H-J1-output-1',['A19-S22-shoulder-foot-12mm-R6'],[p['id'] for p in d['parts'] if p['id'].startswith('A16-C04-H-J2-')],[],[0,0,1],140),
  ('upper-tube-before-distal-socket','A16-H-J3-output-1',['A16-S105-upper-stock-tube'],['A16-C04-J4-mount-plate','A16-S104-upper-distal-socket'],[],[1,0,0],230),
  ('J7-bearing-journal-module-after-fixed-bolts-before-retainer','A16-H-J7-fixed-1',['A16-C05-J7-bearing-housing','A16-H-J7-6807-1','A16-H-J7-6807-2','A13-J7-103-output-journal'],[],[],[1,0,0],80),
  ('J7-retainer-after-bearing-module','A16-H-J7-fixed-1',['A13-J7-102-bearing-retainer'],[],['A16-C05-J7-bearing-housing','A16-H-J7-6807-1','A16-H-J7-6807-2'],[1,0,0],80),
  ('tool-carrier-after-J7-output','A16-H-J7-output-1',['A13-IF-301-recessed-carrier'],[],[],[1,0,0],80)]:
  stage=next(p for p in tools['tools']if p['id']==bolt);removed=set(stage['removed_at_stage'])|set(extra_remove)|set(incoming);removed-=set(added);targets=[(p,c.transform(s,F[p['frame']]))for p,s in items if p['id']not in removed]
  records=[];direction=F[maps[incoming[0]][0]['frame']][:3,:3]@np.array(axis)
  for distance in sorted(set([0,.5,1,2,3,4,5,7,10,15,20,30,40,60,start]+list(np.arange(0,start+1,10))),reverse=True):
   hits=[]
   for id in incoming:
    p,shape=maps[id];moving=c.transform(shape,F[p['frame']]).translate((direction*distance).tolist())
    for other,target in targets:
     if not r.overlap(moving,target):continue
     vol=r.common_volume(moving,target)
     if vol>.08:hits.append(dict(incoming=id,target=other['id'],volume_mm3=vol))
   records.append(dict(distance_mm=float(distance),hits=hits))
   if hits:print('PATH38_HIT',name,distance,hits,flush=True)
  rec=dict(stage=name,after_tool_bolt=bolt,incoming=incoming,kept_at_stage=[p['id']for p,s in targets],extra_install_later=extra_remove,axis_first_incoming_local=axis,start_distance_mm=start,checks=records,sampled_clear=not any(p['hits']for p in records));stages.append(rec);print('PATH38_STAGE',name,rec['sampled_clear'],flush=True)
 # Separate bench fixtures establish that the incoming bearing module can
 # itself be assembled. No other arm rows are silently treated as absent here.
 for name,incoming,targetids,axis in [
  ('bench-first-6807-from-rear',['A16-H-J7-6807-1'],['A16-C05-J7-bearing-housing'],[-1,0,0]),
  ('bench-second-6807-from-front',['A16-H-J7-6807-2'],['A16-C05-J7-bearing-housing','A16-H-J7-6807-1'],[1,0,0]),
  ('bench-output-journal-from-rear',['A13-J7-103-output-journal'],['A16-C05-J7-bearing-housing','A16-H-J7-6807-1','A16-H-J7-6807-2'],[-1,0,0])]:
  records=[]
  for distance in sorted(set([0,.5,1,2,3,4,5,7,10,15,20,30,40,60]+list(np.arange(0,61,5))),reverse=True):
   hits=[]
   for id in incoming:
    moving=maps[id][1].translate((np.array(axis)*distance).tolist())
    for tid in targetids:
     target=maps[tid][1]
     if r.overlap(moving,target):
      vol=r.common_volume(moving,target)
      if vol>.08:hits.append(dict(incoming=id,target=tid,volume_mm3=vol))
   records.append(dict(distance_mm=float(distance),hits=hits))
  rec=dict(stage=name,fixture='bench J7-local frame, bearings before output journal',incoming=incoming,kept_at_stage=targetids,axis_first_incoming_local=axis,start_distance_mm=60,checks=records,sampled_clear=not any(p['hits']for p in records));stages.append(rec);print('PATH38_BENCH',name,rec['sampled_clear'],[p for p in records if p['hits']],flush=True)
 report=dict(revision='A19-STAGED-AXIAL-PATHS38',source_assembly_sha256=c.sha(path),source_tools37_sha256=c.sha(OUT/'tools37.json'),native_sources=tools['native_sources'],source_checker_sha256=c.sha(Path(__file__)),stages=stages,all_sampled_paths_clear=all(s['sampled_clear']for s in stages),production_release=False,scope='Five explicitly staged ordinary straight installation paths and three separate bearing/journal bench paths, finite distances. Source STEP, shaft/bearing/pin fixture nominal only; not continuous/tolerance/press-fit/preload/handling or physical assembly proof.')
 (OUT/'paths38.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
