#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Compare ideal beam sections, not certify an assembled robot.

All mechanics calculations use N, m, Pa, kg, rad internally. Results explicitly
convert to mm, MPa and degrees. Standard library only; no network dependency.
Run from anywhere; --check recomputes and compares the saved JSON numerically.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E = 70.0e9
G = 26.3e9
RHO = 2700.0
YIELD_MIN = 240.0e6
LENGTHS = (0.15, 0.20)
MOMENTS = (20.0, 40.0, 60.0)
TORQUES = (10.0, 20.0)
SOURCES = {
    "thyssenkrupp_6061_2018": "https://d2zo35mdb530wx.cloudfront.net/_legacy/UCPthyssenkruppBAMXUK/assets.files/material-data-sheets/aluminium/aluminium-6061.pdf",
    "hydro_6061_2019": "https://www.hydro.com/globalassets/01-products--services/extruded-profiles/americas/ena-resources/alloy-data-sheets/hydro_2019_data_sheet_6061.pdf",
    "mit_closed_section_torsion": "https://ocw.mit.edu/courses/16-20-structural-mechanics-fall-2002/a58ea050460c29f7389ff55e084521ed_ho3.pdf",
    "nasa_mechanical_design": "https://extapps.ksc.nasa.gov/Reliability/Documents/Mechanical-Design-Reliability-Monograph.pdf",
    "stratasys_abs_m30": "https://go.stratasys.com/rs/533-LAV-099/images/MDS_FDM_ABS-M30_A4_0920a.pdf",
    "nasa_fastener_design_manual": "https://ntrs.nasa.gov/api/citations/19900009424/downloads/19900009424.pdf",
}


def rectangle(b, h, t, name):
    """Sharp-corner rectangular tube; Bredt torsion is thin-wall approximate."""
    if not 0 < 2 * t < min(b, h):
        raise ValueError("Invalid rectangular tube wall")
    bi, hi = b - 2 * t, h - 2 * t
    area = b * h - bi * hi
    ix = (b * h**3 - bi * hi**3) / 12
    iy = (h * b**3 - hi * bi**3) / 12
    am = (b - t) * (h - t)
    j = 4 * am**2 * t / (2 * (b + h - 2 * t))
    return {"id": name, "kind": "closed_rectangle", "b": b, "h": h,
            "t": t, "A": area, "Ix": ix, "Iy": iy, "J": j, "Am": am,
            "cx": b / 2, "cy": h / 2}


def twin_tubes(d=0.020, t=0.003, spacing=0.048):
    if not 0 < 2 * t < d or spacing < d:
        raise ValueError("Invalid separated circular tubes")
    di = d - 2 * t
    a = math.pi * (d**2 - di**2) / 4
    i = math.pi * (d**4 - di**4) / 64
    return {"id": "twin_D20_t3_s48", "kind": "twin_circles", "d": d,
            "t": t, "s": spacing, "b": spacing + d, "h": d,
            "A": 2 * a, "A_each": a, "I_each": i, "J_each": 2 * i,
            "Ix": 2 * i, "Iy": 2 * (i + a * (spacing / 2)**2),
            "J": 4 * i, "cx": (spacing + d) / 2, "cy": d / 2}


def bend(moment, length, inertia, outer_distance, end_force=False, e=E):
    """M means constant end moment, or root M=F*L for an end-force case."""
    angle = moment * length / (e * inertia) / (2 if end_force else 1)
    displacement = moment * length**2 / (e * inertia) / (3 if end_force else 2)
    return {"stress": moment * outer_distance / inertia, "angle": angle,
            "displacement": displacement,
            "end_force": moment / length if end_force else 0.0}


def twist(section, torque, length, g=G):
    angle = torque * length / (g * section["J"])
    if section["kind"] == "closed_rectangle":
        shear = torque / (2 * section["Am"] * section["t"])
    else:
        # Equal torque in the two circular members; no parallel-axis addition.
        shear = torque * section["d"] / (2 * section["J"])
    return {"angle": angle, "shear": shear}


