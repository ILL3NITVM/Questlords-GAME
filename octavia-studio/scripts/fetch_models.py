#!/usr/bin/env python3
"""Download checkpoints for the pure-Python backend — deliberately manual.

The studio never fetches weights on its own. A checkpoint is 4-24 GB and
which one belongs on a given machine is the operator's call, so this is a
separate command that reports sizes, checks free disk, and asks before it
touches the network.

    python scripts/fetch_models.py --list
    python scripts/fetch_models.py --model runwayml/stable-diffusion-v1-5
    python scripts/fetch_models.py --model <id> --yes        # skip the prompt
"""
from __future__ import annotations

import argparse
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from renderers.diffusers_local import MODEL_TIERS, select_device  # noqa: E402
from scripts.detect_hardware import full_report  # noqa: E402


def human(gb: float) -> str:
    return f"{gb:.1f} GB"


def cmd_list() -> int:
    hw = full_report(ROOT)
    tier = hw["advice"]["tier"]
    device, dtype = select_device()
    free = hw["storage"]["free_gb"]

    print("HARDWARE")
    print(f"  device      {device} ({dtype})")
    print(f"  gpu         {hw['gpu']['vendor'] or 'none'}")
    for d in hw["gpu"]["devices"]:
        print(f"              {d['name']} ({d.get('vram_mb', 0)} MB VRAM)")
    print(f"  system ram  {hw['memory']['total_mb']} MB")
    print(f"  free disk   {human(free)}")
    print(f"  tier        {tier}")

    print("\nRECOMMENDED CHECKPOINTS (nothing is downloaded by this command)")
    for model_id, size in MODEL_TIERS.get(tier, MODEL_TIERS["cpu_only"]):
        fits = "ok" if free > size * 1.4 else "NOT ENOUGH FREE DISK"
        print(f"  {model_id:52s} ~{human(size):>9s}   {fits}")

    if device == "cpu":
        print("\n  Note: on CPU a single 40-step pass at 896x1152 takes minutes, not")
        print("  seconds. Lower `hero.passes.base.steps` and the output resolution,")
        print("  or run on a CUDA/MPS machine.")
    print(f"\n  Then set in config/studio.yaml:")
    print(f"    renderer.backend: diffusers")
    print(f"    renderer.diffusers.model_id: <the id above>")
    return 0


def cmd_fetch(model_id: str, assume_yes: bool) -> int:
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("huggingface_hub is not installed.")
        print("  pip install -r requirements-local.txt")
        return 1

    known = {m: s for tier in MODEL_TIERS.values() for m, s in tier}
    size = known.get(model_id)
    free = shutil.disk_usage(ROOT).free / 2**30

    print(f"Model      {model_id}")
    print(f"Size       ~{human(size) if size else 'unknown'}")
    print(f"Free disk  {human(free)}")
    if size and free < size * 1.4:
        print(f"\nRefusing: needs roughly {human(size * 1.4)} free including working "
              f"space, and only {human(free)} is available.")
        return 1

    if not assume_yes:
        reply = input("\nDownload now? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("Cancelled. Nothing was downloaded.")
            return 1

    print("\nDownloading (this takes a while) ...")
    path = snapshot_download(repo_id=model_id,
                            allow_patterns=["*.json", "*.txt", "*.safetensors",
                                            "*.model"])
    print(f"\nDone: {path}")
    print("\nSet in config/studio.yaml:")
    print(f"  renderer.backend: diffusers")
    print(f"  renderer.diffusers.model_id: {model_id}")
    print(f"  renderer.diffusers.local_files_only: true")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch checkpoints for the local backend")
    ap.add_argument("--list", action="store_true", help="show recommendations only")
    ap.add_argument("--model", default=None, help="model id to download")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    args = ap.parse_args()

    if args.model:
        return cmd_fetch(args.model, args.yes)
    return cmd_list()


if __name__ == "__main__":
    raise SystemExit(main())
