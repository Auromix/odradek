# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Exact segment/face occlusion of a nominated target patch in the current CAD.

This is not a calibrated fisheye image simulation. Camera pupils, lens shape,
FOV cropping, optical distortion and missing mechanism parts remain unknown.
"""
import json
import hashlib
from pathlib import Path
import numpy as np
import cadquery as cq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.gp import gp_Lin,gp_Pnt,gp_Dir
from check_layout import finger_transform
from build_layout import moved

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'engineering/generated/layout'


def main():
    p=json.loads((ROOT/'engineering/parameters/r4-layout.json').read_text())
    entries=json.loads((OUT/'manifest.json').read_text())['parts']
    face=np.asarray(p['head']['face_center_mm'],dtype=float);h=p['head'];results=[]
    sources={e['name']:cq.importers.importStep(str(OUT/'parts-step'/f'{e["name"]}.step')).val() for e in entries if e['attachment']==7}
    for state in ['open','grasp_example','closed']:
        intersectors={}
        for e in entries:
            n=e['name']
            if n not in sources:continue
            shape=sources[n]
            if e['finger']:
                f=next(f for f in h['fingers'] if f['id']==e['finger'])
                q=0 if state=='open' else f['pad_target_q_deg'] if state=='grasp_example' else f['closure_study_deg']
                shape=moved(shape,finger_transform(p,f['id'],q))
            intersector=IntCurvesFace_ShapeIntersector();intersector.Load(shape.wrapped,1e-7)
            bb=shape.BoundingBox();bounds=(np.array([bb.xmin,bb.ymin,bb.zmin]),np.array([bb.xmax,bb.ymax,bb.zmax]))
            intersectors[n]=(intersector,bounds)
        camera_rows=[]
        for sign in [1,-1]:
            R=Rotation.from_rotvec([-sign*np.deg2rad(h['camera_outward_pitch_deg']),0,0]).as_matrix()
            # Provisional entrance pupil on the front of the 5 mm lens envelope.
            eye=face+[0,sign*h['camera_baseline_mm']/2,0]+R@np.array([0,0,5.1])
            rays=[]
            for x in np.linspace(-30,30,7):
                for y in np.linspace(-30,30,7):
                    target=face+[x,y,90];vec=target-eye;length=np.linalg.norm(vec);direction=vec/length
                    local=R.T@direction
                    bearing=[float(np.rad2deg(np.arctan2(local[0],local[2]))),float(np.rad2deg(np.arctan2(local[1],local[2])))]
                    line=gp_Lin(gp_Pnt(*eye),gp_Dir(*direction));hits=[]
                    for name,(intersector,(bmin,bmax)) in intersectors.items():
                        if name.startswith(f'CAM_{sign}_'):continue
                        if np.any(np.maximum(eye,target)<bmin) or np.any(np.minimum(eye,target)>bmax):continue
                        intersector.Perform(line,.05,length-.5)
                        if not intersector.IsDone():raise RuntimeError('Failed ray/face intersection')
                        if intersector.NbPnt():
                            hits.append((min(intersector.WParameter(i) for i in range(1,intersector.NbPnt()+1)),name))
                    hits.sort()
                    rays.append({'target_head_mm':[float(x),float(y),90.],
                                 'bearing_horizontal_vertical_deg':bearing,
                                 'occluded':bool(hits),'first_hit':None if not hits else {'part':hits[0][1],'distance_mm':hits[0][0]}})
            camera_rows.append({'camera':'upper' if sign==1 else 'lower','unoccluded_of_49':sum(not r['occluded'] for r in rays),
                                'provisional_pupil_head_mm':(eye-face).tolist(),'rays':rays})
        union=sum(not a['occluded'] or not b['occluded'] for a,b in zip(camera_rows[0]['rays'],camera_rows[1]['rays']))
        both=sum(not a['occluded'] and not b['occluded'] for a,b in zip(camera_rows[0]['rays'],camera_rows[1]['rays']))
        results.append({'state':state,'cameras':camera_rows,'visible_to_at_least_one_of_49':union,'visible_to_both_of_49':both})
    report={'revision':p['revision'],'status':'NOMINAL GEOMETRIC SIGHTLINES ONLY',
            'parameter_sha256':hashlib.sha256((ROOT/'engineering/parameters/r4-layout.json').read_bytes()).hexdigest(),
            'target_patch':'60 x 60 mm square, head z=90 mm; 7 x 7 target points; no physical object solid',
            'camera_pupil':'assumed at front of 5 mm proxy lens, not manufacturer entrance-pupil data',
            'cases':results,'limits':['does not prove actual image coverage, calibration or stereo overlap',
                                    'no fisheye projection, sensitivity, glare or exposure model',
                                    'no real supported motor/bearing/cable/cover CAD yet',
                                    'no occlusion by an actual grasped opaque object',
                                    'three nominated states, not full independent motion sweep']}
    dest=ROOT/'docs/engineering/analysis/optical-sightline-screen.json';dest.write_text(json.dumps(report,indent=2)+'\n')
    fig,axes=plt.subplots(3,3,figsize=(9,9),sharex=True,sharey=True)
    for row,data in enumerate(results):
        ur=data['cameras'][0]['rays'];lr=data['cameras'][1]['rays']
        for col,label in enumerate(['Upper camera','Lower camera','At least one camera']):
            ax=axes[row,col]
            for a,b in zip(ur,lr):
                ok=(not a['occluded']) if col==0 else (not b['occluded']) if col==1 else (not a['occluded'] or not b['occluded'])
                x,y,_=a['target_head_mm'];ax.scatter(x,y,c='#127c80' if ok else '#bd4b36',marker='o' if ok else 'x',s=33)
            ax.set_aspect('equal');ax.set_xlim(-36,36);ax.set_ylim(-36,36);ax.grid(alpha=.15)
            count=data['cameras'][col]['unoccluded_of_49'] if col<2 else data['visible_to_at_least_one_of_49']
            ax.set_title(f'{label}: {count}/49',fontsize=10)
            if col==0:ax.set_ylabel(data['state']+' / y (mm)')
            if row==2:ax.set_xlabel('x (mm)')
    fig.suptitle('Nominal CAD sightlines to a 60 x 60 mm target patch at z=90 mm',fontsize=12)
    fig.text(.5,.015,'Teal: clear segment   Red: proxy geometry obstruction. Not a calibrated image / full-FOV qualification.',ha='center',fontsize=8)
    fig.tight_layout(rect=[0,.035,1,.96]);fig.savefig(dest.with_suffix('.png'),dpi=160);plt.close(fig)
    for row in results:print(row['state'],[(x['camera'],x['unoccluded_of_49']) for x in row['cameras']], 'union',row['visible_to_at_least_one_of_49'],'both',row['visible_to_both_of_49'])


if __name__=='__main__':main()
