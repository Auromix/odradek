# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""SI-unit rigid-body calculations. No actuator commands or safety controller.

Each revolute axis is specified in the zero-configuration base frame. Bodies
give a home COM, a COM-frame inertia and number of preceding moving joints.
Mass properties must be measured or taken from validated CAD before release.
"""
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation


def skew(v):
    x, y, z = np.asarray(v, dtype=float)
    return np.array([[0., -z, y], [z, 0., -x], [-y, x, 0.]])


def revolute(axis, point, angle):
    w = np.asarray(axis, dtype=float)
    if not np.isclose(np.linalg.norm(w), 1., atol=1e-10):
        raise ValueError("Joint axes must be unit vectors")
    R = Rotation.from_rotvec(w * angle).as_matrix()
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = (np.eye(3) - R) @ np.asarray(point)
    return T


class Arm:
    def __init__(self, parameters):
        self.p = parameters
        self.joints = parameters["joints"]
        self.n = len(self.joints)
        self.gravity = np.asarray(parameters.get("gravity_m_s2", [0., 0., -9.80665]))
        self.bodies = parameters.get("bodies", [])
        self.home = np.asarray(parameters["tool_home_transform"], dtype=float)
        self.limits = np.deg2rad([j["limit_deg"] for j in self.joints])
        for b in self.bodies:
            R = np.asarray(b.get("orientation_home", np.eye(3)), dtype=float)
            I = np.asarray(b["inertia_com_kg_m2"], dtype=float)
            if (not np.allclose(R.T @ R, np.eye(3), atol=1e-9)
                    or not np.isclose(np.linalg.det(R), 1., atol=1e-9)):
                raise ValueError("Body orientation_home must be a proper rotation")
            if (b["mass_kg"] <= 0 or not np.allclose(I, I.T, atol=1e-12)
                    or np.linalg.eigvalsh(I).min() < -1e-12):
                raise ValueError("Positive mass and symmetric positive semidefinite COM inertia required")
            if not 0 <= b["preceding_joints"] <= self.n:
                raise ValueError("Invalid body joint attachment")

    def prefixes(self, q):
        q = np.asarray(q, dtype=float)
        if q.shape != (self.n,) or not np.all(np.isfinite(q)):
            raise ValueError("Expected one finite angle per joint")
        result = [np.eye(4)]
        for joint, angle in zip(self.joints, q):
            result.append(result[-1] @ revolute(joint["axis"], joint["origin_m"], angle))
        return result

    def fk(self, q):
        return self.prefixes(q)[-1] @ self.home

    def axes(self, q, prefixes=None):
        pre = self.prefixes(q) if prefixes is None else prefixes
        origins, axes = [], []
        for T, joint in zip(pre, self.joints):
            origins.append((T @ np.r_[joint["origin_m"], 1.])[:3])
            axes.append(T[:3, :3] @ joint["axis"])
        return np.asarray(origins), np.asarray(axes)

    def point_jacobian(self, q, point_world, preceding=None, prefixes=None):
        n = self.n if preceding is None else preceding
        origins, axes = self.axes(q, prefixes)
        J = np.zeros((6, self.n))
        for i in range(n):
            J[:3, i] = np.cross(axes[i], point_world - origins[i])
            J[3:, i] = axes[i]
        return J

    def jacobian(self, q):
        return self.point_jacobian(q, self.fk(q)[:3, 3])

    def body_states(self, q):
        pre = self.prefixes(q)
        result = []
        for b in self.bodies:
            n = b["preceding_joints"]
            T = pre[n]
            p = (T @ np.r_[b["com_home_m"], 1.])[:3]
            Rhome = np.asarray(b.get("orientation_home", np.eye(3)))
            R = T[:3, :3] @ Rhome
            J = self.point_jacobian(q, p, n, pre)
            result.append((b, p, R, J))
        return result

    def gravity_compensation(self, q):
        return sum((-J[:3].T @ (b["mass_kg"] * self.gravity)
                    for b, _, _, J in self.body_states(q)), np.zeros(self.n))

    def potential_energy(self, q):
        return sum(-b["mass_kg"] * self.gravity @ p for b, p, _, _ in self.body_states(q))

    def mass_matrix(self, q):
        M = np.zeros((self.n, self.n))
        for b, _, R, J in self.body_states(q):
            I = R @ np.asarray(b["inertia_com_kg_m2"]) @ R.T
            M += b["mass_kg"] * J[:3].T @ J[:3] + J[3:].T @ I @ J[3:]
        reflected = self.p.get("reflected_rotor_inertia_kg_m2", [0.] * self.n)
        return M + np.diag(reflected)

    def coriolis_effort(self, q, qd, h=1e-5):
        """Christoffel terms via central differences of M, not friction."""
        q, qd = np.asarray(q), np.asarray(qd)
        derivative = np.empty((self.n, self.n, self.n))
        for k in range(self.n):
            step = np.eye(self.n)[k] * h
            derivative[:, :, k] = (self.mass_matrix(q+step)-self.mass_matrix(q-step))/(2*h)
        C = np.zeros(self.n)
        for i in range(self.n):
            for j in range(self.n):
                for k in range(self.n):
                    C[i] += .5 * (derivative[i, j, k] + derivative[i, k, j]
                                    - derivative[j, k, i]) * qd[j] * qd[k]
        return C

    def inverse_dynamics(self, q, qd, qdd, external_wrench=None):
        effort = self.mass_matrix(q) @ qdd + self.coriolis_effort(q, qd) + self.gravity_compensation(q)
        if external_wrench is not None:
            # External wrench: environment acting on robot at tool origin,
            # [Fx,Fy,Fz,Mx,My,Mz] expressed in the base frame.
            effort -= self.jacobian(q).T @ np.asarray(external_wrench)
        return effort

    def ik(self, target, seed, rotation_scale_m=.25):
        """Bounded numerical IK; collision and cable constraints are separate."""
        target = np.asarray(target)
        def residual(q):
            current = self.fk(q)
            position = target[:3, 3] - current[:3, 3]
            orientation = Rotation.from_matrix(target[:3, :3] @ current[:3, :3].T).as_rotvec()
            return np.r_[position, rotation_scale_m * orientation]
        seed = np.clip(seed, self.limits[:, 0]+1e-9, self.limits[:, 1]-1e-9)
        solution = least_squares(residual, seed, bounds=self.limits.T,
                                 xtol=1e-12, ftol=1e-12, gtol=1e-12, max_nfev=1000)
        err = residual(solution.x)
        return {"q_rad": solution.x, "position_error_m": np.linalg.norm(err[:3]),
                "orientation_error_rad": np.linalg.norm(err[3:])/rotation_scale_m,
                "solver_success": bool(solution.success),
                "pose_reached": bool(np.linalg.norm(err[:3]) < 1e-5 and
                                     np.linalg.norm(err[3:])/rotation_scale_m < 1e-5)}
