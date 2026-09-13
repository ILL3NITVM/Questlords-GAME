"""Export a finished run into the existing octavia_studio catalogue.

THE RULE THIS MODULE EXISTS TO RESPECT
--------------------------------------
The existing project's context document is explicit:

    "record actual visible state rather than copying the prompt as truth"
    "Pendant absence/occlusion can be annotated; unknown is not absence"

This studio knows what was *requested*. It does not know what was *rendered*
— the same gap that makes `qc/headpose.py` distinguish a measured head pose
from a requested one. A diffusion model does not reliably obey a prompt, so
copying spec fields into `asset annotate` would launder intent into recorded
observation and quietly corrupt the catalogue that the whole continuity
system depends on.

So this module emits two clearly separated things:

* ``intent.json`` — what the shoot asked for, labelled as intent.
* ``annotate.sh``  — annotation commands **pre-filled but commented out**,
  with `--pendant unknown`, for a human to verify against the actual image
  and uncomment. Nothing is auto-recorded as observed.

``import.sh`` is safe to run unattended: importing pixels and creating a
shoot record asserts nothing about what the image contains.
"""
from __future__ import annotations

import json
import pathlib
import shlex
from typing import Any, Dict, List, Optional

# Their annotate flags that this studio can supply an INTENT for.
INTENT_FIELDS = ("pose", "framing", "expression", "hair_state")


def _spec_intent(spec: Dict[str, Any]) -> Dict[str, Any]:
    camera = spec.get("camera", {}) or {}
    wardrobe = spec.get("wardrobe", {}) or {}
    head = spec.get("head", {}) or {}
    accessories = [a.get("id") for a in (wardrobe.get("accessories") or [])]

    garments: List[str] = []
    for key in ("top", "bottom", "dress", "outer_layer", "footwear"):
        item = wardrobe.get(key)
        if item:
            # Prefer the catalogue id when the garment came from the observed
            # wardrobe, so the outfit is traceable to real records.
            src = (item.get("source") or {}).get("wardrobe_item_id")
            garments.append(src or item.get("id", ""))

    return {
        "pose": (spec.get("pose", {}) or {}).get("label", ""),
        "framing": (camera.get("shot", {}) or {}).get("label", ""),
        "expression": (spec.get("expression", {}) or {}).get("label", ""),
        "hair_state": "as generated; not specified by the shoot",
        "room_hint": (spec.get("scene", {}) or {}).get("label", ""),
        "garments_requested": [g for g in garments if g],
        "pendant_requested": "purple_crystal_pendant" in accessories,
        "head_roll_requested_deg": head.get("roll"),
        "head_yaw_requested_deg": head.get("yaw"),
        "lighting": (spec.get("lighting", {}) or {}).get("label", ""),
    }


