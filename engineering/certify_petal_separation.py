# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Analytic quadrant-separation certificate for current rigid polygonal petals.

Minimize every CAD vertex coordinate A+B*cos(q)+C*sin(q) analytically over
the whole angular interval. Each polygonal solid is inside its convex hull;
positive quadrant margins separate ALL independent configurations without
sampling. Curved replacement parts invalidate this vertex-only method.
It excludes the stationary mechanism, tolerance, compliance and workpieces.
"""
import json
import math
import hashlib
from itertools import combinations
from pathlib import Path
import cadquery as cq
import numpy as np
from check_layout import finger_transform

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/layout'


def trig_min(A,B,C,lo,hi):
    candidates=[lo,hi]
    phase=math.atan2(C,B)
    for k in range(math.ceil((lo-phase)/math.pi),math.floor((hi-phase)/math.pi)+1):
        q=phase+k*math.pi
        if lo<=q<=hi:candidates.append(q)
    q=min(candidates,key=lambda q:A+B*math.cos(q)+C*math.sin(q))
    return A+B*math.cos(q)+C*math.sin(q),q


def main():
    p=json.loads((ROOT/'engineering/parameters/r4-layout.json').read_text())
    entries=json.loads((OUT/'manifest.json').read_text())['parts']
    assert json.loads((OUT/'manifest.json').read_text())['revision']==p['revision']
    result=[]
    for f in p['head']['fingers']:
        # Extract exact B-rep prism vertices, not mesh/bevel approximations.
        vertices=[];names=[]
        for e in entries:
            if e['finger']!=f['id']:continue
            shape=cq.importers.importStep(str(OUT/'parts-step'/f'{e["name"]}.step')).val()
            if any(face.geomType()!='PLANE' for face in shape.Faces()):
                raise ValueError('Vertex bound only justified for plane-faced solids')
            vertices.extend([v.toTuple() for v in shape.Vertices()]);names.append(e['name'])
        V=np.c_[vertices,np.ones(len(vertices))].T
        positions=[(finger_transform(p,f['id'],deg)@V)[:3].T for deg in [0,90,180]]
        A=(positions[0]+positions[2])/2
        B=(positions[0]-positions[2])/2
        C=positions[1]-A
        A-=np.asarray(p['head']['face_center_mm'])
        phi=math.radians(f['phi_deg']);signs=[1 if math.cos(phi)>0 else -1,1 if math.sin(phi)>0 else -1]
        margins=[]
        for axis,sign in enumerate(signs):
            candidates=[(*trig_min(sign*A[i,axis],sign*B[i,axis],sign*C[i,axis],0,math.radians(f['closure_study_deg'])),i) for i in range(len(vertices))]
            margin,q,i=min(candidates,key=lambda x:x[0])
            margins.append({'axis':'xy'[axis],'side_sign':sign,'minimum_signed_coordinate_mm':margin,
                            'worst_q_deg':math.degrees(q),'home_vertex_mm':vertices[i]})
        result.append({'finger':f['id'],'interval_deg':[0,f['closure_study_deg']],
                       'parts':names,'planar_vertex_count':len(vertices),'quadrant_margins':margins})
    pair_bounds=[]
    for a,b in combinations(result,2):
        separating=[]
        for ma,mb in zip(a['quadrant_margins'],b['quadrant_margins']):
            if ma['side_sign']!=mb['side_sign']:
                separating.append({'axis':ma['axis'],'lower_bound_mm':ma['minimum_signed_coordinate_mm']+mb['minimum_signed_coordinate_mm']})
        best=max(separating,key=lambda x:x['lower_bound_mm'])
        pair_bounds.append({'a':a['finger'],'b':b['finger'],'best_axis_certificate':best,
                            'nominal_2mm_separation_proven':bool(best['lower_bound_mm']>=2)})
    # Independent self-check of analytic scalar minimizer against dense samples.
    rng=np.random.default_rng(104)
    for _ in range(100):
        A,B,C=rng.normal(size=3);hi=rng.uniform(.01,math.pi)
        m,q=trig_min(A,B,C,0,hi);dense=np.min(A+B*np.cos(np.linspace(0,hi,10001))+C*np.sin(np.linspace(0,hi,10001)))
        assert -1e-10<=dense-m<1e-7
    report={'revision':p['revision'],'status':'ANALYTIC NOMINAL PETAL-TO-PETAL SEPARATION ONLY',
            'input_sha256':{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in [ROOT/'engineering/parameters/r4-layout.json',OUT/'manifest.json',*[OUT/'parts-step'/f'{e["name"]}.step' for e in entries if e['finger']]]},
            'proof_method':'coordinate extrema of every exact planar-solid vertex over independent intervals',
            'fingers':result,'pair_bounds':pair_bounds,
            'all_six_pairs_separated_by_2mm':all(x['nominal_2mm_separation_proven'] for x in pair_bounds),
            'excludes':['stationary head, cameras, belts, shafts, supports, cable motion',
                        'manufacturing tolerance, fillet changes, flexure, wear and objects',
                        'gripping efficacy or a sealed shell'],
            'minimizer_self_check_count':100}
    out=ROOT/'docs/engineering/analysis/petal-separation-certificate.json'
    out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='fingers'},indent=2))


if __name__=='__main__':main()
