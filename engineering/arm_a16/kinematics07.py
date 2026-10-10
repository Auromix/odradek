# SPDX-License-Identifier: CC-BY-NC-4.0
"""Current assembly FK/Jacobian convention with independent finite differences."""
import csv,json,numpy as np
import common as c

def tcp(q):return c.frames(q)['J7.rotor']@np.array([[1,0,0,110],[0,1,0,0],[0,0,1,0],[0,0,0,1]],float)
def jacobian(q):
    F=c.frames(q);end=tcp(q)[:3,3]/1000;columns=[]
    for j in c.L['joints']:
        f=F[j['id']+'.fixed'];axis=f[:3,:3]@np.array(j['axis']);origin=f[:3,3]/1000
        columns.append(np.r_[np.cross(axis,end-origin),axis])
    return np.column_stack(columns)

def main():
    poses=list(c.L['poses'].values())+[[23,55,35,-85,68,24,42],[-67,-20,-48,82,39,-41,-59]]
    linear=[];angular=[];roll=[];h=1e-5
    for q in poses:
        J=jacobian(q);T=tcp(q);assert np.allclose(T[:3,:3].T@T[:3,:3],np.eye(3),atol=1e-12)
        for i in range(7):
            plus=np.array(q,float);minus=plus.copy();plus[i]+=np.degrees(h);minus[i]-=np.degrees(h)
            A=tcp(plus);B=tcp(minus);dp=(A[:3,3]-B[:3,3])/(2000*h)
            skew=((A[:3,:3]-B[:3,:3])/(2*h))@T[:3,:3].T
            omega=np.array([skew[2,1],skew[0,2],skew[1,0]])
            linear.append(float(np.max(abs(dp-J[:3,i]))));angular.append(float(np.max(abs(omega-J[3:,i]))))
        shift=np.array(q,float);shift[6]+=35;roll.append(float(np.linalg.norm(tcp(shift)[:3,3]-T[:3,3])))
    assert max(linear)<1e-8 and max(angular)<1e-8 and max(roll)<1e-8
    with (c.OUT/'kinematics07-joint-table.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['joint','model','parent_translation_x_mm','y_mm','z_mm','local_axis_x','axis_y','axis_z','CAD_zero_offset_deg','q_min_deg','q_max_deg'])
        for j in c.L['joints']:w.writerow([j['id'],j['model'],*j['offset'],*j['axis'],j['zero_deg'],*j['limits_deg']])
    record=dict(layout=c.L,root_transform_mm=c.L['root_transform_mm'],flange_from_J7_mm=[110,0,0],
        pose_TCP_world_mm={name:tcp(q).tolist() for name,q in c.L['poses'].items()},
        jacobian_units='top3 m/rad;bottom3 rad/rad;inputq_deg converted before differentiation',
        finite_difference_pose_count=len(poses),max_linear_J_error_m_per_rad=max(linear),max_angular_J_error=max(angular),J7_roll_TCP_translation_max_error_mm=max(roll),
        physical_encoder_zero_qualified=False,controller_limits_qualified=False,production_release=False,
        scope='Kinematic convention and differentiation only; no elastic deflection, encoder calibration, actual workspace, dynamics or motor control release.')
    (c.OUT/'kinematics07.json').write_text(json.dumps(record,indent=2)+'\n');print('KINEMATICS07',max(linear),max(angular),max(roll),flush=True)

if __name__=='__main__':main()
