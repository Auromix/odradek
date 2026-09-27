# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Independent pose-difference checks of the 7+4 constrained rigid-body model.

These random states are mathematical tests, not collision-qualified trajectories.
Unweighed head reserves and unknown motor rotor inertias are excluded explicitly.
"""
from pathlib import Path
import hashlib
import json

import numpy as np

from articulated_head_dynamics import ArticulatedHeadArm, FINGER_ORDER, p16_geometry
from structural_mass_model import ROOT, structural_model


OUT = ROOT/'engineering/generated/articulated-dynamics-review'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def vee(a):
    return np.array([a[2, 1]-a[1, 2], a[0, 2]-a[2, 0], a[1, 0]-a[0, 1]])*.5


def numeric_jacobians(model, q, h=2e-6):
    """Differentiate positions/orientations; no analytic Jacobian is consumed."""
    center = model.states(q)
    jacobians = np.zeros((len(center), 6, 11))
    for k in range(11):
        e = np.eye(11)[k]*h
        minus, plus = model.states(q-e), model.states(q+e)
        for i, (b, m, p) in enumerate(zip(center, minus, plus)):
            assert b['id'] == m['id'] == p['id']
            jacobians[i, :3, k] = (p['p']-m['p'])/(2*h)
            jacobians[i, 3:, k] = vee((p['R']-m['R'])/(2*h)@b['R'].T)
    return jacobians


def direct_body_effort(model, q, velocity, acceleration, numeric_J, h):
    """Newton/Euler from trajectory pose differences, without M or C.

    R(t) and p(t) are evaluated at q(t)=q+velocity*t+acceleration*t²/2.
    Double differences have finite roundoff/truncation error, reported explicitly.
    """
    center = model.states(q)
    minus = model.states(q-velocity*h+.5*acceleration*h*h)
    plus = model.states(q+velocity*h+.5*acceleration*h*h)
    effort = model.rotor_inertia*acceleration
    for b, m, p, J in zip(center, minus, plus, numeric_J):
        linear_acceleration = (p['p']-2*b['p']+m['p'])/(h*h)
        Rdot = (p['R']-m['R'])/(2*h)
        Rddot = (p['R']-2*b['R']+m['R'])/(h*h)
        omega = vee(Rdot@b['R'].T)
        alpha = vee(Rddot@b['R'].T+Rdot@Rdot.T)
        force = b['mass_kg']*(linear_acceleration-model.gravity)
        moment = b['I_world']@alpha+np.cross(omega, b['I_world']@omega)
        effort += J[:3].T@force+J[3:].T@moment
    return effort


def load_model():
    parameters = ROOT/'engineering/parameters/r4-layout.json'
    head_path = ROOT/'engineering/generated/head-mass04/mass-properties.json'
    p = json.loads(parameters.read_text()); h = json.loads(head_path.read_text())
    arm, links = structural_model(p, links=('12', '23', '34', '45', '56', '67'), extension_mm=24.)
    removed = [b['id'] for b in arm['bodies'] if b['id'] in ('head_budget', 'L7_budget')]
    assert set(removed) == {'head_budget', 'L7_budget'}
    arm['bodies'] = [b for b in arm['bodies'] if b['id'] not in removed]
    arm['model_scope'] = dict(links_with_CAD=list(links), head_is_budget=False,
                             head='HEAD-MASS04 nominal material integrations and explicit catalog inertia proxies',
                             removed_duplicate_budgets=removed,
                             unweighed_head_reserve='185..450g excluded from this measured-geometry subtotal; not a complete machine mass or rating',
                             base='Fixed base plates/fork hardware are not part of this moving-chain mass subtotal; fixedJ1 is included',
                             joint_mass='Catalog mass/upstream cylinder inertia proxies; rotor distribution unknown',
                             object='2kg held rigid at world-home TCP914mm; finger/object contact constraints not solved',
                             finger_load='Free finger inertial/gravity effort only; gripping contact forces and friction must be added separately',
                             manufacturing_release=False)
    model = ArticulatedHeadArm(arm, h['aggregated_bodies'], h['finger_joints'], np.array(h['head_face_world_mm'])*.001)
    sources = {str(parameters.relative_to(ROOT)):sha(parameters), str(head_path.relative_to(ROOT)):sha(head_path)}
    for link in links.values():
        sources.update(link['source_hashes'])
    source_model = dict(arm=arm, head_bodies=h['aggregated_bodies'], finger_joints=h['finger_joints'],
                        head_face_home_m=(np.array(h['head_face_world_mm'])*.001).tolist(), source_hashes=sources,
                        limitations=arm['model_scope'])
    return model, source_model


def main():
    model, inputs = load_model()
    rng = np.random.default_rng(741104)
    reports = []
    qlow, qhigh = model.limits.T
    # Keep margins for central finite differences. Do not imply these arbitrary
    # joint combinations satisfy current structural/cable/contact constraints.
    for trial in range(8):
        q = rng.uniform(qlow*.85+qhigh*.15, qlow*.15+qhigh*.85)
        v = rng.uniform(-.6, .6, 11); a = rng.uniform(-1.2, 1.2, 11)
        states = model.states(q); numeric = numeric_jacobians(model, q)
        jac_error = max(np.max(abs(b['J']-J)) for b, J in zip(states, numeric))
        assert jac_error < 2e-8, (trial, 'Jacobian', jac_error)
        gradient = np.array([(model.potential_energy(q+np.eye(11)[k]*2e-6)-model.potential_energy(q-np.eye(11)[k]*2e-6))/4e-6 for k in range(11)])
        g = model.gravity_compensation(q)
        gradient_error = float(np.max(abs(g-gradient)))
        assert gradient_error < 2e-7, (trial, 'potential gradient', gradient_error)
        M = model.mass_matrix(q); eigen = np.linalg.eigvalsh(M)
        assert np.max(abs(M-M.T)) < 1e-12 and eigen.min() > 0
        C = model.coriolis_effort(q, v)
        effort = M@a+C+g
        references = []
        for step in (2e-4, 1e-4):
            reference = direct_body_effort(model, q, v, a, numeric, step)
            error = float(np.max(abs(reference-effort)))
            assert error < 3e-4, (trial, 'direct body forces', step, error)
            references.append(dict(trajectory_difference_step_s=step, max_effort_error_Nm=error))
        Mdot = (model.mass_matrix(q+v*1e-5)-model.mass_matrix(q-v*1e-5))/2e-5
        energy_error = abs(float(v@(C-.5*Mdot@v)))
        assert energy_error < 2e-7, (trial, 'power', energy_error)
        kinetic = sum(.5*b['mass_kg']*np.linalg.norm(J[:3]@v)**2+.5*(J[3:]@v)@b['I_world']@(J[3:]@v) for b, J in zip(states, numeric))
        kinetic += .5*v@np.diag(model.rotor_inertia)@v
        kinetic_error = abs(float(kinetic-.5*v@M@v))
        assert kinetic_error < 2e-8, (trial, 'kinetic', kinetic_error)
        forces = model.actuator_forces_from_effort(q, effort)
        speed_fd = np.array([(p16_geometry(q[7+k]+v[7+k]*1e-5)[0]-p16_geometry(q[7+k]-v[7+k]*1e-5)[0])/2e-5 for k in range(4)])
        work_error = abs(float(forces@speed_fd-effort[7:]@v[7:]))
        assert work_error < 2e-8, (trial, 'P16 virtual work', work_error)
        reports.append(dict(trial=trial, q_deg=np.rad2deg(q).tolist(), qd_rad_s=v.tolist(), qdd_rad_s2=a.tolist(),
                            max_analytic_numeric_J_error=float(jac_error), max_gravity_gradient_error_Nm=gradient_error,
                            minimum_mass_matrix_eigenvalue_kg_m2=float(eigen.min()), direct_force_comparisons=references,
                            kinetic_energy_error_J=kinetic_error, energy_identity_error_W=energy_error,
                            P16_virtual_work_error_W=work_error, generalized_effort_Nm=effort.tolist(),
                            ideal_P16_axial_force_N=forces.tolist(), sample_is_qualified_trajectory=False))
        print('Trial',trial,'max effort difference',max(x['max_effort_error_Nm'] for x in references),flush=True)
    q = np.r_[np.deg2rad([0,-25,0,-95,0,-15,0]),[0.]*4]
    M = model.mass_matrix(q)
    closed = q.copy();closed[7:] = [model.limits[k,1] for k in range(7,11)]
    coupling = dict(pose='inspect; only a static mathematical comparison',
                    arm_finger_mass_matrix_cross_block_kg_m2=M[:7,7:].tolist(),
                    open_gravity_effort_Nm=model.gravity_compensation(q).tolist(),
                    closed_gravity_effort_Nm=model.gravity_compensation(closed).tolist())
    result = dict(revision='DYNAMICS-11DOF01', passed=True, manufacturing_release=False, physical_payload_qualification=False,
                  model_mass_including_fixed_J1_and_2kg_object_kg=sum(b['mass_kg'] for b in model.states(np.zeros(11))),
                  head_modeled_mass_kg=sum(b['mass_kg'] for b in model.head_bodies),
                  generalized_order=[f'J{i}' for i in range(1,8)]+list(FINGER_ORDER),
                  trials=reports, arm_finger_coupling=coupling, input_model_scope=inputs['limitations'],
                  source_hashes=inputs['source_hashes'],
                  scripts_sha256={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'engineering/articulated_head_dynamics.py',ROOT/'engineering/structural_mass_model.py',ROOT/'engineering/kinematics.py']})
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'model.json').write_text(json.dumps(inputs,indent=2)+'\n')
    (OUT/'review.json').write_text(json.dumps(result,indent=2)+'\n')
    print('All8 mathematical states passed; this does not qualify physical trajectories.')


if __name__ == '__main__':
    main()
