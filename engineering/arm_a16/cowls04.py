# SPDX-License-Identifier: CC-BY-NC-4.0
"""Ordinary through-bolt RS04 cowl mounts; genuine replacement geometry."""
import itertools,json,math,numpy as np,cadquery as cq
import common as c
import covers01 as skin
import hardware01 as h
import skeleton_review as r
from vendor import interfaces

O=c.OUT/'cowls04';O.mkdir(exist_ok=True);g=c.cad
ANGLES=[45,135,225,315]
SPECS=[('J2','A16-S101-root-to-shoulder-L',1,'J1.rotor',[0,0,114]),
       ('J3','A16-S102-shoulder-cross-adapter',2,'J2.rotor',[0,-15,0]),
       ('J4','A16-S104-upper-distal-socket',3,'J3.rotor',[340,0,0])]

def main():
    g.OUT=O;skin.O=O;g.PARTS.clear();g.SHAPES.clear();h.H.clear();I=interfaces()
    replacements={p for _,p,_,_,_ in SPECS}
    replacements.update('A16-C02-'+j+'-cowl-'+k for j in ['J2','J3'] for k in ['a','b'])
    replacements.update(['A16-C02-elbow-dorsal','A16-C02-elbow-ventral'])
    sources={};targets=[]
    for name in ['root01','skeleton01','hardware01','covers02','root-cover03']:
        folder=c.OUT/name;mf=folder/'manifest.json';d=json.loads(mf.read_text());assert d['layout']==c.L
        sources[str(mf.relative_to(c.ROOT))]=c.sha(mf)
        omit=replacements | set(json.loads((c.OUT/'root-cover03/manifest.json').read_text())['replaces_only'])
        for p in d['parts']:
            path=folder/'step'/(p['id']+'.step');sources[str(path.relative_to(c.ROOT))]=c.sha(path)
            if p['id'] not in omit:targets.append((p,r.load(path)))
    mounts=[]
    for joint,oldplate,owner,frame,offset in SPECS:
        inf=next(x for x in I if x['joint']==joint);n,u,v=[np.array(inf[k],float) for k in ['n','u','v']]
        p=np.array(inf['out_mm']);T=np.eye(4);T[:3,:3]=np.column_stack([n,u,v]);T[:3,3]=p
        plate=r.load(c.OUT/'skeleton01/step'/(oldplate+'.step'));off=np.array(offset,float)
        points=[p+64*(math.cos(math.radians(a))*u+math.sin(math.radians(a))*v) for a in ANGLES]
        for pt in points:plate=g.drill(plate,pt+off-n*.6,n,3.5,8.2)
        g.add('A16-C04-'+joint+'-mount-plate',plate,owner,frame=frame,role='printed_structure',material='PETG supported fit',mass=plate.Volume()*1.27e-6,
              note='Existing core plate replaced, fourD3.5 atR64; native mounting faces and source hole patterns unchanged. No plastic threads.')
        ru=70 if joint=='J3' else 71;rv=69
        outer=cq.Workplane(cq.Plane(origin=(8,0,0),normal=(1,0,0),xDir=(0,1,0))).polyline([(a*ru,b*rv) for a,b in skin.PROFILE]).close().extrude(3).val()
        for label,sign in [('a',1),('b',-1)]:
            oldid=('A16-C02-elbow-ventral' if label=='a' else 'A16-C02-elbow-dorsal') if joint=='J4' else 'A16-C02-'+joint+'-cowl-'+label
            part=r.load(c.OUT/'covers02/step'/(oldid+'.step'))
            # Extend the front skin only, not the motor datum or load bracket.
            if joint!='J3':
                extension=c.transform(skin.skin([(8,ru,rv),(11.5,ru,rv)],0,sign,ruled=True),T)
                if joint=='J4':
                    extension=extension.translate(tuple(off)).intersect(cq.Solid.makeBox(200,400,400,g.V([275.25,-200,-200])))
                part=part.fuse(extension).clean().fix()
            for a,pt in zip(ANGLES,points):
                if math.sin(math.radians(a))*sign<0:continue
                t=math.radians(a);d=np.array([math.cos(t),math.sin(t)]);e=np.array([-d[1],d[0]])
                poly=[d*x+e*y for x,y in [(58,-4),(100,-4),(100,4),(58,4)]]
                tab=cq.Workplane(cq.Plane(origin=(8,0,0),normal=(1,0,0),xDir=(0,1,0))).polyline([x.tolist() for x in poly]).close().extrude(3).val().intersect(outer)
                tab=c.transform(tab,T)
                if joint=='J4':tab=tab.translate(tuple(off))
                part=part.fuse(tab).clean().fix();part=g.drill(part,pt+(off if joint=='J4' else 0)+n*7.9,n,3.5,3.2)
            skin.export('A16-C04-'+joint+'-cowl-'+label,part,owner,frame=frame if joint=='J4' else joint+'.fixed',note='Two straight3mm thick internal ears per removable half; ordinary M3 through-bolts. Front skin ends11.5mm from output plane, original body outline retained.')
        for k,pt in enumerate(points,1):
            q=pt+off
            h.bolt(f'A16-C04-H-{joint}-{k}',q-n*.5,n,3,16,11.5,owner,frame,w=.5,washer_hole=3.2)
            h.washer(f'A16-C04-H-{joint}-spacer-{k}',q+n*7.5,n,3,owner,frame,.5,7,hole=3.2)
            h.nut(f'A16-C04-H-{joint}-nut-{k}',q-n*2.9,n,3,owner,frame)
            mounts.append(dict(joint=joint,k=k,frame=frame,p_mm=q.tolist(),n=n.tolist(),angle_deg=ANGLES[k-1],radius_mm=64))
    vendor=json.loads((c.OUT/'vendor-audit.json').read_text());assert vendor['layout']==c.L
    for m in vendor['motors']:
        for suffix,fr in [('stator','fixed'),('external-output','rotor')]:
            f=c.CACHE/'vendor'/(m['joint']+'-'+suffix+'.step');assert c.sha(f)==m['cache_step_sha256'][suffix]
            targets.append((dict(id=m['joint']+'-'+suffix,frame=m['joint']+'.'+fr),r.load(f)))
    parts=[{k:v for k,v in p.items() if k not in ['vertices_mm','triangles']} for p in g.PARTS]
    own=[(p,r.load(O/'step'/(p['id']+'.step'))) for p in parts]
    cache={};hits=[];checks=[]
    for pose,q in c.L['poses'].items():
        r.BOUNDS.clear();F=c.frames(q);a=[(p,c.transform(s,F[p['frame']])) for p,s in own];b=[(p,c.transform(s,F[p['frame']])) for p,s in targets];count=fresh=0
        for (p,s),(t,w) in itertools.chain(itertools.product(a,b),itertools.combinations(a,2)):
            if not r.overlap(s,w):continue
            count+=1;rel=np.linalg.inv(F[p['frame']])@F[t['frame']];key=(p['id'],t['id'],tuple(np.round(rel,8).flat))
            if key not in cache:cache[key]=r.common_volume(s,w);fresh+=1
            if cache[key]>.08:
                hit=dict(pose=pose,a=p['id'],b=t['id'],volume_mm3=cache[key]);hits.append(hit);print('C04_HIT',hit,flush=True)
        checks.append(dict(pose=pose,bbox_pairs=count,new_exact_checks=fresh));print('C04_POSE',pose,count,fresh,flush=True)
    tool_hits=[];r.BOUNDS.clear();F=c.frames(c.L['poses']['reference']);allparts=[(p,c.transform(s,F[p['frame']])) for p,s in targets+own]
    for m in mounts:
        p=np.array(m['p_mm']);n=np.array(m['n']);tool=c.transform(g.cyl(p+n*14.6,n,1.6,25),F[m['frame']])
        for target,s in allparts:
            if r.overlap(tool,s):
                vol=r.common_volume(tool,s)
                if vol>.08:tool_hits.append(dict(joint=m['joint'],k=m['k'],target=target['id'],volume_mm3=vol))
    (O/'meshes.json').write_text(json.dumps(g.PARTS,separators=(',',':'))+'\n')
    record=dict(revision='A16-COWLS04-RS04-THROUGH-M3',layout=c.L,base_context=c.base_context(),source_sha256=sources,vendor_audit_sha256=c.sha(c.OUT/'vendor-audit.json'),parts=parts,replaces_only=sorted(replacements),mounts=mounts,
        hardware_BOM={'ISO4762_M3x16':12,'DIN125_M3_OD7_ID3.2_H0.5':24,'ISO4032_M3_AF5.5_H2.4':12},
        checks=checks,collisions=hits,scoped_clear=not hits,tool_access=dict(pose='reference',empty_diameter_mm=3.2,axial_length_mm=25,collisions=tool_hits,scoped_clear=not tool_hits,actual_tool_selected=False),
        nominal_stack_mm=dict(plate=[-.5,7.5],spacer=[7.5,8],tab=[8,11],head_washer=[11,11.5],head=[11.5,14.5],nut=[-2.9,-.5],screw_tip=-4.5),
        assembly='Preassemble rear nuts while fixed mounting rings remain accessible. Two screws per cover half. Remove cowls before servicing native motor mounting screws. No adhesive, heat-set threads or additional transmission.',
        scope='Replacement shoulder/elbow plates and covers,48 purchased steel envelopes versus current core,C03 root,otherC02 covers,352 hardware,14 exact motor partitions,3 static poses. Empty axial tool spaces only; no insertion path or measured tool.',
        physical_assembly_qualified=False,retention_strength_qualified=False,continuous_motion_qualified=False,production_release=False)
    (O/'manifest.json').write_text(json.dumps(record,indent=2)+'\n');print('COWLS04',len(parts),'collisions',len(hits),'tool_hits',tool_hits,flush=True)

if __name__=='__main__':main()
