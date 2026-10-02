#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Check STL / Core 3MF geometry and printer envelope; never repair source meshes.

Requires numpy and trimesh. This is a mesh gate, not a manufacturing release.
STL coordinates have no embedded unit; --stl-unit defaults explicitly to mm.
3MF Core mesh objects, component instances, units and build transforms are read.
External component models / mandatory extensions are rejected, not ignored.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import platform
import posixpath
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import trimesh

UNIT_MM = {"micron": .001, "millimeter": 1., "centimeter": 10.,
           "inch": 25.4, "foot": 304.8, "meter": 1000.}
STL_MM = {"mm": 1., "cm": 10., "m": 1000., "in": 25.4}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def transform_3mf(text: str | None) -> np.ndarray:
    matrix = np.eye(4)
    if text:
        values = np.asarray([float(x) for x in text.split()])
        if values.size != 12 or not np.isfinite(values).all():
            raise ValueError("3MF transform must contain 12 finite values")
        matrix[:3, :4] = values.reshape(4, 3).T
    return matrix


def load_3mf(path: Path) -> tuple[list[tuple[str, trimesh.Trimesh]], str]:
    """Read Core build instances without silently dropping unsupported components."""
    with zipfile.ZipFile(path) as archive:
        rels = ET.fromstring(archive.read("_rels/.rels"))
        model_targets = [r.attrib["Target"] for r in rels
                         if r.attrib.get("Type", "").endswith("/3dmodel")]
        if len(model_targets) != 1:
            raise ValueError("3MF must name exactly one root 3D model")
        target = posixpath.normpath(model_targets[0].lstrip("/"))
        if target.startswith("../"):
            raise ValueError("3MF root model path escapes archive")
        root = ET.fromstring(archive.read(target))
    if root.attrib.get("requiredextensions", "").strip():
        raise ValueError("3MF mandatory extensions are not checked by this Core reader")
    units = root.attrib.get("unit", "millimeter")
    if units not in UNIT_MM:
        raise ValueError(f"Unsupported 3MF unit: {units}")
    objects = {}
    for obj in root.findall("./{*}resources/{*}object"):
        oid = obj.attrib["id"]
        if oid in objects:
            raise ValueError(f"Duplicate 3MF object id {oid}")
        objects[oid] = obj
    output = []

    def visit(oid: str, matrix: np.ndarray, stack: tuple[str, ...], instance: str):
        if oid in stack:
            raise ValueError(f"Cyclic 3MF component reference: {stack + (oid,)}")
        if oid not in objects:
            raise ValueError(f"Undefined 3MF component {oid}")
        obj = objects[oid]
        mesh_xml = obj.find("./{*}mesh")
        children = obj.findall("./{*}components/{*}component")
        if (mesh_xml is None) == (not children):
            raise ValueError(f"Object {oid} must contain either mesh or components")
        if mesh_xml is not None:
            vertices = [[float(v.attrib[a]) for a in ("x", "y", "z")]
                        for v in mesh_xml.findall("./{*}vertices/{*}vertex")]
            faces = [[int(t.attrib[a]) for a in ("v1", "v2", "v3")]
                     for t in mesh_xml.findall("./{*}triangles/{*}triangle")]
            mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
            mesh.apply_transform(matrix)
            mesh.apply_scale(UNIT_MM[units])
            output.append((f"{instance}:{obj.attrib.get('name', oid)}", mesh))
        else:
            for index, child in enumerate(children):
                if any(key.rsplit("}", 1)[-1] == "path" for key in child.attrib):
                    raise ValueError("External 3MF component model is unsupported")
                visit(child.attrib["objectid"], matrix @ transform_3mf(child.get("transform")),
                      stack + (oid,), f"{instance}/{index}")

    for index, item in enumerate(root.findall("./{*}build/{*}item")):
        # Deliberately examine nonprintable build objects too; omissions are unsafe.
        visit(item.attrib["objectid"], transform_3mf(item.get("transform")), (), str(index))
    if not output:
        raise ValueError("3MF has no mesh instances in its build")
    return output, units


def envelope(extents: np.ndarray, bed: np.ndarray, margin: float) -> dict:
    usable = bed - np.array([2 * margin, 2 * margin, 0.])
    fits = [list(order) for order in itertools.permutations(range(3))
            if np.all(extents[list(order)] <= usable + 1e-6)]
    return {"size_mm": extents.tolist(), "usable_bed_mm": usable.tolist(),
            "fits_exported_orientation_after_translation": [0, 1, 2] in fits,
            "orthogonal_axis_orders_that_fit": fits,
            "arbitrary_angle_nesting_checked": False}


