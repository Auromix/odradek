# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Read-only static-screen review; print results, never qualify an actuator.

Run from any directory with the same dependencies as arm_screening.py.
The independent reference uses Rodrigues transforms and direct moments of
weights, not Arm.gravity_compensation, Arm.point_jacobian or Arm.body_states.
All offsets below are in the zero-pose tool frame; its rotation is identity
in this R4 parameter file. Arbitrary tool_home rotations are handled explicitly.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from arm_screening import arm_parameters
from kinematics import Arm

ROOT = Path(__file__).resolve().parents[1]


def reference_states(model, configurations):
    """Batch product transforms, using the closed Rodrigues formula."""
    q = np.atleast_2d(configurations)
    n = len(model['joints'])
    transforms = np.broadcast_to(np.eye(4), (len(q), n + 1, 4, 4)).copy()
    origins = np.empty((len(q), n, 3))
    axes = np.empty_like(origins)
    for i, joint in enumerate(model['joints']):
        w = np.asarray(joint['axis'], dtype=float)
        p = np.asarray(joint['origin_m'], dtype=float)
        assert np.isclose(np.linalg.norm(w), 1)
        origins[:, i] = np.einsum('nij,j->ni', transforms[:, i, :3, :3], p) + transforms[:, i, :3, 3]
        axes[:, i] = np.einsum('nij,j->ni', transforms[:, i, :3, :3], w)
        cross = np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0.]])
        sine = np.sin(q[:, i])[:, None, None]
        cosine = np.cos(q[:, i])[:, None, None]
        rotation = cosine * np.eye(3) + (1 - cosine) * np.outer(w, w) + sine * cross
        step = np.broadcast_to(np.eye(4), (len(q), 4, 4)).copy()
        step[:, :3, :3] = rotation
        step[:, :3, 3] = np.einsum('nij,j->ni', np.eye(3) - rotation, p)
        transforms[:, i + 1] = transforms[:, i] @ step
    return transforms, origins, axes


def reference_gravity(model, configurations):
    """Sum -axis dot ((body COM - joint origin) cross body weight)."""
    transforms, origins, axes = reference_states(model, configurations)
    gravity = np.asarray(model['gravity_m_s2'])
    effort = np.zeros(origins.shape[:2])
    states = []
    for body in model['bodies']:
        count = body['preceding_joints']
        point = np.einsum('nij,j->ni', transforms[:, count, :3, :3], body['com_home_m']) + transforms[:, count, :3, 3]
        lever = point[:, None, :] - origins[:, :count, :]
        moments = np.cross(lever, body['mass_kg'] * gravity)
        effort[:, :count] -= np.einsum('nij,nij->ni', axes[:, :count], moments)
        states.append((body, point))
    return effort, (transforms, origins, axes, states)


