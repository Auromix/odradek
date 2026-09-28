# SPDX-License-Identifier: CC-BY-NC-4.0
# Attribution: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""R5-BODY01: separate bare-arm gravity from a parameterized new head.

Read-only upstream model; all outputs in generated/r5-body01. Sobol samples and
local optimization are mathematical configurations, not collision certificates.
"""
from pathlib import Path
import copy
import csv
import hashlib
import json
import math

import numpy as np
from scipy.optimize import minimize
from scipy.spatial import ConvexHull
from scipy.stats import qmc
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from kinematics import Arm

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "engineering/generated/r5-body01"
GRAVITY = np.array([0., 0., -9.80665])


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def write(name, obj): (OUT/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2)+"\n")


def csvout(name, rows):
    with (OUT/name).open("w", newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def transforms(joints, qs):
    """Independent batch Rodrigues implementation, positions in metres."""
    qs=np.atleast_2d(qs);n=len(qs)
    ts=np.broadcast_to(np.eye(4),(n,8,4,4)).copy()
    origins=np.empty((n,7,3));axes=np.empty_like(origins)
    for i,j in enumerate(joints):
        a=np.array(j['axis'],float);p=np.array(j['origin_m'])
        origins[:,i]=np.einsum('nij,j->ni',ts[:,i,:3,:3],p)+ts[:,i,:3,3]
        axes[:,i]=np.einsum('nij,j->ni',ts[:,i,:3,:3],a)
        x,y,z=a;sk=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
        c=np.cos(qs[:,i])[:,None,None];s=np.sin(qs[:,i])[:,None,None]
        r=c*np.eye(3)+(1-c)*np.outer(a,a)+s*sk
        step=np.broadcast_to(np.eye(4),(n,4,4)).copy();step[:,:3,:3]=r
        step[:,:3,3]=np.einsum('nij,j->ni',np.eye(3)-r,p)
        ts[:,i+1]=ts[:,i]@step
    return ts,origins,axes


def effort(joints,bodies,qs,cache=None):
    ts,origins,axes=transforms(joints,qs) if cache is None else cache
    answer=np.zeros((len(ts),7));base_moment=np.zeros((len(ts),3))
    for b in bodies:
        n=b['preceding_joints'];mass=b['mass_kg']
        p=np.einsum('nij,j->ni',ts[:,n,:3,:3],b['com_home_m'])+ts[:,n,:3,3]
        if n:
            m=np.cross(p[:,None,:]-origins[:,:n],mass*GRAVITY)
            answer[:,:n]-=np.einsum('nij,nij->ni',axes[:,:n],m)
        base_moment+=np.cross(p-origins[:,0],mass*GRAVITY)
    return answer,base_moment


def pointbody(name,mass,point,n=7):
    return dict(id=name,mass_kg=mass,preceding_joints=n,com_home_m=list(point),
                orientation_home=np.eye(3).tolist(),inertia_com_kg_m2=np.zeros((3,3)).tolist())


def aggregate_by_attachment(bodies):
    """Exact for gravity only; inertia not transferred into this acceleration helper."""
    out=[]
    for n in range(8):
        group=[b for b in bodies if b['preceding_joints']==n]
        if group:
            m=sum(b['mass_kg'] for b in group)
            p=sum(b['mass_kg']*np.array(b['com_home_m']) for b in group)/m
            out.append(pointbody('gravity_attachment_'+str(n),m,p,n))
    return out


def triangle(joints,bodies):
    bound=np.zeros(7)
    for b in bodies:
        n=b['preceding_joints']
        if not n:continue
        pts=np.array([j['origin_m'] for j in joints[:n]]+[b['com_home_m']])
        radii=np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1)[::-1])[::-1]
        bound[:n]+=b['mass_kg']*np.linalg.norm(GRAVITY)*radii
    bound[0]=0. # fixed vertical axis; gravity creates no yaw effort
    # Every downstream point lies on J7's home axis in this on-axis sweep.
    o=np.array(joints[6]['origin_m']);a=np.array(joints[6]['axis'])
    if all(np.linalg.norm(np.cross(np.array(b['com_home_m'])-o,a))<1e-12
           for b in bodies if b['preceding_joints']==7):bound[6]=0.
    return bound


def refine(joints,bodies,seeds,which):
    # q1 yaw is gravity invariant; q7 moves only on-axis points here.
    bounds=np.deg2rad([j['limit_deg'] for j in joints[1:6]])
    aggregate=aggregate_by_attachment(bodies)
    best=(-1.,None)
    for seed in seeds:
        for sign in (-1,1):
            def fun(x):
                q=np.r_[0.,x,0.]
                return -sign*effort(joints,aggregate,q)[0][0,which]
            sol=minimize(fun,seed[1:6],method='L-BFGS-B',bounds=bounds,
                         options=dict(maxiter=150,ftol=1e-13,gtol=1e-8))
            val=abs(effort(joints,aggregate,np.r_[0.,sol.x,0.])[0][0,which])
            if val>best[0]:best=(float(val),np.r_[0.,sol.x,0.])
    return {'best_found_abs_Nm':best[0],'q_deg':np.rad2deg(best[1]).tolist(),
            'global_optimum_certified':False}


def cylinder_projection(j,projection,ts=None):
    axis=np.array(j['axis'],float);p=np.array(j['origin_m'])*1000
    v=np.array([1.,0,0]);v-=axis*(v@axis);v/=np.linalg.norm(v)
    w=np.cross(axis,v);theta=np.linspace(0,2*np.pi,80,endpoint=False)
    rim=(np.cos(theta)[:,None]*v+np.sin(theta)[:,None]*w)*j['diameter_mm']/2
    pts=np.vstack([rim+p+axis*2,rim+p-axis*(j['length_mm']-2)])
    if ts is not None:pts=pts@ts[:3,:3].T+ts[:3,3]*1000
    xy=pts[:,projection];return xy[ConvexHull(xy).vertices]


def drawings(joints,results,poses,body_mass):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'svg.fonttype':'none'})
    colors=['#35616b','#d4a04c','#497c86','#cf884e','#568fa0','#c3945e','#738ea3']
    fig=plt.figure(figsize=(15,10),layout='constrained')
    grid=fig.add_gridspec(2,3,height_ratios=[3,1.4])
    for k,(view,proj) in enumerate([('Front X-Z',(0,2)),('Side Y-Z',(1,2)),('Top X-Y',(0,1))]):
        ax=fig.add_subplot(grid[0,k])
        for i,j in enumerate(joints):
            xy=cylinder_projection(j,proj);ax.add_patch(Polygon(xy,facecolor=colors[i],alpha=.23,edgecolor=colors[i]))
            p=np.array(j['origin_mm']);ax.plot(*p[list(proj)],'o',color=colors[i],ms=5)
            if k != 2:ax.annotate(j['id'],p[list(proj)],xytext=(8,5+3*(i%2)),textcoords='offset points',color=colors[i])
        if k == 2:
            for xy,label,dy in [([0,0],'J1/J2/J4/J6',-17),([0,55],'J3/J7',8),([0,-55],'J5',-17)]:
                ax.annotate(label,xy,xytext=(9,dy),textcoords='offset points',fontsize=8)
        pts=np.array([j['origin_mm'] for j in joints]);ax.plot(pts[:,proj[0]],pts[:,proj[1]],'-',color='#284953',lw=1)
        flange=pts[-1];tcp=flange+np.array([0,0,150])
        ax.plot([flange[proj[0]],tcp[proj[0]]],[flange[proj[1]],tcp[proj[1]]],'--',color='#a45446')
        ax.plot(*tcp[list(proj)],'x',color='#a45446',ms=8)
        if 2 in proj:ax.annotate('TCP +150 (scenario)',tcp[list(proj)],xytext=(12,0),textcoords='offset points',fontsize=8)
        ax.set_aspect('equal');ax.autoscale_view();ax.margins(.28,.08);ax.grid(alpha=.15)
        ax.set_title(view+' / zero configuration');ax.set_xlabel('XYZ'[proj[0]]+' / mm');ax.set_ylabel('XYZ'[proj[1]]+' / mm')
    ax=fig.add_subplot(grid[1,:]);ax.axis('off')
    table=[]
    for j in joints:table.append([j['id'],j['model'],str(j['origin_mm']),str(j['axis']),f"{j['diameter_mm']} x {j['length_mm']}",j['bore_mm'],j['mass_kg']])
    tab=ax.table(cellText=table,colLabels=['Axis','Module','Output plane origin [X,Y,Z] mm','Home axis','OD x length / mm','Bore mm','Catalog kg'],loc='center',cellLoc='center',colWidths=[.06,.1,.25,.15,.16,.12,.12])
    tab.auto_set_font_size(False);tab.set_fontsize(9);tab.scale(1,1.6)
    fig.suptitle('R5-BODY01 | Bare 7-axis datums; RAISE03 shoulder already at Z205 mm\nCatalog cylinders, not OEM contours or manufacturing interfaces. No extra +35 mm. Head excluded.',fontsize=12)
    for ext in ['svg','png']:fig.savefig(OUT/('body-datums.'+ext),dpi=170,bbox_inches='tight')
    plt.close(fig)
    fig,axs=plt.subplots(1,3,figsize=(15,7),layout='constrained')
    for ax,(label,angles) in zip(axs,poses.items()):
        ts,origins,_=transforms(joints,np.deg2rad(angles));pp=origins[0]*1000
        for i,j in enumerate(joints):ax.add_patch(Polygon(cylinder_projection(j,(0,2),ts[0,i]),facecolor=colors[i],alpha=.2,edgecolor=colors[i]))
        ax.plot(pp[:,0],pp[:,2],'-o',color='#284953',lw=1.8)
        for i,p in enumerate(pp):ax.annotate('J'+str(i+1),p[[0,2]],xytext=(5,5),textcoords='offset points')
        flange=np.array(joints[6]['origin_m']);tcp=ts[0,7]@np.r_[flange+[0,0,.15],1]
        ax.plot([pp[6,0],tcp[0]*1000],[pp[6,2],tcp[2]*1000],'--',color='#a45446')
        ax.annotate('2 kg at TCP',tcp[[0,2]]*1000,xytext=(10,-24),textcoords='offset points',color='#a45446')
        ax.annotate('',tcp[[0,2]]*1000+[0,-55],tcp[[0,2]]*1000,arrowprops=dict(arrowstyle='->',color='#a45446'))
        ax.set_aspect('equal');ax.autoscale_view();ax.margins(.18);ax.grid(alpha=.15);ax.set_title(label+'\nq='+str(angles),fontsize=9)
        ax.set_xlabel('X / mm');ax.set_ylabel('Z / mm')
    fig.suptitle('Calculated postures + load direction | Illustrations, not approved robot motions',fontsize=14)
    for ext in ['svg','png']:fig.savefig(OUT/('postures.'+ext),dpi=170,bbox_inches='tight')
    plt.close(fig)
    fig,(ax,am)=plt.subplots(1,2,figsize=(15,6),gridspec_kw={'width_ratios':[2,1]},layout='constrained')
    chosen=[r for r in results if r['id']=='body_only' or (r['tcp_offset_mm']==150 and r['head_com_offset_mm']==100)]
    xs=np.arange(7);w=.14
    for k,r in enumerate(chosen):
        ax.bar(xs+(k-2)*w,r['sampled_abs_max_gravity_Nm'],width=w,label='Body only' if r['id']=='body_only' else f"Head {r['head_mass_kg']:g} kg + object 2 kg")
    ax.plot(xs,[j['rated_torque_Nm'] for j in joints],'kd',label='Catalog running rated (NOT static hold)')
    ax.set_xticks(xs,[j['id'] for j in joints]);ax.set_ylabel('Absolute gravity effort / N m');ax.grid(axis='y',alpha=.15);ax.legend(fontsize=8)
    ax.set_title('32,776 sampled poses | COM +100 / TCP +150 mm\nSamples are not a global maximum or feasible-motion set',fontsize=10)
    labels=['Fixed base\nmetal','Fixed J1','Moving\nRH modules','Moving\nmetal links','Moving\nhardware budgets']
    vals=[body_mass[k] for k in ['fixed_base_original_metal_kg','fixed_J1_catalog_kg','moving_joint_catalog_kg','moving_link_metal_kg','moving_hardware_budget_kg']]
    am.barh(labels,vals,color=['#91a7b1','#708c9d','#345968','#cf945b','#d6b477']);am.invert_yaxis();am.set_xlabel('kg');am.set_title('Bare-body inventory, head/object excluded')
    for i,v in enumerate(vals):am.text(v+.05,i,f'{v:.3f}',va='center')
    am.set_xlim(0,max(vals)*1.2)
    for ext in ['svg','png']:fig.savefig(OUT/('loads-and-mass.'+ext),dpi=170,bbox_inches='tight')
    plt.close(fig)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    source_paths=[ROOT/'engineering/generated/raised-arm-integration01/model.json',
                  ROOT/'engineering/generated/raised-arm-integration01/assembly-parameters.json',
                  ROOT/'engineering/generated/shoulder-raise03/mass-properties.json',
                  ROOT/'engineering/generated/base-study/evidence.json',
                  ROOT/'docs/engineering/sources/rh-operation-evidence.json',ROOT/'engineering/kinematics.py']
    hashes={str(p.relative_to(ROOT)):sha(p) for p in source_paths}
    old=read(source_paths[0]);new_shoulder=read(source_paths[2]);base_evidence=read(source_paths[3])
    arm=copy.deepcopy(old['arm']);joints=arm['joints']
    assert joints[1]['origin_mm'][2]==205 and joints[6]['origin_mm'][2]==675
    discarded=[b for b in arm['bodies'] if b['id'].startswith('L12_')]
    old_object=next(b for b in arm['bodies'] if b['id']=='net_object')
    arm['bodies']=[b for b in arm['bodies'] if b['id']!='net_object' and not b['id'].startswith('L12_')]
    replacement=copy.deepcopy(new_shoulder['planning_models']['primary_preserve_200g_total']['bodies'])
    assert len(discarded)==4 and len(replacement)==12 and all(b['preceding_joints']==1 for b in replacement)
    assert math.isclose(sum(b['mass_kg'] for b in replacement),1.4277519681113167,abs_tol=1e-12)
    arm['bodies']+=replacement
    assert len({b['id'] for b in arm['bodies']})==len(arm['bodies'])==45
    assert not any(b['preceding_joints']==7 for b in arm['bodies'])
    flange=np.array(joints[6]['origin_m']);arm['tool_home_transform']=np.eye(4).tolist()
    for i in range(3):arm['tool_home_transform'][i][3]=float(flange[i])
    arm['model_scope']={'revision':'R5-BODY01','head':'excluded; old head_bodies not loaded',
        'payload':'excluded in this bare model; scenarios append exactly one2kg body',
        'shoulder':'RAISE03 planning set replaces oldL12 metal and0.20kg; no further translation',
        'base':'fixed J1 included;fixed mounting metal reported separately',
        'joints':'catalog masses/upstream geometric cylinderCOM, not manufacturer mass-property measurement',
        'qualification':'gravity model only; no manufacturing or actuator static-hold release'}
    write('body-only-model.json',arm)
    bodies=arm['bodies'];aggregate=aggregate_by_attachment(bodies)
    hardware=[b for b in bodies if b['id'].endswith('hardware_reserve')]
    metal=[b for b in bodies if b['id'].startswith('L') and not b['id'].endswith('hardware_reserve')]
    mass=dict(fixed_base_original_metal_kg=base_evidence['loads']['base_original_mass_kg'],fixed_J1_catalog_kg=2.74,
              moving_joint_catalog_kg=sum(j['mass_kg'] for j in joints[1:]),
              moving_link_metal_kg=sum(b['mass_kg'] for b in metal),moving_hardware_budget_kg=sum(b['mass_kg'] for b in hardware))
    mass['moving_body_planning_kg']=sum(b['mass_kg'] for b in bodies if b['preceding_joints']>0)
    mass['body_including_J1_excluding_mounting_base_kg']=sum(b['mass_kg'] for b in bodies)
    mass['fixed_base_plus_fixed_J1_kg']=mass['fixed_base_original_metal_kg']+2.74
    mass['body_plus_fixed_base_planning_kg']=mass['body_including_J1_excluding_mounting_base_kg']+mass['fixed_base_original_metal_kg']
    mass['fixed_base_fasteners_wires_extra_covers_unknown_kg']=None
    perlink=[]
    for group in ['12','23','34','45','56','67']:
        ll=[b for b in bodies if b['id'].startswith('L'+group+'_')]
        perlink.append(dict(link=group,metal_kg=sum(b['mass_kg'] for b in ll if not b['id'].endswith('hardware_reserve')),
                            hardware_budget_kg=sum(b['mass_kg'] for b in ll if b['id'].endswith('hardware_reserve'))))
    csvout('body-mass-ledger.csv',[dict(id=b['id'],mass_kg=b['mass_kg'],preceding_joints=b['preceding_joints'],
        com_X_m=b['com_home_m'][0],com_Y_m=b['com_home_m'][1],com_Z_m=b['com_home_m'][2],
        basis='catalog joint/geometric COM proxy' if b['id'].startswith('J') else ('hardware budget' if b['id'].endswith('reserve') else 'nominal original metal CAD')) for b in bodies])
    csvout('link-mass-groups.csv',perlink)
    poses=read(source_paths[1])['poses_deg']
    poses.update(horizontal_plus=[0,90,0,0,0,0,0],horizontal_minus=[0,-90,0,0,0,0,0],
                 folded=[0,0,0,-120,0,90,0],twist=[0,30,90,-60,-90,35,0],neutral_tilt=[0,-45,0,0,0,0,0])
    lo,hi=np.deg2rad([j['limit_deg'] for j in joints]).T
    unit=qmc.Sobol(d=5,scramble=True,seed=501).random_base2(15)
    qs=np.zeros((len(unit),7));qs[:,1:6]=lo[1:6]+unit*(hi[1:6]-lo[1:6])
    qs=np.vstack([qs,np.deg2rad(list(poses.values()))]);cache=transforms(joints,qs)
    gbody,bmbody=effort(joints,aggregate,qs,cache)
    check_ids=np.r_[np.arange(0,32768,4096),np.arange(32768,len(qs))]
    direct,_=effort(joints,bodies,qs[check_ids]);aa=Arm(arm)
    armcheck=np.array([aa.gravity_compensation(q) for q in qs[check_ids]])
    err=float(abs(direct-armcheck).max());agerr=float(abs(direct-gbody[check_ids]).max())
    assert err<1e-10 and agerr<1e-10
    # Potential-energy finite difference verifies gravity signs with a separate method.
    qtest=qs[17];h=1e-6
    energygrad=np.array([(aa.potential_energy(qtest+np.eye(7)[i]*h)-aa.potential_energy(qtest-np.eye(7)[i]*h))/(2*h) for i in range(7)])
    energy_error=float(abs(energygrad-aa.gravity_compensation(qtest)).max());assert energy_error<1e-6
    point_basis={offset:effort(joints,[pointbody('unit',1,flange+[0,0,offset/1000])],qs,cache) for offset in [50,100,150,200]}
    scenarios=[];gravity_arrays={}
    def add(label,hm,hc,tcp,payload):
        sb=copy.deepcopy(bodies);g=gbody.copy();bm=bmbody.copy()
        if hm:
            sb.append(pointbody('head_parameter',hm,flange+[0,0,hc/1000]));g+=hm*point_basis[hc][0];bm+=hm*point_basis[hc][1]
        if payload:
            sb.append(pointbody('net_object',payload,flange+[0,0,tcp/1000]));g+=payload*point_basis[tcp][0];bm+=payload*point_basis[tcp][1]
        bound=triangle(joints,sb);mx=np.max(abs(g),axis=0)
        assert np.all(mx<=bound+1e-9) and mx[0]<1e-10 and mx[6]<1e-10
        report=dict(id=label,head_mass_kg=hm,head_com_offset_mm=hc,tcp_offset_mm=tcp,payload_net_kg=payload,
            sampled_abs_max_gravity_Nm=mx.tolist(),sampled_worst_q_deg_by_joint=[np.rad2deg(qs[np.argmax(abs(g[:,i]))]).tolist() for i in range(7)],
            all_configuration_triangle_upper_bound_Nm=bound.tolist(),
            running_rated_over_sampled_ratio_not_static_margin=[None if v<1e-9 else joints[i]['rated_torque_Nm']/v for i,v in enumerate(mx)],
            sampled_base_overturning_moment_Nm=float(np.max(np.linalg.norm(bm[:,:2],axis=1))),
            J7_all_axis_scalar_gravity_Nm=0.,
            J7_bending_max_attainable_axial_model_Nm=9.80665*((hm or 0)*(hc or 0)/1000+payload*(tcp or 0)/1000),
            moving_planning_mass_with_head_payload_kg=mass['moving_body_planning_kg']+(hm or 0)+payload,
            named_pose_gravity_Nm={n:g[32768+i].tolist() for i,n in enumerate(poses)})
        report['contributions_at_each_joint_sample_max_Nm']=[]
        for i in range(7):
            index=int(np.argmax(abs(g[:,i])))
            terms=dict(body=float(gbody[index,i]),head=float(hm*point_basis[hc][0][index,i]) if hm else 0.,
                       object=float(payload*point_basis[tcp][0][index,i]) if payload else 0.)
            assert abs(sum(terms.values())-g[index,i])<1e-10
            report['contributions_at_each_joint_sample_max_Nm'].append(terms)
        scenarios.append(report);gravity_arrays[label]=(g,sb)
    add('body_only',0,None,None,0)
    for tcp in [100,150,200]:add(f'body_object_tcp{tcp}',0,None,tcp,2)
    for hm in [1.,1.5,2.,3.]:
        for hc in [50,100,150]:
            for tcp in [100,150,200]:add(f'head{hm:g}_com{hc}_tcp{tcp}',hm,hc,tcp,2)
    # Best-found refinements only for the three communication cases; no global claim.
    for label in ['body_only','body_object_tcp150','head1.5_com100_tcp150','head3_com100_tcp150']:
        g,sb=gravity_arrays[label];rep=next(r for r in scenarios if r['id']==label)
        rep['local_refinement_by_joint']={}
        for i in range(1,6):
            ii=np.argsort(abs(g[:,i]))[-2:];rr=refine(joints,sb,qs[ii],i)
            assert rr['best_found_abs_Nm']<=rep['all_configuration_triangle_upper_bound_Nm'][i]+1e-8
            rep['local_refinement_by_joint'][joints[i]['id']]=rr
    # Explicit off-axis payload uncertainty: exact worst direction at each fixed q.
    g,_=gravity_arrays['head1.5_com100_tcp150'];ts,origins,axes=cache
    coeff=np.cross(axes,GRAVITY)
    coeff_tool=np.einsum('nji,nkj->nki',ts[:,7,:3,:3],coeff)
    lateral=[]
    for rho in [.05,.10]:
        increments=2*rho*np.linalg.norm(coeff_tool[:,:,:2],axis=2)
        mx=np.max(abs(g)+increments,axis=0)
        nominal=next(r for r in scenarios if r['id']=='head1.5_com100_tcp150')
        bb=np.array(nominal['all_configuration_triangle_upper_bound_Nm'])+2*rho*np.linalg.norm(GRAVITY);bb[0]=0
        lateral.append(dict(object_COM_offset_in_flange_XY_disk_radius_mm=rho*1000,
            sampled_configuration_exact_direction_max_Nm=mx.tolist(),all_configuration_upper_bound_Nm=bb.tolist(),
            added_J7_attainable_max_Nm=2*rho*9.80665,global_configuration_max_certified=False))
    # Reach is reported for bare flange and explicit new TCP offsets, never old tool length.
    reaches=[];shoulder=np.array(joints[1]['origin_m'])
    path=sum(np.linalg.norm(np.array(joints[i+1]['origin_m'])-joints[i]['origin_m']) for i in range(1,6))
    for offset in [0,100,150,200,250]:
        point=flange+[0,0,offset/1000]
        world=np.einsum('nij,j->ni',ts[:,7,:3,:3],point)+ts[:,7,:3,3]
        distance=np.linalg.norm(world-origins[:,1],axis=1);best=int(distance.argmax())
        def rf(x):
            tt,oo,_=transforms(joints,np.r_[0.,x,0.]);p=tt[0,7]@np.r_[point,1]
            return -np.linalg.norm(p[:3]-oo[0,1])
        sol=minimize(rf,qs[best,1:6],method='L-BFGS-B',bounds=list(zip(lo[1:6],hi[1:6])),options={'ftol':1e-14})
        reaches.append(dict(TCP_offset_from_bare_J7_flange_mm=offset,home_shoulder_distance_mm=float(np.linalg.norm(point-shoulder)*1000),
            sampled_max_shoulder_distance_mm=float(distance.max()*1000),local_best_found_mm=float(-sol.fun*1000),
            polygonal_all_configuration_upper_bound_mm=float((path+offset/1000)*1000),
            best_found_q_deg=np.rad2deg(np.r_[0.,sol.x,0.]).tolist(),reachable_collision_free_certified=False))
    # Different upper/lower bounds: calculate required home-aligned extension only.
    required=(math.sqrt(.7**2-(flange[1]-shoulder[1])**2)-(flange[2]-shoulder[2]))*1000
    oldreach=float(np.linalg.norm(np.array(old_object['com_home_m'])-shoulder)*1000)
    # Full-form finite difference check of one off-axis payload equivalence.
    sb=copy.deepcopy(bodies)+[pointbody('head',1.5,flange+[0,0,.1]),pointbody('object',2,flange+[.05,0,.15])]
    off_model={**arm,'bodies':sb};off_q=np.deg2rad([0,90,0,0,0,0,0])
    off_e=effort(joints,sb,off_q)[0][0];off_a=Arm(off_model).gravity_compensation(off_q)
    assert np.max(abs(off_e-off_a))<1e-10
    # Verify exact disk-direction extrema by explicitly constructing the offset.
    base_case_bodies=gravity_arrays['head1.5_com100_tcp150'][1]
    disk_error=0.
    for k in [11,57,137]:
        for i in range(1,7):
            c=coeff_tool[k,i,:2];length=np.linalg.norm(c)
            if length<1e-12:continue
            sign=1 if g[k,i]>=0 else -1
            off=.05*sign*c/length
            trial=copy.deepcopy(base_case_bodies)
            trial[-1]['com_home_m'][:2]=(np.array(trial[-1]['com_home_m'][:2])+off).tolist()
            actual=effort(joints,trial,qs[k])[0][0,i]
            predicted=abs(g[k,i])+2*.05*length
            disk_error=max(disk_error,abs(abs(actual)-predicted))
    assert disk_error<1e-9
    old_bare=[b for b in old['arm']['bodies'] if b['id']!='net_object']
    old_effort=effort(joints,old_bare,qs[check_ids])[0]
    raise_gravity_delta=float(np.max(abs(old_effort-direct)))
    assert raise_gravity_delta<1e-10
    # Numerical check of the yaw/roll symmetry used to reduce sampling dimension.
    qs2=qs[check_ids].copy();qs2[:,0]=.71;qs2[:,6]=-.53
    symmetry_error=float(abs(effort(joints,base_case_bodies,qs2)[0]-effort(joints,base_case_bodies,qs[check_ids])[0]).max())
    assert symmetry_error<1e-10
    report=dict(revision='R5-BODY01',license='CC-BY-NC-4.0',attribution='Odradek — Auromix contributors',
        source_hashes=hashes,script_sha256=sha(Path(__file__)),
        replacement=dict(removed_L12_body_ids=[b['id'] for b in discarded],removed_L12_mass_kg=sum(b['mass_kg'] for b in discarded),
            inserted_mass_kg=sum(b['mass_kg'] for b in replacement),inserted_bodies=len(replacement),
            extra_translation_mm=0,known_0p1276kg_hardware_not_added_again=True,
            old_head_bodies_excluded_count=len(old['head_bodies']),old_head_bodies_excluded_mass_kg=sum(b['mass_kg'] for b in old['head_bodies']),
            old_net_object_removed=old_object),
        mass=mass,link_groups=perlink,joints=joints,
        sampling=dict(count=len(qs),sobol_count=32768,seed=501,q1_q7_fixed_zero_by_gravity_symmetry=True,
            varied_joint_limits_deg=[j['limit_deg'] for j in joints[1:6]],
            collision_cable_and_table_constraints_applied=False,
            definition='sample maxima and local best-found values are lower bounds on mathematical worst case; triangle bounds are conservative upper bounds only for stated COM/mass model'),
        scenarios=scenarios,off_axis_payload_sensitivity=lateral,reach=reaches,
        TCP_extension_for_700mm_home_shoulder_distance_mm=required,
        old_head_TCP_home_shoulder_distance_mm=oldreach,
        static_J7_zero_is_not_zero_bearing_bending=True,
        catalogue_running_rated_Nm=[j['rated_torque_Nm'] for j in joints],catalogue_peak_Nm=[j['peak_torque_Nm'] for j in joints],
        quality=dict(independent_Rodrigues_vs_Arm_max_Nm=err,aggregate_attachment_vs_all_bodies_max_Nm=agerr,
                     potential_energy_gradient_max_error_Nm=energy_error,all_sampled_efforts_below_triangle_bounds=True,
                     zero_q1_q7_for_axial_load_model=True,exact_offset_disk_direction_max_error_Nm=disk_error,
                     old_to_RAISE03_gravity_delta_Nm=raise_gravity_delta,q1_q7_symmetry_max_error_Nm=symmetry_error),
        limits=['No collision-free reach or motion-domain proof.', 'RH running ratings are not guaranteed zero-speed continuous holding.',
                'Joint masses are catalog values; internal rotor mass split and trueCOM unknown.',
                'Hardware allowances are budgets, not weighed maxima.', 'Head masses and axialCOM/TCP offsets are scenarios, not built head geometry.',
                'No acceleration, friction, harness, contact or machining-process allowance included.',
                'Base anchors remain required; fixed base mass does not qualify free-standing stability.'])
    write('study.json',report)
    csvout('scenario-summary.csv',[dict(id=r['id'],head_kg=r['head_mass_kg'],head_COM_mm=r['head_com_offset_mm'],TCP_mm=r['tcp_offset_mm'],
        **{f'J{i+1}_sample_Nm':r['sampled_abs_max_gravity_Nm'][i] for i in range(7)},
        **{f'J{i+1}_triangle_Nm':r['all_configuration_triangle_upper_bound_Nm'][i] for i in range(7)},
        J7_bending_Nm=r['J7_bending_max_attainable_axial_model_Nm']) for r in scenarios])
    csvout('reach.csv',reaches)
    drawings(joints,scenarios,{k:poses[k] for k in ['home','inspect','reach']},mass)
    manifest={str(p.relative_to(ROOT)):sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='manifest.json'}
    write('manifest.json',manifest)
    for p in source_paths:assert sha(p)==hashes[str(p.relative_to(ROOT))],p
    print(json.dumps({'mass':mass,'reach':reaches,'quality':report['quality'],
        'key_cases':[r for r in scenarios if r['id'] in ['body_only','body_object_tcp150','head1.5_com100_tcp150','head3_com100_tcp150']]},indent=2))


if __name__=='__main__':main()