def rigid_endplate_frame(section, torque, length, e=E, g=G):
    """A specific optimistic twin-tube restraint model, not a section J.

    Both tube ends are clamped against transverse-axis rotation. A rigid end
    plate twists about z, imposing +/-s*theta/2 lateral tube displacements.
    Each tube is a fixed-guided beam with lateral stiffness 12 E I / L^3.
    Joint compliance, plate flexibility, shear deflection, axial warping and
    local stresses are omitted. This is not a general bound on real hardware.
    """
    i, j, s = section["I_each"], section["J_each"], section["s"]
    k_tube = 2 * g * j / length
    k_frame = 6 * e * i * s**2 / length**3
    angle = torque / (k_tube + k_frame)
    displacement = s * angle / 2
    transverse_force = 12 * e * i * displacement / length**3
    end_bending_moment = transverse_force * length / 2
    torque_each = g * j * angle / length
    return {"angle": angle, "K_tube": k_tube, "K_frame": k_frame,
            "transverse_force_each": transverse_force,
            "end_bending_moment_each": end_bending_moment,
            "torque_each": torque_each,
            "frame_nominal_bending_stress": end_bending_moment * section["d"] / (2 * i),
            "tube_nominal_torsion_shear": torque_each * section["d"] / (2 * j),
            "torque_recovered": 2 * torque_each + transverse_force * s}


def simpson(function, end, count=1000):
    if count % 2:
        raise ValueError("Simpson count must be even")
    step = end / count
    weighted = function(0) + function(end)
    weighted += sum((4 if k % 2 else 2) * function(k * step)
                    for k in range(1, count))
    return step * weighted / 3


def checks(sections):
    """Independent reverse, unit, integration, energy and limiting checks."""
    results = []

    def close(name, actual, expected, rtol=2e-10):
        relative = abs(actual - expected) / max(abs(expected), 1e-30)
        result = {"name": name, "passed": relative <= rtol,
                  "relative_error": relative, "tolerance": rtol}
        results.append(result)
        if not result["passed"]:
            raise AssertionError(result)

    m, torque, length = 40.0, 20.0, 0.20
    for section in sections:
        label = section["id"]
        i, c = section["Ix"], section["cy"]
        for end_force in (False, True):
            case = "end_force" if end_force else "end_moment"
            r = bend(m, length, i, c, end_force)
            close(label + "/" + case + "/recover_M_from_stress", r["stress"] * i / c, m)
            close(label + "/" + case + "/recover_M_from_angle",
                  r["angle"] * E * i / length * (2 if end_force else 1), m)
            # Independent N-mm calculation (MPa=N/mm^2).
            m_nmm, l_mm, i_mm4, e_mpa = m * 1000, length * 1000, i * 1e12, E / 1e6
            delta_mm = m_nmm * l_mm**2 / (e_mpa * i_mm4 * (3 if end_force else 2))
            close(label + "/" + case + "/N_mm_vs_SI_displacement", delta_mm, r["displacement"] * 1000)
            moment_at = (lambda x: m * (1 - x / length)) if end_force else (lambda x: m)
            close(label + "/" + case + "/integrated_curvature_angle",
                  simpson(lambda x: moment_at(x) / (E * i), length), r["angle"])
            close(label + "/" + case + "/integrated_curvature_displacement",
                  simpson(lambda x: (length - x) * moment_at(x) / (E * i), length), r["displacement"])
        tr = twist(section, torque, length)
        close(label + "/recover_T_from_twist", tr["angle"] * G * section["J"] / length, torque)
        close(label + "/torsion_N_mm_vs_SI",
              torque * 1000 * (length * 1000) / ((G / 1e6) * (section["J"] * 1e12)), tr["angle"])
        # Castigliano: d(T^2 L/(2 G J))/dT = twist angle.
        step = torque * 1e-4
        energy = lambda value: value**2 * length / (2 * G * section["J"])
        close(label + "/torsion_energy_derivative",
              (energy(torque + step) - energy(torque - step)) / (2 * step), tr["angle"])
        energy_m = lambda value: value**2 * length / (2 * E * i)
        close(label + "/bending_energy_derivative",
              (energy_m(m + step) - energy_m(m - step)) / (2 * step), bend(m, length, i, c)["angle"])
        close(label + "/mass_N_mm_vs_SI",
              RHO * 1e-9 * (section["A"] * 1e6) * (length * 1000), RHO * section["A"] * length)

    rect = sections[0]
    rotated = rectangle(rect["h"], rect["b"], rect["t"], "rotated")
    close("rectangle/rotation_swaps_Ix_Iy", rotated["Ix"], rect["Iy"])
    close("rectangle/rotation_preserves_J", rotated["J"], rect["J"])
    doubled = rectangle(2 * rect["b"], 2 * rect["h"], 2 * rect["t"], "scaled")
    close("scale2/A_scales4", doubled["A"], rect["A"] * 4)
    close("scale2/I_scales16", doubled["Ix"], rect["Ix"] * 16)
    close("scale2/J_scales16", doubled["J"], rect["J"] * 16)
    close("scale2/beam_mass_scales8", RHO * doubled["A"] * length * 2, RHO * rect["A"] * length * 8)
    # Independent section integration in y, split at the inner wall boundary.
    bi, hi = rect["b"] - 2 * rect["t"], rect["h"] - 2 * rect["t"]
    integrated_ix = 2 * (simpson(lambda y: (rect["b"] - bi) * y*y, hi / 2)
                         + simpson(lambda dy: rect["b"] * (hi / 2 + dy)**2, rect["t"]))
    close("rectangle/numeric_area_moment", integrated_ix, rect["Ix"])

    twin = sections[2]
    # Bredt formula tends to exact circular-annulus J in the thin-wall limit.
    radius, wall = 0.01, 0.000002
    exact_j = math.pi / 2 * ((radius + wall / 2)**4 - (radius - wall / 2)**4)
    thin_j = 2 * math.pi * radius**3 * wall
    close("thin_wall_circular_limit", thin_j, exact_j, 2e-8)
    for l in LENGTHS:
        frame = rigid_endplate_frame(twin, torque, l)
        close(f"twin_frame/L{l}/torque_equilibrium", frame["torque_recovered"], torque)
        close(f"twin_frame/L{l}/released_frame_recovers_tube_only",
              torque / frame["K_tube"], twist(twin, torque, l)["angle"])
        # Elastic energy in two fixed-guided tubes + torsional strain energy.
        theta = frame["angle"]
        energy = lambda angle: (G * twin["J_each"] / l * angle**2
                                + 12 * E * twin["I_each"] / l**3 * (twin["s"] * angle / 2)**2)
        step = theta * 1e-4
        close(f"twin_frame/L{l}/energy_derivative_is_T",
              (energy(theta + step) - energy(theta - step)) / (2 * step), torque)
    close("twin/J_is_sum_of_local_J_only", twin["J"], 2 * twin["J_each"])
    return results


