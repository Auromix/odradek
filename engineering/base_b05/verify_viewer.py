# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Exercise real mesh embedding, role precedence and offline-file selection.

This validates the viewer pipeline, not manufacturing or assembly clearance.
Optionally preserve a small fixture with --fixture-dir for HTTP browser review.
"""
import argparse
import base64
import json
import tempfile
from pathlib import Path

import numpy as np
import trimesh

from viewer import build_viewer, classify, collect


def fixture(directory):
    (directory / "stl").mkdir(parents=True, exist_ok=True)
    parts = []
    definitions = [
        ("B05-301-ARMOR-L", "左肩甲", "cover", [-55, 80, 34], [95, 190, 18], [.27, .3, .34]),
        ("B05-301-ARMOR-R", "右肩甲", "cover", [55, 80, 34], [95, 190, 18], [.27, .3, .34]),
        ("B05-304-REAR-LID", "可拆后盖", "rear_lid", [0, -30, 35], [90, 8, 35], [.18, .21, .24]),
        ("B05-310-INTERFACE-PANEL", "接口面板", "interface", [0, 0, 35], [86, 4, 28], [.32, .37, .4]),
        ("B04-101-DECK", "金属框架参考", "structure", [0, 85, 7], [200, 200, 14], [.48, .5, .52]),
    ]
    for pid, name, role, center, size, color in definitions:
        mesh = trimesh.creation.box(extents=size)
        mesh.apply_translation(center)
        relative = f"stl/{pid}.stl"
        mesh.export(directory / relative)
        parts.append(dict(id=pid, name=name, stl=relative, category="custom", color=color,
                          material="fixture", process="viewer QA only", assembly_role=role,
                          prototype_status="查看器测试几何，不是产品模型", notes=["Fixture for viewer QA"],
                          viewer_group="cover" if role == "rear_lid" else role))
    (directory / "manifest.json").write_text(json.dumps(dict(revision="B05-VIEWER-FIXTURE", length_unit="mm", parts=parts)))
    return parts


def verify(directory):
    source = fixture(directory)
    parts, meta = collect(directory)
    assert len(parts) == 5
    assert not meta["files"], "Absent CAD artifacts must not get broken download links"
    assert classify(source[2]) == ("rear_lid", "rear_lid"), "Explicit rear lid outranks cover group"
    for original, result in zip(source, parts):
        vertices = np.frombuffer(base64.b64decode(result["v"]), dtype="<f4").reshape(-1, 3)
        normals = np.frombuffer(base64.b64decode(result["n"]), dtype="<f4").reshape(-1, 3)
        assert vertices.shape == normals.shape == (36, 3)
        assert np.allclose(np.ptp(vertices, axis=0) * 1000, result["bbox"]["size"])
        assert np.allclose(np.linalg.norm(normals, axis=1), 1)
    assert parts[2]["explode_mm"][1] < 0, "Rear lid must move away from rear opening"
    html = build_viewer(directory).read_text()
    assert "__ASSEMBLY_" not in html
    assert '<script src=' not in html and 'cdn.' not in html
    assert all(f'id="{identifier}"' in html for identifier in ("assembled", "shellOpen", "rearOpen", "exploded", "partSearch", "detail"))
    for bad_unit in ("m", "inch"):
        data = json.loads((directory / "manifest.json").read_text())
        data["length_unit"] = bad_unit
        (directory / "manifest.json").write_text(json.dumps(data))
        try:
            collect(directory)
        except ValueError:
            pass
        else:
            raise AssertionError("Wrong-scale assembly must be rejected")
    fixture(directory)
    print("PASS: render payload, millimetre scale, role precedence, lid direction, offline HTML and absent-artifact links")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-dir", type=Path)
    args = parser.parse_args()
    if args.fixture_dir:
        verify(args.fixture_dir)
    else:
        with tempfile.TemporaryDirectory(prefix="odradek-b05-viewer-") as temp:
            verify(Path(temp))
