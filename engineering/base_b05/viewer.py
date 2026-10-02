# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Build an offline, millimetre-aware B05 assembly viewer from actual meshes.

The HTML embeds every render triangle. Companion CAD/STL links are included only
for files present in the build directory. No network library or CDN is used.
"""
import argparse
import base64
import json
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
GROUP_NAMES = {
    "cover": "外罩 / 底座灯", "rear_lid": "可拆后盖",
    "interface": "后部接口组件", "electronics": "PCB / 元件",
    "structure": "承力结构 / 参考件", "fasteners": "标准件",
    "cradle": "盒架 / 盒体检具", "routing": "线束空间",
    "environment": "桌面 / 墙面", "guide": "拧紧工具示意",
}


def classify(part):
    """Explicit roles win over legacy IDs, including an explicit rear-lid role."""
    pid = part["id"]
    category = part.get("category", "custom")
    role = part.get("assembly_role", "")
    if role == "rear_lid" or pid.startswith("B05-304"):
        return "rear_lid", "rear_lid"
    if role == "cover" or pid.startswith(tuple(f"B05-{n}" for n in (301, 302, 303, 305))):
        return "cover", "cover"
    explicit = part.get("viewer_group")
    if explicit:
        return explicit, role or explicit
    if category in ("environment", "guide", "routing"):
        return category, role or category
    if pid.startswith(("BRI-", "B05-310", "B05-311", "B04-40")):
        return "interface", role or "interface"
    if pid == "ENV-CONTROLLER" or pid.startswith("B04-20"):
        return "cradle", role or "cradle"
    if category == "component" or "PCB" in pid:
        return "electronics", role or "electronics"
    if category in ("fastener", "hardware"):
        return "fasteners", role or "fasteners"
    if pid.startswith("B04-30"):
        return "cover", role or "cover"
    return "structure", role or "structure"


def explode_vector(part, role, bbox):
    if "explode_mm" in part:
        vector = np.asarray(part["explode_mm"], dtype=float)
        if vector.shape != (3,) or not np.isfinite(vector).all():
            raise ValueError(f"Invalid explode_mm for {part['id']}")
        return vector.tolist()
    center = (np.asarray(bbox["min"]) + np.asarray(bbox["max"])) / 2
    if role == "rear_lid":
        return [85, -85, 65]
    if role == "cover":
        x = 0 if abs(center[0]) < 25 else np.sign(center[0]) * 65
        y = 55 if "NOSE" in part["id"] else -35 if "REAR" in part["id"] else 0
        return [float(x), y, 90 if "COLLAR" in part["id"] else 65]
    return {"electronics": [0, 0, 30], "interface": [0, -25, 15],
            "cradle": [0, 0, -45]}.get(role, [0, 0, 0])


def encoded(values):
    return base64.b64encode(np.asarray(values, dtype="<f4").tobytes()).decode("ascii")


def collect(build_dir):
    manifest = json.loads((build_dir / "manifest.json").read_text())
    if manifest.get("length_unit", "mm") != "mm":
        raise ValueError("Viewer requires an explicitly millimetre-scaled assembly")
    normals_path = next((build_dir / name for name in ("render-meshes.json", "cad-surface-meshes.json")
                         if (build_dir / name).exists()), None)
    render_meshes = json.loads(normals_path.read_text()) if normals_path else {}
    parts = []
    seen = set()
    for source in manifest["parts"]:
        pid = source["id"]
        if pid in seen:
            raise ValueError(f"Duplicate assembly ID: {pid}")
        seen.add(pid)
        stl = source.get("stl", f"stl/{pid}.stl")
        mesh = trimesh.load_mesh(build_dir / stl, process=True)
        if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
            raise ValueError(f"Empty or unsupported mesh: {stl}")
        bbox = {"min": mesh.bounds[0].tolist(), "max": mesh.bounds[1].tolist(),
                "size": mesh.extents.tolist()}
        if pid in render_meshes:
            cm = render_meshes[pid]
            indices = np.asarray(cm["faces"], dtype=int).ravel()
            vertices = np.asarray(cm["vertices"], dtype=float)[indices]
            normals = np.asarray(cm["normals"], dtype=float)[indices]
        else:
            vertices = np.asarray(mesh.triangles).reshape((-1, 3))
            normals = np.repeat(np.asarray(mesh.face_normals), 3, axis=0)
        if vertices.shape != normals.shape or not np.isfinite(vertices).all() or not np.isfinite(normals).all():
            raise ValueError(f"Invalid render vertices/normals for {pid}")
        group_key, role = classify(source)
        notes = source.get("notes", [])
        if isinstance(notes, str):
            notes = [notes]
        part = {key: source.get(key, "") for key in ("id", "name", "material", "process", "category")}
        part.update(group=GROUP_NAMES.get(group_key, group_key), group_key=group_key, role=role,
                    color=source.get("color", [.4, .45, .5]), notes=notes, bbox=bbox,
                    prototype_status=source.get("prototype_status", "数字几何模型；实物试装待验证"),
                    explode_mm=explode_vector(source, role, bbox), stl=stl,
                    v=encoded(vertices * .001), n=encoded(normals))
        parts.append(part)
    if not parts:
        raise ValueError("Manifest has no parts")
    files = []
    for suffix, label in ((".blend", "Blender 场景"), (".glb", "GLB"), (".step", "STEP 总装"), (".3mf", "3MF")):
        candidates = sorted(build_dir.glob("ODR-BASE-*" + suffix))
        if candidates:
            files.append({"name": label, "path": candidates[-1].name})
    visible_parts = [p for p in parts if p["group_key"] not in ("environment", "guide", "routing")]
    bounds = np.array([[p["bbox"]["min"], p["bbox"]["max"]] for p in visible_parts or parts])
    assembly_min, assembly_max = bounds[:, 0].min(axis=0), bounds[:, 1].max(axis=0)
    meta = {"revision": manifest.get("revision", "B05"), "length_unit": "mm",
            "files": files, "bounds": {"min": assembly_min.tolist(), "max": assembly_max.tolist()},
            "review_status": manifest.get("review_status", "数字装配审阅 · 实物试装待验证")}
    return parts, meta


def build_viewer(build_dir, output=None):
    build_dir = Path(build_dir).resolve()
    output = Path(output).resolve() if output else build_dir / "index.html"
    parts, meta = collect(build_dir)
    template = (HERE / "viewer-template.html").read_text()
    def safe_json(value):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = template.replace("__ASSEMBLY_DATA__", safe_json(parts)).replace("__ASSEMBLY_META__", safe_json(meta))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html)
    print(f"Offline viewer: {output} ({len(parts)} parts, {output.stat().st_size:,} bytes)")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, default=HERE / "build")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    build_viewer(args.build_dir, args.output)