def layout_snapshot(path):
    raw = path.read_bytes()
    p = json.loads(raw)
    if p["length_unit"] != "mm" or p["mass_unit"] != "kg":
        raise ValueError("Unsupported layout units")
    joints = p["joints"]
    motor_mass = sum(j["mass_kg"] for j in joints)
    link_mass = sum(p["link_budgets_kg"])
    routes = []
    for i in (2, 4):
        a = list(joints[i]["origin_mm"])
        b = list(joints[i + 1]["origin_mm"])
        center_distance = math.dist(a, b)
        # Mirror only the route-length convention in build_layout.py, not CAD.
        a[2] += 12
        b[2] -= joints[i + 1]["diameter_mm"] / 2 + 8
        routes.append({"from": joints[i]["id"], "to": joints[i + 1]["id"],
                       "joint_center_distance_mm": center_distance,
                       "current_route_tube_length_mm": math.dist(a, b),
                       "route_endpoints_mm": [a, b],
                       "route_is_not_effective_structural_span": True})
    return {"parameter_file": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "parameter_sha256": hashlib.sha256(raw).hexdigest(), "revision": p["revision"],
            "joint_origins_mm": {j["id"]: j["origin_mm"] for j in joints},
            "joint_axis_directions": {j["id"]: j["axis"] for j in joints},
            "joint_modules_total_kg": motor_mass, "link_budgets_total_kg": link_mass,
            "arm_body_budget_including_fixed_J1_kg": motor_mass + link_mass,
            "head_budget_kg": p["head_budget_kg"], "net_payload_kg": p["payload_net_kg"],
            "budget_total_with_fixed_J1_head_payload_kg": motor_mass + link_mass + p["head_budget_kg"] + p["payload_net_kg"],
            "head_mass_sensitivity_totals_kg": [{"head_kg": h, "system_budget_kg": motor_mass + link_mass + h + p["payload_net_kg"]} for h in p["head_mass_sensitivity_kg"]],
            "unbudgeted_examples": ["base plate and anchors", "external harness or power unit"],
            "cad_route_context": routes,
            "load_context": "Section loads below are chosen sensitivity inputs, not loads derived from this kinematic model."}


