# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Seven arm rotations plus four finger hinges, with constrained P16 linkages.

SI units throughout. This is a rigid-body research model, not a motor command
generator. Catalog/proxy inertias and missing hardware remain input assumptions.
"""
import math

import numpy as np
from scipy.spatial.transform import Rotation

from kinematics import Arm


FINGER_ORDER = ('UR', 'UL', 'LL', 'LR')


def p16_geometry(angle):
    """Pin length, aim, and derivatives w.r.t. hinge angle in radians.

    The positive actuator length is work-conjugate to positive hinge rotation.
    The aim angle is measured from head +Z towards the radial direction.
    """
    D, a = .123, .026
    u = float(angle) - math.radians(68)
    length = math.sqrt(D*D + a*a + 2*D*a*math.sin(u))
    aim = math.atan2(a*math.cos(u), D+a*math.sin(u))
    length_derivative = D*a*math.cos(u)/length
    aim_derivative = -a*(D*math.sin(u)+a)/(length*length)
    return length, aim, length_derivative, aim_derivative


class ArticulatedHeadArm:
    """Head tensors are about each COM, expressed in zero-pose head axes.

    `arm_model` must already exclude head_budget and L7_budget when the input
    head includes its adapter. A net object can remain attached to arm prefix7;
    this represents a held rigid object, not a solved finger/object contact loop.
    """

    def __init__(self, arm_model, head_bodies, finger_joints, head_face_home_m):
        self.arm = Arm(arm_model)
        assert self.arm.n == 7
        assert not any(b['id'] in ('head_budget', 'L7_budget') for b in self.arm.bodies)
        self.n = 11
        self.gravity = self.arm.gravity
        self.face = np.asarray(head_face_home_m, dtype=float)
        self.head_bodies = head_bodies
        self.fingers = {f['id']: f for f in finger_joints}
        assert set(self.fingers) == set(FINGER_ORDER)
        self.ids = [b['id'] for b in self.arm.bodies] + [b['id'] for b in head_bodies]
        assert len(self.ids) == len(set(self.ids))
        for b in head_bodies:
            I = np.asarray(b['inertia_about_COM_head_axes_kg_m2'])
            assert b['mass_kg'] > 0
            assert np.allclose(I, I.T, atol=1e-12)
            assert np.linalg.eigvalsh(I).min() >= -1e-12
            assert b['kinematic_group'] in ('head_fixed', 'finger_rotor', 'P16_body', 'P16_slider')
            if b['kinematic_group'] != 'head_fixed':
                assert b['finger'] in FINGER_ORDER
        self.limits = np.vstack([self.arm.limits, np.deg2rad([self.fingers[k]['range_deg'] for k in FINGER_ORDER])])
        self.rotor_inertia = np.r_[arm_model.get('reflected_rotor_inertia_kg_m2', [0.]*7), [0.]*4]

    def _head_pose(self, b, q):
        """Local COM, rotation, linear/angular derivatives for its one hinge."""
        p0 = np.asarray(b['com_head_home_m'])
        zero = np.zeros(3)
        if b['kinematic_group'] == 'head_fixed':
            return p0, np.eye(3), zero, zero, None
        k = FINGER_ORDER.index(b['finger'])
        f = self.fingers[b['finger']]
        angle = q[7+k]
        pivot = np.asarray(f['pivot_head_mm'])*.001
        axis = np.asarray(f['closing_axis_head'])
        if b['kinematic_group'] == 'finger_rotor':
            R = Rotation.from_rotvec(axis*angle).as_matrix()
            p = pivot+R@(p0-pivot)
            return p, R, np.cross(axis, p-pivot), axis, 7+k
        tangent = -axis
        radial = np.array([tangent[1], -tangent[0], 0.])
        base = pivot-.018*f['mechanical_mirror_sign']*tangent+np.array([0., 0., -.123])
        L, theta, Ld, td = p16_geometry(angle)
        L0, theta0, _, _ = p16_geometry(0.)
        R = Rotation.from_rotvec(tangent*(theta-theta0)).as_matrix()
        rod0 = radial*math.sin(theta0)+np.array([0., 0., math.cos(theta0)])
        slider = b['kinematic_group'] == 'P16_slider'
        p = base+R@(p0-base+(L-L0)*rod0 if slider else p0-base)
        dp = td*np.cross(tangent, p-base)
        if slider:
            dp += R@rod0*Ld
        return p, R, dp, tangent*td, 7+k

    def states(self, q):
        q = np.asarray(q, dtype=float)
        if q.shape != (11,) or not np.all(np.isfinite(q)):
            raise ValueError('Expected eleven finite generalized angles, in radians')
        states = []
        for b, p, R, J7 in self.arm.body_states(q[:7]):
            J = np.zeros((6, 11)); J[:, :7] = J7
            states.append(dict(id=b['id'], mass_kg=b['mass_kg'], p=p, R=R, J=J,
                               I_world=R@np.asarray(b['inertia_com_kg_m2'])@R.T))
        prefixes = self.arm.prefixes(q[:7]); T = prefixes[7]; R7 = T[:3, :3]
        for b in self.head_bodies:
            ph, Rh, dp, w, col = self._head_pose(b, q)
            p = R7@(self.face+ph)+T[:3, 3]
            R = R7@Rh
            J = np.zeros((6, 11))
            J[:, :7] = self.arm.point_jacobian(q[:7], p, preceding=7, prefixes=prefixes)
            if col is not None:
                J[:3, col] = R7@dp; J[3:, col] = R7@w
            I = R@np.asarray(b['inertia_about_COM_head_axes_kg_m2'])@R.T
            states.append(dict(id=b['id'], mass_kg=b['mass_kg'], p=p, R=R, J=J, I_world=I))
        return states

    def potential_energy(self, q):
        return sum(-b['mass_kg']*self.gravity@b['p'] for b in self.states(q))

    def gravity_compensation(self, q):
        return sum((-b['J'][:3].T@(b['mass_kg']*self.gravity) for b in self.states(q)), np.zeros(11))

    def mass_matrix(self, q):
        M = np.diag(self.rotor_inertia)
        for b in self.states(q):
            Jv, Jw = b['J'][:3], b['J'][3:]
            M += b['mass_kg']*Jv.T@Jv+Jw.T@b['I_world']@Jw
        return M

    def coriolis_effort(self, q, velocity, h=1e-5):
        q = np.asarray(q); v = np.asarray(velocity)
        dM = np.empty((11, 11, 11))
        for k in range(11):
            delta = np.eye(11)[k]*h
            dM[:, :, k] = (self.mass_matrix(q+delta)-self.mass_matrix(q-delta))/(2*h)
        # C_i = sum_jk dM_ij/dq_k v_j v_k - 1/2 dM_jk/dq_i v_j v_k.
        return np.einsum('ijk,j,k->i', dM, v, v)-.5*np.einsum('jki,j,k->i', dM, v, v)

    def inverse_dynamics(self, q, velocity, acceleration):
        return self.mass_matrix(q)@np.asarray(acceleration)+self.coriolis_effort(q, velocity)+self.gravity_compensation(q)

    def actuator_forces_from_effort(self, q, effort):
        """Ideal P16 axial forces; motor/gearing/friction efficiency not added."""
        ratio = np.array([p16_geometry(a)[2] for a in np.asarray(q)[7:]])
        if np.any(ratio <= 0):
            raise ValueError('Outside the stated monotone P16 closure branch')
        return np.asarray(effort)[7:]/ratio