def check_mesh(mesh: trimesh.Trimesh, bed: np.ndarray, margin: float,
               allow_rotation: bool = False) -> dict:
    # STL encodes triangles with repeated vertices. Weld coincident coordinates
    # only; do not fill holes, remove degenerate faces or fix normals for the check.
    vertices = np.asarray(mesh.vertices)
    faces = np.asarray(mesh.faces)
    if not len(vertices) or not len(faces):
        raise ValueError("Empty mesh")
    if not np.isfinite(vertices).all():
        raise ValueError("Non-finite mesh vertex")
    if np.min(faces) < 0 or np.max(faces) >= len(vertices):
        raise ValueError("Face index outside vertex array")
    work = mesh.copy()
    before = len(work.vertices)
    work.merge_vertices(digits_vertex=8)
    connected = trimesh.graph.connected_components(
        work.face_adjacency, nodes=np.arange(len(work.faces)), min_len=1)
    degenerate = int(np.count_nonzero(~work.nondegenerate_faces(height=1e-8)))
    duplicate = len(work.faces) - len(np.unique(np.sort(work.faces, axis=1), axis=0))
    size = envelope(work.extents, bed, margin)
    topology_ok = bool(work.is_watertight and work.is_winding_consistent
                       and work.volume > 1e-9 and len(connected) == 1
                       and degenerate == 0 and duplicate == 0)
    envelope_ok = bool(size["orthogonal_axis_orders_that_fit"] if allow_rotation
                       else size["fits_exported_orientation_after_translation"])
    return {"vertices_before_weld": before, "vertices_after_weld": len(work.vertices),
            "faces": len(work.faces), "coincident_vertex_weld_precision_mm": 1e-8,
            "watertight": bool(work.is_watertight),
            "winding_consistent": bool(work.is_winding_consistent),
            "face_connected_components": len(connected),
            "degenerate_faces": degenerate, "duplicate_faces": duplicate,
            "signed_volume_mm3": float(work.volume), "surface_area_mm2": float(work.area),
            "bbox_mm": work.bounds.tolist(), **size,
            "topology_pass": topology_ok, "envelope_pass": envelope_ok,
            "mesh_and_envelope_pass": topology_ok and envelope_ok,
            "self_intersection_checked": False, "wall_thickness_checked": False}


def check_file(path: Path, bed: np.ndarray, margin: float, stl_unit: str,
               allow_rotation: bool = False) -> dict:
    result = {"path": str(path.resolve()), "sha256": sha256(path), "instances": []}
    try:
        if path.suffix.lower() == ".stl":
            mesh = trimesh.load_mesh(path, process=False)
            mesh.apply_scale(STL_MM[stl_unit])
            meshes, units = [(path.stem, mesh)], f"assumed {stl_unit}; STL has no unit"
        elif path.suffix.lower() == ".3mf":
            meshes, units = load_3mf(path)
        else:
            raise ValueError("Only STL and Core 3MF are supported")
        result["input_units"] = units
        for name, mesh in meshes:
            result["instances"].append({"name": name,
                                       **check_mesh(mesh, bed, margin, allow_rotation)})
        bounds = np.asarray([p["bbox_mm"] for p in result["instances"]])
        arrangement_size = bounds[:, 1].max(axis=0) - bounds[:, 0].min(axis=0)
        result["whole_file_arrangement"] = envelope(arrangement_size, bed, margin)
        result["mesh_and_envelope_pass"] = all(
            p["mesh_and_envelope_pass"] for p in result["instances"])
        # Each instance must fit, but separate objects do not have to print together.
        result["multiple_objects_need_separate_slicer_placement"] = len(meshes) > 1
    except Exception as error:
        result.update(error=f"{type(error).__name__}: {error}", mesh_and_envelope_pass=False)
    return result


