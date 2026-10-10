# SPDX-License-Identifier: CC-BY-NC-4.0
"""Exact changed-pair regression, with hash-bound unchanged-pair carryover."""
from pathlib import Path
import sys,json
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'engineering/arm_a16'))
import common as c
import skeleton_review as r
from assembly_sources import collect
OUT=HERE/'build/style01'

def main():
    D=json.loads((OUT/'manifest.json').read_text());assert D['layout']==c.L
    inherited_path=c.OUT/'motion07.json';old=json.loads(inherited_path.read_text())
    assert old['sampled_clear'] and old['layout']==c.L
    for path,digest in old['source_sha256'].items():assert c.sha(ROOT/path)==digest,path
    rows,sources,_=collect(last='skins06')
    omit=set(D['replaces_only']);unchanged=[p for p in rows if p['id'] not in omit]
    assert len(rows)-len(unchanged)==18
    changed=[dict(p,step_path=str((OUT/'step'/(p['id']+'.step')).relative_to(ROOT))) for p in D['parts']]
    for p in changed:sources[p['step_path']]=c.sha(ROOT/p['step_path'])
    sources[str((OUT/'manifest.json').relative_to(ROOT))]=c.sha(OUT/'manifest.json')
    sources[str(inherited_path.relative_to(ROOT))]=c.sha(inherited_path)
    items=[(p,r.load(ROOT/p['step_path'])) for p in changed+unchanged]
    v=json.loads((c.OUT/'vendor-audit.json').read_text())
    for m in v['motors']:
        for suffix,fr in [('stator','fixed'),('external-output','rotor')]:
            file=c.CACHE/'vendor'/(m['joint']+'-'+suffix+'.step');assert c.sha(file)==m['cache_step_sha256'][suffix]
            items.append((dict(id=m['joint']+'-'+suffix,frame=m['joint']+'.'+fr),r.load(file)))
    ctx=c.base_context();file=c.BASE/ctx['base_sources']['flange_step']['path']
    items.append((dict(id='B06-load-flange',frame='baseworld'),r.load(file)))
    checks=[];hits=[];cache={}
    for prior in old['checks']:
        name=prior['sample'];q=prior['q_deg'];F=c.frames(q);F['baseworld']=np.eye(4)
        world=[(p,c.transform(s,F[p['frame']])) for p,s in items]
        boxes=np.array([r.bounds(s) for p,s in world]);lo=boxes[:,:3];hi=boxes[:,3:]
        broad=np.all((hi[:,None,:]>lo[None,:,:]+1e-5)&(hi[None,:,:]>lo[:,None,:]+1e-5),axis=2)
        mask=np.triu(broad,1);mask[len(changed):,:]=False
        candidates=np.argwhere(mask);fresh=0;count=0
        for i,j in candidates:
            p,s=world[i];t,w=world[j]
            rel=np.linalg.inv(F[p['frame']])@F[t['frame']]
            key=(p['id'],t['id'],tuple(np.round(rel,8).flat))
            if key not in cache:cache[key]=r.common_volume(s,w);fresh+=1
            if cache[key]>.08:
                hit=dict(sample=name,a=p['id'],b=t['id'],volume_mm3=cache[key]);hits.append(hit);count+=1
                print('A17_HIT',hit,flush=True)
        zmin=float(min(boxes[i,2] for i in range(len(items)-1)))
        checks.append(dict(sample=name,q_deg=q,bbox_pairs=len(candidates),fresh=fresh,collision_count=count,body_min_z_mm=zmin))
        print('A17_SAMPLE',name,len(candidates),fresh,count,flush=True)
    report=dict(revision='A17-MANTA-CARAPACE01-CHANGED-PAIR-REVIEW',layout=c.L,base_context=ctx,source_sha256=sources,
      changed_count=len(changed),unchanged_count=len(unchanged),total_count=len(items),sample_count=len(checks),checks=checks,collisions=hits,
      sampled_clear=not hits,table_plane_sampled_clear=all(x['body_min_z_mm']>0 for x in checks),
      inherited=dict(path=str(inherited_path.relative_to(ROOT)),sha256=c.sha(inherited_path),source_hashes_verified=True,
        scope='Unchanged-unchanged pairs retain the passing A16 report at identical26 joint configurations, layout and source SHA. Every pair with a new A17 part is recomputed with exact BREP.'),
      tolerance_mm3=.08,scope='26 finite configurations, all changed covers vs other covers/core/hardware/14 exact motor partitions/B06 load flange. Not swept volume/full base skin/dynamic wiring/thermal/physical assembly.',
      physical_fit_qualified=False,production_release=False)
    (OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n')
    print('A17_REVIEW_DONE',len(hits),flush=True)

if __name__=='__main__':main()
