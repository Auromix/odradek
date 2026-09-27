# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Independent analytic and finite-difference checks; no hardware validation."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from kinematics import Arm
from gripper import petal_point, petal_jacobian, closing_angle, gravity_friction_lower_bound, contact_effort, grasp_matrix


def model_fixture():
    """Mathematical fixture, not a released Odradek layout."""
    joints = []
    for i, z in enumerate([.09, .17, .25, .47, .525, .73, .775]):
        joints.append({"id": f"J{i+1}", "axis": [0, 0, 1] if i % 2 == 0 else [0, 1, 0],
                       "origin_m": [0, 0, z], "limit_deg": [-140, 140]})
    home = np.eye(4); home[2, 3] = .87
    bodies = [{"id": f"test_body_{i}", "mass_kg": 1.+.1*i, "preceding_joints": i+1,
               "com_home_m": [0.005, -.003, j["origin_m"][2]+.035],
               "inertia_com_kg_m2": np.diag([.01, .012, .008]).tolist()}
              for i, j in enumerate(joints)]
    return {"joints": joints, "tool_home_transform": home.tolist(), "bodies": bodies}


def run():
    results = {}
    # Analytic one-link pendulum: axis +y, COM initially +x.
    L, mass, Iyy, q, qd, qdd = .4, 2., .03, .31, .7, -.8
    home = np.eye(4); home[0, 3] = L
    pendulum = Arm({"joints": [{"axis": [0, 1, 0], "origin_m": [0, 0, 0], "limit_deg": [-180, 180]}],
                    "tool_home_transform": home.tolist(), "bodies": [{"mass_kg": mass,
                    "preceding_joints": 1, "com_home_m": [L, 0, 0],
                    "inertia_com_kg_m2": np.diag([.02, Iyy, .02]).tolist()}]})
    expected = (mass*L*L+Iyy)*qdd - mass*9.80665*L*np.cos(q)
    err = abs(pendulum.inverse_dynamics([q], [qd], [qdd])[0]-expected)
    assert err < 1e-8
    results["analytic_pendulum_inverse_dynamics_error_Nm"] = float(err)
    force = [0., 0., -10., 0., 3., 0.]
    expected_external = -mass*9.80665*L - 10*L - 3
    err = abs(pendulum.inverse_dynamics([0.], [0.], [0.], force)[0]-expected_external)
    assert err < 1e-10
    results["analytic_external_force_and_moment_error_Nm"] = float(err)
    # Planar 2R endpoint, independent trigonometric reference.
    two = model_fixture(); two["joints"] = [
        {"axis": [0, 0, 1], "origin_m": [0, 0, 0], "limit_deg": [-180, 180]},
        {"axis": [0, 0, 1], "origin_m": [.4, 0, 0], "limit_deg": [-180, 180]}]
    two["bodies"] = []; T = np.eye(4); T[0, 3] = .7; two["tool_home_transform"] = T.tolist()
    q2 = np.array([.6, -.2]); xy = [.4*np.cos(.6)+.3*np.cos(.4), .4*np.sin(.6)+.3*np.sin(.4)]
    err = np.linalg.norm(Arm(two).fk(q2)[:2, 3]-xy); assert err < 1e-12
    results["analytic_planar_2R_position_error_m"] = float(err)
    # Coupled planar 2R rod dynamics, gravity perpendicular to its plane.
    m1, m2, l1, l2, c1, c2 = 1.2, .8, .4, .3, .2, .15
    I1, I2 = m1*l1*l1/12, m2*l2*l2/12
    two["bodies"] = [
        {"mass_kg": m1, "preceding_joints": 1, "com_home_m": [c1, 0, 0],
         "inertia_com_kg_m2": np.diag([0., I1, I1]).tolist()},
        {"mass_kg": m2, "preceding_joints": 2, "com_home_m": [l1+c2, 0, 0],
         "inertia_com_kg_m2": np.diag([0., I2, I2]).tolist()}]
    planar = Arm(two); q2=np.array([.7,-.4]); vel=np.array([.8,-.6]); acc=np.array([-.5,.9])
    coupling=m2*l1*c2
    mat=np.array([[I1+I2+m1*c1*c1+m2*(l1*l1+c2*c2)+2*coupling*np.cos(q2[1]),
                   I2+m2*c2*c2+coupling*np.cos(q2[1])],
                  [I2+m2*c2*c2+coupling*np.cos(q2[1]), I2+m2*c2*c2]])
    c=np.array([-coupling*np.sin(q2[1])*(2*vel[0]*vel[1]+vel[1]**2),
                coupling*np.sin(q2[1])*vel[0]**2])
    err=float(np.max(np.abs(planar.inverse_dynamics(q2,vel,acc)-(mat@acc+c))))
    assert err < 1e-8
    results["analytic_coupled_2R_inverse_dynamics_error_Nm"] = err
    arm = Arm(model_fixture()); rng = np.random.default_rng(402)
    jac_err = gravity_err = power_err = 0.; min_eigenvalue = 1.
    for _ in range(12):
        q = rng.uniform(-1.1, 1.1, 7); qd = rng.normal(0, .4, 7); h = 1e-6
        numerical = np.zeros((6, 7))
        grad = np.zeros(7)
        for k in range(7):
            d = np.eye(7)[k]*h; plus, minus = arm.fk(q+d), arm.fk(q-d)
            numerical[:3, k] = (plus[:3, 3]-minus[:3, 3])/(2*h)
            numerical[3:, k] = Rotation.from_matrix(plus[:3, :3] @ minus[:3, :3].T).as_rotvec()/(2*h)
            grad[k] = (arm.potential_energy(q+d)-arm.potential_energy(q-d))/(2*h)
        jac_err = max(jac_err, float(np.max(np.abs(numerical-arm.jacobian(q)))))
        gravity_err = max(gravity_err, float(np.max(np.abs(grad-arm.gravity_compensation(q)))))
        M = arm.mass_matrix(q)
        assert np.allclose(M, M.T, atol=1e-12)
        min_eigenvalue = min(min_eigenvalue, float(np.linalg.eigvalsh(M).min()))
        Mdot = (arm.mass_matrix(q+h*qd)-arm.mass_matrix(q-h*qd))/(2*h)
        # Kinetic-energy identity: qd^T c = 1/2 qd^T Mdot qd.
        power_err = max(power_err, abs(float(qd @ arm.coriolis_effort(q, qd)-.5*qd @ Mdot @ qd)))
    assert jac_err < 1e-7 and gravity_err < 1e-6 and power_err < 1e-7 and min_eigenvalue > 0
    results.update(jacobian_max_error=jac_err, gravity_gradient_max_error_Nm=gravity_err,
                   coriolis_energy_identity_max_error_W=power_err, mass_matrix_min_eigenvalue=min_eigenvalue)
    ik_pos = ik_rot = 0.
    for _ in range(5):
        q = rng.uniform(-.9, .9, 7); result = arm.ik(arm.fk(q), q+rng.normal(0, .15, 7))
        assert result["solver_success"] and result["pose_reached"]
        ik_pos = max(ik_pos, result["position_error_m"]); ik_rot = max(ik_rot, result["orientation_error_rad"])
    assert ik_pos < 1e-7 and ik_rot < 1e-7
    results.update(reachable_fixture_ik_max_position_error_m=ik_pos, reachable_fixture_ik_max_orientation_error_rad=ik_rot)
    far = arm.home.copy(); far[0,3]=10.
    unreachable = arm.ik(far, np.zeros(7))
    assert not unreachable["pose_reached"]
    results["unreachable_target_correctly_rejected"] = True
    invalid=model_fixture(); invalid["bodies"][0]["orientation_home"]=(2*np.eye(3)).tolist()
    try:
        Arm(invalid)
    except ValueError:
        results["invalid_body_rotation_rejected"] = True
    else:
        raise AssertionError("Invalid rotation accepted")
    petal_error = 0.
    for _ in range(30):
        q, phi = rng.uniform(.1, 2.2), rng.uniform(-np.pi, np.pi); h=1e-6
        diff = (petal_point(q+h, phi, .05, .01, .12, .007, .006)
                -petal_point(q-h, phi, .05, .01, .12, .007, .006))/(2*h)
        petal_error = max(petal_error, float(np.linalg.norm(diff-petal_jacobian(q, phi, .12, .006))))
    assert petal_error < 1e-9
    results["petal_jacobian_max_error_m_rad"] = petal_error
    q,phi,s,n=.6,.3,.12,.006; f=np.array([2.,3.,-1.]); h=1e-6
    power=f@(petal_point(q+h,phi,.05,0.,s,normal=n)-petal_point(q-h,phi,.05,0.,s,normal=n))/(2*h)
    assert abs(power-contact_effort(q,phi,s,f,normal=n))<1e-8
    G=grasp_matrix([np.array([.1,0.,0.]),np.array([0.,.2,0.])],np.zeros(3))
    assert np.allclose(G@np.array([0.,1.,0.,1.,0.,0.]),[1.,1.,0.,0.,0.,-.1])
    results["contact_virtual_work_and_grasp_wrench"]="PASS"
    q = closing_angle(.015, .05, .12)
    assert abs(petal_point(q, 0., .05, .0, .12)[0]-.015) < 1e-12
    results["friction_example_not_force_closure"] = gravity_friction_lower_bound(2., .4)
    results["status"] = "PASS: mathematical fixtures only; no physical-layout or hardware qualification"
    target = Path(__file__).resolve().parents[1]/"docs/engineering/analysis/math-verification.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(results, indent=2)+"\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    run()