def calculate(parameter_path):
    sections = [rectangle(.050, .035, .003, "RHS50x35x3"),
                rectangle(.060, .040, .003, "RHS60x40x3"), twin_tubes()]
    section_rows, bending_rows, torsion_rows, frame_rows, combined_rows = [], [], [], [], []
    for s in sections:
        section_rows.append({"id": s["id"], "kind": s["kind"],
            "envelope_mm": [s["b"] * 1000, s["h"] * 1000], "wall_mm": s["t"] * 1000,
            "area_mm2": s["A"] * 1e6, "Ix_mm4": s["Ix"] * 1e12, "Iy_mm4": s["Iy"] * 1e12,
            "torsion_J_mm4": s["J"] * 1e12,
            "J_model": "Bredt thin-wall median-line approximation" if s["kind"] == "closed_rectangle" else "sum of local circular J, with common twist and no frame contribution",
            "mass_per_m_kg": RHO * s["A"],
            "beam_only_mass_kg": {str(round(l * 1000)): RHO * s["A"] * l for l in LENGTHS},
            "specific_Ix_mm2": s["Ix"] / s["A"] * 1e6,
            "specific_Iy_mm2": s["Iy"] / s["A"] * 1e6,
            "specific_J_mm2": s["J"] / s["A"] * 1e6})
        modes = [("x", s["Ix"], s["cy"], "ideal_plane_section"),
                 ("y", s["Iy"], s["cx"], "ideal_plane_section")]
        if s["kind"] == "twin_circles":
            modes.append(("y", 2 * s["I_each"], s["d"] / 2, "no_axial_couple_equal_M_split"))
        for axis, inertia, distance, mode in modes:
            for length in LENGTHS:
                for moment in MOMENTS:
                    for end_force in (False, True):
                        r = bend(moment, length, inertia, distance, end_force)
                        bending_rows.append({"section": s["id"], "axis": axis, "connection_model": mode,
                            "load_model": "end_force_root_M_equals_FL" if end_force else "pure_end_moment",
                            "length_mm": length * 1000, "root_bending_moment_Nm": moment,
                            "end_force_N": r["end_force"], "nominal_max_stress_MPa": r["stress"] / 1e6,
                            "tip_rotation_deg": math.degrees(r["angle"]), "tip_deflection_mm": r["displacement"] * 1000,
                            "yield_min_to_nominal_stress_ratio_not_design_margin": YIELD_MIN / r["stress"]})
        for length in LENGTHS:
            for torque in TORQUES:
                r = twist(s, torque, length)
                torsion_rows.append({"section": s["id"], "length_mm": length * 1000,
                    "torque_Nm": torque, "twist_deg": math.degrees(r["angle"]),
                    "nominal_torsion_shear_MPa": r["shear"] / 1e6,
                    "torsional_stiffness_Nm_per_rad": G * s["J"] / length})
                if s["kind"] == "twin_circles":
                    frame = rigid_endplate_frame(s, torque, length)
                    frame_rows.append({"length_mm": length * 1000, "torque_Nm": torque,
                        "twist_deg": math.degrees(frame["angle"]),
                        "tube_only_twist_deg": math.degrees(r["angle"]),
                        "tube_torsion_stiffness_Nm_per_rad": frame["K_tube"],
                        "frame_coupling_stiffness_Nm_per_rad": frame["K_frame"],
                        "transverse_force_per_tube_N": frame["transverse_force_each"],
                        "end_bending_moment_per_tube_Nm": frame["end_bending_moment_each"],
                        "torque_per_tube_Nm": frame["torque_each"],
                        "frame_nominal_bending_stress_MPa": frame["frame_nominal_bending_stress"] / 1e6,
                        "tube_torsion_shear_MPa": frame["tube_nominal_torsion_shear"] / 1e6,
                        "torque_equilibrium_recovered_Nm": frame["torque_recovered"]})
        for moment in MOMENTS:
            for torque in TORQUES:
                sigma = moment * s["cy"] / s["Ix"]
                tau = twist(s, torque, .2)["shear"]
                vm = math.sqrt(sigma**2 + 3 * tau**2)
                combined_rows.append({"section": s["id"], "weak_axis_M_Nm": moment, "T_Nm": torque,
                    "nominal_von_Mises_MPa": vm / 1e6,
                    "yield_min_to_nominal_vm_ratio_not_design_margin": YIELD_MIN / vm,
                    "caveat": "Nominal section screening. No holes, end effects, preload, fatigue or twin-frame-induced stress included."})
    test_results = checks(sections)
    return {"schema_version": 1, "revision": "structure-screening-01", "source_review_date": "2026-09-27",
            "status": "NON-FROZEN analytical section screening; NOT a 2 kg robot qualification",
            "coordinate_system": "beam z longitudinal; x along width or twin center spacing; y along section height",
            "layout_snapshot": layout_snapshot(parameter_path),
            "material": {"designation": "6061-T6 extruded tube/profile, unwelded parent metal",
                "E_Pa": E, "G_Pa": G, "density_kg_m3": RHO, "yield_min_Pa": YIELD_MIN,
                "poisson_ratio_inferred_from_E_G": E / (2 * G) - 1,
                "moduli_status": "Published guidance values, not certified material tolerance intervals",
                "yield_scope": "Thyssenkrupp extruded profiles/tubes t<=5 mm; Hydro T6/T6511 extrusions t<=6.30 mm: Rp0.2 >=240 MPa. Selected wall=3 mm. No upper bound inferred.",
                "not_applicable_to": ["weld heat-affected zone", "unknown temper", "3D printed polymer", "machined joints with holes without local analysis"]},
            "sensitivity_inputs": {"length_mm": [l * 1000 for l in LENGTHS], "bending_moment_Nm": MOMENTS,
                "torque_Nm": TORQUES,
                "modulus_assumed_scale_factors_not_vendor_tolerances": [0.95, 1.0, 1.05],
                "compliance_multipliers_for_those_scales": [1 / f for f in (0.95, 1, 1.05)],
                "modulus_sensitivity_scope": "Scale E and G together; deflection/rotation inversely scale, force-controlled nominal stress does not. This is a chosen numerical sensitivity, not a measured material range."},
            "sections": section_rows, "bending_cases": bending_rows, "torsion_cases": torsion_rows,
            "twin_rigid_endplate_torsion_cases": frame_rows, "nominal_combined_stress_cases": combined_rows,
            "connection_scale_examples_not_fastener_sizing": {
                "bending_M_Nm": 60, "force_couple_separation_mm": 40, "row_force_N": 60 / .04,
                "torsion_Nm": 20, "bolt_circle_diameter_mm": 50, "equally_loaded_bolts": 4,
                "ideal_tangential_force_per_bolt_N": 20 / (.025 * 4)},
            "exclusions": ["actual joint loads/accelerations/impacts", "joint/gear/bearing compliance",
                "bolt preload and slip", "holes, local bearing, wall crushing, buckling and fatigue",
                "corner radii and extrusion tolerances", "transverse shear deflection",
                "end-plate flexibility", "complete TCP deflection and positioning accuracy",
                "connection, harness and armor mass", "printed structure qualification"],
            "sources": SOURCES, "self_checks": {"all_passed": all(c["passed"] for c in test_results),
                "count": len(test_results), "scope": "Numerical/formula consistency only, not hardware validation", "results": test_results}}


