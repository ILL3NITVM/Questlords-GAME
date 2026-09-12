"""Incremental batch intake for training photographs.

Training sets arrive in batches, not as one finished directory. Rescanning
a folder wholesale is fine for a static set but loses two things that matter
when material arrives over time:

  * **Provenance.** Which batch an image came from, and when.
  * **Idempotence.** Re-sending a batch, or sending one that overlaps an
    earlier one, must not duplicate images into the set. A duplicate is not
    merely wasted disk — it silently doubles that image's weight during
    training, which is exactly the over-representation the curation stage
    exists to prevent.

`add_batch` copies new files into the training source, skipping anything
already present by content hash, and records a batch manifest. Source files
are copied, never moved: whatever directory you point it at is left intact.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import pathlib
import shutil
from typing import Any, Dict, List, Optional, Sequence

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
LEDGER = "intake_ledger.json"


def _sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_ledger(source_dir: pathlib.Path) -> Dict[str, Any]:
    path = source_dir / LEDGER
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"schema_version": 1, "batches": [], "hashes": {}}


def save_ledger(source_dir: pathlib.Path, ledger: Dict[str, Any]) -> pathlib.Path:
    source_dir.mkdir(parents=True, exist_ok=True)
    path = source_dir / LEDGER
    path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    return path


def iter_incoming(paths: Sequence[pathlib.Path]) -> List[pathlib.Path]:
    """Expand a mix of files and directories into a sorted image list."""
    out: List[pathlib.Path] = []
    for p in paths:
        if p.is_dir():
            out.extend(f for f in sorted(p.rglob("*"))
                       if f.is_file() and f.suffix.lower() in IMAGE_EXT)
        elif p.is_file() and p.suffix.lower() in IMAGE_EXT:
            out.append(p)
    return out


def add_batch(incoming: Sequence[pathlib.Path], source_dir: pathlib.Path,
              batch_name: Optional[str] = None,
              dry_run: bool = False) -> Dict[str, Any]:
    """Copy new images into the training source. Idempotent by content hash."""
    source_dir = pathlib.Path(source_dir)
    ledger = load_ledger(source_dir)
    known: Dict[str, str] = dict(ledger.get("hashes", {}))

    files = iter_incoming(list(incoming))
    batch_id = batch_name or _dt.datetime.now().strftime("batch-%Y%m%d-%H%M%S")

    added: List[Dict[str, str]] = []
    duplicates: List[Dict[str, str]] = []
    failed: List[Dict[str, str]] = []

    if not dry_run:
        source_dir.mkdir(parents=True, exist_ok=True)

    for src in files:
        try:
            digest = _sha256(src)
        except Exception as exc:
            failed.append({"source": str(src), "error": f"{type(exc).__name__}: {exc}"})
            continue

        if digest in known:
            duplicates.append({"source": str(src), "existing": known[digest]})
            continue

        # Name by batch + short hash: stable, collision-free, and the origin
        # stays legible in the filename.
        dest_name = f"{batch_id}_{digest[:10]}{src.suffix.lower()}"
        if not dry_run:
            try:
                shutil.copy2(src, source_dir / dest_name)
            except Exception as exc:
                failed.append({"source": str(src), "error": f"{type(exc).__name__}: {exc}"})
                continue
        known[digest] = dest_name
        added.append({"source": str(src), "stored": dest_name, "sha256": digest})

    result = {
        "batch_id": batch_id,
        "scanned": len(files),
        "added": len(added),
        "duplicates_skipped": len(duplicates),
        "failed": len(failed),
        "source_dir": str(source_dir),
        "dry_run": dry_run,
        "failures": failed[:10],
    }

    if not dry_run and added:
        ledger["hashes"] = known
        ledger["batches"].append({
            "batch_id": batch_id,
            "received": _dt.datetime.now().isoformat(timespec="seconds"),
            "added": len(added),
            "duplicates_skipped": len(duplicates),
            "files": [a["stored"] for a in added],
        })
        save_ledger(source_dir, ledger)

    result["total_in_set"] = len(known)
    return result


def ledger_summary(source_dir: pathlib.Path) -> Dict[str, Any]:
    ledger = load_ledger(pathlib.Path(source_dir))
    on_disk = len([f for f in pathlib.Path(source_dir).glob("*")
                   if f.suffix.lower() in IMAGE_EXT]) if pathlib.Path(source_dir).is_dir() else 0
    return {
        "batches": len(ledger.get("batches", [])),
        "unique_images": len(ledger.get("hashes", {})),
        "files_on_disk": on_disk,
        "recent": [
            {k: b[k] for k in ("batch_id", "received", "added", "duplicates_skipped")}
            for b in ledger.get("batches", [])[-8:]
        ],
    }
