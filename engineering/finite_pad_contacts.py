# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Finite, rigid paired-pad contact with a coaxial cylindrical lateral surface.

Convex projections are exact for these unchanged convex CAD solids. Closure
search uses sampled brackets, not a continuous collision certificate. Finite
cylinder slabs are checked where specified. No deformation or full head check.
"""
import hashlib
import json
from pathlib import Path

import cadquery as cq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import brentq
from scipy.spatial import ConvexHull, QhullError

from grasp_screening import solve_grasp

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/engineering/analysis'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_vertices(f, face, path):
    """Read actual STEP vertices, then invert the open-pose placement."""
    phi=np.deg2rad(f['phi_deg'])
    er=np.array([np.cos(phi),np.sin(phi),0.])
    et=np.array([-np.sin(phi),np.cos(phi),0.])
    axes=np.column_stack([er,et,[0.,0.,1.]])
    origin=face+f['root_radius_mm']*er+[0,0,f['root_z_mm']]
    shape=cq.importers.importStep(str(path)).val()
    assert shape.isValid() and len(shape.Solids())==1
    vertices=np.array([v.toTuple() for v in shape.Vertices()])
    assert abs(ConvexHull(vertices).volume-shape.Volume())<1e-4, 'Projection method requires convex input solids'
    return (vertices-origin)@axes


def closest_lateral(vertices, f, q, z_limits=None):
    """Return nearest point of the XY projection and one corresponding 3D point."""
    c,s=np.cos(q),np.sin(q)
    rotated=vertices@np.array([[c,0,s],[0,1,0],[-s,0,c]])
    rotated+=np.array([f['root_radius_mm'],0.,f['root_z_mm']])
    if z_limits is not None:
        # These solids are convex. Every true edge is among all vertex pairs;
        # additional diagonal-plane intersections lie inside the same solid.
        # Their convex hull therefore yields the same exact clipped projection.
        lo,hi=z_limits;z=rotated[:,2]
        keep=(z>=lo-1e-10)&(z<=hi+1e-10)
        positions=[rotated[keep]];material=[vertices[keep]]
        ii,jj=np.triu_indices(len(vertices),1);dz=z[jj]-z[ii]
        valid=np.abs(dz)>1e-12;ii,jj,dz=ii[valid],jj[valid],dz[valid]
        for plane in z_limits:
            t=(plane-z[ii])/dz;hit=(t>=0)&(t<=1);t=t[hit,None];i,j=ii[hit],jj[hit]
            positions.append(rotated[i]+t*(rotated[j]-rotated[i]))
            material.append(vertices[i]+t*(vertices[j]-vertices[i]))
        rotated=np.concatenate(positions);vertices=np.concatenate(material)
        if not len(rotated):return {'radius_mm':1e6,'outside_axial_slab':True}
    xy=rotated[:,:2]
    try:
        hull=ConvexHull(xy)
        if np.all(hull.equations[:,-1]<=1e-10):
            return {'radius_mm':0.,'inside_projection':True}
        order=hull.vertices
    except QhullError:
        distances=np.sum((xy[:,None]-xy[None,:])**2,axis=2)
        order=np.array(np.unravel_index(np.argmax(distances),distances.shape))
    best=None
    for i,j in zip(order,np.roll(order,-1)):
        a,b=xy[i],xy[j];d=b-a
        t=float(np.clip(-a@d/(d@d),0,1)) if d@d>1e-24 else 0.;p=a+t*d
        radius=float(np.linalg.norm(p))
        if best is None or radius<best['radius_mm']:
            local=vertices[i]+t*(vertices[j]-vertices[i])
            position=rotated[i]+t*(rotated[j]-rotated[i])
            best={'radius_mm':radius,'local_point_mm':local.tolist(),
                  'radial_frame_point_mm':position.tolist(),'inside_projection':False}
    return best


def first_contact(vertices, f, radius, z_limits=None):
    qgrid=np.linspace(0,np.deg2rad(f['closure_study_deg']),253)
    values=np.array([closest_lateral(vertices,f,q,z_limits)['radius_mm']-radius for q in qgrid])
    if values[0]<=0:
        return {'status':'open_pose_already_intersects','q_deg':0.}
    hit=np.flatnonzero(values<=0)
    if not len(hit):
        return {'status':'not_reached_in_sampled_closure','q_deg':None,
                'minimum_sampled_radius_mm':float(values.min()+radius)}
    i=int(hit[0]);a,b=qgrid[i-1:i+1]
    q=brentq(lambda t:closest_lateral(vertices,f,t,z_limits)['radius_mm']-radius,a,b,xtol=1e-13)
    answer=closest_lateral(vertices,f,q,z_limits)
    answer.update(status='contact_bracketed',q_deg=float(np.rad2deg(q)),
                  search_bracket_deg=np.rad2deg([a,b]).tolist(),
                  radius_residual_mm=float(answer['radius_mm']-radius))
    if abs(answer['radius_residual_mm'])>1e-6:
        answer['status']='axial_cap_entry_not_lateral_contact'
        return answer
    phi=np.deg2rad(f['phi_deg']);er=np.array([np.cos(phi),np.sin(phi),0.])
    et=np.array([-np.sin(phi),np.cos(phi),0.]);ez=np.array([0.,0.,1.])
    r,y,z=answer['radial_frame_point_mm'];x,_,h=answer['local_point_mm']
    answer['point_head_mm']=(r*er+y*et+z*ez).tolist()
    answer['normal_on_object']=(-(r*er+y*et)/radius).tolist()
    answer['jacobian_m_per_rad']=(((-x*np.sin(q)-h*np.cos(q))*er+
                                  (x*np.cos(q)-h*np.sin(q))*ez)*.001).tolist()
    answer['face_alignment_error_deg']=float(np.rad2deg(q)-f['pad_target_q_deg'])
    answer['at_cylinder_rim']=bool(z_limits is not None and min(abs(z-v) for v in z_limits)<1e-6)
    return answer


def grouped_contact_regression():
    # Splitting every one of four point contacts into two coincident contacts
    # must preserve total normal and shared actuator constraints.
    phi=np.deg2rad([35,145,225,315]);er=np.c_[np.cos(phi),np.sin(phi),np.zeros(4)]
    points=.04*er;normals=-er;J=-np.array([.09,.09,.07,.07])[:,None]*er
    kwargs=dict(com=[0,0,0],wrench=[0,0,-39.2266,0,0,0],mu=.4,torque_limit=[3.7]*4)
    a=solve_grasp(points,normals,J,**kwargs)
    b=solve_grasp(np.repeat(points,2,axis=0),np.repeat(normals,2,axis=0),
                  np.repeat(J,2,axis=0),contact_to_joint=np.repeat(np.arange(4),2),**kwargs)
    assert a['feasible'] and b['feasible']
    normal_error=abs(a['normal_total_N']-b['normal_total_N'])
    torque_error=float(np.max(np.abs(np.array(a['finger_joint_equilibrium_Nm'])-
                                     b['finger_joint_equilibrium_Nm'])))
    assert normal_error<1e-7 and torque_error<1e-7
    assert not solve_grasp(np.repeat(points,2,axis=0),np.repeat(normals,2,axis=0),
                          np.repeat(J,2,axis=0),contact_to_joint=np.repeat(np.arange(4),2),
                          **{**kwargs,'torque_limit':[.1]*4})['feasible']
    return {'split_contact_normal_error_N':normal_error,'shared_torque_error_Nm':torque_error,
            'shared_small_torque_cap_rejected':True}


def boolean_counterexamples(p,cases):
    """Independent BREP intersections for the lower-left pad-contact pose."""
    out=[];face=np.asarray(p['head']['face_center_mm']);f=p['head']['fingers'][2]
    phi=np.deg2rad(f['phi_deg']);er=np.array([np.cos(phi),np.sin(phi),0.])
    axis=np.array([np.sin(phi),-np.cos(phi),0.])
    root=face+f['root_radius_mm']*er+[0,0,f['root_z_mm']]
    for case in cases:
        if case['cylinder_diameter_mm']!=80:continue
        q=case['fingers'][2]['components']['pad_minus']['q_deg']
        lo,hi=case['cylinder_z_limits_head_mm'] or [-100.,300.]
        cylinder=cq.Solid.makeCylinder(40.,hi-lo,cq.Vector(*(face+[0,0,lo])),cq.Vector(0,0,1))
        volumes={}
        for kind,suffix in [('structure','structure'),('light','light'),('pad_minus','pad_-1')]:
            shape=cq.importers.importStep(str(ROOT/f'engineering/generated/layout/parts-step/F_LL_{suffix}.step')).val()
            rotated=shape.rotate(tuple(root),tuple(root+axis),q)
            volumes[kind]=sum(a.intersect(b).Volume() for a in rotated.Solids() for b in cylinder.Solids())
        assert volumes['pad_minus']<1e-5
        assert max(volumes['structure'],volumes['light'])>1e-7
        out.append({'finger':'LL','q_deg':q,'cylinder_diameter_mm':80.,'cylinder_z_limits_head_mm':[lo,hi],
                    'intersection_volume_mm3':volumes,'result':'pad pose obstructed by structure or light'})
    return out


def main():
    pp=ROOT/'engineering/parameters/r4-layout.json';p=json.loads(pp.read_text())
    manifest=ROOT/'engineering/generated/layout/manifest.json'
    assert json.loads(manifest.read_text())['parameters_sha256']==digest(pp)
    source_hashes={str(pp.relative_to(ROOT)):digest(pp),str(manifest.relative_to(ROOT)):digest(manifest)}
    face=np.array(p['head']['face_center_mm']);fs=p['head']['fingers'];shapes={}
    for f in fs:
        shapes[f['id']]={}
        for kind,suffix in [('structure','structure'),('light','light'),('pad_minus','pad_-1'),('pad_plus','pad_1')]:
            path=ROOT/f'engineering/generated/layout/parts-step/F_{f["id"]}_{suffix}.step'
            source_hashes[str(path.relative_to(ROOT))]=digest(path)
            shapes[f['id']][kind]=local_vertices(f,face,path)
    cases=[]
    scenarios=[(d,None) for d in [30,40,50,60,70,80,90,100,110,120]]
    scenarios += [(d,z) for z in [(80.,140.),(95.,125.)] for d in [40,60,80,100]]
    for diameter,z_limits in scenarios:
        fingers=[];points=[];normals=[];J=[];groups=[]
        for index,f in enumerate(fs):
            contacts={k:first_contact(v,f,diameter/2,z_limits) for k,v in shapes[f['id']].items()}
            finite=[(v['q_deg'],k) for k,v in contacts.items() if v['q_deg'] is not None]
            order=sorted(finite)
            padq=contacts['pad_minus']['q_deg']
            pad_first=padq is not None and contacts['pad_minus']['status']=='contact_bracketed' and all(
                contacts[k]['q_deg'] is None or padq<contacts[k]['q_deg']-1e-6 for k in ['structure','light'])
            fingers.append({'id':f['id'],'first_kind':order[0][1] if order else None,
                            'paired_pads_first':pad_first,'components':contacts})
            if pad_first:
                assert abs(contacts['pad_plus']['q_deg']-padq)<1e-6
                for k in ['pad_minus','pad_plus']:
                    x=contacts[k];points.append(np.array(x['point_head_mm'])*.001)
                    normals.append(x['normal_on_object']);J.append(x['jacobian_m_per_rad']);groups.append(index)
        answer={'cylinder_diameter_mm':diameter,'fingers':fingers,
                'cylinder_z_limits_head_mm':z_limits,
                'all_four_paired_pads_first':all(x['paired_pads_first'] for x in fingers)}
        if answer['all_four_paired_pads_first'] and not any(
                x['components']['pad_minus']['at_cylinder_rim'] for x in fingers):
            zs=np.array(points)[:,2];com=[0.,0.,float(np.mean(zs))]
            answer['contact_z_span_mm']=(zs*1000).tolist()
            answer['assumed_object_com_head_m']=com
            answer['conditional_grasps']=[]
            for mu in [.3,.4,.6]:
                for cap in [3.,3.7]:
                    for factor in [1.,2.]:
                        answer['conditional_grasps'].append({'mu':mu,'torque_cap_Nm':cap,'load_factor':factor,
                            **solve_grasp(points,normals,J,com,[0,0,-2*9.80665*factor,0,0,0],mu,[cap]*4,
                                          minimum_normal_N=1.,contact_to_joint=groups)})
        cases.append(answer)
    regression=grouped_contact_regression()
    # Independent local contact derivative check, holding the same material
    # point fixed (not differentiating the moving support point selection).
    maxerr=0.
    for f in fs:
        v=first_contact(shapes[f['id']]['pad_minus'],f,40.)
        q=np.deg2rad(v['q_deg']);x,y,h=v['local_point_mm'];phi=np.deg2rad(f['phi_deg'])
        er=np.array([np.cos(phi),np.sin(phi),0.]);et=np.array([-np.sin(phi),np.cos(phi),0.])
        def point(t):
            return ((f['root_radius_mm']+x*np.cos(t)-h*np.sin(t))*er+y*et+
                    [0,0,f['root_z_mm']+x*np.sin(t)+h*np.cos(t)])*.001
        fd=(point(q+1e-6)-point(q-1e-6))/2e-6
        maxerr=max(maxerr,float(np.max(np.abs(fd-v['jacobian_m_per_rad']))))
    assert maxerr<1e-9
    regression['contact_jacobian_max_error_m_per_rad']=maxerr
    counterexamples=boolean_counterexamples(p,cases)
    report={'revision':'R4-FINITE-PAD-01','parameter_revision':p['revision'],
            'status':'rigid CAD lateral-contact screening; not a grasp qualification',
            'input_sha256':source_hashes,'script_sha256':digest(Path(__file__)),
            'solver_sha256':digest(ROOT/'engineering/grasp_screening.py'),
            'search':'253 uniform angle nodes per component; Brent solve in first crossing bracket',
            'contact_model':'8 unilateral point contacts at finite pad supports; two contacts share each finger torque cap',
            'regression':regression,'brep_counterexamples':counterexamples,'cases':cases,
            'limitations':['coaxial cylinder only; finite axial clipping included where bounds stated; no complete head collision',
                           'cylinder-rim and axial-cap contacts are not fed into the lateral-normal grasp model',
                           'fixed pads use inner edges and often longitudinal corners, not full-area contact',
                           'rigid support point is ill-conditioned near exactly parallel face/cylinder generatrix',
                           'normal force >=1 N per pad is an imposed active-contact assumption, not observed preload',
                           'zero finger self-weight, friction and transmission-loss bias; no motor thermal rating',
                           'COM is assumed at mean contact height, not a measured object COM',
                           '3.0 and 3.7 Nm are comparison caps; neither qualifies the bevel transmission',
                           'unchanged CAD convex solids only; new pockets/supports require regeneration',
                           'sampled bracket search is not a continuous first-collision certificate']}
    OUT.mkdir(exist_ok=True)
    (OUT/'finite-pad-contacts.json').write_text(json.dumps(report,indent=2)+'\n')
    fig,axes=plt.subplots(1,3,figsize=(14,4.5),layout='constrained')
    for index,label,color in [(0,'Upper','#b57718'),(2,'Lower','#227a84')]:
        infinite=[c for c in cases if c['cylinder_z_limits_head_mm'] is None]
        d=np.array([c['cylinder_diameter_mm'] for c in infinite])
        contact=[c['fingers'][index]['components']['pad_minus'] for c in infinite]
        q=[x['q_deg'] if x['q_deg'] is not None else np.nan for x in contact]
        z=[x.get('radial_frame_point_mm',[0,0,np.nan])[2] for x in contact]
        angle=[x.get('face_alignment_error_deg',np.nan) for x in contact]
        for ax,data in zip(axes,[q,z,angle]):ax.plot(d,data,'o-',label=label,color=color)
    for ax,title,unit in zip(axes,['Pad contact closure','Actual contact height','Face alignment to design pose'],['q / degrees','z in head frame / mm','q - q_target / degrees']):
        ax.set(title=title,xlabel='Coaxial cylinder diameter / mm',ylabel=unit);ax.grid(alpha=.2);ax.legend()
    fig.suptitle('R4 finite paired-pad study — rigid lateral contacts, not a payload rating')
    fig.savefig(OUT/'finite-pad-contacts.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,6),layout='constrained')
    for ax,f in zip(axes,[fs[0],fs[2]]):
        q=np.deg2rad(f['pad_target_q_deg']);c,s=np.cos(q),np.sin(q)
        for kind,color in [('structure','#536574'),('light','#e6ae41'),('pad_minus','#267f75')]:
            v=shapes[f['id']][kind];rz=np.c_[f['root_radius_mm']+v[:,0]*c-v[:,2]*s,
                                             f['root_z_mm']+v[:,0]*s+v[:,2]*c]
            hull=ConvexHull(rz);xy=rz[hull.vertices];ax.fill(xy[:,0],xy[:,1],color=color,alpha=.75,label=kind)
        ax.add_patch(plt.Rectangle((0,80),40,60,facecolor='#ad3f35',alpha=.15,edgecolor='#ad3f35',label='80 mm cylinder / 60 mm long'))
        ax.axvline(40,color='#ad3f35',ls='--',lw=1)
        ax.set(title=f'{f["id"]}: nominal q = {f["pad_target_q_deg"]:.3f} deg',
               xlabel='Radial-plane coordinate r / mm',ylabel='Head z / mm',xlim=(10,85),ylim=(45,165),aspect='equal')
        ax.legend(fontsize=8,loc='lower left');ax.grid(alpha=.15)
    fig.suptitle('Current nominal grasp pose: finite solids obstruct the assumed 80 mm contact\nMeridional projections; BREP intersection volumes are recorded separately')
    fig.savefig(OUT/'finite-pad-obstruction.png',dpi=160);plt.close(fig)
    print(json.dumps({'regression':regression,'cases':[{'diameter':x['cylinder_diameter_mm'],
                      'pads_first':x['all_four_paired_pads_first'],
                      'z_limits':x['cylinder_z_limits_head_mm'],
                      'q':[f['components']['pad_minus']['q_deg'] for f in x['fingers']],
                      'first':[f['first_kind'] for f in x['fingers']]} for x in cases]},indent=2))


if __name__=='__main__':main()