def build_bundle(records: List[Dict[str, Any]], out_dir: pathlib.Path,
                 shoot_id: str, run_id: str,
                 studio_root: Optional[str] = None) -> Dict[str, Any]:
    """Write an import bundle for `octavia.py`.

    ``records`` are manifest entries (or a hero recipe) carrying `spec`,
    `image_path` and `prompt`.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    octavia = "python3 octavia.py"
    if studio_root:
        octavia = f"cd {shlex.quote(studio_root)} && python3 octavia.py"

    frames: List[Dict[str, Any]] = []
    import_paths: List[str] = []
    for rec in records:
        image = rec.get("image_path")
        if not image or not pathlib.Path(image).is_file():
            continue
        spec = rec.get("spec", {}) or {}
        frames.append({
            "frame_id": rec.get("frame_id"),
            "index": rec.get("index"),
            "image_path": str(image),
            "seeds": rec.get("seeds"),
            "prompt": rec.get("prompt"),
            "negative_prompt": rec.get("negative_prompt"),
            "intent": _spec_intent(spec),
            "studio_qc": {
                "overall_score": rec.get("overall_score"),
                "scorer": rec.get("scorer"),
                "placeholder_metrics": True,
                "note": "Scores from this studio's heuristic scorer. Ten of its "
                        "fourteen metrics are placeholders, not measurements.",
            },
        })
        import_paths.append(str(image))

    intent = {
        "schema_version": 1,
        "run_id": run_id,
        "shoot_id": shoot_id,
        "frames": frames,
        "WARNING": "These are REQUESTED values, not observations. A renderer "
                   "does not reliably obey a prompt. Verify against the actual "
                   "image before recording any of this as observed state.",
    }
    (out_dir / "intent.json").write_text(json.dumps(intent, indent=2, default=str),
                                         encoding="utf-8")

    # --- import.sh: safe to run unattended -----------------------------
    lines = [
        "#!/usr/bin/env bash",
        "# Import this run's images into the octavia_studio catalogue.",
        "# Safe to run unattended: importing pixels and creating a shoot",
        "# record asserts nothing about what the images contain.",
        "set -euo pipefail",
        "",
        f"{octavia} shoot create {shlex.quote(shoot_id)} "
        f"--name {shlex.quote(f'Generated by octavia-studio run {run_id}')}",
        "",
    ]
    for path in import_paths:
        lines.append(f"{octavia} import {shlex.quote(path)} "
                     f"--shoot {shlex.quote(shoot_id)} --source octavia-studio")
    lines += ["", f"{octavia} --json asset list --shoot {shlex.quote(shoot_id)}",
              f"{octavia} integrity --json", ""]
    script = out_dir / "import.sh"
    script.write_text("\n".join(lines), encoding="utf-8")
    script.chmod(0o755)

    # --- annotate.sh: deliberately inert until a human verifies --------
    ann = [
        "#!/usr/bin/env bash",
        "# Annotation commands pre-filled from the SHOOT INTENT.",
        "#",
        "# Every line is commented out on purpose. This studio knows what it",
        "# ASKED FOR, not what was rendered, and the octavia_studio catalogue",
        "# is a record of observed state. Open each image, check the values,",
        "# correct them, then uncomment the line.",
        "#",
        "# --pendant is 'unknown' rather than 'present' even when the shoot",
        "# requested it: unknown is not absence, and a request is not evidence.",
        "set -euo pipefail",
        "",
        "# Replace <ASSET_ID> with the id printed by import.sh.",
        "",
    ]
    for frame in frames:
        i = frame["intent"]
        ann.append(f"# frame {frame['frame_id']}  ({pathlib.Path(frame['image_path']).name})")
        ann.append(f"#   requested room: {i['room_hint']}")
        ann.append(f"#   requested garments: {', '.join(i['garments_requested']) or 'n/a'}")
        ann.append(
            "# " + f"{octavia} asset annotate <ASSET_ID>"
            f" --pose {shlex.quote(i['pose'])}"
            f" --framing {shlex.quote(i['framing'])}"
            f" --expression {shlex.quote(i['expression'])}"
            f" --pendant unknown"
            f" --notes {shlex.quote(f'octavia-studio run {run_id}; values are INTENT until verified')}")
        ann.append("")
    ann_path = out_dir / "annotate.sh"
    ann_path.write_text("\n".join(ann), encoding="utf-8")
    ann_path.chmod(0o755)

    readme = out_dir / "README.md"
    readme.write_text(f"""# Handoff bundle — run `{run_id}` -> shoot `{shoot_id}`

{len(frames)} image(s) ready for the octavia_studio catalogue.

    bash import.sh        # imports pixels and creates the shoot — safe
    # then verify each image, edit and uncomment annotate.sh

## Why annotate.sh is commented out

This studio records what a shoot **requested**. The catalogue records what a
photograph **shows**. A renderer does not reliably obey a prompt, so copying
spec fields into `asset annotate` would turn intent into recorded observation
and corrupt the continuity history that depends on it.

`--pendant` is emitted as `unknown` even when the shoot asked for the pendant.
Per the project's canon: unknown is not absence, and a request is not evidence.

`intent.json` holds the full requested state for every frame, clearly labelled.

## A note on the QC scores

Any `studio_qc` score in `intent.json` comes from this studio's heuristic
scorer. Ten of its fourteen metrics are deterministic placeholders pending a
vision model. Do not read them as measurements of identity or anatomy.
""", encoding="utf-8")

    return {"shoot_id": shoot_id, "frames": len(frames),
            "bundle_dir": str(out_dir),
            "import_script": str(script), "annotate_script": str(ann_path)}
