# SPDX-License-Identifier: CC-BY-NC-4.0
"""Ordinary four-screw root-cover attachment, isolated from the issued core."""
import itertools,json,math,numpy as np,cadquery as cq
import common as c
import covers01 as skin
import hardware01 as h
import skeleton_review as r

O=c.OUT/'root-cover03';O.mkdir(exist_ok=True);g=c.cad
ANGLES=[20,160,200,340]

def main():
    c.base_context();g.OUT=O;skin.O=O;g.PARTS.clear();g.SHAPES.clear();h.H.clear()
    points=[np.array([62*math.cos(math.radians(a)),62*math.sin(math.radians(a)),0]) for a in ANGLES]
    sources={};targets=[]
    replacements={'A16-R102-J1-front-holder','A16-C02-J1-cowl-a','A16-C02-J1-cowl-b'}
    for name in ['root01','skeleton01','hardware01','covers02']:
        folder=c.OUT/name;mf=folder/'manifest.json';d=json.loads(mf.read_text());assert d['layout']==c.L
        sources[str(mf.relative_to(c.ROOT))]=c.sha(mf)
        for p in d['parts']:
            path=folder/'step'/(p['id']+'.step');sources[str(path.relative_to(c.ROOT))]=c.sha(path)
            if p['id'] not in replacements:targets.append((p,r.load(path)))
    plate=r.load(c.OUT/'root01/step/A16-R102-J1-front-holder.step')
    for p in points:plate=g.drill(plate,p+np.array([0,0,-2.6]),[0,0,1],3.5,6.2)
    g.add('A16-C03-root-front-holder',plate,0,role='printed_structure',frame='J1.fixed',
        material='PETG supported dimensional fit',mass=plate.Volume()*1.27e-6,
        note='Replacement R102 only: four additionalD3.5 atR62,20/160/200/340deg. X+/-58.2609 lies outside S101 foot+/-55, allowing an outward hex-key access allocation. Native mounts/slots/datums unchanged; old R102 is not simultaneously installed.')
    # The tabs are straight radial strips clipped to the existing outer loft.
    # Two tabs per half; ordinary half-mm steel washers fill the designed gap.
    wires=[]
    for z in [4,4.5,7]:
        if z<=4.5:ru=70+(z+10)/14.5;rv=69+(z+10)/14.5
        else:ru=71+(z-4.5)*2/24;rv=70+(z-4.5)/24
        wire=cq.Workplane('XY',origin=(0,0,z)).polyline([(u*ru,v*rv) for u,v in skin.PROFILE]).close().val();wires.append(wire)
    clip=cq.Solid.makeLoft(wires,ruled=True)
    for label,sign in [('a',1),('b',-1)]:
        part=r.load(c.OUT/'covers02/step'/f'A16-C02-J1-cowl-{label}.step')
        # Ordinary trim gives a real1.2mm nominal vertical service seam above
        # the base's Z74 neck; the current C02 source ended at exactly Z74.
        part=part.cut(cq.Solid.makeBox(400,400,20.2,g.V([-200,-200,-110]))).fix()
        for angle,p in zip(ANGLES,points):
            if p[1]*sign<0:continue
            t=math.radians(angle);u=np.array([math.cos(t),math.sin(t)]);v=np.array([-u[1],u[0]])
            poly=[u*x+v*y for x,y in [(58,-4),(100,-4),(100,4),(58,4)]]
            tab=cq.Workplane('XY',origin=(0,0,4)).polyline([x.tolist() for x in poly]).close().extrude(3).val().intersect(clip)
            part=part.fuse(tab).clean().fix()
            part=g.drill(part,p+np.array([0,0,3.9]),[0,0,1],3.5,3.2)
        skin.export('A16-C03-root-cowl-'+label,part,0,frame='J1.fixed',
            note='Existing A continuous root outline retained. Two straight3mm internal tabs per half, D3.5 clearance. Print upright with brim and internal support under tabs; slicer and physical retention not qualified.')
    for k,p in enumerate(points,1):
        h.bolt(f'A16-C03-H-M3-{k}',p+np.array([0,0,-2.5]),[0,0,1],3,16,9.5,0,'J1.fixed',w=.5,washer_hole=3.2)
        h.washer(f'A16-C03-H-tab-spacer-{k}',p+np.array([0,0,3.5]),[0,0,1],3,0,'J1.fixed',.5,7,hole=3.2)
        h.nut(f'A16-C03-H-nut-{k}',p+np.array([0,0,-4.9]),[0,0,1],3,0,'J1.fixed')
    V=json.loads((c.OUT/'vendor-audit.json').read_text());assert V['layout']==c.L
    for motor in V['motors']:
        for suffix,frame in [('stator','fixed'),('external-output','rotor')]:
            path=c.CACHE/'vendor'/(motor['joint']+'-'+suffix+'.step');assert c.sha(path)==motor['cache_step_sha256'][suffix]
            targets.append((dict(id=motor['joint']+'-'+suffix,frame=motor['joint']+'.'+frame),r.load(path)))
    context=c.base_context();targets.append((dict(id='B06-load-flange',frame=None),r.load(c.BASE/context['base_sources']['flange_step']['path'])))
    routing=json.loads((c.OUT/'routing01/manifest.json').read_text());assert routing['layout']==c.L
    sources[str((c.OUT/'routing01/manifest.json').relative_to(c.ROOT))]=c.sha(c.OUT/'routing01/manifest.json')
    for p in routing['parts']:targets.append((p,r.load(c.OUT/'routing01/step'/(p['id']+'.step'))))
    parts=[{k:v for k,v in p.items() if k not in ['vertices_mm','triangles']} for p in g.PARTS]
    own=[(p,r.load(O/'step'/(p['id']+'.step'))) for p in parts]
    base_manifest=json.loads((c.BASE/context['base_sources']['manifest']['path']).read_text())
    product=[p for p in base_manifest['parts'] if p['category']!='environment']
    base_top=max(p['bbox']['max'][2] for p in product)
    F0=c.frames(c.L['poses']['attention'])
    bottom=min(c.transform(s,F0[p['frame']]).BoundingBox().zmin for p,s in own)
    assert bottom-base_top>1.19
    cache={};collisions=[];checks=[]
    for pose,q in c.L['poses'].items():
        r.BOUNDS.clear();F=c.frames(q)
        a=[(p,c.transform(s,F[p['frame']])) for p,s in own]
        b=[(p,c.transform(s,F[p['frame']]) if p['frame'] else s) for p,s in targets]
        count=fresh=0
        for (p,s),(t,w) in itertools.chain(itertools.product(a,b),itertools.combinations(a,2)):
            if not r.overlap(s,w):continue
            count+=1;relative=np.linalg.inv(F[p['frame']])@(F[t['frame']] if t['frame'] else np.eye(4))
            key=(p['id'],t['id'],tuple(np.round(relative,8).flat))
            if key not in cache:cache[key]=r.common_volume(s,w);fresh+=1
            if cache[key]>.08:
                hit=dict(pose=pose,a=p['id'],b=t['id'],volume_mm3=cache[key]);collisions.append(hit);print('ROOT_COVER_HIT',hit,flush=True)
        checks.append(dict(pose=pose,bbox_pairs=count,new_exact_checks=fresh));print('ROOT_COVER_POSE',pose,count,fresh,flush=True)
    # Empty conventional L-key access above each screw head, in the supported
    # reference maintenance pose. This is not an exact purchased tool model,
    # insertion trajectory, socket engagement or a torque qualification.
    tool_hits=[];r.BOUNDS.clear();Fs=c.frames(c.L['poses']['reference'])
    tg=[(p,c.transform(s,Fs[p['frame']]) if p['frame'] else s) for p,s in targets+own]
    for k,p in enumerate(points,1):
        sign=1 if p[0]>0 else -1
        space=g.cyl(p+np.array([0,0,10.6]),[0,0,1],1.6,19.9).fuse(g.cyl(p+np.array([0,0,30.5]),[sign,0,0],1.6,30))
        space=c.transform(space,Fs['J1.fixed'])
        for target,solid in tg:
            if not r.overlap(space,solid):continue
            v=r.common_volume(space,solid)
            if v>.08:tool_hits.append(dict(tool=k,target=target['id'],volume_mm3=v))
    print('ROOT_TOOL_HITS',tool_hits,flush=True)
    (O/'meshes.json').write_text(json.dumps(g.PARTS,separators=(',',':'))+'\n')
    record=dict(revision='A16-ROOT-COVER03-FOUR-M3',layout=c.L,source_sha256=sources,
        vendor_audit_sha256=c.sha(c.OUT/'vendor-audit.json'),base_context=context,parts=parts,
        replaces_only=sorted(replacements),mount_radius_mm=62,mount_angles_deg=ANGLES,
        holes_diameter_mm=3.5,tab_z_mm=[4,7],tab_thickness_mm=3,
        whole_base_nominal_bounds=dict(product_count=len(product),base_top_z_mm=base_top,module_bottom_z_mm=bottom,vertical_gap_mm=bottom-base_top,scope='Conservative world-Z separation against canonical source-manifest product bounds, not base-shell BREP or tolerance/physical qualification.'),
        hardware_BOM={'ISO4762_M3x16':4,'DIN125_M3_washer_OD7_ID3.2_H0.5':8,'ISO4032_M3_AF5.5_H2.4':4},
        rear_thread_tip_z_mm=-8.5,nut_bottom_z_mm=-4.9,checks=checks,collisions=collisions,scoped_clear=not collisions,
        tool_access=dict(pose='reference',J1_deg=0,empty_space_diameter_mm=3.2,shaft_z_mm=[10.6,30.5],outward_leg_mm=30,collisions=tool_hits,scoped_clear=not tool_hits,actual_tool_selected=False,socket_and_insertion_qualified=False),
        assembly_order='Nut below R102, half-mm washer above R102, two tabs per cowl, head washer then M3x16. Preassemble R102 nuts before fitting cowls. Motor outputs and B06 interface untouched.',
        scope='Root replacement plate/two covers plus16 purchased envelopes vs current full core, other covers,352 existing hardware,14 exact external motor partitions, B06 load flange and two root space allocations;3 named static poses. No complete base shell, real plugs or motion path.',
        physical_assembly_qualified=False,retention_strength_qualified=False,thermal_qualified=False,production_release=False)
    (O/'manifest.json').write_text(json.dumps(record,indent=2)+'\n');print('ROOT_COVER03',len(parts),'hits',len(collisions),flush=True)

if __name__=='__main__':main()
