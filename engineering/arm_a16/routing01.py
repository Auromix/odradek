# SPDX-License-Identifier: CC-BY-NC-4.0
"""Empty routing allocations through ordinary root slots, not installed wires."""
import json,numpy as np,cadquery as cq
import common as c
import skeleton_review as r

O=c.OUT/'routing01';O.mkdir(exist_ok=True);g=c.cad;g.OUT=O

def main():
    g.PARTS.clear();sources={};targets=[]
    for name in ['root01','skeleton01','hardware01']:
        folder=c.OUT/name;mf=folder/'manifest.json';D=json.loads(mf.read_text());assert D['layout']==c.L
        sources[str(mf.relative_to(c.ROOT))]=c.sha(mf)
        for p in D['parts']:
            path=folder/'step'/(p['id']+'.step');sources[str(path.relative_to(c.ROOT))]=c.sha(path);targets.append((p,r.load(path)))
    V=json.loads((c.OUT/'vendor-audit.json').read_text());assert V['layout']==c.L
    for m in V['motors']:
        for suffix,fr in [('stator','fixed'),('external-output','rotor')]:
            p=c.CACHE/'vendor'/(m['joint']+'-'+suffix+'.step');assert c.sha(p)==m['cache_step_sha256'][suffix]
            targets.append((dict(id=m['joint']+'-'+suffix,frame=m['joint']+'.'+fr),r.load(p)))
    shapes=[];rad=18.75
    for name,angle in [('camera',55),('power-control',235)]:
        a=np.radians(angle);u=np.array([np.cos(a),np.sin(a),0]);origin=u*18+np.array([0,0,66])
        def point(x,z):return g.V(u*x+np.array([0,0,z]))
        edges=[cq.Edge.makeThreePointArc(point(18,66),point(36.75-rad/np.sqrt(2),66+rad/np.sqrt(2)),point(36.75,84.75)),
          cq.Edge.makeThreePointArc(point(36.75,84.75),point(36.75+rad/np.sqrt(2),103.5-rad/np.sqrt(2)),point(55.5,103.5)),
          cq.Edge.makeLine(point(55.5,103.5),point(55.5,203))]
        path=cq.Wire.assembleEdges(edges);plane=cq.Plane(origin=g.V(origin),normal=(0,0,1),xDir=g.V(u))
        space=cq.Workplane(plane).rect(4,10).sweep(path,isFrenet=False).val();assert space.isValid() and len(space.Solids())==1
        p=g.add('A16-A-root-'+name+'-space',space,0,role='space_reservation',material='Empty unsourced bundle allocation4x10; DO NOT PRINT',frame='world',mass=0,
          note='Fixed-root S passage:2 bends of centrelineR18.75 below motor, then peripheral slots atR55.5. Only J1zero static fit; not a rotating service loop or a selected GMSL/power cable. Bend radius/current/EMI/connector pull-through unqualified.')
        shapes.append((p,space))
    collisions=[];checks=[]
    for pose,q in c.L['poses'].items():
        assert q[0]==0,'This straight upper-root allocation is not a yaw service-loop model.'
        r.BOUNDS.clear();F=c.frames(q);count=0
        for p,s in shapes:
            space=c.transform(s,F['world'])
            for t,shape in targets:
                solid=c.transform(shape,F[t['frame']])
                if not r.overlap(space,solid):continue
                count+=1;v=r.common_volume(space,solid)
                if v>.08:collisions.append(dict(pose=pose,allocation=p['id'],target=t['id'],volume_mm3=v))
        checks.append(dict(pose=pose,J1_deg=q[0],positive_bbox_pairs=count));print('ROOT_SPACE_POSE',pose,count,flush=True)
    parts=[{k:v for k,v in p.items() if k not in ['vertices_mm','triangles']} for p in g.PARTS]
    (O/'meshes.json').write_text(json.dumps(g.PARTS,separators=(',',':'))+'\n')
    R=dict(revision='A16-ROOT-ROUTING-ALLOCATION01',layout=c.L,source_sha256=sources,vendor_audit_sha256=c.sha(c.OUT/'vendor-audit.json'),parts=parts,checks=checks,collisions=collisions,scoped_clear=not collisions,
      plate_slot_mm=[6,14],end_mill_diameter_mm=6,slot_centres_radius_mm=55,slot_angles_deg=[55,235],bundle_allocation_mm=[4,10],bundle_allocation_centre_radius_mm=55.5,
      centreline_bend_radius_mm=18.75,source_cable_bend_radius_verified=False,
      scope='Empty4x10 root allocations vs core, exact supplier partitions and352 nominal hardware parts;3 named static poses all atJ1zero. Root S route is fixed, upper moving-ring service loop absent.',
      installed_wires=False,continuous_harness_qualified=False,connector_pull_through_qualified=False,power_current_qualified=False,production_release=False)
    (O/'manifest.json').write_text(json.dumps(R,indent=2)+'\n');print('ROOT_SPACE_HITS',collisions,flush=True)

if __name__=='__main__':main()
