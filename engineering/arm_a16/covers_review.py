# SPDX-License-Identifier: CC-BY-NC-4.0
"""Report shell interference, with rigid-pair reuse but no collision suppression."""
import itertools,json,numpy as np
import common as c
import skeleton_review as r

def main():
    V=json.loads((c.OUT/'vendor-audit.json').read_text());assert V['layout']==c.L
    covers=[];targets=[];sources={}
    for name in ['root01','skeleton01','covers01']:
        folder=c.OUT/name;p=folder/'manifest.json';D=json.loads(p.read_text());assert D['layout']==c.L;sources[str(p.relative_to(c.ROOT))]=c.sha(p)
        for x in D['parts']:
            path=folder/'step'/(x['id']+'.step');sources[str(path.relative_to(c.ROOT))]=c.sha(path)
            (covers if name=='covers01' else targets).append((x,r.load(path)))
    for j in c.L['joints']:
        motor=next(m for m in V['motors'] if m['joint']==j['id'])
        for suffix,frame in [('stator','fixed'),('external-output','rotor')]:
            path=c.CACHE/'vendor'/(j['id']+'-'+suffix+'.step');assert c.sha(path)==motor['cache_step_sha256'][suffix]
            targets.append((dict(id=j['id']+'-'+suffix,frame=j['id']+'.'+frame),r.load(path)))
    cache={};hits=[];checks=[]
    for pose,q in c.L['poses'].items():
        r.BOUNDS.clear();F=c.frames(q);own=[(p,c.transform(s,F[p['frame']])) for p,s in covers];tg=[(p,c.transform(s,F[p['frame']])) for p,s in targets];count=fresh=0
        for (a,s),(b,t) in itertools.chain(itertools.product(own,tg),itertools.combinations(own,2)):
            if not r.overlap(s,t):continue
            count+=1;rel=np.linalg.inv(F[a['frame']])@F[b['frame']];key=(a['id'],b['id'],tuple(np.round(rel,8).flat))
            if key not in cache:cache[key]=r.common_volume(s,t);fresh+=1
            v=cache[key]
            if v>.08:
                hit=dict(pose=pose,a=a['id'],b=b['id'],volume_mm3=v);hits.append(hit);print('COVER_HIT',hit,flush=True)
        checks.append(dict(pose=pose,positive_bbox_pairs=count,new_exact_checks=fresh));print('COVER_POSE',pose,count,fresh,flush=True)
    (c.OUT/'covers01/review.json').write_text(json.dumps(dict(layout=c.L,source_sha256=sources,vendor_audit_sha256=c.sha(c.OUT/'vendor-audit.json'),checks=checks,collisions=hits,scoped_clear=not hits,
      scope='18 closed shell CAD candidates vs root,core and exact supplier partitions plus shell-to-shell;3 named poses. No hardware, wires, source plugs, complete base shell or path qualification.',
      same_frame_overlap_allowed=False,rigid_pair_reuse='Only identical relative rigid frame matrix and unchanged source pair; no old-layout volume reuse.',production_release=False),indent=2)+'\n')
    print('COVER_REVIEW',len(hits),flush=True)

if __name__=='__main__':main()
