# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Independent distal contact-shoe geometry; does not modify R4-layout-03."""
import copy
import hashlib
import json
from itertools import combinations
from pathlib import Path

import cadquery as cq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial import ConvexHull

from build_layout import moved
from certify_petal_separation import trig_min
from finite_pad_contacts import first_contact, closest_lateral
from grasp_screening import solve_grasp

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/contact02-study'


def main():
    pp=ROOT/'engineering/parameters/r4-layout.json';p=copy.deepcopy(json.loads(pp.read_text()))
    p['revision']='R4-CONTACT-02';p['status']='distal contact study; root transmission and pad retention unresolved'
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'parts-step').mkdir(exist_ok=True)
    shapes={};solids={};entries=[];assembly=cq.Assembly(name='R4_CONTACT_02_STUDY')
    face=np.array(p['head']['face_center_mm']);proof=[]
    for i,f in enumerate(p['head']['fingers']):
        # With roots separated by 50 mm, a 150/100 mm pair brings distal
        # contacts closer to one axial level than the earlier 140/100 pair.
        f['length_mm']=150. if i<2 else 100.
        L,W,t=f['length_mm'],f['width_mm'],f['thickness_mm']
        f['closure_study_deg']=109. if i<2 else 122.
        f['contact_along_mm']=L-9.
        f['pad_target_q_deg']=float(np.rad2deg(np.arccos(-30/np.hypot(L-9,11))-np.arctan2(11,L-9)))
        # A six-vertex convex taper ends in a 14 mm flat toe, supporting two
        # 5 mm pads centred at y=+-3.5 mm. Original maximum width stays.
        outline=[(0,-W*.27),(L*.18,-W*.5),(L,-7),(L,7),(L*.18,W*.5),(0,W*.27)]
        body=cq.Workplane('XY').polyline(outline).close().extrude(t).val()
        window=[(L*.13,-W*.24),(L*.24,-W*.36),(L*.72,-W*.20),(L*.94,-W*.08),
                (L*.94,W*.08),(L*.72,W*.20),(L*.24,W*.36),(L*.13,W*.24)]
        light=cq.Workplane('XY').workplane(offset=t).polyline(window).close().extrude(.6).val()
        crop=cq.Workplane('XY').box(L-22,100,30,centered=(False,True,False)).val()
        light=light.intersect(crop)
        parts={'structure':body,'light':light}
        for side in [-1,1]:
            s=L-9.;slope=1/np.tan(np.deg2rad(f['pad_target_q_deg']))
            pad=cq.Workplane('XZ').polyline([(s-9,t),(s+9,t),(s+9,11+9*slope),(s-9,11-9*slope)]).close().extrude(5).translate((0,side*3.5+2.5,0)).val()
            parts['pad_minus' if side<0 else 'pad_plus']=pad
        phi=np.deg2rad(f['phi_deg']);er=np.array([np.cos(phi),np.sin(phi),0.]);et=np.array([-np.sin(phi),np.cos(phi),0.])
        T=np.eye(4);T[:3,:3]=np.column_stack([er,et,[0,0,1.]])
        T[:3,3]=face+f['root_radius_mm']*er+[0,0,f['root_z_mm']]
        shapes[f['id']]={};solids[f['id']]=parts;allv=[]
        for kind,shape in parts.items():
            assert shape.isValid() and len(shape.Solids())==1
            assert all(x.geomType()=='PLANE' for x in shape.Faces())
            v=np.array([x.toTuple() for x in shape.Vertices()])
            assert abs(ConvexHull(v).volume-shape.Volume())<1e-4
            shapes[f['id']][kind]=v;allv.extend(v)
            name=f'{f["id"]}_{kind}';world=moved(shape,T)
            cq.exporters.export(world,str(OUT/'parts-step'/f'{name}.step'))
            color=(.22,.3,.34) if kind=='structure' else ((1.,.65,.2) if kind=='light' else (.22,.55,.49))
            assembly.add(world,name=name,color=cq.Color(*color))
            entries.append({'finger':f['id'],'part':kind,'volume_mm3':shape.Volume(),
                            'world_step':f'parts-step/{name}.step'})
        v=np.asarray(allv);margins=[]
        for axis in [0,1]:
            sign=1 if er[axis]>0 else -1
            A=sign*(f['root_radius_mm']*er[axis]+v[:,1]*et[axis]);B=sign*v[:,0]*er[axis];C=-sign*v[:,2]*er[axis]
            vals=[trig_min(a,b,c,0,np.deg2rad(f['closure_study_deg'])) for a,b,c in zip(A,B,C)]
            index=min(range(len(vals)),key=lambda k:vals[k][0])
            margins.append({'axis':'xy'[axis],'sign':sign,'min_mm':vals[index][0],'q_deg':float(np.rad2deg(vals[index][1]))})
        proof.append({'finger':f['id'],'interval_deg':[0,f['closure_study_deg']],'margins':margins})
    pair_bounds=[]
    for a,b in combinations(proof,2):
        bounds=[ma['min_mm']+mb['min_mm'] for ma,mb in zip(a['margins'],b['margins']) if ma['sign']!=mb['sign']]
        pair_bounds.append({'a':a['finger'],'b':b['finger'],'separating_axis_bound_mm':max(bounds)})
    assembly.save(str(OUT/'contact02-open.step'))
    scenarios=[(d,None) for d in [30,40,50,60,70,80,90,100,110,120]]+[(80.,[115.,155.]),(80.,[95.,125.])]
    cases=[]
    for diameter,zlimits in scenarios:
        details=[];points=[];normals=[];jac=[];groups=[]
        for index,f in enumerate(p['head']['fingers']):
            hits={kind:first_contact(v,f,diameter/2,zlimits) for kind,v in shapes[f['id']].items()}
            pad=hits['pad_minus'];q=pad['q_deg'];pad_first=pad['status']=='contact_bracketed' and all(
                hits[k]['q_deg'] is None or q<hits[k]['q_deg']-1e-6 for k in ['structure','light'])
            clearance={k:closest_lateral(v,f,np.deg2rad(q),zlimits)['radius_mm']-diameter/2
                       for k,v in shapes[f['id']].items()} if q is not None else None
            details.append({'finger':f['id'],'paired_pads_first':pad_first,'components':hits,
                            'radial_clearance_at_pad_first_mm':clearance})
            if pad_first:
                for k in ['pad_minus','pad_plus']:
                    item=hits[k];points.append(np.array(item['point_head_mm'])*.001)
                    normals.append(item['normal_on_object']);jac.append(item['jacobian_m_per_rad']);groups.append(index)
        row={'diameter_mm':diameter,'z_limits_mm':zlimits,'fingers':details,
             'all_four_paired_pads_first':all(d['paired_pads_first'] for d in details)}
        if row['all_four_paired_pads_first'] and not any(d['components']['pad_minus']['at_cylinder_rim'] for d in details):
            com=np.mean(points,axis=0);com[:2]=0
            row['assumed_com_mm']=(com*1000).tolist();row['conditional_grasps']=[]
            for mu in [.3,.4,.6]:
                for cap in [3.,3.7]:
                    row['conditional_grasps'].append({'mu':mu,'cap_Nm':cap,
                        **solve_grasp(points,normals,jac,com,[0,0,-39.2266,0,0,0],mu,[cap]*4,
                                      minimum_normal_N=1.,contact_to_joint=groups)})
        cases.append(row)
    # Separate B-rep check at selected contact poses. This cross-checks the
    # projection method with the exported CAD solids, not just its vertices.
    brep=[]
    for diameter,zlimits in [(30.,None),(80.,None),(120.,None),(80.,[115.,155.])]:
        case=next(c for c in cases if c['diameter_mm']==diameter and c['z_limits_mm']==zlimits)
        lo,hi=zlimits or [-100.,300.]
        obj=cq.Solid.makeCylinder(diameter/2,hi-lo,cq.Vector(0,0,lo),cq.Vector(0,0,1))
        for f,detail in zip(p['head']['fingers'],case['fingers']):
            q=np.deg2rad(detail['components']['pad_minus']['q_deg']);c,s=np.cos(q),np.sin(q)
            T=np.array([[c,0,-s,f['root_radius_mm']],[0,1,0,0],
                        [s,0,c,f['root_z_mm']],[0,0,0,1.]])
            for kind,shape in solids[f['id']].items():
                placed=moved(shape,T);vol=placed.intersect(obj).Volume();dist=placed.distance(obj)
                brep.append({'diameter_mm':diameter,'z_limits_mm':zlimits,'finger':f['id'],
                             'part':kind,'q_deg':float(np.rad2deg(q)),
                             'intersection_mm3':vol,'minimum_distance_mm':dist})
                assert vol<1e-5
                assert dist>0.2 if kind in ['structure','light'] else dist<1e-5
    closed=cq.Assembly(name='CONTACT02_EMPTY_CLOSED')
    for f in p['head']['fingers']:
        phi=np.deg2rad(f['phi_deg']);er=np.array([np.cos(phi),np.sin(phi),0.]);et=np.array([-np.sin(phi),np.cos(phi),0.])
        root=np.eye(4);root[:3,:3]=np.column_stack([er,et,[0,0,1.]])
        root[:3,3]=face+f['root_radius_mm']*er+[0,0,f['root_z_mm']]
        q=np.deg2rad(f['closure_study_deg']);c,s=np.cos(q),np.sin(q)
        rot=np.array([[c,0,-s,0],[0,1,0,0],[s,0,c,0],[0,0,0,1.]])
        for kind,shape in solids[f['id']].items():
            closed.add(moved(shape,root@rot),name=f'{f["id"]}_{kind}')
    closed.save(str(OUT/'contact02-empty-closed.step'))
    result={'revision':p['revision'],'baseline_sha256':hashlib.sha256(pp.read_bytes()).hexdigest(),
            'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'fingers':p['head']['fingers'],'parts':entries,'independent_interval_proof':proof,
            'pair_bounds':pair_bounds,'all_pairs_separated_by_2mm':all(v['separating_axis_bound_mm']>=2 for v in pair_bounds),
            'contact_cases':cases,'independent_brep_crosscheck':brep,'manufacturing_release':False,
            'limits':['changed distal silhouette: 14 mm flat toe, upper length 150 instead of 140, original maximum widths',
                      'root shapes not yet merged with new shaft-support necks',
                      'light is 0.6 mm optical-face placeholder; true PCB stack is not designed here',
                      'pads have no attachment/retention construction or material validation',
                      '1 N minimum per pad and zero self-weight/loss bias remain conditional assumptions',
                      'closure search is sampled bracket plus root, not a continuous object-collision certificate',
                      'no object/head/camera/support or full-arm collision qualification',
                      'contact height changes do not automatically update the main TCP or load model']}
    (OUT/'study.json').write_text(json.dumps(result,indent=2)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(12,6),layout='constrained')
    ax=axes[0]
    for f in p['head']['fingers']:
        phi=np.deg2rad(f['phi_deg']);R=np.array([[np.cos(phi),-np.sin(phi)],[np.sin(phi),np.cos(phi)]])
        for kind,color in [('structure','#536574'),('light','#e6ae41'),('pad_minus','#267f75'),('pad_plus','#267f75')]:
            v=shapes[f['id']][kind];hull=ConvexHull(v[:,:2]);xy=(v[hull.vertices,:2]+[f['root_radius_mm'],0])@R.T
            ax.fill(xy[:,0],xy[:,1],color=color,alpha=.9)
    ax.add_patch(plt.Circle((0,0),31,color='#35434d'));ax.set(aspect='equal',title='Open / distal shoes and trimmed light windows',xlabel='Head x / mm',ylabel='Head y / mm')
    ax=axes[1];case=next(c for c in cases if c['diameter_mm']==80 and c['z_limits_mm'] is None)
    for index,col in [(0,'#b57718'),(2,'#227a84')]:
        f=p['head']['fingers'][index];q=np.deg2rad(case['fingers'][index]['components']['pad_minus']['q_deg']);c,s=np.cos(q),np.sin(q)
        for kind,alpha in [('structure',.3),('pad_minus',.9)]:
            v=shapes[f['id']][kind];rz=np.c_[f['root_radius_mm']+v[:,0]*c-v[:,2]*s,f['root_z_mm']+v[:,0]*s+v[:,2]*c]
            hull=ConvexHull(rz);xy=rz[hull.vertices];ax.fill(xy[:,0],xy[:,1],color=col,alpha=alpha,label=f'{f["id"]} {kind}')
    ax.add_patch(plt.Rectangle((0,115),40,40,facecolor='#ad3f35',alpha=.12));ax.axvline(40,color='#ad3f35',ls='--')
    ax.set(aspect='equal',xlim=(10,90),ylim=(45,165),xlabel='Radial plane r / mm',ylabel='Head z / mm',title='80 mm lateral contact / changed axial position');ax.legend(fontsize=8)
    fig.suptitle('Contact-02 candidate — independent geometry study, not a released mechanism')
    fig.savefig(OUT/'contact02-study.png',dpi=160);plt.close(fig)
    print('Pair separation bounds:',pair_bounds)
    for c in cases:print(c['diameter_mm'],c['z_limits_mm'],c['all_four_paired_pads_first'],
                        [d['components']['pad_minus']['q_deg'] for d in c['fingers']])


if __name__=='__main__':main()