def compare(saved, current, trail="root"):
    """Tolerant float comparison, exact keys/strings; portable JSON --check."""
    if isinstance(current, dict):
        if not isinstance(saved, dict) or saved.keys() != current.keys():
            raise AssertionError(f"Different keys at {trail}")
        for key in current:
            compare(saved[key], current[key], trail + "." + key)
    elif isinstance(current, (list, tuple)):
        if not isinstance(saved, (list, tuple)) or len(saved) != len(current):
            raise AssertionError(f"Different length at {trail}")
        for i, value in enumerate(current):
            compare(saved[i], value, f"{trail}[{i}]")
    elif isinstance(current, float):
        if not isinstance(saved, (int, float)) or not math.isclose(saved, current, rel_tol=1e-10, abs_tol=1e-12):
            raise AssertionError(f"Different value at {trail}: {saved} != {current}")
    elif saved != current:
        raise AssertionError(f"Different value at {trail}: {saved} != {current}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parameters", type=Path, default=ROOT / "engineering/parameters/r4-layout.json")
    parser.add_argument("--output", type=Path, default=ROOT / "analysis/structure-screening.json")
    parser.add_argument("--check", action="store_true", help="recompute and verify existing JSON; do not write")
    args = parser.parse_args()
    report = calculate(args.parameters.resolve())
    if args.check:
        compare(json.loads(args.output.read_text()), report)
        action = "verified"
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        action = "wrote"
    print(f"{action} {args.output}; {report['self_checks']['count']} numerical self-checks passed")


if __name__ == "__main__":
    main()