def triangle_bounds(model):
    """Sum m|g| times polygonal joint-to-COM path lengths."""
    n = len(model['joints'])
    radii = np.zeros((len(model['bodies']), n))
    bound = np.zeros(n)
    for k, body in enumerate(model['bodies']):
        count = body['preceding_joints']
        points = [j['origin_m'] for j in model['joints'][:count]] + [body['com_home_m']]
        if not count:
            continue
        lengths = np.linalg.norm(np.diff(np.asarray(points), axis=0), axis=1)
        radii[k, :count] = np.cumsum(lengths[::-1])[::-1]
        bound += body['mass_kg'] * np.linalg.norm(model['gravity_m_s2']) * radii[k]
    # Only the base axis remains fixed in the gravity frame for every pose.
    if np.linalg.norm(np.cross(model['joints'][0]['axis'], model['gravity_m_s2'])) < 1e-12:
        bound[0] = 0
    return bound, radii


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, default=ROOT / 'engineering/parameters/r4-layout.json')
    args = parser.parse_args()
    raw = args.parameters.read_bytes()
    p = json.loads(raw)
    model = arm_parameters(p)
    arm = Arm(model)
    assert len(model['joints']) == 7
    assert p['payload_net_kg'] == 2 and p['head_budget_kg'] == 2, 'This review fixture states 2 kg + 2 kg.'
    assert np.allclose(np.asarray(model['tool_home_transform'])[:3, :3], np.eye(3))
    bodies = {b['id']: b for b in model['bodies']}
    for i, joint in enumerate(p['joints']):
        assert bodies[joint['id'] + '_mass_proxy']['preceding_joints'] == i
        assert bodies[joint['id'] + '_mass_proxy']['mass_kg'] == joint['mass_kg']
        assert bodies[f'L{i + 1}_budget']['preceding_joints'] == i + 1
    assert bodies['net_object']['mass_kg'] == p['payload_net_kg']
    assert bodies['head_budget']['mass_kg'] == p['head_budget_kg']
    lo, hi = arm.limits.T
    rng = np.random.default_rng(704)
    original_samples = np.vstack([rng.uniform(lo, hi, (1500, 7)), np.deg2rad(list(p['poses_deg'].values()))])
    horizontal = np.deg2rad([0, 90, 0, 0, 0, 0, 0])
    samples = np.vstack([original_samples, horizontal])
    reference, (_, origins, axes, states) = reference_gravity(model, samples)
    compare_q = samples[np.unique(np.r_[np.arange(0, 1500, 37), np.arange(1500, len(samples))])]
    calculated = np.array([arm.gravity_compensation(q) for q in compare_q])
    independent, _ = reference_gravity(model, compare_q)
    direct_error = float(np.max(abs(calculated - independent)))
    assert direct_error < 1e-10

    # Hand simplification for q2=+90 degrees; no rotation or cross product here.
    expected = np.zeros(7)
    for i in range(1, 7):
        # Pitch axes measure original z lever; original z roll axes measure y.
        coordinate = 2 if i in [1, 3, 5] else 1
        sign = -1 if i in [1, 5] else 1
        expected[i] = sign * 9.80665 * sum(
            b['mass_kg'] * (b['com_home_m'][coordinate] - model['joints'][i]['origin_m'][coordinate])
            for b in model['bodies'] if b['preceding_joints'] > i)
    assert np.max(abs(reference[-1] - expected)) < 1e-10
    bound, radii = triangle_bounds(model)
    assert np.all(np.max(abs(reference), axis=0) <= bound + 1e-10)
    max_distance_excess = -np.inf
    for k, (body, point) in enumerate(states):
        count = body['preceding_joints']
        if count:
            actual = np.linalg.norm(point[:, None, :] - origins[:, :count], axis=2)
            max_distance_excess = max(max_distance_excess, np.max(actual - radii[k, :count]))
    assert max_distance_excess < 1e-10
    assert np.max(abs(reference[:, 6])) < 1e-10

    # A displaced object is modeled once as a body; independently compare the
    # equivalent force + moment at TCP after removing the object body.
    offset = np.array([0., .1, 0.])
    displaced = arm_parameters(p, payload_offset=offset)
    displaced_arm = Arm(displaced)
    no_object = {**model, 'bodies': [b for b in model['bodies'] if b['id'] != 'net_object']}
    bare = Arm(no_object)
    equivalence_error = 0.
    for q in compare_q[:12]:
        force = p['payload_net_kg'] * arm.gravity
        offset_world = arm.fk(q)[:3, :3] @ offset
        wrench = np.r_[force, np.cross(offset_world, force)]
        as_external = bare.gravity_compensation(q) - bare.jacobian(q).T @ wrench
        equivalence_error = max(equivalence_error, float(np.max(abs(as_external - displaced_arm.gravity_compensation(q)))))
    assert equivalence_error < 1e-10
    offset_example = displaced_arm.gravity_compensation(horizontal)
    assert abs(offset_example[6] - 1.96133) < 1e-10

    # For fixed q, maximizing over every tool-frame displacement direction of
    # radius rho gives |G_i(q)| + m*rho*|axis_i(q) cross g|, exactly. Maximizing
    # over sampled q remains only a sampled configuration result.
    sensitivity = []
    coefficient_norm = p['payload_net_kg'] * np.linalg.norm(np.cross(axes, arm.gravity), axis=2)
    for rho in [.05, .1, .15]:
        row_bound = bound + p['payload_net_kg'] * np.linalg.norm(arm.gravity) * rho
        row_bound[0] = 0
        # Existing nominal J7 axial COMs give exactly zero generalized gravity.
        row_bound[6] = p['payload_net_kg'] * np.linalg.norm(arm.gravity) * rho
        sensitivity.append({
            'object_COM_displacement_radius_mm': rho * 1000,
            'sampled_q_max_over_all_displacement_directions_Nm': np.max(abs(reference) + rho * coefficient_norm, axis=0).tolist(),
            'all_configuration_bound_with_exact_nominal_J7_zero_Nm': row_bound.tolist(),
            'maximum_increment_Nm_except_fixed_vertical_J1': p['payload_net_kg'] * np.linalg.norm(arm.gravity) * rho})

    # J7 bearing reaction and overturning moment are not its scalar drive effort.
    _, (_, origin, axis, horizontal_states) = reference_gravity(model, horizontal)
    weight = np.zeros(3)
    moment = np.zeros(3)
    for body, point in horizontal_states:
        if body['preceding_joints'] == 7:
            force = body['mass_kg'] * arm.gravity
            weight += force
            moment += np.cross(point[0] - origin[0, 6], force)
    bending = moment - axis[0, 6] * (moment @ axis[0, 6])
    assert abs(np.linalg.norm(bending) - bound[6]) < 1e-10
    total_mass = sum(b['mass_kg'] for b in model['bodies'])
    moving_mass = sum(b['mass_kg'] for b in model['bodies'] if b['preceding_joints'] > 0)
    result = {
        'status': 'independent numerical checks pass; installed zero-speed holding and 2 kg capability remain unqualified',
        'parameter_revision': p['revision'], 'parameter_sha256': hashlib.sha256(raw).hexdigest(),
        'gravity_m_s2': 9.80665, 'payload_net_kg': p['payload_net_kg'], 'head_kg': p['head_budget_kg'],
        'total_model_mass_including_fixed_J1_and_object_kg': total_mass,
        'mass_moved_by_J1_including_object_kg': moving_mass,
        'mass_downstream_of_each_drive_kg': [sum(b['mass_kg'] for b in model['bodies'] if b['preceding_joints'] > i) for i in range(7)],
        'independent_cross_moment_error_Nm': direct_error,
        'object_body_vs_TCP_wrench_error_Nm': equivalence_error,
        'triangle_distance_max_excess_m': float(max_distance_excess),
        'original_1503_sample_max_Nm': np.max(abs(reference[:-1]), axis=0).tolist(),
        'horizontal_q_deg': np.rad2deg(horizontal).tolist(),
        'horizontal_hand_calculated_gravity_Nm': expected.tolist(),
        'triangle_bound_Nm': bound.tolist(),
        'catalog_running_rated_Nm_NOT_zero_speed_limit': [j['rated_torque_Nm'] for j in p['joints']],
        'horizontal_object_plus_100mm_tool_Y_gravity_Nm': offset_example.tolist(),
        'off_axis_object_sensitivity': sensitivity,
        'horizontal_J7_output_weight_force_world_N': weight.tolist(),
        'horizontal_J7_output_weight_moment_world_Nm': moment.tolist(),
        'horizontal_J7_output_bending_magnitude_Nm': float(np.linalg.norm(bending)),
        'head_COM_50mm_plus_object_COM_100mm_increment_bound_Nm': 9.80665 * (2 * .05 + 2 * .1),
        'not_verified': ['physical COM and mass splits', 'collision and cable reachable configurations',
                         'installed zero-speed thermal limit', 'brake output holding torque',
                         'bearing load spectrum and overturning moment limit', 'dynamic or contact loads']}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
