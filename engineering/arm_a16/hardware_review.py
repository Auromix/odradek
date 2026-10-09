# SPDX-License-Identifier: CC-BY-NC-4.0
"""Hash-bound nominal fastener fit; only explicit tapped-thread zones exempted."""
import itertools,json,numpy as np
import common as c
import skeleton_review as r

def main():
    V=json.loads((c.OUT/'vendor-audit.json').read_text());assert V['layout']==c.L
    for m in V['motors']:
        for suffix,h in m['cache_step_sha256'].items():assert c.sha(c.CACHE/'vendor'/(m['joint']+'-'+suffix+'.step'))==h
    H=c.OUT/'hardware01';D=json.loads((H/'manifest.json').read_text());assert D['layout']==c.L
    sources={};hardware=[];targets=[]
    for name in ['root01','skeleton01','hardware01']:
        folder=c.OUT/name;p=folder/'manifest.json';doc=json.loads(p.read_text());assert doc['layout']==c.L
        sources[str(p.relative_to(c.ROOT))]=c.sha(p)
        for x in doc['parts']:
            path=folder/'step'/(x['id']+'.step');sources[str(path.relative_to(c.ROOT))]=c.sha(path)
            (hardware if name=='hardware01' else targets).append((x,r.load(path)))
    ctx=c.base_context();base=c.BASE/ctx['base_sources']['load_flange']['path'] if 'load_flange' in ctx['base_sources'] else None
    if base is None:
        base=c.BASE/'engineering/base_b06/build/load-frame/step/B06-104-LOAD-FLANGE.step'
    # B06 is already in world coordinates: undo the body-root transform.
    targets.append((dict(id='B06',frame='world'),c.transform(r.load(base),np.linalg.inv(np.array(c.L['root_transform_mm'])))))
    sources[str(base)]=c.sha(base)
    for j in c.L['joints']:
        for suffix,frame in [('stator','fixed'),('external-output','rotor')]:
            targets.append((dict(id=j['id']+'-'+suffix,motor=j['id'],frame=j['id']+'.'+frame),r.load(c.CACHE/'vendor'/(j['id']+'-'+suffix+'.step'))))
    collisions=[];checks=[];thread_exemptions=[]
    for pose,q in c.L['poses'].items():
        r.BOUNDS.clear();F=c.frames(q);hw=[(p,c.transform(s,F[p['frame']])) for p,s in hardware];tg=[(p,c.transform(s,F[p['frame']])) for p,s in targets]
        pairs=itertools.chain(itertools.product(hw,tg),itertools.combinations(hw,2));tested=0
        for (a,s),(b,t) in pairs:
            if not r.overlap(s,t):continue
            tested+=1;shape=s
            if a.get('intentional_thread_motor')==(b.get('motor') or b['id']):
                z=a['thread_zone_mm'];p=np.array(z['p']);n=np.array(z['n'])
                zone=c.transform(c.cad.cyl(p-n*(z['depth']+.01),n,z['diameter']/2,z['depth']+.02),F[a['frame']])
                shape=s.cut(zone);thread_exemptions.append(dict(pose=pose,a=a['id'],b=b['id'],zone=z))
            v=r.common_volume(shape,t)
            if v>.08:
                hit=dict(pose=pose,a=a['id'],b=b['id'],volume_mm3=v);collisions.append(hit);print('HARDWARE_HIT',hit,flush=True)
        checks.append(dict(pose=pose,positive_bbox_pairs=tested,hardware_parts=len(hw),target_parts=len(tg)))
        print('HARDWARE_POSE',pose,tested,'hits',len(collisions),flush=True)
    # A straight D12 reservation at Z11 clears stock sleeves, inner tube walls
    # and transverse clamp bolts. No connection across any rotating joint.
    reservations=[]
    for owner,start,length,cy in [(3,50,220,0),(4,20,55,62)]:
        wire=c.cad.cyl([start,cy,11],[1,0,0],6,length);hits=[]
        for p,s in hardware+targets:
            if p['frame']!=f'J{owner}.rotor':continue
            if r.overlap(wire,s):
                v=r.common_volume(wire,s)
                if v>.08:hits.append(dict(id=p['id'],volume_mm3=v))
        reservations.append(dict(frame=f'J{owner}.rotor',diameter_mm=12,start_mm=[start,cy,11],length_mm=length,hits=hits,straight_reservation_clear=not hits))
    report=dict(revision='A16-HARDWARE01',layout=c.L,source_sha256=sources,vendor_audit_sha256=c.sha(c.OUT/'vendor-audit.json'),checks=checks,collisions=collisions,thread_zone_exemptions=thread_exemptions,
        straight_tube_reservations=reservations,scoped_clear=not collisions,
        scope='Complete core nominal purchased hardware vs current core,14 supplier partitions and B06 load flange; hardware-to-hardware;3 named static poses. Tapped-thread allowances are local cylinders with actual engagement only.',
        limits=['No cosmetic covers, connected harness, source mating plugs, full base shell, tool/head or continuous path.','Fastener nominal envelopes and washer stack do not prove thread strength, printed preload retention or tightening tool access.','RS00 front usable blind-thread depth needs physical confirmation.','Bearing mass is a uniform solid steel annular envelope, not manufacturer mass.'],
        physical_assembly_qualified=False,whole_motion_qualified=False,production_release=False)
    (H/'review.json').write_text(json.dumps(report,indent=2)+'\n');print('HARDWARE_REVIEW_DONE',len(collisions),flush=True)

if __name__=='__main__':main()
