#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Build B05 internal reference geometry, with independently replaceable PCB parts.

Metal load capacity is inherited and unqualified. BRI01 J2/J6 changes are geometry
candidates, not a claim that a revised native PCB has already been exported.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import cadquery as cq
import trimesh

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "build/frame"
B04 = HERE.parent / "base_b04"
SPEC = importlib.util.spec_from_file_location("odradek_b04_reference", B04 / "model.py")
OLD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OLD)
SOURCES = {}


def source(path):
    path = ROOT / path
    SOURCES[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return path


def read(path):
    return json.loads(source(path).read_text())


def bbox(shape):
    b = shape.BoundingBox()
    return {"min": [b.xmin, b.ymin, b.zmin], "max": [b.xmax, b.ymax, b.zmax],
            "size": [b.xlen, b.ylen, b.zlen]}


def annotate(part, status, module, source_reference=None, printable=False):
    part.prototype_status = status
    part.module = module
    part.source_reference = source_reference
    part.printable = printable
    return part


def native_service_parts():
    folder = "engineering/electronics/base-b04/"
    metadata = read(folder + "mechanical/verification.json")["component_reference_objects"]
    pins = [p for p in read(folder + "native-readback.json")["holes"] if p["type"] == "PTH"]
    shapes = cq.importers.importStep(str(source(folder + "mechanical/base-b04-local.step"))).val().Solids()
    result = []
    for shape in shapes:
        b = bbox(shape)
        def error(row):
            return sum(abs(b[side][i] - row[f"bbox_{side}_mm"][i])
                       for side in ("min", "max") for i in range(3))
        row = min(metadata, key=error)
        if error(row) < .01:
            ref = row["name"]
            basis = row["scope"]
        elif b["size"][0] > 79:
            ref, basis = "PCB", "Native B04 drilled board, rigidly relocated; same circuit and holes"
        else:
            u, v = [(b["min"][i] + b["max"][i]) / 2 for i in (0, 1)]
            pin = min(pins, key=lambda p: math.dist([u, v], p["uv_mm"]))
            assert math.dist([u, v], pin["uv_mm"]) < .1, (u, v)
            ref, basis = f"PIN-{pin['ref']}-{pin['pin']}", "Native through-hole lead planning geometry"
        transformed = shape.rotate((0, 0, 0), (0, 0, 1), 90).translate((-58, 87, 23))
        part = OLD.Part("B05-SERVICE-" + ref, transformed, "FR4", basis,
                        category="component", color=[.03, .26, .16, 1] if ref == "PCB" else [.13, .17, .19, 1])
        part.notes = ["X=-58-v;Y=87+u;Z=23+w", "PCB assembly reference includes mated connector planning envelopes."]
        result.append(annotate(part, "native_pcb_reference_rigid_relocation", "service_reference",
                               {"revision": "B04-SERVICE01", "name": ref, "source": folder + "mechanical/base-b04-local.step"}))
    return result


def candidate_io_parts():
    folder = "engineering/electronics/base-rear-interface01/"
    meta = read(folder + "mechanical/parts.json")["parts"]
    shapes = cq.importers.importStep(str(source(folder + "mechanical/base-rear-interface01-local.step"))).val().Solids()
    result = []
    for shape in shapes:
        b = bbox(shape)
        def error(row):
            return sum(abs(b[side][i] - row["bbox_local"][k][i])
                       for k, side in enumerate(("min", "max")) for i in range(3))
        row = min(meta, key=error)
        assert error(row) < .01, (row["name"], error(row))
        name = row["name"]
        transformed = shape.rotate((0, 0, 0), (0, 0, 1), 180).translate((58, 76, 20))
        adjustment = [0, 0, 0]
        if name.startswith("J2_"):
            adjustment = [-38, 0, 0]
        elif name.startswith("J6_"):
            adjustment = [4, -8, 0]
        transformed = transformed.translate(tuple(adjustment))
        part = OLD.Part("B05-IO-CANDIDATE-" + name, transformed, "FR4", row["basis"],
                        category="component", color=[.025, .30, .21, 1] if row["role"] == "PCB" else [.20, .23, .25, 1])
        part.notes = ["CANDIDATE REFERENCE ONLY: X=58-u;Y=76-v;Z=20+w.",
                      "J2 moved to u58 and J6 to u42,v20; old PCB drill/copper layout is NOT regenerated here.",
                      "Replace this whole module using a verified JLCEDA native export before fabrication."]
        result.append(annotate(part, "candidate_reference_not_updated_native_board", "io_candidate_reference",
                               {"revision": "BRI01", "name": name, "role": row["role"],
                                "source": folder + "mechanical/base-rear-interface01-local.step",
                                "candidate_translation_after_main_transform_mm": adjustment}))
    return result


def pcb_mount(parts, deck, prefix, holes, height, bolt_length):
    """Four purchased M/F posts: integral male 6 mm, bore depth set by stack."""
    records = []
    for index, (x, y) in enumerate(holes):
        # Test support against the existing deck BEFORE cutting the new tap.
        footprint = OLD.cyl((x, y, 13.9), (0, 0, 1), 3.2, .1)
        unsupported = max(0., footprint.cut(deck.shape).Volume())
        assert unsupported < .01, (prefix, x, y, "unsupported footprint", unsupported)
        deck.hole((x, y, 14), (0, 0, -1), 2.5, 8,
                  "NEW B05 M3x0.5-6H; FULL THREAD6; DRILL8; M/F PCB POST MALE6",
                  {"interface": prefix, "prototype_status": "new_hole_unqualified_metal_reference"})
        top = 14 + height
        engagement = bolt_length - 1.6 - .5
        female_depth = 6 if height >= 9 else 4
        assert engagement > 0 and engagement <= female_depth
        shape = OLD.cyl((x, y, 14), (0, 0, 1), 3.2, height)
        shape = shape.fuse(OLD.cyl((x, y, 8), (0, 0, 1), 1.5, 6))
        shape = shape.cut(OLD.cyl((x, y, top - female_depth), (0, 0, 1), 1.25, female_depth))
        post = OLD.Part(f"B05-{prefix}-POST-{index+1}", shape, "brass",
                        f"Purchase M3 M/F post; AF5.5 envelope D6.4; body{height}; male6; female>={female_depth}",
                        category="hardware")
        post.notes = ["New non-load-bearing electronics mount; NOT a printed structural part.",
                      "Thread is represented by pilot/bounding cylinders. Supplier thread depth and stock must be confirmed."]
        parts.append(annotate(post, "new_non_load_bearing_purchased_support", prefix.lower() + "_mount"))
        seat = top + 1.6 + .5
        shaft = OLD.cyl((x, y, seat - bolt_length), (0, 0, 1), 1.5, bolt_length)
        washer = OLD.cyl((x, y, top + 1.6), (0, 0, 1), 3.5, .5).cut(
            OLD.cyl((x, y, top + 1.6), (0, 0, 1), 1.6, .5))
        head = OLD.cyl((x, y, seat), (0, 0, 1), 2.75, 3)
        drive = cq.Workplane("XY").polygon(6, 2.5 / math.cos(math.pi / 6)).extrude(2).translate((x, y, seat+1)).val()
        head = head.cut(drive)
        screw = OLD.Part(f"B05-{prefix}-M3-{index+1}", shaft.fuse(washer).fuse(head), "steel",
                         f"Purchase ISO4762 M3x{bolt_length} + D7 x0.5 washer; effective post engagement {engagement:.1f}mm",
                         category="fastener")
        screw.free_shape = washer.fuse(head)
        screw.notes = ["Threads simplified; new board stack only, no load rating."]
        parts.append(annotate(screw, "new_non_load_bearing_purchased_fastener", prefix.lower() + "_mount"))
        records.append({"id": post.id, "hole_xyz": [x, y, top], "deck_entry_z": 14,
                        "post_body_height": height, "post_female_depth": female_depth,
                        "post_male_engagement": 6, "top_screw_effective_engagement": engagement,
                        "unsupported_base_volume_mm3": unsupported})
    return records


def build_parts():
    source("engineering/base_b04/model.py")
    source("engineering/base_b04/parameters.json")
    old_parts = OLD.make(t=30, covers=False, environment=True)
    obsolete_prefixes = ("B04-30", "B04-40", "HW-COVER-POST-", "HW-PCB-POST-", "HW-M3-PCB-",
                         "HW-M3-COVER-", "HW-M4-CARRIER-", "HW-INTERFACE-POST-",
                         "HW-M3-INTERFACE-", "HW-M3-PORT-HOOD-", "HW-LIGHT-", "HW-M2-LIGHT-")
    parts, removed = [], []
    for part in old_parts:
        if part.id == "ENV-PCB" or part.id.startswith(obsolete_prefixes):
            removed.append(part.id)
            continue
        if part.category == "environment":
            status, module = "environment_reference_not_manufactured", "environment"
        elif part.category in ("guide", "envelope"):
            status, module = "space_or_operation_reference_not_manufactured", "reference_gauges"
        elif part.material == "PETG":
            status, module = "inherited_non_load_bearing_retainer_trial_print", "clamp_retainer"
        elif part.category in ("hardware", "fastener"):
            status, module = "inherited_purchased_hardware_reference", "inherited_frame_hardware"
        elif part.material in ("6061-T651", "S355"):
            status, module = "inherited_metal_structure_unqualified", "inherited_metal_structure"
        else:
            status, module = "inherited_nonmetal_reference", "inherited_other"
        parts.append(annotate(part, status, module, {"revision": "B04-P2", "name": part.id},
                               printable=part.material == "PETG" and part.category == "custom"))
    deck = next(p for p in parts if p.id == "B04-101-DECK")
    deck.id = "B05-101-DECK"
    deck.prototype_status = "modified_inherited_metal_reference_new_pcb_taps_unqualified"
    for feature in deck.features:
        feature["history"] = "Inherited B04 feature; unused old cover/service holes intentionally retained as history"
    deck.note("B05 adds service and IO mounting taps; old unused service/cover/carrier holes retained. Not a released fabrication drawing.")
    service_contract = read("engineering/electronics/base-b04/mechanical-interface.json")
    service_holes = [(-58 - v, 87 + u) for u, v in service_contract["mount_holes_uv_mm"]]
    io_contract = read("engineering/electronics/base-rear-interface01/connector-contract.json")
    io_holes = [(58 - h["uv"][0], 76 - h["uv"][1]) for h in io_contract["board"]["holes"]
                if h["role"] == "PCB chassis standoff"]
    assert len(service_holes) == 4 and len(io_holes) == 4
    mount_records = pcb_mount(parts, deck, "SERVICE", service_holes, 9, 8)
    mount_records += pcb_mount(parts, deck, "IO", io_holes, 6, 6)
    parts.extend(native_service_parts())
    parts.extend(candidate_io_parts())
    assert len({p.id for p in parts}) == len(parts)
    return parts, removed, mount_records


def positive_overlap(a, b):
    aa, bb = bbox(a), bbox(b)
    if any(min(aa["max"][i], bb["max"][i]) - max(aa["min"][i], bb["min"][i]) <= 1e-6 for i in range(3)):
        return 0.
    return max(0., a.intersect(b).Volume())


def main():
    (OUT / "parts").mkdir(parents=True, exist_ok=True)
    (OUT / "print-parts").mkdir(exist_ok=True)
    parts, removed, mounts = build_parts()
    rows, checks = [], []
    assembly = cq.Assembly(name="B05_INTERNAL_REFERENCE_NOT_RELEASED")
    for part in parts:
        assert part.shape.isValid() and len(part.shape.Solids()) == 1, part.id
        target = OUT / "parts" / part.id
        cq.exporters.export(part.shape, str(target.with_suffix(".step")))
        cq.exporters.export(part.shape, str(target.with_suffix(".stl")), tolerance=.07, angularTolerance=.14)
        mesh = trimesh.load_mesh(target.with_suffix(".stl"), process=True)
        assert mesh.is_watertight, (part.id, "STL not closed")
        reopened = cq.importers.importStep(str(target.with_suffix(".step"))).val()
        volume_error = abs(reopened.Volume() - part.shape.Volume())
        volume_limit = max(.02, part.shape.Volume() * 1e-5)
        assert reopened.isValid() and len(reopened.Solids()) == 1 and volume_error <= volume_limit, part.id
        geometry = {"id": part.id, "valid_single_solid": True, "stl_watertight": bool(mesh.is_watertight),
                    "volume_mm3": part.shape.Volume(), "triangles": len(mesh.faces),
                    "step_reimport_valid_single_solid": True, "step_volume_error_mm3": volume_error,
                    "step_volume_error_limit_mm3": volume_limit}
        checks.append(geometry)
        print_path = None
        if part.printable:
            # Translate inherited non-load-bearing retaining clips to Z0 for slicing.
            print_mesh = mesh.copy()
            centre = [(print_mesh.bounds[0][i] + print_mesh.bounds[1][i])/2 for i in range(2)]
            print_mesh.apply_translation([-centre[0], -centre[1], -print_mesh.bounds[0][2]])
            pp = OUT / "print-parts" / (part.id + "-trial-mm.stl")
            print_mesh.export(pp)
            print_path = str(pp.relative_to(OUT))
        if part.category not in ("environment", "guide", "envelope"):
            assembly.add(part.shape, name=part.id.replace("-", "_"), color=cq.Color(*part.color))
        rows.append({"id": part.id, "material": part.material, "process": part.process,
                     "category": part.category, "quantity": 1, "module": part.module,
                     "prototype_status": part.prototype_status, "source_reference": part.source_reference,
                     "features": part.features, "notes": part.notes, "bbox": bbox(part.shape),
                     "local_bbox": bbox(part.shape), "volume_mm3": part.shape.Volume(),
                     "mass_kg": part.shape.Volume()*OLD.DENSITY[part.material] if part.material in OLD.DENSITY and part.category in ("custom", "hardware", "fastener") else None,
                     "color": part.color, "step": str(target.with_suffix(".step").relative_to(OUT)),
                     "stl": str(target.with_suffix(".stl").relative_to(OUT)),
                     "stl_role": "trial_print_non_load_bearing" if part.printable else "display_or_fit_reference_not_load_print",
                     "print_stl": print_path})
    assembly.export(str(OUT / "B05-FRAME-REFERENCE.step"))
    # Check new reference PCB geometry and NEW free hardware heads against retained metal.
    metal = [p for p in parts if p.module == "inherited_metal_structure"]
    movable = [p for p in parts if p.module in ("service_reference", "io_candidate_reference")]
    contacts = []
    for a in movable:
        for b in metal:
            volume = positive_overlap(a.shape, b.shape)
            if volume > .01:
                contacts.append({"a": a.id, "b": b.id, "volume_mm3": volume})
    for a in parts:
        if a.module in ("service_mount", "io_mount") and hasattr(a, "free_shape"):
            for b in metal + movable:
                volume = positive_overlap(a.free_shape, b.shape)
                if volume > .01:
                    contacts.append({"a": a.id + ":head/washer", "b": b.id, "volume_mm3": volume})
    manifest = {"revision": "B05-FRAME-REFERENCE01", "length_unit": "mm",
                "stage": "internal geometry reference; no metal load or PCB manufacturing release",
                "coordinates": OLD.P["coordinates"], "parts": rows, "removed_b04_parts": removed,
                "new_electronics_mounts": mounts, "sources_sha256": SOURCES,
                "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "io_candidate_transform": "X=58-u;Y=76-v;Z=20+w; J2 extra X-38; J6 extra X+4,Y-8",
                "service_transform": "X=-58-v;Y=87+u;Z=23+w",
                "io_carrier_decision": "All four chassis mounting holes lie on supported deck at (X+/-52,Y26/70); no bridge over rear U-notch needed.",
                "unclosed_interfaces": [
                    "JLCEDA B05 native IO layout/drills/routing and corresponding mechanical export must replace this candidate module",
                    "New outer cover mount points are not defined here; no old cover posts retained",
                    "Coax ledge two holes X+/-10,Y38 retained as source references; bracket torque reaction independent of FR4 is not completed",
                    "Rear faceplate/hood and cable bend/release paths need final shell integration",
                    "All new purchased post/thread depths and screw stacks need actual component fit verification",
                    "Metal base strength, desk contact and load test unchanged/unqualified; never substitute printed load-bearing metal parts"]}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (OUT / "geometry-checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    (OUT / "interface-collisions.json").write_text(json.dumps({"scope": "new PCB references and free new heads vs retained metal; excludes intended threads, component self-overlap and shell", "collisions": contacts}, indent=2) + "\n")
    with (OUT / "parts-bom.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "module", "category", "material", "prototype_status", "mass_kg", "stl_role"], extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
    print(json.dumps({"parts": len(parts), "removed": len(removed), "new_mounts": len(mounts),
                      "trial_print_parts": sum(p.printable for p in parts), "collisions": contacts, "output": str(OUT)}, indent=2), flush=True)
    assert not contacts, contacts


if __name__ == "__main__":
    main()
