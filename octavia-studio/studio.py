#!/usr/bin/env python3
"""Octavia Studio — command line interface.

    python studio.py doctor
    python studio.py index-references
    python studio.py generate --count 8 --campaign wardrobe
    python studio.py generate --count 64 --campaign wardrobe --diversity high
    python studio.py contact-sheet <RUN_ID>
    python studio.py qc <RUN_ID>
    python studio.py review <RUN_ID>
    python studio.py reroll <RUN_ID> --rejected-only
    python studio.py stats <RUN_ID>
    python studio.py status
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import pathlib
import sys
from typing import Any, Dict, List, Optional

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from pipeline.runner import Run, load_manifest  # noqa: E402
from pipeline.seeds import reroll_axes, seed_record  # noqa: E402
from pipeline.spec import SeedRecord  # noqa: E402
from qc import review as review_mod  # noqa: E402
from qc.contact_sheet import build_contact_sheet  # noqa: E402
from qc.scoring import COMPUTED_METRICS, VISION_METRICS  # noqa: E402
from renderers.base import RendererUnavailable  # noqa: E402
from renderers.registry import available_backends, get_renderer  # noqa: E402
from scripts.detect_hardware import full_report  # noqa: E402

REF_DIRS = ["assets/octavia/reference", "assets/octavia/face_reference",
            "assets/octavia/body_reference"]
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}

C = {"g": "\033[32m", "y": "\033[33m", "r": "\033[31m", "b": "\033[1m",
     "d": "\033[2m", "x": "\033[0m"}


def _c(key: str, text: str) -> str:
    return f"{C[key]}{text}{C['x']}" if sys.stdout.isatty() else text


def load_configs() -> Dict[str, Any]:
    def y(p: str) -> Dict[str, Any]:
        return yaml.safe_load((ROOT / p).read_text(encoding="utf-8"))
    return {"studio": y("config/studio.yaml"), "identity": y("config/identity.yaml"),
            "physique": y("config/physique.yaml"), "policy": y("config/content_policy.yaml")}


def load_feedback(cfg: Dict[str, Any]) -> Dict[str, Any]:
    path = ROOT / cfg.get("feedback", {}).get("store", "data/feedback.json")
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def new_run_id() -> str:
    return _dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def run_dir(run_id: str) -> pathlib.Path:
    return ROOT / "runs" / run_id


def resolve_run(run_id: Optional[str]) -> str:
    if run_id and run_id != "latest":
        return run_id
    runs = sorted((ROOT / "runs").glob("*/manifest.jsonl"))
    if not runs:
        raise SystemExit("No runs found. Generate one first.")
    return runs[-1].parent.name


# ======================================================================
# index-references
# ======================================================================
def cmd_index_references(args: argparse.Namespace) -> int:
    index: Dict[str, Any] = {"schema_version": 1, "generated": _dt.datetime.now().isoformat(),
                             "sets": {}}
    total = 0
    for rel in REF_DIRS:
        d = ROOT / rel
        entries = []
        if d.is_dir():
            for f in sorted(d.iterdir()):
                if f.suffix.lower() not in IMAGE_EXT:
                    continue
                data = f.read_bytes()
                rec = {"file": f.name, "relpath": str(f.relative_to(ROOT)),
                       "bytes": len(data),
                       "sha256": hashlib.sha256(data).hexdigest()}
                try:
                    from PIL import Image
                    with Image.open(f) as im:
                        rec["width"], rec["height"] = im.size
                        rec["mode"] = im.mode
                        rec["aspect"] = round(im.width / im.height, 3)
                except Exception as exc:
                    rec["error"] = str(exc)
                entries.append(rec)
                total += 1
        index["sets"][rel] = {"count": len(entries), "images": entries}

    index["total_images"] = total
    index["identity_version"] = load_configs()["identity"].get("identity_version")
    out = ROOT / "assets/octavia/reference_index.json"
    out.write_text(json.dumps(index, indent=2), encoding="utf-8")

    print(_c("b", "Reference index"))
    for rel, s in index["sets"].items():
        label = rel.split("/")[-1]
        print(f"  {label:18s} {s['count']:3d} images")
        if args.verbose:
            for im in s["images"]:
                dims = f"{im.get('width','?')}x{im.get('height','?')}"
                print(f"      {im['file']:44s} {dims:>11s}  {im['sha256'][:12]}")
    print(f"\n  total {total} images -> {out.relative_to(ROOT)}")
    print(_c("d", "  Reference files are read-only inputs; this command never modifies them."))
    return 0


# ======================================================================
# doctor
# ======================================================================
def cmd_doctor(args: argparse.Namespace) -> int:
    cfgs = load_configs()
    cfg = cfgs["studio"]
    print(_c("b", "OCTAVIA STUDIO — DOCTOR\n"))

    # -- references ----------------------------------------------------
    counts = {}
    for rel in REF_DIRS:
        d = ROOT / rel
        counts[rel] = len([f for f in d.iterdir() if f.suffix.lower() in IMAGE_EXT]) \
            if d.is_dir() else 0
    print(_c("b", "References"))
    for rel, n in counts.items():
        ok = n > 0
        print(f"  {'OK ' if ok else 'MISS'}  {rel:38s} {n} images")

    # -- data ----------------------------------------------------------
    print(_c("b", "\nData"))
    from pipeline.sampler import Catalogue
    try:
        cat = Catalogue()
        data_ok = True
        print(f"  OK    tops {len(cat.tops)}  bottoms {len(cat.bottoms)}  "
              f"dresses {len(cat.dresses)}  footwear {len(cat.footwear)}  "
              f"accessories {len(cat.accessories)}")
        print(f"  OK    scenes {len(cat.scenes)}  lighting {len(cat.lighting)}  "
              f"materials {len(cat.materials)}  colours {len(cat.colours)}  "
              f"harmonies {len(cat.harmonies)}")
        print(f"  OK    poses {len(cat.poses)}  head_positions {len(cat.head_positions)}  "
              f"hands {len(cat.hands)}  expressions {len(cat.expressions)}")
        lefts = [h["id"] for h in cat.head_positions if h["is_left_tilt"]]
        print(f"  OK    left-tilt head positions: {', '.join(lefts)} "
              f"(capped at {cfg['head_pose']['left_tilt_target_share']:.0%})")
    except Exception as exc:
        data_ok = False
        print(f"  FAIL  catalogue failed to load: {exc}")

    # -- python deps ---------------------------------------------------
    print(_c("b", "\nDependencies"))
    deps = {}
    for mod, why in [("PIL", "contact sheets + mock renderer"),
                     ("yaml", "configuration"), ("requests", "optional HTTP helpers")]:
        try:
            __import__(mod)
            deps[mod] = True
            print(f"  OK    {mod:10s} ({why})")
        except ImportError:
            deps[mod] = False
            print(f"  MISS  {mod:10s} ({why})  -> pip install -r requirements.txt")

    # -- hardware ------------------------------------------------------
    print(_c("b", "\nHardware"))
    hw = full_report(ROOT)
    gpu = hw["gpu"]
    print(f"  cpu cores      {hw['cpu_count']}")
    print(f"  system ram     {hw['memory']['total_mb']} MB")
    print(f"  free storage   {hw['storage']['free_gb']} GB")
    print(f"  gpu            {gpu['vendor'] or 'none detected'}")
    for dev in gpu["devices"]:
        print(f"                 {dev['name']} ({dev.get('vram_mb', 0)} MB VRAM)")
    print(f"  tier           {hw['advice']['tier']}")
    for line in hw["advice"]["recommendations"]:
        print(f"    - {line}")
    for w in hw["advice"]["warnings"]:
        print(_c("y", f"    ! {w}"))
    if hw["advice"]["model_classes"]:
        print("    suggested model classes (NOT downloaded):")
        for m in hw["advice"]["model_classes"]:
            print(f"      * {m}")

    # -- renderers -----------------------------------------------------
    print(_c("b", "\nRenderers"))
    backend_status: Dict[str, Any] = {}
    for name, desc in available_backends().items():
        try:
            r = get_renderer(name, cfg, ROOT / "runs/_probe")
            info = r.preflight()
            backend_status[name] = {"ok": True, "info": info}
            extra = ""
            if name == "comfyui":
                caps = [k for k, v in info.get("capabilities", {}).items() if v]
                extra = f"  capabilities: {', '.join(caps) if caps else 'none detected'}"
                if not info.get("ready"):
                    extra += "  (workflow/node_map/checkpoint not configured)"
            print(_c("g", f"  OK    {name:9s}") + f" {desc}{extra}")
        except RendererUnavailable as exc:
            backend_status[name] = {"ok": False, "error": str(exc)}
            print(_c("d", f"  n/a   {name:9s} {exc}"))
        except Exception as exc:
            backend_status[name] = {"ok": False, "error": str(exc)}
            print(_c("r", f"  ERR   {name:9s} {type(exc).__name__}: {exc}"))
    print(f"  active backend in config: {_c('b', cfg['renderer']['backend'])}")

    # -- QC ------------------------------------------------------------
    print(_c("b", "\nQC"))
    print(f"  OK    computed metrics    : {', '.join(COMPUTED_METRICS)}")
    print(_c("y", f"  STUB  vision metrics      : {', '.join(VISION_METRICS)}"))
    print(_c("d", "        These return deterministic placeholders until a vision scorer"))
    print(_c("d", "        is implemented — see qc/scoring.py. Do not trust them as"))
    print(_c("d", "        measurements of identity or anatomy."))

    # -- blocking summary ----------------------------------------------
    blocking = []
    if not any(counts.values()):
        blocking.append("No reference images indexed")
    if not data_ok:
        blocking.append("Data catalogue failed to load")
    if not deps.get("PIL"):
        blocking.append("Pillow not installed")
    real = [n for n, s in backend_status.items() if s["ok"] and n != "mock"]
    if not real:
        blocking.append("No real render backend available (only mock)")
    elif "comfyui" in real and not backend_status["comfyui"]["info"].get("ready"):
        blocking.append("ComfyUI reachable but no workflow_template / node_map / checkpoint")
    blocking.append("Vision-based QC scorer not implemented (identity/anatomy scores are placeholders)")

    print(_c("b", "\nBlocking items for real generation"))
    if blocking:
        for b in blocking:
            print(_c("y", f"  - {b}"))
    else:
        print(_c("g", "  none"))

    (ROOT / "runs").mkdir(exist_ok=True)
    (ROOT / "runs/_doctor.json").write_text(
        json.dumps({"hardware": hw, "backends": backend_status,
                    "references": counts, "blocking": blocking}, indent=2, default=str),
        encoding="utf-8")
    return 0


# ======================================================================
# generate
# ======================================================================
def cmd_generate(args: argparse.Namespace) -> int:
    cfgs = load_configs()
    cfg = cfgs["studio"]
    run_id = args.run_id or new_run_id()
    backend = args.backend or cfg["renderer"]["backend"]

    run = Run(ROOT, run_id, cfg, cfgs["identity"], cfgs["physique"], cfgs["policy"])
    feedback = load_feedback(cfg) if cfg.get("feedback", {}).get("enabled", True) else {}
    if feedback:
        print(_c("d", f"  applying human feedback across {len(feedback)} axes"))

    def progress(i: int, total: int, rec: Dict[str, Any]) -> None:
        v = rec.get("verdict", {})
        mark = _c("g", "keep") if v.get("accepted") else _c("r", "rej ")
        if not rec.get("render_ok"):
            mark = _c("r", "FAIL")
        k = rec.get("category_keys", {})
        hp = rec.get("head_pose") or {}
        print(f"  [{i+1:3d}/{total}] {mark} {rec.get('overall_score',0):5.1f}  "
              f"{k.get('scene_id',''):24s} {k.get('pose_id',''):20s} "
              f"{k.get('head_position',''):22s} roll{hp.get('roll',0):+6.1f}")

    print(_c("b", f"OCTAVIA STUDIO — run {run_id}"))
    print(f"  count={args.count} campaign={args.campaign} diversity={args.diversity} "
          f"backend={backend}\n")
    try:
        summary = run.execute(count=args.count, campaign=args.campaign,
                              diversity=args.diversity, master_seed=args.seed,
                              backend=backend, feedback=feedback, progress=progress)
    except RendererUnavailable as exc:
        print(_c("r", f"\nRenderer unavailable: {exc}"))
        return 2

    print()
    _print_summary(summary)

    if not args.no_sheets:
        sheets = _build_sheets(run_id, cfg)
        print(f"\n  contact sheets: {len(sheets)} -> runs/{run_id}/contact_sheets/")

    manifest = load_manifest(run_dir(run_id))
    review_path = run_dir(run_id) / "review.csv"
    review_mod.write_review_template(manifest, review_path)
    print(f"  review template: runs/{run_id}/review.csv")
    print(f"\n  next: python studio.py qc {run_id}")
    return 0


def _print_summary(s: Dict[str, Any]) -> None:
    print(_c("b", "Run summary"))
    print(f"  run_id        {s['run_id']}")
    print(f"  master_seed   {s['master_seed']}   (reproduce with --seed {s['master_seed']})")
    print(f"  accepted      {s['accepted']} / {s['count']}")
    print(f"  rejected      {s['rejected']}     failed {s['failed']}")
    print(f"  elapsed       {s['elapsed_seconds']}s")
    target = s.get("left_tilt_target") or 0.08
    share = s.get("left_tilt_share", 0.0)
    ok = share <= target
    print(f"  left tilt     {share:.1%} of accepted  (target <= {target:.0%})  "
          f"{_c('g','OK') if ok else _c('r','OVER')}")
    if s.get("scorer_placeholder_metrics"):
        print(_c("y", f"  scorer        {s['scorer']} — "
                      f"{len(s['scorer_placeholder_metrics'])} metrics are placeholders"))


def _build_sheets(run_id: str, cfg: Dict[str, Any]) -> List[pathlib.Path]:
    manifest = load_manifest(run_dir(run_id))
    batch = int(cfg.get("studio", {}).get("contact_sheet_batch", 8))
    out: List[pathlib.Path] = []
    sheets_dir = run_dir(run_id) / "contact_sheets"
    sheets_dir.mkdir(parents=True, exist_ok=True)
    for i in range(0, len(manifest), batch):
        n = i // batch + 1
        path = sheets_dir / f"{n:02d}.jpg"
        try:
            build_contact_sheet(manifest[i:i + batch], path, n, run_id)
            out.append(path)
        except Exception as exc:
            print(_c("r", f"  contact sheet {n} failed: {exc}"))
    return out


def cmd_contact_sheet(args: argparse.Namespace) -> int:
    run_id = resolve_run(args.run_id)
    cfg = load_configs()["studio"]
    sheets = _build_sheets(run_id, cfg)
    for s in sheets:
        print(f"  {s.relative_to(ROOT)}")
    print(f"\n  {len(sheets)} contact sheets for {run_id}")
    return 0


# ======================================================================
# qc / stats
# ======================================================================
def cmd_qc(args: argparse.Namespace) -> int:
    run_id = resolve_run(args.run_id)
    manifest = load_manifest(run_dir(run_id))
    if not manifest:
        raise SystemExit(f"No manifest for run {run_id}")
    cfg = load_configs()["studio"]

    accepted = [r for r in manifest if r.get("verdict", {}).get("accepted")]
    rejected = [r for r in manifest if r.get("render_ok") and not r.get("verdict", {}).get("accepted")]
    failed = [r for r in manifest if not r.get("render_ok")]

    print(_c("b", f"QC — {run_id}"))
    print(f"  frames    {len(manifest)}")
    print(f"  accepted  {len(accepted)}   rejected {len(rejected)}   failed {len(failed)}")

    metrics = sorted({m for r in manifest for m in (r.get("scores") or {})})
    if metrics:
        print(_c("b", "\n  metric            mean   min   max   below-floor"))
        hard = cfg["qc"]["hard_reject"]
        for m in metrics:
            vals = [r["scores"][m] for r in manifest if r.get("scores", {}).get(m) is not None]
            if not vals:
                continue
            floor = hard.get(m)
            below = sum(1 for v in vals if floor and v < floor)
            flag = _c("y", " *placeholder") if m in VISION_METRICS else ""
            print(f"  {m:18s} {sum(vals)/len(vals):5.1f} {min(vals):5.1f} {max(vals):5.1f}"
                  f"   {below if floor else '-':>3}{flag}")

    if rejected:
        print(_c("b", "\n  rejections"))
        for r in rejected[:20]:
            print(f"    #{r['index']:03d}  " + "; ".join(r["verdict"]["reasons"]))

    print(_c("b", "\n  head pose"))
    tilts = {"left": 0, "neutral": 0, "right": 0}
    for r in accepted:
        hp = r.get("head_pose") or {}
        tilts[hp.get("tilt_class", "neutral")] = tilts.get(hp.get("tilt_class", "neutral"), 0) + 1
    total = max(1, len(accepted))
    target = cfg["head_pose"]["left_tilt_target_share"]
    for k, v in tilts.items():
        bar = "#" * int(40 * v / total)
        flag = ""
        if k == "left":
            flag = _c("g", "  within target") if v / total <= target else _c("r", "  OVER TARGET")
        print(f"    {k:8s} {v:3d}  {v/total:5.1%} {bar}{flag}")

    sources = {}
    for r in accepted:
        s = (r.get("head_pose") or {}).get("source", "?")
        sources[s] = sources.get(s, 0) + 1
    print(f"    pose source: {sources}")
    if sources.get("requested"):
        print(_c("y", "    ! Some head poses are the REQUESTED angle, not a measured one."))
        print(_c("d", "      A real renderer may not obey the request; implement a measured"))
        print(_c("d", "      estimator in qc/headpose.py before trusting the left-tilt figure."))

    review_path = run_dir(run_id) / "review.csv"
    review_mod.write_review_template(manifest, review_path)
    print(f"\n  review template refreshed: runs/{run_id}/review.csv")
    print(f"  mark the MARK column, then: python studio.py review {run_id}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    run_id = resolve_run(args.run_id)
    manifest = load_manifest(run_dir(run_id))
    if not manifest:
        raise SystemExit(f"No manifest for run {run_id}")
    cfg = load_configs()["studio"]
    accepted = [r for r in manifest if r.get("verdict", {}).get("accepted")]

    from collections import Counter
    print(_c("b", f"DIVERSITY — {run_id}  ({len(accepted)} accepted frames)"))
    caps = cfg["diversity"]["max_family_share"]
    axes = ["wardrobe_family", "scene_family", "scene_id", "env_palette", "pose_family",
            "pose_id", "head_position", "tilt_class", "colour_family", "camera_shot",
            "camera_focal", "camera_height", "expression", "lighting", "hands"]

    over_cap: List[str] = []
    for axis in axes:
        counter = Counter(r.get("category_keys", {}).get(axis, "") for r in accepted)
        counter.pop("", None)
        if not counter:
            continue
        total = sum(counter.values())
        cap = caps.get(axis)
        print(_c("b", f"\n  {axis}") + _c("d", f"   distinct={len(counter)}"
              + (f"  cap={cap:.0%}" if cap else "")))
        for value, n in counter.most_common(args.top):
            share = n / total
            flag = ""
            if cap and share > cap:
                flag = _c("r", "  OVER CAP")
                over_cap.append(f"{axis}={value} at {share:.0%} (cap {cap:.0%})")
            bar = "#" * int(34 * share)
            print(f"    {value[:30]:30s} {n:3d} {share:6.1%} {bar}{flag}")

    print(_c("b", "\n  collapse check"))
    if over_cap:
        for o in over_cap:
            print(_c("r", f"    OVER  {o}"))
        print(_c("d", "    Subsequent runs will automatically bias away from these."))
    else:
        print(_c("g", "    no family exceeds its share cap"))
    return 0


# ======================================================================
# review
# ======================================================================
def cmd_review(args: argparse.Namespace) -> int:
    run_id = resolve_run(args.run_id)
    cfg = load_configs()["studio"]
    manifest = load_manifest(run_dir(run_id))
    review_path = run_dir(run_id) / "review.csv"
    marks = review_mod.read_review(review_path)
    if not marks:
        print(_c("y", f"  No marks found in {review_path.relative_to(ROOT)}"))
        print("  Fill the MARK column with one of: " + ", ".join(review_mod.MARKS))
        return 1
    fb_path = ROOT / cfg["feedback"]["store"]
    result = review_mod.apply_review(manifest, marks, fb_path, cfg)
    print(_c("b", f"Review applied — {run_id}"))
    print(f"  marks read     {result['marks_read']}")
    for mark, n in sorted(result["adjustments"].items()):
        print(f"    {mark:16s} {n} weight adjustments")
    print(f"  axes touched   {', '.join(result['axes_touched'])}")
    print(f"  feedback file  {fb_path.relative_to(ROOT)}")
    print(_c("d", "\n  The next generate run will bias sampling using these weights."))
    return 0


# ======================================================================
# reroll
# ======================================================================
def cmd_reroll(args: argparse.Namespace) -> int:
    run_id = resolve_run(args.run_id)
    cfgs = load_configs()
    cfg = cfgs["studio"]
    manifest = load_manifest(run_dir(run_id))
    if not manifest:
        raise SystemExit(f"No manifest for run {run_id}")

    state_path = run_dir(run_id) / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
    master_seed = state.get("master_seed")
    if master_seed is None:
        raise SystemExit("Run state.json missing master_seed; cannot reroll deterministically.")

    if args.rejected_only:
        targets = [r for r in manifest
                   if not r.get("verdict", {}).get("accepted") or not r.get("render_ok")]
    elif args.index is not None:
        targets = [r for r in manifest if r["index"] in args.index]
    else:
        targets = manifest

    if not targets:
        print(_c("g", "  Nothing to reroll — no rejected frames."))
        return 0

    axes = args.axes or ["pose_seed", "scene_seed", "wardrobe_seed",
                         "colour_seed", "camera_seed", "expression_seed"]
    print(_c("b", f"REROLL — {run_id}"))
    print(f"  frames: {len(targets)}   axes: {', '.join(axes)}")
    print(f"  attempt salt: {args.salt}\n")

    # Rebuild the diversity history from the frames we are KEEPING, so the
    # rerolled frames are pushed away from what already survived.
    from pipeline.history import DiversityHistory
    from pipeline.sampler import Catalogue, Sampler
    from pipeline.compose import Composer
    from pipeline.prompt import build_prompts
    from qc.scoring import get_scorer, overall
    from qc.rules import apply_defect_penalties, judge
    from qc import headpose as hp_mod

    target_idx = {r["index"] for r in targets}
    keepers = [r for r in manifest if r["index"] not in target_idx
               and r.get("verdict", {}).get("accepted")]

    history = DiversityHistory(window=int(cfg["diversity"]["history_window"]))
    for r in keepers:
        history.record(r.get("category_keys", {}), accepted=True)

    catalogue = Catalogue()
    sampler = Sampler(catalogue, history, cfg, feedback=load_feedback(cfg),
                      planned_total=len(manifest), diversity=args.diversity)
    composer = Composer(catalogue, sampler, cfg, cfgs["policy"])
    scorer = get_scorer(cfg)
    backend = args.backend or cfg["renderer"]["backend"]
    renderer = get_renderer(backend, cfg, run_dir(run_id) / "images")
    try:
        renderer.preflight()
    except RendererUnavailable as exc:
        print(_c("r", f"  Renderer unavailable: {exc}"))
        return 2

    run = Run(ROOT, run_id, cfg, cfgs["identity"], cfgs["physique"], cfgs["policy"])
    accepted = 0
    with open(run.manifest_path, "a", encoding="utf-8") as mf:
        for rec in targets:
            index = rec["index"]
            old = SeedRecord.from_dict(rec["seeds"])
            seeds = reroll_axes(old, axes, master_seed, run_id, index, salt=args.salt)
            spec = composer.compose(run_id, index, seeds, campaign=rec.get("campaign", "wardrobe"))
            spec.prompt, spec.negative_prompt = build_prompts(
                spec, cfgs["identity"], cfgs["physique"], cfgs["policy"], catalogue)
            result = renderer.generate_image(spec)
            if not result.ok:
                print(_c("r", f"  #{index:03d} render failed: {result.error}"))
                continue
            head = hp_mod.estimate(spec.head, result.measured_head_pose, backend == "mock")
            scores, defects = scorer.score(spec, result.image_path, head, history)
            scores = apply_defect_penalties(scores, defects, cfg["qc"]["defect_penalties"])
            verdict = judge(scores, defects, cfg["qc"])
            keys = spec.category_keys()
            keys["tilt_class"] = head.tilt_class
            history.record(keys, accepted=verdict.accepted)
            if verdict.accepted:
                accepted += 1
            new_rec = run._record(spec, head, scores, verdict.to_dict(), scorer.kind,
                                  result, overall(scores), keys)
            new_rec["rerolled_from"] = rec["seeds"]
            new_rec["reroll_salt"] = args.salt
            mf.write(json.dumps(new_rec, default=str) + "\n")
            mark = _c("g", "keep") if verdict.accepted else _c("r", "rej ")
            print(f"  #{index:03d} {mark} {overall(scores):5.1f}  "
                  f"{keys.get('scene_id',''):24s} {keys.get('pose_id','')}")
            if not verdict.accepted:
                print(_c("d", f"         {'; '.join(verdict.reasons)}"))

    renderer.close()
    print(f"\n  {accepted}/{len(targets)} rerolled frames accepted")
    _build_sheets(run_id, cfg)
    print(f"  contact sheets rebuilt for {run_id}")
    return 0


# ======================================================================
# status
# ======================================================================
def cmd_status(args: argparse.Namespace) -> int:
    cfgs = load_configs()
    cfg = cfgs["studio"]
    counts = {}
    for rel in REF_DIRS:
        d = ROOT / rel
        counts[rel] = len([f for f in d.iterdir() if f.suffix.lower() in IMAGE_EXT]) \
            if d.is_dir() else 0

    from pipeline.sampler import Catalogue
    try:
        cat = Catalogue()
        wardrobe_n = len(cat.tops) + len(cat.bottoms) + len(cat.dresses) + \
            len(cat.footwear) + len(cat.accessories)
        data_ok = True
    except Exception:
        wardrobe_n, data_ok = 0, False

    real_backends = []
    for name in ("comfyui", "api"):
        try:
            r = get_renderer(name, cfg, ROOT / "runs/_probe")
            info = r.preflight()
            real_backends.append((name, info.get("ready", True)))
        except Exception:
            pass

    runs = sorted(p.parent.name for p in (ROOT / "runs").glob("*/manifest.jsonl"))

    blocking = []
    if not any(counts.values()):
        blocking.append("no reference images")
    if not data_ok:
        blocking.append("data catalogue broken")
    if not real_backends:
        blocking.append("no real render backend configured (mock only)")
    elif not any(ready for _, ready in real_backends):
        blocking.append("render backend reachable but not fully configured")
    blocking.append("vision-based QC scorer not implemented "
                    "(identity/physique/anatomy scores are placeholders)")

    ready = not blocking

    print()
    print("OCTAVIA STUDIO STATUS")
    print(f"Identity references: {counts['assets/octavia/reference']} in reference/, "
          f"{counts['assets/octavia/face_reference']} in face_reference/")
    print(f"Body references:     {counts['assets/octavia/body_reference']}")
    backend_desc = cfg["renderer"]["backend"]
    if real_backends:
        backend_desc += "  (available: " + ", ".join(
            f"{n}{'' if r else ' [unconfigured]'}" for n, r in real_backends) + ")"
    else:
        backend_desc += "  (no real backend reachable)"
    print(f"Renderer:            {backend_desc}")
    print(f"QC:                  rules + {len(COMPUTED_METRICS)} computed metrics, "
          f"{len(VISION_METRICS)} placeholder metrics pending a vision scorer")
    print(f"Pose balancing:      active — left tilt capped at "
          f"{cfg['head_pose']['left_tilt_target_share']:.0%} of accepted frames")
    print(f"Wardrobe database:   {wardrobe_n} garments, {len(cat.colours) if data_ok else 0} colours, "
          f"{len(cat.scenes) if data_ok else 0} scenes, {len(cat.poses) if data_ok else 0} poses")
    print(f"Ready for first real batch: {'YES' if ready else 'NO'}")
    print("Blocking items:")
    for b in blocking:
        print(f"  - {b}")
    if runs:
        print(f"Completed runs:      {len(runs)} (latest: {runs[-1]})")
    print(f"Next command:        {'python studio.py generate --count 64 --campaign wardrobe --diversity high' if ready else 'python studio.py doctor'}")
    print()
    return 0


# ======================================================================
def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="studio.py", description="Octavia Studio")
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("doctor", help="environment, renderer and QC readiness check")
    d.set_defaults(func=cmd_doctor)

    ix = sub.add_parser("index-references", help="hash and index the Octavia reference set")
    ix.add_argument("-v", "--verbose", action="store_true")
    ix.set_defaults(func=cmd_index_references)

    g = sub.add_parser("generate", help="generate a campaign")
    g.add_argument("--count", type=int, default=64)
    g.add_argument("--campaign", default="wardrobe",
                   choices=["wardrobe", "outdoor", "studio", "editorial"])
    g.add_argument("--diversity", default="normal", choices=["low", "normal", "high"])
    g.add_argument("--seed", type=int, default=None, help="master seed (reproducibility)")
    g.add_argument("--backend", default=None, choices=["mock", "comfyui", "api"])
    g.add_argument("--run-id", default=None)
    g.add_argument("--no-sheets", action="store_true")
    g.set_defaults(func=cmd_generate)

    cs = sub.add_parser("contact-sheet", help="(re)build contact sheets for a run")
    cs.add_argument("run_id", nargs="?", default="latest")
    cs.set_defaults(func=cmd_contact_sheet)

    q = sub.add_parser("qc", help="QC report for a run")
    q.add_argument("run_id", nargs="?", default="latest")
    q.set_defaults(func=cmd_qc)

    s = sub.add_parser("stats", help="diversity statistics for a run")
    s.add_argument("run_id", nargs="?", default="latest")
    s.add_argument("--top", type=int, default=8)
    s.set_defaults(func=cmd_stats)

    rv = sub.add_parser("review", help="ingest review.csv marks into feedback weights")
    rv.add_argument("run_id", nargs="?", default="latest")
    rv.set_defaults(func=cmd_review)

    rr = sub.add_parser("reroll", help="re-generate frames with fresh seeds on chosen axes")
    rr.add_argument("run_id", nargs="?", default="latest")
    rr.add_argument("--rejected-only", action="store_true")
    rr.add_argument("--index", type=int, nargs="*", default=None)
    rr.add_argument("--axes", nargs="*", default=None)
    rr.add_argument("--salt", type=int, default=1)
    rr.add_argument("--diversity", default="high", choices=["low", "normal", "high"])
    rr.add_argument("--backend", default=None, choices=["mock", "comfyui", "api"])
    rr.set_defaults(func=cmd_reroll)

    st = sub.add_parser("status", help="print the studio status block")
    st.set_defaults(func=cmd_status)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