def self_test():
    bed = np.array([220., 220., 250.])
    good = trimesh.creation.box([20., 30., 10.])
    assert check_mesh(good, bed, 5)["mesh_and_envelope_pass"]
    opened = good.copy()
    opened.update_faces(np.arange(len(opened.faces) - 1))
    assert not check_mesh(opened, bed, 5)["topology_pass"]
    reversed_mesh = good.copy()
    reversed_mesh.invert()
    assert not check_mesh(reversed_mesh, bed, 5)["topology_pass"]
    other = good.copy()
    other.apply_translation([40, 0, 0])
    assert check_mesh(trimesh.util.concatenate([good, other]), bed, 5)["face_connected_components"] == 2
    duplicated = trimesh.Trimesh(vertices=good.vertices, faces=np.vstack([good.faces, good.faces[0]]), process=False)
    assert check_mesh(duplicated, bed, 5)["duplicate_faces"] == 1
    degenerate = trimesh.Trimesh(vertices=good.vertices, faces=np.vstack([good.faces, [0, 0, 1]]), process=False)
    assert check_mesh(degenerate, bed, 5)["degenerate_faces"] == 1
    tall = trimesh.creation.box([230., 10., 10.])
    assert not check_mesh(tall, bed, 5)["envelope_pass"]
    assert check_mesh(tall, bed, 5, True)["envelope_pass"]
    huge = trimesh.creation.box([260., 260., 260.])
    assert not check_mesh(huge, bed, 5, True)["envelope_pass"]
    with tempfile.TemporaryDirectory(prefix="odradek-print-check-") as folder:
        root = Path(folder)
        good.export(root / "good.stl")
        assert check_file(root / "good.stl", bed, 5, "mm")["mesh_and_envelope_pass"]
        source = good.copy()
        source.apply_scale(.001)
        source.export(root / "meters.stl")
        meters_stl = check_file(root / "meters.stl", bed, 5, "m")
        assert np.allclose(meters_stl["instances"][0]["size_mm"], [20., 30., 10.]), meters_stl
        model = ET.Element("model", {"xmlns": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02", "unit": "meter"})
        resources = ET.SubElement(model, "resources")
        obj = ET.SubElement(resources, "object", {"id": "1", "type": "model"})
        xml_mesh = ET.SubElement(obj, "mesh")
        xml_vertices, xml_faces = ET.SubElement(xml_mesh, "vertices"), ET.SubElement(xml_mesh, "triangles")
        for vertex in source.vertices:
            ET.SubElement(xml_vertices, "vertex", dict(zip(("x", "y", "z"), map(str, vertex))))
        for face in source.faces:
            ET.SubElement(xml_faces, "triangle", dict(zip(("v1", "v2", "v3"), map(str, face))))
        parent = ET.SubElement(resources, "object", {"id": "2", "type": "model"})
        children = ET.SubElement(parent, "components")
        ET.SubElement(children, "component", {"objectid": "1"})
        ET.SubElement(children, "component", {"objectid": "1", "transform": "1 0 0 0 1 0 0 0 1 0.04 0 0"})
        ET.SubElement(ET.SubElement(model, "build"), "item",
                      {"objectid": "2", "transform": "1 0 0 0 1 0 0 0 1 0.1 0 0"})
        rels = b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'
        with zipfile.ZipFile(root / "meters.3mf", "w") as archive:
            archive.writestr("_rels/.rels", rels)
            archive.writestr("3D/3dmodel.model", ET.tostring(model))
        result = check_file(root / "meters.3mf", bed, 5, "mm")
        assert result["mesh_and_envelope_pass"], result
        assert np.allclose(result["instances"][0]["size_mm"], [20., 30., 10.]), result
        assert len(result["instances"]) == 2, result
        assert np.isclose(result["instances"][0]["bbox_mm"][0][0], 90), result
        assert np.isclose(result["instances"][1]["bbox_mm"][0][0], 130), result
    print("PASS: closed/open/reversed/disconnected/duplicate/degenerate meshes, orientation/oversize, STL units, 3MF units and nested transforms")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path, nargs="*", help="STL/3MF files or recursive part folders")
    parser.add_argument("--bed", type=float, nargs=3, default=[220, 220, 250], metavar=("X", "Y", "Z"))
    parser.add_argument("--margin", type=float, default=5., help="reserved clearance on each XY bed edge (mm)")
    parser.add_argument("--stl-unit", choices=STL_MM, default="mm")
    parser.add_argument("--allow-orthogonal-rotation", action="store_true",
                        help="accept any fitting axis permutation; default requires exported orientation")
    parser.add_argument("--output", type=Path, help="JSON report path")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    bed = np.asarray(args.bed)
    if not np.isfinite(bed).all() or not np.isfinite(args.margin) or args.margin < 0:
        parser.error("bed and margin must be finite; margin must be nonnegative")
    if np.any(bed - [2 * args.margin, 2 * args.margin, 0] <= 0):
        parser.error("bed must have positive usable dimensions after margin")
    files = set()
    for path in args.inputs:
        if path.is_dir():
            files.update(p for p in path.rglob("*") if p.suffix.lower() in {".stl", ".3mf"})
        elif path.is_file():
            files.add(path)
        else:
            parser.error(f"input does not exist: {path}")
    if not files:
        parser.error("supply at least one STL/3MF or a folder containing them")
    results = [check_file(p, bed, args.margin, args.stl_unit, args.allow_orthogonal_rotation)
               for p in sorted(files)]
    passed = all(r["mesh_and_envelope_pass"] for r in results)
    report = {"schema": "odradek.print-checks.v1", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "mesh integrity and per-instance print-bed envelope only; not manufacturing or load release",
              "script_sha256": sha256(Path(__file__)), "python": platform.python_version(),
              "trimesh_version": trimesh.__version__, "numpy_version": np.__version__,
              "bed_mm": bed.tolist(), "edge_margin_mm": args.margin,
              "orthogonal_rotation_allowed": args.allow_orthogonal_rotation,
              "mesh_and_envelope_pass": passed, "files": results,
              "not_checked": ["self intersections", "minimum walls", "supports and overhangs", "layer strength",
                              "bed adhesion and distortion", "mating tolerances", "insert retention", "assembly collision",
                              "connector or cable fit", "payload or clamp capacity"]}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    for result in results:
        print(("PASS" if result["mesh_and_envelope_pass"] else "FAIL"), result["path"])
        if "error" in result:
            print(" ", result["error"])
        for part in result["instances"]:
            print(" ", part["name"], "size", [round(v, 3) for v in part["size_mm"]],
                  "closed", part["watertight"], "components", part["face_connected_components"],
                  "envelope", part["envelope_pass"])
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
