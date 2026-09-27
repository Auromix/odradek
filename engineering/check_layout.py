# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""OCCT solid collision samples. Separation is evidence only for tested poses.

Joint bodies are conservative cylinders, so overlap flags require real vendor
geometry inspection. Finger solids are the actual current design-study solids.
No continuous motion, tolerance or load deformation guarantee is implied.
"""
import json
from itertools import combinations
from pathlib import Path
import numpy as np
import cadquery as cq
from build_layout import moved
from kinematics import revolute

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/layout'


def prefixes(p, qdeg):
    pre=[np.eye(4)]
    for j,q in zip(p['joints'],qdeg):
        pre.append(pre[-1]@revolute(j['axis'],j['origin_mm'],np.deg2rad(q)))
    return pre


def finger_transform(p, finger, angle_deg):
    f=next(x for x in p['head']['fingers'] if x['id']==finger)
    phi=np.deg2rad(f['phi_deg']);er=np.array([np.cos(phi),np.sin(phi),0])
    root=np.array(p['head']['face_center_mm'])+f['root_radius_mm']*er+[0,0,f['root_z_mm']]
    return revolute([np.sin(phi),-np.cos(phi),0],root,np.deg2rad(angle_deg))


def relation(a,b):
    gap=a.distance(b)
    # OCCT common on some vendor/disconnected compounds can return an empty
    # aggregate despite solid-level overlap. Pair solids explicitly. This is
    # an overlap sum (may double count overlapping input solids), not union V.
    volume=0. if gap>1e-5 else sum(max(sa.intersect(sb).Volume(),0.) for sa in a.Solids() for sb in b.Solids())
    return {'distance_mm':float(gap),'common_volume_mm3':float(max(volume,0)),
            'interferes':bool(volume>1e-4)}


def main():
    p=json.loads((ROOT/'engineering/parameters/r4-layout.json').read_text())
    manifest=json.loads((OUT/'manifest.json').read_text())
    entries={e['name']:e for e in manifest['parts']}
    shapes={name:cq.importers.importStep(str(OUT/'parts-step'/f'{name}.step')).val() for name in entries}
    arm_names=[n for n in shapes if n.endswith('_housing_envelope')]
    arm_tests=[]
    for label,q in p['poses_deg'].items():
        pre=prefixes(p,q)
        ss={n:moved(shapes[n],pre[entries[n]['attachment']]) for n in arm_names}
        pairs=[]
        for a,b in combinations(arm_names,2):
            r=relation(ss[a],ss[b]);pairs.append({'a':a,'b':b,**r})
        arm_tests.append({'pose':label,'q_deg':q,'pairs':pairs})
    # Combine each finger's structure/light/contact pads; internal intended
    # mounting contacts are not treated as inter-finger collisions.
    fingers={f['id']:cq.Compound.makeCompound([shapes[n] for n,e in entries.items() if e['finger']==f['id']]) for f in p['head']['fingers']}
    fixed_names=[n for n in shapes if n.startswith(('CAM_','HEAD_front','HEAD_screen'))]
    drive_names=[n for n in shapes if n.startswith('HEAD_DRIVE_')]
    static=[]
    for a in drive_names:
        for b in fixed_names:
            static.append({'a':a,'b':b,**relation(shapes[a],shapes[b])})
    closure=[]
    for alpha in np.linspace(0,1,25):
        angles={f['id']:float(alpha*f['closure_study_deg']) for f in p['head']['fingers']}
        fs={n:moved(s,finger_transform(p,n,angles[n])) for n,s in fingers.items()}
        pairs=[]
        for a,b in combinations(fingers,2):pairs.append({'a':a,'b':b,**relation(fs[a],fs[b])})
        for a in fingers:
            for b in fixed_names:
                r=relation(fs[a],shapes[b]);pairs.append({'a':a,'b':b,**r})
        closure.append({'fraction':float(alpha),'angles_deg':angles,'pairs':pairs})
    result={'revision':p['revision'],'status':'DISCRETE SOLID CHECK; NOT A CONTINUOUS OR MANUFACTURING QUALIFICATION',
            'static_drive_vs_optics_and_front_plate':static,
            'arm_envelope_tests':arm_tests,'coupled_closure_samples':closure,
            'limits':['joint cylinders are outer envelopes, intersections can be conservative false positives',
                      'only listed poses and coupled finger samples tested, not full independent four-dimensional travel',
                      'support brackets, harness, fasteners, real driven mechanism and object contact excluded',
                      'no allowance for assembly tolerance or deformation']}
    dest=ROOT/'docs/engineering/analysis/layout-collision-samples.json'
    dest.write_text(json.dumps(result,indent=2)+'\n')
    for row in arm_tests:
        print('ARM',row['pose'],[(r['a'],r['b'],round(r['common_volume_mm3'],2)) for r in row['pairs'] if r['interferes']])
    print('DRIVE_VS_OPTICS',[(r['a'],r['b'],round(r['common_volume_mm3'],2)) for r in static if r['interferes']])
    for row in closure:
        bad=[(r['a'],r['b'],round(r['common_volume_mm3'],2)) for r in row['pairs'] if r['interferes']]
        if bad:print('CLOSURE',round(row['fraction'],3),bad)
    print('Wrote',dest)


if __name__=='__main__':main()
