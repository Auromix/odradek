# SPDX-License-Identifier: CC-BY-NC-4.0
"""Selected complete-body finite samples, not swept-volume qualification."""
import itertools,json
import numpy as np
import common as c
import skeleton_review as r
from assembly_sources import collect

def main():
    rows,sources,operations=collect(last='skins06')
    items=[(p,r.load(c.ROOT/p['step_path'])) for p in rows]
    vendor=c.OUT/'vendor-audit.json';v=json.loads(vendor.read_text());assert v['layout']==c.L
    sources[str(vendor.relative_to(c.ROOT))]=c.sha(vendor)
    for m in v['motors']:
        for suffix,fr in [('stator','fixed'),('external-output','rotor')]:
            file=c.CACHE/'vendor'/(m['joint']+'-'+suffix+'.step')
            assert c.sha(file)==m['cache_step_sha256'][suffix]
            items.append((dict(id=m['joint']+'-'+suffix,motor=m['joint'],frame=m['joint']+'.'+fr),r.load(file)))
    ctx=c.base_context();file=c.BASE/'engineering/base_b06/build/load-frame/step/B06-104-LOAD-FLANGE.step'
    items.append((dict(id='B06',frame='baseworld'),r.load(file)))
    samples=[]
    a=np.array(c.L['poses']['idle'],float);b=np.array(c.L['poses']['attention'],float)
    for k in range(13):samples.append((f'idle-attention-{k:02}',((1-k/12)*a+k/12*b).tolist()))
    for x in [-90,-67.5,-45,-22.5,22.5,45,67.5,90]:
        q=b.copy();q[6]=x;samples.append((f'attention-J7-{x:g}',q.tolist()))
    for x in [-60,-30,30,60]:
        q=b.copy();q[5]=x;samples.append((f'attention-J6-{x:g}',q.tolist()))
    samples.append(('reference',c.L['poses']['reference']))
    cache={};hits=[];checks=[];minimum=1e9
    for name,q in samples:
        F=c.frames(q);F['baseworld']=np.eye(4);r.BOUNDS.clear()
        world=[(p,c.transform(s,F[p['frame']])) for p,s in items]
        boxes=np.array([r.bounds(s) for p,s in world]);low=boxes[:,:3];high=boxes[:,3:]
        # Conservative bbox test, exact BREP common-volume narrow phase.
        broad=np.all((high[:,None,:]>low[None,:,:]+1e-5)&(high[None,:,:]>low[:,None,:]+1e-5),axis=2)
        candidates=np.argwhere(np.triu(broad,1));fresh=0;pose_hits=[]
        for i,j in candidates:
            p,s=world[i];t,w=world[j]
            # Two partitions describe the same intact actuator's external
            # surfaces, not separable physical internals. Never waive motors
            # against different motors or any added part.
            if p.get('motor') and p.get('motor')==t.get('motor'):continue
            rel=np.linalg.inv(F[p['frame']])@F[t['frame']]
            key=(p['id'],t['id'],tuple(np.round(rel,8).flat))
            if key not in cache:
                def adjusted(meta,shape,other):
                    if meta.get('intentional_thread_motor')==(other.get('motor') or other['id']):
                        z=meta['thread_zone_mm'];point=np.array(z['p']);n=np.array(z['n'])
                        zone=c.cad.cyl(point-n*(z['depth']+.01),n,z['diameter']/2,z['depth']+.02)
                        shape=shape.cut(c.transform(zone,F[meta['frame']]))
                    if meta.get('intentional_heatset_target')==other['id']:
                        z=meta['heatset_zone_mm'];zone=c.cad.ring(z['p'],z['n'],z['outer_diameter']/2,z['pilot_diameter']/2,z['length'])
                        shape=shape.cut(c.transform(zone,F[meta['frame']]))
                    return shape
                cache[key]=r.common_volume(adjusted(p,s,t),adjusted(t,w,p));fresh+=1
            if cache[key]>.08:
                hit=dict(sample=name,a=p['id'],b=t['id'],volume_mm3=cache[key]);hits.append(hit);pose_hits.append(hit)
                print('MOTION_HIT',hit,flush=True)
        body_z=float(min(boxes[i,2] for i,(p,s) in enumerate(world) if p['id']!='B06'));minimum=min(minimum,body_z)
        checks.append(dict(sample=name,q_deg=q,bbox_pair_count=len(candidates),new_exact_checks=fresh,collision_count=len(pose_hits),body_min_z_mm=body_z))
        print('MOTION_SAMPLE',name,len(candidates),fresh,len(pose_hits),flush=True)
    report=dict(revision='A16-SELECTED-MOTION07',layout=c.L,base_context=ctx,source_sha256=sources,replacement_chain=operations,
        checks=checks,collisions=hits,sampled_clear=not hits,body_min_z_mm=minimum,table_plane_sampled_clear=minimum>0,
        checked_part_count=len(items),sample_count=len(samples),
        tolerance_mm3=.08,
        allowances='Only designated motor thread engagement cylinder and designated heat-set pilot annulus; identical actuator external partitions not treated as independent parts. No whole added-part pair waiver.',
        scope='13 finite samples along straight joint interpolation idle to attention,8 J7 and4 J6 independent attention samples,1 reference;541 own parts+14 actuator partitions+B06 load flange. Full B06 shell, camera/head, wires, actual tolerance, tools and swept volume excluded.',
        whole_motion_qualified=False,connected_harness_qualified=False,production_release=False)
    (c.OUT/'motion07.json').write_text(json.dumps(report,indent=2)+'\n')
    print('MOTION_DONE',len(samples),len(hits),flush=True)

if __name__=='__main__':main()
