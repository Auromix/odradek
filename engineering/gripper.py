# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Independent rigid petal joints. SI units; contact is not presumed.

Positive closing q rotates about MINUS tangent(phi), not plus tangent(phi).
"""
import numpy as np


def radial(phi):
    return np.array([np.cos(phi), np.sin(phi), 0.])


def tangent(phi):
    return np.array([-np.sin(phi), np.cos(phi), 0.])


def petal_point(q, phi, root_radius, root_z, along, across=0., normal=0.):
    er, et, ez = radial(phi), tangent(phi), np.array([0., 0., 1.])
    longitudinal = np.cos(q)*er + np.sin(q)*ez
    lamp_normal = -np.sin(q)*er + np.cos(q)*ez
    return root_radius*er + root_z*ez + along*longitudinal + across*et + normal*lamp_normal


def petal_jacobian(q, phi, along, normal=0.):
    er, ez = radial(phi), np.array([0., 0., 1.])
    return along*(-np.sin(q)*er+np.cos(q)*ez) + normal*(-np.cos(q)*er-np.sin(q)*ez)


def closing_angle(target_radius, root_radius, length):
    """Mathematical [0, pi] branch, excluding pads and physical joint limits."""
    if length <= 0 or not np.all(np.isfinite([target_radius, root_radius, length])):
        raise ValueError("Finite radii and positive length required")
    v = (target_radius-root_radius)/length
    if not -1 <= v <= 1:
        raise ValueError("Target radius is unreachable by this rigid petal")
    return float(np.arccos(v))


def contact_effort(q, phi, along, force_on_finger, normal=0.):
    """External generalized force; motor equilibrium torque is its negative."""
    return float(petal_jacobian(q, phi, along, normal) @ force_on_finger)


def gravity_friction_lower_bound(mass_kg, friction, acceleration=0., design_factor=2., contacts=4):
    """Necessary translational condition only; no proof of force closure.

    Assumes all normal forces orthogonal to gravity and usable friction aligned
    against it, equal contact loads and no external moments. Failure of any
    assumption requires solving the actual contact wrench problem.
    """
    if min(mass_kg, friction, design_factor, contacts) <= 0 or acceleration < 0:
        raise ValueError("Positive inputs required")
    total = design_factor*mass_kg*(9.80665+acceleration)/friction
    return {"normal_total_N": total, "normal_per_contact_N": total/contacts}


def grasp_matrix(contact_points, object_com):
    """Map base-frame point contact forces to object wrench; no contact moments."""
    from kinematics import skew
    return np.hstack([np.vstack([np.eye(3), skew(np.asarray(p)-object_com)]) for p in contact_points])
