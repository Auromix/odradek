# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Conservative polyhedral friction-cone LP with point contacts and torque limits.

Contact geometry is an explicit assumption, never inferred from a rendered
object. Radial-pad examples require task-specific pad/contact construction.
"""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from gripper import petal_point,petal_jacobian,radial,grasp_matrix

ROOT=Path(__file__).resolve().parents[1]


def solve_grasp(points,normals,jacobians,com,wrench,mu,torque_limit,rays=16,minimum_normal_N=0.,contact_to_joint=None,normal_ratio_constraints=None):
    """Optional triples (a,b,k) impose normal[a] = k*normal[b].

    They expose assumed coupled pad load sharing, not independent force control
    or a measured compliance model. Without triples the original LP is retained.
    """
    n=len(points);ndof=len(torque_limit)
    groups=np.arange(n) if contact_to_joint is None else np.asarray(contact_to_joint)
    if (len(groups)!=n or np.any(groups!=np.floor(groups)) or
            np.any(groups<0) or np.any(groups>=ndof)):
        raise ValueError('Every contact must map to one valid finger joint')
    groups=groups.astype(int)
    F=np.zeros((3*n,n*rays));Q=np.zeros((ndof,n*rays))
    normals=np.asarray(normals,dtype=float).copy();norm=np.linalg.norm(normals,axis=1)
    if (mu<0 or minimum_normal_N<0 or rays<4 or np.any(norm<=0) or
            not np.all(np.isfinite(normals)) or np.any(np.asarray(torque_limit)<0)):
        raise ValueError('Finite nonzero normals, nonnegative friction/preload/caps and at least four rays required')
    normals/=norm[:,None]
    for i,(normal,J) in enumerate(zip(normals,jacobians)):
        normal=np.asarray(normal,dtype=float);normal/=np.linalg.norm(normal)
        ref=np.array([0.,0,1]) if abs(normal[2])<.99 else np.array([1.,0,0])
        t1=ref-(ref@normal)*normal;t1/=np.linalg.norm(t1);t2=np.cross(normal,t1)
        for k in range(rays):
            theta=2*np.pi*k/rays
            v=normal+mu*(np.cos(theta)*t1+np.sin(theta)*t2)
            F[3*i:3*i+3,i*rays+k]=v;Q[groups[i],i*rays+k]=J@v
    G=grasp_matrix(points,np.asarray(com));W=G@F
    normal_map=np.kron(np.eye(n),np.ones((1,rays)))
    balance=[]
    for a,b,k in normal_ratio_constraints or []:
        if (not np.isfinite(k) or k<0 or a!=int(a) or b!=int(b) or
                not 0<=a<n or not 0<=b<n or a==b):
            raise ValueError('Normal ratio requires two distinct valid contacts and finite nonnegative ratio')
        balance.append(normal_map[int(a)]-k*normal_map[int(b)])
    equality=np.vstack([W,*balance]) if balance else W
    rhs=np.r_[-np.asarray(wrench),np.zeros(len(balance))]
    A_ub=np.vstack([Q,-Q,-normal_map]);b_ub=np.r_[torque_limit,torque_limit,[-minimum_normal_N]*n]
    sol=linprog(np.ones(n*rays),A_ub=A_ub,
                b_ub=b_ub,A_eq=equality,b_eq=rhs,
                bounds=(0,None),method='highs')
    answer={'feasible':bool(sol.success),'solver_message':sol.message}
    if sol.success:
        # Resolve degenerate minimum-normal solutions by minimizing peak finger
        # torque while retaining the first-stage normal optimum to 1e-7 N.
        m=n*rays
        second=linprog(np.r_[np.zeros(m),1.],
                       A_ub=np.vstack([np.c_[A_ub,np.zeros(len(b_ub))],
                                       np.r_[np.ones(m),0.],np.c_[Q,-np.ones(ndof)],np.c_[-Q,-np.ones(ndof)]]),
                       b_ub=np.r_[b_ub,sol.fun+1e-7,np.zeros(2*ndof)],
                       A_eq=np.c_[equality,np.zeros(len(rhs))],b_eq=rhs,bounds=(0,None),method='highs')
        weights=second.x[:m] if second.success else sol.x
        forces=(F@weights).reshape(n,3);normal=np.sum(weights.reshape(n,rays),axis=1)
        residual=G@forces.reshape(-1)+wrench
        answer.update({'normal_N':normal.tolist(),'forces_on_object_N':forces.tolist(),
                       'finger_joint_equilibrium_Nm':(Q@weights).tolist(),'normal_total_N':float(sum(weights)),
                       'max_force_balance_residual_N':float(max(abs(residual[:3]))),
                       'max_moment_balance_residual_Nm':float(max(abs(residual[3:]))),
                       'friction_norms_N':np.linalg.norm(forces-np.asarray(normals)*normal[:,None],axis=1).tolist()})
        if balance:answer['normal_ratio_constraint_max_residual_N']=float(np.max(np.abs(np.array(balance)@weights)))
    return answer


def main():
    # Known analytic symmetric-in-wrench example from gripper-analysis.md.
    phi=np.deg2rad([35,145,225,315]);points=np.array([.04*radial(f) for f in phi])
    normals=np.array([-radial(f) for f in phi]);J=np.array([-.09*radial(f) if i<2 else -.07*radial(f) for i,f in enumerate(phi)])
    analytic=solve_grasp(points,normals,J,[0,0,0],[0,0,-39.2266,0,0,0],.4,[3.7]*4)
    assert analytic['feasible'] and abs(analytic['normal_total_N']-98.0665)<1e-7
    assert analytic['max_moment_balance_residual_Nm']<1e-9
    # Impossible case: zero friction and gravity perpendicular to all normals.
    impossible=solve_grasp(points,normals,J,[0,0,0],[0,0,-39.2266,0,0,0],0,[3.7]*4)
    assert not impossible['feasible']
    p=json.loads((ROOT/'engineering/parameters/r4-layout.json').read_text())
    fs=p['head']['fingers'];points=[];J=[];flat=[];rad=[];qdeg=[]
    contact=p['head']['contact_study']
    for f in fs:
        r=f['root_radius_mm']*.001;s=f['contact_along_mm']*.001;h=contact['pad_surface_center_normal_mm']*.001;target=contact['target_radius_mm']*.001
        # R+s*cos(q)-h*sin(q)=target at the nominal pad centre.
        q=np.arccos((target-r)/np.hypot(s,h))-np.arctan2(h,s)
        assert 0<=np.rad2deg(q)<=f['closure_study_deg']
        assert abs(np.rad2deg(q)-f['pad_target_q_deg'])<1e-8
        ph=np.deg2rad(f['phi_deg']);qdeg.append(float(np.rad2deg(q)))
        points.append(petal_point(q,ph,r,f['root_z_mm']*.001,s,normal=h))
        J.append(petal_jacobian(q,ph,s,normal=h))
        flat.append(-np.sin(q)*radial(ph)+[0,0,np.cos(q)])
        rad.append(-radial(ph))
    points=np.asarray(points);com=np.array([0,0,np.mean(points[:,2])])
    cases=[]
    for pad,normals in [('flat_pad_comparison',flat),('fixed_angle_pad_at_80mm_study_pose',rad)]:
        for mu in [.3,.4,.6]:
            for gravity in [[0,0,-1],[0,-1,0],[1,0,0]]:
                for factor in [1.,2.]:
                    wrench=np.r_[np.asarray(gravity)*2*9.80665*factor,[0,0,0]]
                    for limit in [3.,3.7]:
                        cases.append({'contact_model':pad,'mu':mu,'load_direction_head':gravity,
                                      'payload_kg':2.,'design_factor':factor,'output_torque_cap_Nm':limit,
                                      **solve_grasp(points,normals,J,com,wrench,mu,[limit]*4,minimum_normal_N=2.)})
    report={'revision':p['revision'],'status':'CONDITIONAL POINT-CONTACT LP, NOT A GRASP TEST',
            'friction_cone':'16 boundary rays; their convex cone is inside Coulomb cone',
            'contact_radius_m':target,'pad_nominal_offset_m':h,'q_deg':qdeg,
            'minimum_normal_per_nominal_contact_N':2.,'finger_self_weight_inertia_friction_torque_bias_Nm':[0,0,0,0],
            'points_head_m':points.tolist(),'object_com_head_m':com.tolist(),
            'contact_jacobians_m_per_rad':np.asarray(J).tolist(),
            'cases':cases,'analytic_regression':analytic,'zero_friction_infeasible_check':impossible,
            'limits':['actual two pads per finger are replaced by one nominal point contact; contact location must be proven on an object',
                      'actual 3D contact positions enter force and moment equilibrium; this study has coplanar nominal contacts at z110mm',
                      'flat-pad case is a local compatible-contact geometry assumption, not proof that a cylinder contacts those points',
                      'angled CAD pads match radial normal only at the specified pose; real object faces, two-pad contact and deformation remain unverified',
                      '3.7 Nm is catalog gearbox output, not verified motor zero-speed capability or belt output',
                      '3.0 Nm is a comparison cap, not certified thermal or transmission derating',
                      'infeasible is relative to the conservative 16-ray cone and stated contact/torque model',
                      'zero torque bias excludes finger weight, inertia and joint friction; these must be added before actuator release',
                      'no robustness to COM error, slip, wear, acceleration beyond stated factor or contact loss']}
    out=ROOT/'docs/engineering/analysis/grasp-screening.json';out.write_text(json.dumps(report,indent=2)+'\n')
    print('Analytic example reproduced; zero-friction rejection verified.')
    for c in cases:
        if c['design_factor']==2 and c['mu']==.4 and c['output_torque_cap_Nm']==3.7:
            print(c['contact_model'],c['load_direction_head'],c['feasible'],c.get('normal_total_N'))


if __name__=='__main__':main()
