# SPDX-License-Identifier: CC-BY-NC-4.0
# Attribution: Auromix Odradek contributors.
"""HEAD-POWER01 resistive DC planning; not transient/thermal/regen approval.

Run with Python >=3.10. Reads frozen upstream budgets; writes only beside itself.
Optional --source-dir points to locally downloaded official documents for hash QA.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
INPUTS = [
    "docs/engineering/sources/head-power01.json",
    "engineering/electronics/head-ctrl02/control-contract.json",
    "engineering/electronics/head-ctrl02/bom.csv",
    "engineering/electronics/head-passives01/catalog.json",
    "engineering/electronics/final-petal-fpl01/upper/mechanical-power-budget.json",
    "engineering/electronics/final-petal-fpl01/lower/mechanical-power-budget.json",
    "engineering/electronics/central-display-cd01/power-budget.json",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: str) -> dict:
    return json.loads((REPO / path).read_text())


def csv_write(name: str, rows: list[dict]) -> None:
    with (HERE / name).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def solve_trunk(source_v: float, resistance: float, motor_a: float,
                aux_w: float) -> dict:
    """High-voltage root: Vh=Vs-R*(Im+Paux/Vh); no current-limit dynamics."""
    b = source_v - resistance * motor_a
    disc = b*b - 4 * resistance * aux_w
    if disc <= 0:
        raise ValueError("No high-voltage static operating point")
    head_v = (b + math.sqrt(disc)) / 2
    current = motor_a + aux_w / head_v
    return dict(head_V=head_v, trunk_A=current,
                line_loss_W=current**2 * resistance,
                source_W=source_v * current,
                motor_at_head_W=head_v * motor_a,
                aux_at_head_W=aux_w,
                energy_residual_W=source_v * current -
                (head_v * motor_a + aux_w + current**2 * resistance),
                kcl_residual_A=(source_v - head_v) / resistance - current)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path)
    args = parser.parse_args()
    cfg = read(INPUTS[0]); a = cfg["assumptions"]
    u, lo, c = [read(p) for p in INPUTS[-3:]]
    vled_w = 2*u["P_VLED_W_before_blanking"] + 2*lo["P_VLED_W_before_blanking"] + c["VLED_power_W_20mA"]
    vio_w = 2*u["logic_planning_W_not_datasheet_max"] + 2*lo["logic_planning_W_not_datasheet_max"] + c["logic_planning_W_not_datasheet_max"]
    vled_peak = 2*u["I_LED_peak_A_at20mA"] + 2*lo["I_LED_peak_A_at20mA"] + c["total_VLED_peak_A_20mA"]
    rails = dict(logic_budget_W=3.3*a["logic_budget_A"],
                 LED_budget_W=3.3*a["led_budget_A"],
                 VLED_baseline_W=vled_w, lighting_VIO_planning_W=vio_w,
                 light_total_baseline_W=vled_w+vio_w,
                 VLED_baseline_mean_A=vled_w/3.3, VLED_baseline_peak_A=vled_peak,
                 first_light_VLED_mean_W=vled_w*3/20,
                 first_light_VLED_peak_A=vled_peak*3/20,
                 note="logic 1A includes lighting VIO; no double counting 4.074W+3.3W; baseline is not measurement")
    wires = [dict(name="LAPP0028170_2x1", r20_ohm_per_m=.0195, area_mm2=1),
             dict(name="LAPP0028181_3G2p5", r20_ohm_per_m=.00798, area_mm2=2.5)]
    resistances = []
    for wire, length, temp, other in itertools.product(wires, a["one_way_lengths_m"], a["conductor_temperatures_C"], a["loop_other_resistance_ohm"]):
        copper_r = 2*length*wire["r20_ohm_per_m"]*(1+a["copper_alpha_per_K"]*(temp-20))
        resistances.append(dict(wire=wire["name"], area_mm2=wire["area_mm2"],
                                one_way_m=length, conductor_C=temp,
                                other_loop_ohm=other, copper_loop_ohm=copper_r,
                                loop_ohm=copper_r+other))
    long33=[]
    for r, current in itertools.product(resistances, [1.,3.]):
        drop=current*r["loop_ohm"]
        long33.append(dict(**r, rail_A=current, nominal_source_V=3.3,
                          head_V=3.3-drop, voltage_drop_V=drop,
                          drop_percent_of3p3=100*drop/3.3,
                          loss_W=current*drop,
                          passes_3percent_drop_only=drop<=3.3*.03))
    local=[]
    for r, vs, eta, motor, ledload in itertools.product(
            resistances, [11.88,12.,12.12], a["converter_efficiency_sensitivity"],
            [0.,a["motor_head_current_budget_A"]], ["baseline","budget"]):
        pout=rails["logic_budget_W"]+(vled_w if ledload=="baseline" else rails["LED_budget_W"])
        local.append(dict(**r, source_V=vs, efficiency_assumed=eta,
                          motor_current_assumed_A=motor, LED_load=ledload,
                          auxiliary_output_W=pout, converter_loss_W=pout/eta-pout,
                          **solve_trunk(vs,r["loop_ohm"],motor,pout/eta)))
    parts=[]
    for p in cfg["parts"]:
        parts.append(dict(refs=p["ref"],mpn=p["mpn"],qty=p["qty_total"],value=p["value"],
                          body_max_mm=" x ".join(map(str,p["body_max_mm"])),
                          sources=";".join(p["source_ids"]),role=p["role"]))
    # Independent bisection of Kirchhoff's scalar equation validates root selection.
    error=0.
    for row in local:
        vs=row["source_V"]; r=row["loop_ohm"]; im=row["motor_current_assumed_A"]; p=row["aux_at_head_W"]
        low=(vs-r*im)/2; high=vs
        for _ in range(65):
            x=(low+high)/2
            if x+r*(im+p/x)>vs: high=x
            else: low=x
        error=max(error,abs((low+high)/2-row["head_V"]))
    checks=dict(positive_solutions=all(x["head_V"]>0 for x in local),
                max_energy_residual_W=max(abs(x["energy_residual_W"]) for x in local),
                max_KCL_residual_A=max(abs(x["kcl_residual_A"]) for x in local),
                root_vs_bisection_max_V=error,
                catalogue_baseline_matches=abs(vled_w+vio_w-4.074)<1e-12,
                local_12V_scenarios=len(local), long_3V3_scenarios=len(long33),
                selected_unique_PN=len(parts), selected_piece_count=sum(p["qty"] for p in parts))
    assert checks["positive_solutions"] and checks["catalogue_baseline_matches"]
    assert checks["max_energy_residual_W"]<1e-10 and error<1e-10
    inputs={path:sha(REPO/path) for path in INPUTS}
    source_checks={}
    if args.source_dir:
        for name,s in cfg["sources"].items():
            if "local" in s:
                path=args.source_dir/s["local"]
                source_checks[name] = dict(file=s["local"],expected=s["sha256"],actual=sha(path))
                assert source_checks[name]["actual"]==s["sha256"],name
    result=dict(revision="HEAD-POWER01",release=False,source_hashes=inputs,
                official_local_hash_checks=source_checks,rail_budgets=rails,
                resistive_only=True,check=checks,
                PSU_planning=dict(motor_allocation_W=72,aux_W_at_eta80=13.2/.8,
                                  line_and_protection_reserve_W=10,
                                  subtotal_W=72+13.2/.8+10,margin_fraction=.2,
                                  with20percent_W=(72+13.2/.8+10)*1.2,
                                  selected_W=150,selected_A=12.5),
                not_modelled=["wire inductance", "converter/input stability", "ampacity",
                              "PSU current limit/startup", "motor dynamic demand and regeneration",
                              "thermal", "rail transients", "connector thermal", "common-return noise"])
    csv_write("long-3v3-drop.csv",long33)
    csv_write("local-12v-drop.csv",local)
    csv_write("converter-bom.csv",parts)
    pins = {
        "RT": ([1], "16.5k to local AGND; 800kHz candidate"),
        "EN/SYNC": ([2], "VIN; automatic start, no external sync"),
        "VIN": ([3,4,18,19], "head12V; symmetrical CIN to PGND"),
        "PGND": ([5,6,16,17,28,29], "power return; local input/output capacitor loops"),
        "VOUT": ([7,8,9,10,12,13,14,15,30], "own3V3 output; COUT to PGND"),
        "SW": ([11], "no connection; minimum copper per TI layout"),
        "CBOOT": ([20], "no external component; internal boot capacitor"),
        "RBOOT": ([21], "no external component; internal100ohm retained"),
        "VLDOIN": ([22], "ownVOUT; optional0.1..1uF bypass footprint DNP"),
        "VCC": ([23], "1uF to local ground; no external load"),
        "AGND": ([24,27], "join PGND at single local point"),
        "FB": ([25], "Kelvin to own output capacitor; FIXED V3, no divider"),
        "PG": ([26], "49.9k pullup to ownVOUT; diagnostic testpoint only"),
    }
    pinrows=[dict(pin=n,signal=s,connection=connection,source="TI_MODULE Table5-1 p4; TI_EVM schematicp8")
             for s,(numbers,connection) in pins.items() for n in numbers]
    assert sorted(p["pin"] for p in pinrows)==list(range(1,31))
    csv_write("module-pin-contract.csv",sorted(pinrows,key=lambda x:x["pin"]))
    (HERE/"budget.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    artifact_names=["calculate.py","long-3v3-drop.csv","local-12v-drop.csv","converter-bom.csv","module-pin-contract.csv","budget.json"]
    (HERE/"manifest.json").write_text(json.dumps(dict(revision="HEAD-POWER01",release=False,
        outputs={name:sha(HERE/name) for name in artifact_names}),indent=2)+"\n")
    print(json.dumps(checks,indent=2))


if __name__ == "__main__":
    main()
