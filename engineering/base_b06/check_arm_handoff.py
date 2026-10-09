# SPDX-License-Identifier: CC-BY-NC-4.0
"""Check canonical base fingerprints; optionally reject stale arm context/receipt.

Source consistency only. Does not validate assembly, wiring, or rated loads.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HANDOFF = ROOT / "engineering/base_b06/arm-handoff.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(root, handoff, context=None, receipt=None):
    errors = []
    for name, artifact in handoff["sources"].items():
        path = root / artifact["path"]
        if not path.is_file() or sha(path) != artifact["sha256"]:
            errors.append("canonical source changed or missing: " + name)
    manifest = json.loads((root / handoff["sources"]["manifest"]["path"]).read_text())
    if manifest.get("interface_contract_sha256") != handoff["sources"]["interface"]["sha256"]:
        errors.append("base manifest does not bind current interface")
    if manifest.get("arm_reference_included") is not False:
        errors.append("canonical base must remain independent of the arm")
    expected = {
        "base_revision": handoff["base_revision"],
        "base_native_sha256": handoff["sources"]["native"]["sha256"],
        "base_manifest_sha256": handoff["sources"]["manifest"]["sha256"],
        "base_interface_contract_sha256": handoff["sources"]["interface"]["sha256"],
    }
    if context is not None:
        for key, value in expected.items():
            if context.get(key) != value:
                errors.append("arm context missing or stale: " + key)
    if receipt is not None:
        if receipt.get("schema") != "odradek.base.arm-handoff-receipt.v1":
            errors.append("receipt schema missing or unsupported")
        for key in ("arm_commit", "arm_model", "integration_status"):
            if not receipt.get(key):
                errors.append("receipt missing: " + key)
        if receipt.get("base_priority") is not True:
            errors.append("receipt must acknowledge base priority")
        for key, value in expected.items():
            if receipt.get("base_context", {}).get(key) != value:
                errors.append("receipt source missing or stale: " + key)
        for name, artifact in handoff["sources"].items():
            if receipt.get("base_sources", {}).get(name) != artifact["sha256"]:
                errors.append("receipt source missing or stale: " + name)
        # A cache is acceptable only when its actual bytes match the native.
        model_context = receipt.get("base_cache_path")
        if model_context:
            path = Path(model_context)
            if not path.is_absolute():
                path = root / path
            if not path.is_file() or sha(path) != expected["base_native_sha256"]:
                errors.append("receipt native cache bytes missing or stale")
    return {
        "schema": "odradek.base.arm-handoff-check.v1",
        "base_revision": handoff["base_revision"],
        "canonical_sources_pass": not any(e.startswith("canonical") or e.startswith("base manifest") or e.startswith("canonical base") for e in errors),
        "arm_context_checked": context is not None,
        "receipt_checked": receipt is not None,
        "pass": not errors,
        "errors": errors,
        "limits": "Fingerprint and metadata consistency only; no model mesh, mating, wiring, load or production qualification.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm-context", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(HANDOFF.read_text())
        context = json.loads(args.arm_context.read_text()) if args.arm_context else None
        receipt = json.loads(args.receipt.read_text()) if args.receipt else None
        report = check(ROOT, data, context, receipt)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report = {"pass": False, "errors": [str(exc)]}
    result = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result)
    print(result, end="")
    raise SystemExit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
