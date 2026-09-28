#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Stock containment and nominal tie-screw reach; not connection qualification."""
from pathlib import Path
import hashlib
import json
import math
import cadquery as cq

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "engineering/generated/shoulder-procurement01"
SOURCE = ROOT / "docs/engineering/sources/shoulder-procurement01.json"
FORK = ROOT / "engineering/generated/shoulder-raise02/L12_rear_fork.step"
FORK_SHA = "c5af756a04674a71831daf07d21cffd0b36e9c49c6cfa25b8e5886467a3fc206"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert sha(FORK) == FORK_SHA, "Frozen RAISE02 fork changed"
    source = json.loads(SOURCE.read_text())
    fork = cq.importers.importStep(str(FORK)).val()
    b = fork.BoundingBox()
    low = [b.xmin, b.ymin, b.zmin]
    high = [b.xmax, b.ymax, b.zmax]
    centre = [(a + z) / 2 for a, z in zip(low, high)]
    spans = [z - a for a, z in zip(low, high)]
    material = source["procurement_definition"]["rear_fork"]
    stocks = []
    for key in ["nominal_raw_stock_world_XYZ_mm", "minimum_clean_usable_box_world_XYZ_mm"]:
        dims = material[key]
        box = cq.Workplane("XY").box(*dims).translate(tuple(centre)).val()
        outside = sum(s.cut(box).Volume() for s in fork.Solids())
        margin = [(d - span) / 2 for d, span in zip(dims, spans)]
        assert outside < 1e-5 and min(margin) > 0
        stocks.append({"definition": key, "dimensions_world_XYZ_mm": dims,
                       "centre_world_mm": centre, "nominal_each_side_margin_XYZ_mm": margin,
                       "outside_fork_volume_mm3": outside,
                       "box_volume_mm3": math.prod(dims),
                       "nominal_box_mass_kg": math.prod(dims) * 2700e-9,
                       "net_material_fraction": fork.Volume() / math.prod(dims)})

    # Existing geometry, not chosen engagement allowance or bolt length tolerance.
    entry_y, block_front_y, block_rear_y = -11.5, -104.5, -112.5
    bolt_length, thread_length, nominal_block_depth = 100.0, 20.0, 8.0
    grip = entry_y - block_front_y
    entry_from_tip = bolt_length - grip
    thread_transition = bolt_length - thread_length
    assert grip == 93.0 and entry_from_tip == 7.0
    assert block_front_y - block_rear_y == nominal_block_depth
    nominal = {
        "head_bearing_world_Y_mm": entry_y, "block_front_world_Y_mm": block_front_y,
        "block_rear_world_Y_mm": block_rear_y, "grip_mm": grip,
        "bolt_nominal_tip_world_Y_mm": entry_y - bolt_length,
        "nominal_geometric_insertion_mm": entry_from_tip,
        "nominal_tip_to_block_back_face_mm": nominal_block_depth - entry_from_tip,
        "catalog_thread_b_mm": thread_length,
        "nominal_thread_transition_distance_from_head_mm": thread_transition,
        "block_front_minus_thread_transition_mm": grip - thread_transition,
        "maximum_head_diameter_mm": 7.0, "maximum_head_height_mm": 4.0,
        "previous_geometry_head_diameter_proxy_mm": 7.22,
        "catalog_eight_screws_mass_kg": 8 * 0.011,
        "condition": "No washers added; neither end chamfers nor incomplete threads deducted",
        "thread_tolerance_relation": "effective_engagement_min = L_min - grip_max - bolt_tip_incomplete_max - block_entry_incomplete_max; all four terms require controlled limits",
        "release": False,
    }
    # Unit conversion only; this is not a design allowable or failure calculation.
    ksi_to_mpa = 6.894757293168361
    report = {
        "revision": "SHOULDER-PROC01", "manufacturing_release": False,
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in [SOURCE, FORK, Path(__file__)]},
        "fork_bbox_world_mm": [low, high], "fork_volume_mm3": fork.Volume(),
        "stock_containment": stocks, "screw_nominal_fit": nominal,
        "certificate_request_unit_conversion": {
            "ultimate_42_ksi_MPa": 42 * ksi_to_mpa,
            "tensile_yield_35_ksi_MPa": 35 * ksi_to_mpa,
            "meaning": "Procurement request from the cited old manufacturer table, not measured material values or a structural allowable"},
        "unclosed": ["post-facing stock actual dimensions and grain direction", "batch material certificate",
                     "screw controlled length/runout and full thread engagement", "OEM clamp load limit",
                     "bolt preload, torsion and joint compliance", "head bearing/contact and relaxation",
                     "tail connector access", "whole-arm mass and interference integration"],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "procurement-check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"stock_outside_mm3": [x["outside_fork_volume_mm3"] for x in stocks],
                      "stock_each_side_margin_mm": [x["nominal_each_side_margin_XYZ_mm"] for x in stocks],
                      "bolt_nominal_insertion_mm": entry_from_tip,
                      "manufacturing_release": False}, indent=2))


if __name__ == "__main__":
    main()
