# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Independent rigid-body force/moment review of Lagrange inverse dynamics.

No hardware commands. SI units. The reference does not call Arm Jacobians,
mass matrices, Coriolis or body_states, or numerically differentiate dynamics.
"""
from pathlib import Path
import argparse
import copy
import json
import numpy as np

from kinematics import Arm
from review_arm_screening import reference_states
from structural_mass_model import structural_model, sha, ROOT


def body_kinematics(model, q, qd, qdd):
    frames, os, zs = reference_states(model, np.atleast_2d(q))
    frames, origins, axes = frames[0], os[0], zs[0]
    n = len(axes)
    origin_vel = np.zeros_like(origins)
    axis_derivative = np.zeros_like(axes)
    for j in range(n):
        omega_upstream = sum((axes[k] * qd[k] for k in range(j)), np.zeros(3))
        axis_derivative[j] = np.cross(omega_upstream, axes[j])
        for k in range(j):
            origin_vel[j] += np.cross(axes[k], origins[j]-origins[k]) * qd[k]
    states = []
    for body in model['bodies']:
        count = body['preceding_joints']
        point = frames[count, :3, :3] @ body['com_home_m'] + frames[count, :3, 3]
        velocity = sum((np.cross(axes[j], point-origins[j]) * qd[j] for j in range(count)), np.zeros(3))
        acceleration = np.zeros(3)
        omega, alpha = np.zeros(3), np.zeros(3)
        for j in range(count):
            acceleration += np.cross(axes[j], point-origins[j]) * qdd[j]
            acceleration += (np.cross(axis_derivative[j], point-origins[j])
                             + np.cross(axes[j], velocity-origin_vel[j])) * qd[j]
            omega += axes[j] * qd[j]
            alpha += axes[j] * qdd[j] + axis_derivative[j] * qd[j]
        orientation = frames[count, :3, :3] @ np.array(body.get('orientation_home', np.eye(3)))
        inertia = orientation @ body['inertia_com_kg_m2'] @ orientation.T
        states.append((body, point, velocity, acceleration, omega, alpha, inertia))
    return states, frames, origins, axes


def newton_euler_effort(model, q, qd, qdd, external_wrench=None):
    q, qd, qdd = (np.asarray(x, dtype=float) for x in (q, qd, qdd))
    states, frames, origins, axes = body_kinematics(model, q, qd, qdd)
    effort = np.zeros(len(q))
    gravity = np.asarray(model['gravity_m_s2'])
    for body, point, _, acceleration, omega, alpha, inertia in states:
        force = body['mass_kg'] * (acceleration-gravity)
        moment_at_com = inertia @ alpha + np.cross(omega, inertia @ omega)
        for j in range(body['preceding_joints']):
            effort[j] += axes[j] @ (np.cross(point-origins[j], force) + moment_at_com)
    effort += np.array(model.get('reflected_rotor_inertia_kg_m2', [0.]*len(q))) * qdd
    if external_wrench is not None:
        wrench = np.asarray(external_wrench)
        tool = (frames[-1] @ np.asarray(model['tool_home_transform']))[:3, 3]
        for j in range(len(q)):
            effort[j] -= axes[j] @ (np.cross(tool-origins[j], wrench[:3]) + wrench[3:])
    return effort


def energy(model, q, qd):
    states, _, _, _ = body_kinematics(model, q, qd, np.zeros(len(q)))
    value = 0.
    for body, point, v, _, omega, _, inertia in states:
        value += .5*body['mass_kg']*(v@v) + .5*omega@inertia@omega - body['mass_kg']*np.array(model['gravity_m_s2'])@point
    value += .5*np.dot(model.get('reflected_rotor_inertia_kg_m2', [0.]*len(q)), qd**2)
    return float(value)


def review(model, count=24):
    arm = Arm(model)
    rng = np.random.default_rng(927703)
    records = []
    for i in range(count):
        q = rng.uniform(*arm.limits.T)
        qd = rng.uniform(-.8, .8, arm.n)
        qdd = rng.uniform(-1.5, 1.5, arm.n)
        external = rng.uniform(-1, 1, 6)*np.array([20, 20, 20, 3, 3, 3])
        direct = newton_euler_effort(model, q, qd, qdd, external)
        lagrange = arm.inverse_dynamics(q, qd, qdd, external)
        err = float(np.max(abs(direct-lagrange)))
        # Refine only the existing finite-difference M derivatives, independently
        # of the analytic force/moment reference.
        half = arm.mass_matrix(q)@qdd + arm.coriolis_effort(q, qd, h=5e-6) + arm.gravity_compensation(q) - arm.jacobian(q).T@external
        refined_err = float(np.max(abs(direct-half)))
        M = arm.mass_matrix(q)
        eigmin = float(np.linalg.eigvalsh(M).min())
        assert err < 1e-6 and refined_err < 1e-6 and eigmin > 0
        h = 1e-5
        denergy = (energy(model, q+h*qd+.5*h*h*qdd, qd+h*qdd)
                   - energy(model, q-h*qd+.5*h*h*qdd, qd-h*qdd))/(2*h)
        power = newton_euler_effort(model, q, qd, qdd) @ qd
        power_err = float(abs(power-denergy))
        assert power_err < 2e-6
        records.append({'q_rad': q.tolist(), 'qd_rad_s': qd.tolist(), 'qdd_rad_s2': qdd.tolist(),
                        'external_environment_wrench_base': external.tolist(), 'effort_Nm': direct.tolist(),
                        'lagrange_error_Nm': err, 'refined_lagrange_error_Nm': refined_err,
                        'power_identity_error_W': power_err, 'mass_matrix_min_eigenvalue_kg_m2': eigmin})
    # A one-axis pendulum has a closed answer independent of both arm methods.
    pendulum = {'joints': [{'axis': [0, 1, 0], 'origin_m': [0, 0, 0], 'limit_deg': [-180, 180]}],
                'gravity_m_s2': [0, 0, -9.80665], 'tool_home_transform': np.eye(4).tolist(),
                'bodies': [{'id': 'mass', 'mass_kg': 2., 'preceding_joints': 1, 'com_home_m': [0, 0, .3],
                            'inertia_com_kg_m2': np.diag([.01, .02, .03]).tolist()}]}
    errors = []
    for angle in [-1.2, -.2, 0., .7]:
        answer = (.02 + 2*.3**2)*.9 - 2*9.80665*.3*np.sin(angle)
        got = newton_euler_effort(pendulum, [angle], [.4], [.9])[0]
        errors.append(float(abs(got-answer)))
    assert max(errors) < 1e-10
    # Synthetic rotor fixture only exercises the constant reflected inertia term.
    rotor = copy.deepcopy(model)
    rotor['reflected_rotor_inertia_kg_m2'] = np.linspace(.001, .007, arm.n).tolist()
    q = np.zeros(arm.n);qd=np.ones(arm.n)*.2;qdd=np.ones(arm.n)*.3
    rotor_err = float(np.max(abs(newton_euler_effort(rotor,q,qd,qdd)-Arm(rotor).inverse_dynamics(q,qd,qdd))))
    assert rotor_err < 1e-6
    return {'samples': records, 'pendulum_max_error_Nm': max(errors), 'synthetic_rotor_fixture_error_Nm': rotor_err,
            'maximum_lagrange_error_Nm': max(x['lagrange_error_Nm'] for x in records),
            'maximum_power_identity_error_W': max(x['power_identity_error_W'] for x in records),
            'scope': 'Mathematical implementation consistency only. Model proxies, friction, thermal, brakes, fingers, contact, collision and cable limits remain unqualified.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path)
    parser.add_argument('--out', type=Path, default=ROOT/'engineering/generated/dynamics-review')
    args = parser.parse_args()
    source = {}
    if args.model:
        model = json.loads(args.model.read_text())
        source[str(args.model)] = sha(args.model)
    else:
        baseline = ROOT/'engineering/parameters/r4-layout.json'
        model, links = structural_model(json.loads(baseline.read_text()), extension_mm=24.)
        source['engineering/parameters/r4-layout.json'] = sha(baseline)
        for row in links.values():source.update(row['source_hashes'])
    result = review(model)
    result.update({'revision': 'DYNAMICS-REVIEW01', 'model_scope': model.get('model_scope'),
                   'source_hashes': source, 'manufacturing_release': False,
                   'implementation_hashes': {f:sha(ROOT/'engineering'/f) for f in ['review_rigid_body_dynamics.py','structural_mass_model.py','kinematics.py','review_arm_screening.py','arm_screening.py']}})
    args.out.mkdir(exist_ok=True, parents=True)
    (args.out/'model.json').write_text(json.dumps(model,indent=2)+'\n')
    result['model_sha256'] = sha(args.out/'model.json')
    (args.out/'review.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k in ['revision','maximum_lagrange_error_Nm','maximum_power_identity_error_W','pendulum_max_error_Nm','synthetic_rotor_fixture_error_Nm']},indent=2))


if __name__ == '__main__':main()
