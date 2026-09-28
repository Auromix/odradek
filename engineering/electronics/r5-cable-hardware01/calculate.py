#!/usr/bin/env python3
"""R5-CABLE-HARDWARE01: conditional cable screening, not an assembly release.

Original calculation/organization: CC-BY-NC-4.0. SI internally except catalogue
inputs explicitly in inches/lbf/lb per 100 ft. No network or CAD dependencies.
"""
from pathlib import Path
import csv
import hashlib
import json
import math

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INCH = 0.0254
LBF = 4.4482216152605
LB = 0.45359237
FT = 0.3048
LIFE_FACTOR = 10.0  # manufacturer life-optimization guideline, not safety law


def dump(name, obj):
    (HERE / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def csv_out(name, rows):
    with (HERE / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    data = json.loads((HERE / "catalogue-data.json").read_text())
    scenarios, combinations = [], {}
    checks = []
    for pair in data["combinations"]:
        cable = data["cables"][pair["cable"]]
        pulley = data["pulleys"][pair["pulley"]]
        b = cable["min_break_lbf"] * LBF
        ratio = pulley["root_in"] / cable["diameter_nominal_in"]
        worst_ratio = ((pulley["root_in"] - pulley["legacy_root_tolerance_in"]) /
                       (cable["diameter_nominal_in"] + cable["legacy_od_plus_in"]))
        # All evaluated ratios, nominal and legacy full-tolerance, exceed 20.
        # Use the lower 20:1 manufacturer bin (0.91), never interpolate silently.
        assert ratio >= 20 and worst_ratio >= 20
        eta_bend = 0.91
        bend_break = b * eta_bend
        c = {
            "cable": pair["cable"], "pulley": pair["pulley"],
            "role": pair["role"], "selection_status": pair["status"],
            "diameter_nominal_mm": cable["diameter_nominal_in"] * 25.4,
            "mass_g_per_m": cable["mass_lb_per_100ft"] * LB / (100 * FT) * 1000,
            "min_break_N": b, "root_over_d_nominal": ratio,
            "legacy_full_tolerance_root_over_d": worst_ratio,
            "nominal_root_over_d_ge25": ratio >= 25,
            "legacy_full_tolerance_root_over_d_ge25": worst_ratio >= 25,
            "max_actual_d_mm_for_25_with_legacy_root_min":
                (pulley["root_in"] - pulley["legacy_root_tolerance_in"]) * 25.4 / 25,
            "root_min_required_mm_for_legacy_cable_max":
                25 * (cable["diameter_nominal_in"] + cable["legacy_od_plus_in"]) * 25.4,
            "bend_efficiency_screen": eta_bend,
            "bend_reduced_break_proxy_N": bend_break,
            "conditional_T_ceiling_N_at_term_eta1_and_guideline10": bend_break / LIFE_FACTOR,
            "conditional_T_ceiling_N_at_term_eta085_and_guideline10": min(bend_break, b * .85) / LIFE_FACTOR,
            "extra_product_derating_sensitivity_N_eta085": bend_break * .85 / LIFE_FACTOR,
            "termination_eta_verified": None,
            "qualified_working_tension_N": None,
            "radial_load_legacy_basis_N_at500rpm": pulley["legacy_radial_load_lbf"] * LBF,
            "fixed_pulley_rpm_at_cable_speed_m_s": {
                str(v): 60*v/(math.pi*(pulley["root_in"] + cable["diameter_nominal_in"])*INCH)
                for v in [0.2, 0.225, 0.45]
            },
            "fixed_pulley_cable_speed_m_s_at500rpm":
                500*math.pi*(pulley["root_in"] + cable["diameter_nominal_in"])*INCH/60,
        }
        combinations[pair["id"]] = c
        for t in pair["loads_N"]:
            for turn in [90, 180]:
                load = 2*t*math.sin(math.radians(turn/2))
                scenarios.append({
                    "combination": pair["id"], "role": pair["role"], "T_N": t,
                    "direction_deflection_deg": turn, "pulley_radial_load_N": load,
                    "legacy500rpm_radial_rating_over_load": c["radial_load_legacy_basis_N_at500rpm"]/load,
                    "straight_break_over_T": b/t,
                    "bend_break_proxy_over_T": bend_break/t,
                    "bend_proxy_meets_guideline10": bend_break/t >= LIFE_FACTOR,
                    "minimum_terminal_retention_fraction_for_guideline10": LIFE_FACTOR*t/b,
                    "terminal_retention_measured": False,
                    "assembly_qualified": False,
                })
        checks.extend([
            {"id": pair["id"]+"_bend_bin_covers_nominal_and_legacy_worst", "pass": worst_ratio >= 20},
            {"id": pair["id"]+"_nominal_cable_fits_current_max", "pass": cable["diameter_nominal_in"] <= pulley["max_cable_current_in"]},
        ])
    primary = [combinations[k] for k in ["leaf_upgrade", "secondary_upgrade"]]
    checks.extend([
        {"id": "middle50_100_bend_proxy10_pass_conditionally", "pass": all(c["conditional_T_ceiling_N_at_term_eta1_and_guideline10"] >= t for c,t in zip(primary,[50,100]))},
        {"id": "high75_150_bend_proxy10_fails", "pass": all(c["conditional_T_ceiling_N_at_term_eta1_and_guideline10"] < t for c,t in zip(primary,[75,150]))},
        {"id": "full_tolerance25_ratio_gap_retained", "pass": all(not c["legacy_full_tolerance_root_over_d_ge25"] for c in primary)},
        {"id": "no_terminal_qualified_by_calculation", "pass": all(c["qualified_working_tension_N"] is None for c in combinations.values())},
        {"id": "force_vector180_is2T", "pass": abs(2*100*math.sin(math.pi/2)-200) < 1e-12},
        {"id": "conversion90lbf", "pass": abs(90*LBF-400.339945373445) < 1e-9},
    ])
    budget = {
        "revision": "R5-CABLE-HARDWARE01", "status": "conditional component screening; not assembly-qualified",
        "load_inputs_are_conditions_not_measured_or_solved": True,
        "life_optimization_factor": LIFE_FACTOR,
        "life_factor_scope": "manufacturer's 10x straight-cable guideline, extended here conservatively to weak-link break proxies; distinct from workpiece load factor",
        "weak_link_model": "Bsystem_proxy=min(B*eta_bend, B*eta_term, anchor_failure_load, other_failure_load); unknown entries prevent a qualified rating",
        "multiplication_warning": "eta_bend and eta_term refer to separate sites; do not multiply by default or once per pulley. Extra product derating is only a sensitivity.",
        "pulley_force_model": "equalT: P=2*T*sin(deflection/2); unequalT: P=sqrt(T1^2+T2^2-2*T1*T2*cos(deflection)); add moving-body force separately",
        "moving_pulley_velocity_model": "two parallel, no-slip runs: vc=(v1+v2)/2; abs(omega)=abs(v1-v2)/(Droot+d); signed run speeds share one spatial axis",
        "cable_stiffness_N_per_m": None, "friction_efficiency": None,
        "cycle_life": None, "pulley_max_rpm": None, "temperature_limit": None,
        "combinations": combinations,
        "checks": checks,
    }
    dump("budget.json", budget)
    csv_out("load-scenarios.csv", scenarios)
    interfaces = {
        "revision": "R5-CABLE-HARDWARE01", "unit": "mm",
        "scope": "original catalogue envelopes only; no actual route, axle, fork or pull-point hole frozen",
        "carrier_input": {"A_local_mm": ["R+13",0,-12],"R_range_mm":[31,91],"closing_pull_direction":"-er","initial_available_head_Z_mm":"less than -17; not clash-certified"},
        "pulley_local_frame": "wheel axis=Z; groove radial plane=XY; origin at nominal bearing/pulley midplane, centering not tolerance-certified",
        "pulleys": {},
        "termination_planning": {
            "main_sleeves": {"leaf":"7030C", "secondary":"7047C"},
            "optional_thimbles": {"leaf":"AN100C01", "secondary":"AN100C03"},
            "actual_loop_bbox_mm": None,
            "anchor_PN": None,
            "bare_loop_geometric_example_only": {
                "leaf_pin_P_mm":6,"leaf_bearing_point_to_sleeve_D_min_mm":15,
                "secondary_pin_P_mm":7,"secondary_bearing_point_to_sleeve_D_min_mm":17.5,
                "leaf_min_bearing_point_to_sleeve_far_end_mm":15+.28*25.4,
                "secondary_min_bearing_point_to_sleeve_far_end_mm":17.5+.44*25.4,
                "caveat":"P>=5*legacy cable OD max; D>=2.5P; bare smooth pins are original planning variables, not selected parts or qualified wear/retention. Thimble dimensions cannot be substituted for pin P without an assembly drawing. Cable tail length TBD."
            }
        },
        "integration_gaps": ["current controlled drawing/tolerance revisions", "inner-race shoulder diameter and actual centering", "axle fit/retention and double-shear fork design", "groove conformity for actual wire OD", "end eye geometry/strength/tool cavity verification", "anti-derailment/fleet angle and all swept paths", "slack take-up/preload and moving masses", "friction/stretch and reversal fatigue"]
    }
    for name in ["SP3106", "SP4125"]:
        p=data["pulleys"][name]
        d,e,od=p["bearing_width_in"]*25.4,p["nylon_width_in"]*25.4,p["outside_in"]*25.4
        interfaces["pulleys"][name]={
            "nominal_body_bbox_mm":[[-od/2,-od/2,-max(d,e)/2],[od/2,od/2,max(d,e)/2]],
            "legacy_tolerance_planning_bbox_mm":[[-(od+.020*25.4)/2,-(od+.020*25.4)/2,-(max(d,e)+.010*25.4)/2],[(od+.020*25.4)/2,(od+.020*25.4)/2,(max(d,e)+.010*25.4)/2]],
            "root_diameter_mm":p["root_in"]*25.4,
            "bore_legacy_mm":p["legacy_bore_in"]*25.4,
            "bore_legacy_tolerance_mm":.0005*25.4,
            "bore_current_web_mm":p["bore_current_in"]*25.4,
            "nylon_width_mm":e,"bearing_width_mm":d,
            "groove_radius_reference_mm":p["groove_radius_in"]*25.4,
            "nominal_per_side_bearing_over_nylon_projection_mm":(d-e)/2,
            "legacy_min_per_side_projection_mm_assuming_centered":((p["bearing_width_in"]-.010)-(p["nylon_width_in"]+.010))*25.4/2,
            "axial_spacer_inner_land_OD_mm":None,
            "extended_inner_race":False,"mass_kg":None,
            "geometry_kind":"bounding solid only, not manufacturer CAD; separate inner-race-only spacers required; envelopes exclude axle/fork/guards/cable"
        }
    dump("mechanical-interface.json",interfaces)
    bom=[]
    for role,k,pk,sk,tk in [("leaf","2037","SP3106","7030C","AN100C01"),("secondary","2050","SP4125","7047C","AN100C03")]:
        for kind,part,fact,qty,unit,note in [
            ("bare cable",k,data["cables"][k],"TBD","m","length/routing unknown; no stock or price verification"),
            ("pulley",pk,data["pulleys"][pk],"1 per required wheel","each","total count/axle/spacer/guard unknown; controlled drawing gap"),
            ("standard loop sleeve",sk,data["terminations"][sk],"1 per terminated eye","each","tool/cavity and retention process unqualified"),
            ("optional thimble",tk,data["terminations"][tk],"TBD per qualified eye","each","not a frozen termination assembly; pin/envelope/retention unresolved")]:
            bom.append(dict(role=role,kind=kind,manufacturer="Sava",part=part,item=fact["item"],qty=qty,unit=unit,status="candidate",unit_mass_g="TBD",price="TBD",source=fact["url"],gap=note))
    bom += [dict(role="tool",kind="prototype crimper",manufacturer="Sava",part="T185",item="101904",qty="1 shared",unit="each",status="candidate",unit_mass_g="TBD",price="TBD",source="https://www.savacable.com/crimping-tool-light-duty",gap="legacy cavities D/B for selected bare sleeve sizes; current revision/process confirmation and destructive coupons required")]
    for kind,note in [("wheel axle and retention","no exact catalogue shaft selected; inch bore and tolerance unresolved"),("inner-race-only spacers and double-shear fork","inner-race contact land diameter unknown; must not clamp nylon"),("anchor pin and lug/eye","carrier end hole not designed; contact pressure/bending/wear/retention unverified"),("anti-derailment guide and cable guards","actual fleet angle and slot clearances unknown"),("cable cutting tool and inspection gauges","cut quality and correct die/gauging method must be qualified")]:
        bom.append(dict(role="integration",kind=kind,manufacturer="TBD",part="TBD",item="TBD",qty="TBD",unit="each",status="TBD",unit_mass_g="TBD",price="TBD",source="",gap=note))
    csv_out("bom.csv",bom)
    generate_svg(combinations, interfaces)
    assert all(x["pass"] for x in checks)
    print(json.dumps({"checks_passed":len(checks),"conditional_max_N":[c["conditional_T_ceiling_N_at_term_eta1_and_guideline10"] for c in primary]}))


def generate_svg(combos, interfaces):
    # Original explanatory diagram, not copied manufacturer drawing or fabrication drawing.
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="750" viewBox="0 0 1100 750">',
         '<rect width="1100" height="750" fill="#f5f7fa"/>',
         '<style>text{font-family:Arial,sans-serif;fill:#172c42} .h{font-size:23px;font-weight:bold}.s{font-size:16px}.sm{font-size:14px}.dim{stroke:#50667d;stroke-width:1.3}.load{stroke:#df790d;stroke-width:3;fill:none}</style>',
         '<text x="35" y="42" class="h">R5-CABLE-HARDWARE01 / conditional component screen</text>',
         '<text x="35" y="69" class="s">Original catalogue-envelope illustration. No cable route or assembly release.</text>']
    for i,key in enumerate(["leaf_upgrade","secondary_upgrade"]):
        c=combos[key]; p=interfaces["pulleys"][c["pulley"]]; cx=205+i*515;cy=216;scale=4
        rad=p["nominal_body_bbox_mm"][1][0]*scale; rr=p["root_diameter_mm"]*scale/2
        svg += [f'<circle cx="{cx}" cy="{cy}" r="{rad}" fill="#d5e6f2" stroke="#254c6e" stroke-width="2"/>',f'<circle cx="{cx}" cy="{cy}" r="{rr}" fill="none" stroke="#548ca8" stroke-width="2" stroke-dasharray="5 4"/>',f'<circle cx="{cx}" cy="{cy}" r="{p["bore_legacy_mm"]*scale/2}" fill="white" stroke="#254c6e"/>',f'<text x="{cx-150}" y="112" class="h">{c["cable"]} + {c["pulley"]}</text>',f'<text x="{cx-150}" y="325" class="s">OD {rad*2/scale:.2f} / root {rr*2/scale:.4f} mm</text>',f'<text x="{cx-150}" y="350" class="s">wire d {c["diameter_nominal_mm"]:.4f} mm / ratio {c["root_over_d_nominal"]:.3f}</text>',f'<text x="{cx-150}" y="375" class="s">bearing width {p["bearing_width_mm"]:.4f} mm</text>',f'<text x="{cx-150}" y="400" class="s">bore {p["bore_legacy_mm"]:.4f} +/- 0.0127 mm (legacy)</text>',f'<text x="{cx-150}" y="431" class="s">conditional tension ceiling {c["conditional_T_ceiling_N_at_term_eta1_and_guideline10"]:.2f} N *</text>']
    svg += ['<line x1="40" y1="454" x2="1060" y2="454" class="dim"/>',
        '<text x="35" y="482" class="s">* B x 0.91 / 10 with ideal terminal retention; actual permitted tension is NOT yet established.</text>',
        '<text x="35" y="510" class="s">Legacy full-tolerance D/d falls below 25 for both pairs. OD/process confirmation is required.</text>',
        '<text x="35" y="538" class="s">SP4125 bearing and nylon widths are nominally equal: never clamp the rotating nylon faces.</text>',
        '<text x="35" y="566" class="s">Inner-race-only spacers, forks, axle retention, thimble loops and anti-derailment guards remain TBD.</text>',
        '<path d="M165 707 L165 637 A43 43 0 0 1 251 637 L251 707" class="load"/>',
        '<circle cx="208" cy="637" r="35" fill="none" stroke="#254c6e" stroke-width="2"/>',
        '<text x="117" y="722" class="s">T</text><text x="270" y="722" class="s">T</text>',
        '<text x="350" y="617" class="s">180-degree cable turnaround: axle force = 2T, not T.</text>',
        '<text x="350" y="645" class="s">Legacy 90 lbf = 400.34 N radial rating at 500 rpm;</text>',
        '<text x="350" y="673" class="s">2500 h average-life basis is not 1 Hz reversing-cable life.</text>',
        '<text x="350" y="716" class="sm">No pulley mass, friction, stiffness or endurance value is invented.</text></svg>']
    (HERE/"component-screen.svg").write_text("\n".join(svg)+"\n")


if __name__ == "__main__":
    main()
