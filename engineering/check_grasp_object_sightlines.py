# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""CONTACT-02 nominal camera rays, including an opaque finite workpiece."""
from pathlib import Path
import json,hashlib
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

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/contact02-sightlines'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    params=ROOT/'engineering/parameters/r4-layout.json';cp=ROOT/'engineering/generated/contact02-study/study.json'
    p=json.loads(params.read_text());contact=json.loads(cp.read_text());face=np.asarray(p['head']['face_center_mm'],float)
    case=next(c for c in contact['contact_cases'] if c['diameter_mm']==80 and c['z_limits_mm']==[115.,155.])
    assert case['all_four_paired_pads_first']
    manifest=ROOT/'engineering/generated/layout/manifest.json';entries=json.loads(manifest.read_text())['parts']
    common={}
    for e in entries:
        if e['attachment']==7 and not e['finger']:
            path=ROOT/'engineering/generated/layout/parts-step'/f'{e["name"]}.step'
            common[e['name']]=cq.importers.importStep(str(path)).val()
    object_=cq.Solid.makeCylinder(40,40,cq.Vector(*(face+[0,0,115.])),cq.Vector(0,0,1))
    common['WORKPIECE_OPAQUE_80x40']=object_
    targets=[]
    for x in np.linspace(-30,30,7):
        for y in np.linspace(-30,30,7):targets.append({'id':f'rear_cap_{x:g}_{y:g}','kind':'near_cap','head_mm':[float(x),float(y),115.]})
    # 60x60 square corners (r=42.4) are outside the 80mm cap; omit them explicitly.
    targets=[t for t in targets if np.linalg.norm(t['head_mm'][:2])<39.]
    for detail in case['fingers']:
        for k in ['pad_minus','pad_plus']:
            targets.append({'id':detail['finger']+'_'+k,'kind':'actual_pad_contact','head_mm':detail['components'][k]['point_head_mm']})
    rows=[]
    for state in ['pregrasp_open','contact_pose']:
        shapes=dict(common)
        for detail in case['fingers']:
            for part in ['structure','light','pad_minus','pad_plus']:
                name=detail['finger']+'_'+part
                path=cp.parent/'parts-step'/f'{name}.step';shape=cq.importers.importStep(str(path)).val()
                if state=='contact_pose':shape=moved(shape,finger_transform(p,detail['finger'],detail['components']['pad_minus']['q_deg']))
                shapes[name]=shape
        intersectors={}
        for name,shape in shapes.items():
            it=IntCurvesFace_ShapeIntersector();it.Load(shape.wrapped,1e-7)
            bb=shape.BoundingBox();intersectors[name]=(it,np.array([bb.xmin,bb.ymin,bb.zmin]),np.array([bb.xmax,bb.ymax,bb.zmax]))
        cameras=[]
        for sign in [1,-1]:
            R=Rotation.from_rotvec([-sign*np.deg2rad(p['head']['camera_outward_pitch_deg']),0,0]).as_matrix()
            eye=face+[0,sign*p['head']['camera_baseline_mm']/2,0]+R@np.array([0,0,5.1])
            rays=[]
            for t in targets:
                target=face+np.array(t['head_mm']);vec=target-eye;length=np.linalg.norm(vec);direction=vec/length
                local=R.T@direction;halfangle=np.rad2deg(np.arctan2(np.linalg.norm(local[:2]),local[2]))
                hits=[];line=gp_Lin(gp_Pnt(*eye),gp_Dir(*direction))
                for name,(it,bmin,bmax) in intersectors.items():
                    if name.startswith(f'CAM_{sign}_'):continue
                    if np.any(np.maximum(eye,target)<bmin) or np.any(np.minimum(eye,target)>bmax):continue
                    it.Perform(line,.05,length-.01)
                    assert it.IsDone()
                    if it.NbPnt():hits.append((min(it.WParameter(i) for i in range(1,it.NbPnt()+1)),name))
                hits.sort()
                normal=np.array(t['head_mm']);normal[2]=0
                outward_facing=None
                if t['kind']=='actual_pad_contact':outward_facing=float((eye-face-np.array(t['head_mm']))@normal/40.)
                rays.append({**t,'clear_segment':not bool(hits),'required_half_angle_deg':float(halfangle),
                             'camera_dot_outward_normal_mm':outward_facing,
                             'hits_before_target':[{'distance_mm':float(h[0]),'part':h[1]} for h in hits]})
            cameras.append({'id':'upper' if sign==1 else 'lower','pupil_head_mm':(eye-face).tolist(),'rays':rays})
        summary={}
        for kind in ['near_cap','actual_pad_contact']:
            both=[(u,l) for u,l in zip(cameras[0]['rays'],cameras[1]['rays']) if u['kind']==kind]
            summary[kind]={'count':len(both),'upper_clear':sum(u['clear_segment'] for u,l in both),
                'lower_clear':sum(l['clear_segment'] for u,l in both),
                'union_clear':sum(u['clear_segment'] or l['clear_segment'] for u,l in both),
                'both_clear':sum(u['clear_segment'] and l['clear_segment'] for u,l in both)}
        rows.append({'state':state,'cameras':cameras,'summary':summary})
    assert len(targets)==53
    # Independent convex-object normal test: a side point whose outward normal
    # faces away from both pupils cannot be directly visible through the object.
    contact_rays=[r for c in rows[-1]['cameras'] for r in c['rays'] if r['kind']=='actual_pad_contact']
    assert all(r['camera_dot_outward_normal_mm']<0 and not r['clear_segment'] for r in contact_rays)
    assert all(any(h['part']=='WORKPIECE_OPAQUE_80x40' for h in r['hits_before_target']) for r in contact_rays)
    result={'revision':'CONTACT-02-OPTICS-01','status':'nominal straight-ray geometry; not calibrated fisheye visibility',
        'inputs_sha256':{str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [params,cp,manifest,Path(__file__)]},
        'object':{'diameter_mm':80,'z_limits_mm':[115,155],'opaque':True},
        'cases':rows,'independent_convex_normal_test_passed':True,
        'limits':['lens pupils are provisional at front of a 5mm proxy, not manufacturer entrance-pupil data',
                  'camera pitch 8deg and baseline100mm unchanged',
                  'ray bearing is not a fisheye calibration or guaranteed cropped image field',
                  'support03, candidate linear-drive hardware, shell and harness not included',
                  'target grids are finite samples at two poses, not continuous task coverage',
                  'viewing the object cap does not imply direct visibility of its side contact patches',
                  'no transparency, deformation, reflection, exposure or dynamic blur model'],
        'manufacturing_release':False}
    (OUT/'study.json').write_text(json.dumps(result,indent=2)+'\n')
    fig,axes=plt.subplots(2,3,figsize=(12,8),layout='constrained')
    for row,data in enumerate(rows):
        for col,label in enumerate(['Upper','Lower','Either camera']):
            ax=axes[row,col];ax.add_patch(plt.Circle((0,0),40,fill=False,color='#bec8ce'))
            for u,l in zip(data['cameras'][0]['rays'],data['cameras'][1]['rays']):
                okay=u['clear_segment'] if col==0 else l['clear_segment'] if col==1 else u['clear_segment'] or l['clear_segment']
                ax.scatter(*u['head_mm'][:2],color='#177f80' if okay else '#b94839',marker='o' if u['kind']=='near_cap' else 'X',s=28 if u['kind']=='near_cap' else 70)
            sm=data['summary'];counts=[sm['near_cap']['upper_clear'],sm['near_cap']['lower_clear'],sm['near_cap']['union_clear']]
            ax.set(aspect='equal',xlim=(-46,46),ylim=(-46,46),title=f'{label}: cap {counts[col]}/45; contacts 0/8',xlabel='Head x / mm',ylabel=data['state']+' / y mm');ax.grid(alpha=.15)
    fig.suptitle('80 mm opaque workpiece / contact locations need more than direct camera sight',fontsize=13)
    fig.savefig(OUT/'object-sightlines.png',dpi=150);plt.close(fig)
    print(json.dumps([{'state':r['state'],'summary':r['summary']} for r in rows],indent=2))

if __name__=='__main__':main()
