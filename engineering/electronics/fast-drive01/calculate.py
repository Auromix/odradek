# SPDX-License-Identifier: CC-BY-NC-4.0
# Attribution: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""FAST-DRIVE01: conditional single-master actuator screening, SI internally.

No contact geometry, heat rejection, holding brake, or production qualification
is inferred by this calculation. Only task-owned generated files are written.
"""
import csv
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
KIN = ROOT / "engineering/generated/fast-finger-kin01"
G0 = 9.80665
T = 0.5


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def save_csv(name, data):
    with (HERE / name).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def profile(u):
    # Unitless s and time derivatives in s^-1 and s^-2.
    return (10*u**3 - 15*u**4 + 6*u**5,
            (30*u**2 - 60*u**3 + 30*u**4)/T,
            (60*u - 180*u**2 + 120*u**3)/T**2)


def main():
    fingers = rows(KIN / "finger-inputs.csv")
    ds = [math.radians(float(f["range_deg"])) for f in fingers]
    js = [float(f["J_axis_kg_m2"]) for f in fingers]
    gs = [float(f["worst_gravity_Nm"]) for f in fingers]
    mass_fingers = sum(float(f["mass_kg"]) for f in fingers)
    ms = sum(j*d*d for j, d in zip(js, ds))
    gravity_qs_bound = sum(g*d for g, d in zip(gs, ds))
    sdot = 1.875/T
    sddot = 10/math.sqrt(3)/T**2
    beta = math.pi
    ratio = 50.0  # exact ratio, not the rounded 49 of another gear family
    motor_j = 48e-7  # g cm^2 -> kg m^2
    gear_j = 196e-9  # g mm^2 -> kg m^2; supplier MAX incl pinion
    encoder_j = .08e-7
    jin = motor_j + gear_j + encoder_j
    j_master_fingers = ms/beta**2
    gravity_master = gravity_qs_bound/beta
    omega_peak = beta*sdot
    motor_rpm_peak = omega_peak*ratio*60/(2*math.pi)
    empty = []
    for eta in (.50, .65, .77):
        motor_abs, out_abs, output_power = [], [], []
        for k in range(10001):
            _, v, a = profile(k/10000)
            om, al = beta*v, beta*a
            rpm = abs(om)*ratio*60/(2*math.pi)
            # Bounds add maximum gravity at every point; not an actual trajectory.
            tout = j_master_fingers*abs(al)+gravity_master
            tm = jin*ratio*abs(al)+tout/(ratio*eta)+.00204+.000000924*rpm
            motor_abs.append(tm)
            out_abs.append(tout)
            output_power.append(tout*abs(om))
        empty.append({
            "assumed_dynamic_gear_efficiency": eta,
            "motor_abs_torque_bound_peak_Nm": max(motor_abs),
            "motor_abs_torque_bound_sample_RMS_Nm": math.sqrt(sum(x*x for x in motor_abs)/len(motor_abs)),
            "motor_torque_over_kt_A_not_DC_bus_or_driver_RMS": max(motor_abs)/.0281,
            "output_torque_bound_peak_Nm": max(out_abs),
            "output_power_bound_peak_W": max(output_power),
            "omissions": "new linkage inertia, preload, bearing/cable friction, seals, motor-controller losses",
        })
    motion = []
    for degrees in (90, 120, 180, 360):
        b = math.radians(degrees)
        for reduction in (45, 50, 66):
            output_rpm = b*sdot*60/(2*math.pi)
            motion.append({"master_stroke_deg": degrees, "exact_or_candidate_ratio": reduction,
                           "master_peak_rpm": output_rpm, "motor_peak_rpm": output_rpm*reduction,
                           "within_32GPT_HT_7000rpm_continuous_input": output_rpm*reduction <= 7000,
                           "within_3274_24V_no_load_8820rpm": output_rpm*reduction <= 8820,
                           "qualification": "speed-only; ratio45 not selected or separately ordered"})
    contact, linear = [], []
    # Equal force allocation, point contact, fixed arms are assumptions, not CAD output.
    for mu in (.2, .4, .6, .8):
        normal = 2*2*G0/(4*mu)
        tangential = 2*2*G0/4
        for arm_mm in (40, 60, 80, 100, 120):
            ell_n, ell_t = arm_mm/1000, .03
            qs_n = sum(ds)*normal*ell_n
            qs_t = sum(ds)*tangential*ell_t
            q_plus = qs_n+qs_t+gravity_qs_bound
            torque = q_plus/beta
            item = {
                "assumed_mu": mu, "four_equal_contacts_object_mass_kg": 2,
                "vertical_load_multiplier": 2, "normal_arm_mm": arm_mm, "tangent_arm_mm": 30,
                "per_finger_normal_N": normal, "per_finger_tangent_N": tangential,
                "normal_component_master_torque_Nm": qs_n/beta,
                "same_sign_contact_plus_finger_gravity_bound_Nm": torque,
                "gear_7p4Nm_continuous_limit_met_for_this_assumption": torque <= 7.4,
                "ideal_lossless_motor_static_torque_Nm": torque/ratio,
                "coefficient_needed_for_0p140Nm_motor_static_budget": torque/(ratio*.140),
                "coefficient_needed_for_0p158Nm_motor_static_budget": torque/(ratio*.158),
                "geared_14W_continuous_speed_ceiling_rpm_at_torque": 14/torque*60/(2*math.pi),
                "note": "coefficient is REQUIRED measured static transfer ratio normalized by G, NOT claimed static efficiency; 0.140/0.158 not qualified installed ratings",
            }
            for kappa in (.50, .65, .77):
                item[f"assumed_static_transfer_{kappa:.2f}_motor_Nm"] = torque/(ratio*kappa)
            contact.append(item)
            for stroke_mm in (20, 30, 50):
                for lead_mm in (2.5, 5):
                    stroke, lead = stroke_mm/1000, lead_mm/1000
                    force = q_plus/stroke
                    linear.append({"assumed_mu": mu,"normal_arm_mm":arm_mm,"tangent_arm_mm":30,
                                   "slider_stroke_mm":stroke_mm,"lead_mm":lead_mm,
                                   "peak_linear_speed_mm_s":stroke_mm*sdot,
                                   "direct_motor_peak_rpm":stroke_mm*sdot/lead_mm*60,
                                   "contact_plus_finger_gravity_axial_N":force,
                                   "ideal_lossless_motor_torque_Nm":force*lead/(2*math.pi),
                                   "required_static_transfer_for_0p140Nm_motor":force*lead/(2*math.pi*.140),
                                   "static_transfer_unverified":True})
    selected = next(x for x in contact if x["assumed_mu"] == .4 and x["normal_arm_mm"] == 60)
    linear_selected = next(x for x in linear if x["assumed_mu"] == .4 and x["normal_arm_mm"] == 60
                           and x["slider_stroke_mm"] == 50 and x["lead_mm"] == 2.5)
    # Independently verify virtual work and analytic extrema, not implementation-only assertions.
    per_n = 2*2*G0/(4*.4)
    assert math.isclose(sum(d*(per_n*.06) for d in ds), selected["normal_component_master_torque_Nm"]*beta, rel_tol=1e-12)
    assert math.isclose(sum(j*(d*sdot)**2/2 for j,d in zip(js,ds)), .5*j_master_fingers*omega_peak**2, rel_tol=1e-12)
    assert abs(profile(0)[0]) < 1e-12 and abs(profile(1)[0]-1) < 1e-12
    assert abs(profile(0)[1])+abs(profile(1)[1])+abs(profile(0)[2])+abs(profile(1)[2]) < 1e-12
    assert math.isclose(profile(.5)[1], sdot, rel_tol=1e-12)
    assert math.isclose(abs(profile((3-math.sqrt(3))/6)[2]), sddot, rel_tol=1e-12)
    assert math.isclose(jin*ratio**2, .01251, rel_tol=1e-12)
    assert math.isclose(motor_rpm_peak, 5625, rel_tol=1e-12)
    # Compare independent normal-only result against the mathematical team's CSV.
    cross = rows(KIN / "single-master-contact.csv")
    reference = next(x for x in cross if x["assumed_mu"] == "0.4" and x["normal_moment_arm_mm"] == "60.0"
                     and x["actuator_type"] == "rotary_master" and x["master_full_stroke_deg"] == "180")
    assert math.isclose(float(reference["normal_component_torque_Nm"]), selected["normal_component_master_torque_Nm"], rel_tol=1e-12)
    result = {
        "revision":"FAST-DRIVE01-single-central-drive",
        "license":"CC-BY-NC-4.0", "attribution":"Odradek — Auromix contributors",
        "status":"conditional actuator preselection; no production or 2kg grip rating",
        "requirements":{"active_motors":1,"mechanically_coupled_petals":4,"empty_roundtrip_max_s":1,
                        "object_mass_net_kg":2,"head_mass_added_separately":True,
                        "head_mass_design_aspiration_kg_not_user_requirement":1.5},
        "source_hashes":{str(p.relative_to(ROOT)):sha(p) for p in [KIN/"finger-inputs.csv",KIN/"single-master-contact.csv",
                                ROOT/"engineering/generated/head-mass04/mass-properties.json",ROOT/"docs/engineering/sources/fast-drive01.json"]},
        "script_sha256":sha(Path(__file__)),
        "motor_rotor_kg_m2":motor_j,"gear_input_with_pinion_max_kg_m2":gear_j,"encoder_magnet_kg_m2":encoder_j,
        "finger_only_mass_kg_historical_geometry":mass_fingers,"finger_generalized_inertia_Joule_second2":ms,
        "single_master":{"stroke_deg":180,"ratio_exact":ratio,"upper_ratio":109/180,"lower_ratio":122/180,
                         "peak_output_rpm":omega_peak*60/(2*math.pi),"peak_motor_rpm":motor_rpm_peak,
                         "peak_master_accel_rad_s2":beta*sddot,"finger_referred_inertia_kg_m2":j_master_fingers,
                         "motor_gear_encoder_referred_inertia_kg_m2":jin*ratio**2,
                         "finger_gravity_absolute_sum_bound_Nm":gravity_master,
                         "peak_kinetic_energy_known_components_J":.5*(j_master_fingers+jin*ratio**2)*omega_peak**2,
                         "energy_note":"energy in moving components at one midpoint, not guaranteed DC bus returned energy; do not multiply by four motors",
                         "empty_cases":empty,"contact_example":selected},
        "linear_alternative":linear_selected,
        "head_mass_lower_bounds_kg":{"motor_gear_encoder":.325+.230+.0135,
                                      "plus_historical_fingers":.325+.230+.0135+mass_fingers,
                                      "plus_MC5010_in_head":.325+.230+.0135+mass_fingers+.270,
                                      "AK70_plus_historical_fingers":.621+mass_fingers,
                                      "direct3274_encoder_plus_historical_fingers_before_screw":.325+.0135+mass_fingers},
        "network":{"native_ET_servo_plus_7_RH_plus_HEAD_IO_stations":9,"CAN_bridge_single_servo_plus_7_RH_plus_HEAD_IO_stations":8,
                   "old_12_station_four_servo_scheme":"superseded by single-master requirement"},
        "checks_passed":["quintic endpoints and analytic extrema","gcm2/gmm2 conversion","virtual work","energy coordinate invariance",
                         "5625rpm selected speed","independent FAST-KIN normal-contact comparison"],
        "excluded_from_qualification":["actual light-face contact geometry/pressure and friction","four-way compliance and linkage synthesis",
                                      "zero-speed thermal performance in enclosure","joint brake and power-off force retention",
                                      "complete assembly PN/CAD/tolerances","all new moving mass and friction","regenerative energy path"]
    }
    (HERE/"budget.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    save_csv("motion-comparison.csv",motion)
    save_csv("contact-sensitivity.csv",contact)
    save_csv("linear-comparison.csv",linear)
    manifest={str(p.relative_to(ROOT)):sha(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name!="manifest.json"}
    (HERE/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({"checks":"PASS","rotary":result["single_master"],"linear":linear_selected,
                      "mass_lower_bounds":result["head_mass_lower_bounds_kg"]},indent=2))


if __name__ == "__main__":
    main()
