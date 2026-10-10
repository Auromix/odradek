# SPDX-License-Identifier: CC-BY-NC-4.0
"""Check a new module against replaced current assembly, without pair waivers."""
import itertools,json,numpy as np
import common as c
import skeleton_review as r
from assembly_sources import collect

def review(module,tool_spaces=()):
    O=c.OUT/module;D=json.loads((O/'manifest.json').read_text())
    rows,sources,operations=collect(last=module);own=[];targets=[]
    for p in rows:
        (own if p['source_module']==module else targets).append((p,r.load(c.ROOT/p['step_path'])))
    V=json.loads((c.OUT/'vendor-audit.json').read_text());assert V['layout']==c.L
    for m in V['motors']:
        for suffix,fr in [('stator','fixed'),('external-output','rotor')]:
            f=c.CACHE/'vendor'/(m['joint']+'-'+suffix+'.step');assert c.sha(f)==m['cache_step_sha256'][suffix]
            targets.append((dict(id=m['joint']+'-'+suffix,frame=m['joint']+'.'+fr),r.load(f)))
    hits=[];checks=[];cache={}
    for pose,q in c.L['poses'].items():
        r.BOUNDS.clear();F=c.frames(q);a=[(p,c.transform(s,F[p['frame']])) for p,s in own];b=[(p,c.transform(s,F[p['frame']])) for p,s in targets];count=fresh=0
        for (p,s),(t,w) in itertools.chain(itertools.product(a,b),itertools.combinations(a,2)):
            if not r.overlap(s,w):continue
            count+=1;rel=np.linalg.inv(F[p['frame']])@F[t['frame']];key=(p['id'],t['id'],tuple(np.round(rel,8).flat))
            if key not in cache:
                checked=s
                if p.get('intentional_heatset_target')==t['id']:
                    z=p['heatset_zone_mm'];zone=c.cad.ring(z['p'],z['n'],z['outer_diameter']/2,z['pilot_diameter']/2,z['length'])
                    checked=s.cut(c.transform(zone,F[p['frame']]))
                elif t.get('intentional_heatset_target')==p['id']:
                    z=t['heatset_zone_mm'];zone=c.cad.ring(z['p'],z['n'],z['outer_diameter']/2,z['pilot_diameter']/2,z['length'])
                    w=w.cut(c.transform(zone,F[t['frame']]))
                cache[key]=r.common_volume(checked,w);fresh+=1
            if cache[key]>.08:
                hit=dict(pose=pose,a=p['id'],b=t['id'],volume_mm3=cache[key]);hits.append(hit);print('MODULE_HIT',hit,flush=True)
        checks.append(dict(pose=pose,bbox_pairs=count,new_exact_checks=fresh));print('MODULE_POSE',module,pose,count,fresh,flush=True)
    tool_hits=[];r.BOUNDS.clear();F=c.frames(c.L['poses']['reference'])
    tg=[(p,c.transform(s,F[p['frame']])) for p,s in own+targets]
    for name,frame,space in tool_spaces:
        tool=c.transform(space,F[frame])
        for p,s in tg:
            if r.overlap(tool,s):
                v=r.common_volume(tool,s)
                if v>.08:tool_hits.append(dict(tool=name,target=p['id'],volume_mm3=v))
    report=dict(layout=c.L,source_sha256=sources,vendor_audit_sha256=c.sha(c.OUT/'vendor-audit.json'),replacements=operations,checks=checks,collisions=hits,scoped_clear=not hits,
      tool_access=dict(pose='reference',space_count=len(tool_spaces),collisions=tool_hits,scoped_clear=not tool_hits,actual_tools_and_insertion_qualified=False),
      heatset_press_allowance='Only designated insert versus designated printed pilot: local annulus betweenD3.98 andD4.62 for actual insert length. No whole-pair waiver. Insertion/pullout remains unqualified.',
      scope='New module vs explicitly replaced current whole body and14 exact external motor partitions;3 named static poses. Empty tool spaces only. Base shell, dynamic cables, physical fit and continuous motion excluded.',production_release=False)
    (O/'review.json').write_text(json.dumps(report,indent=2)+'\n');print('MODULE_REVIEW',module,'hits',len(hits),'tools',tool_hits,flush=True)
    return report
