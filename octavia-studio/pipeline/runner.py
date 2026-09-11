"""Campaign orchestration — the loop that turns a count into a finished run.

Per frame: derive seeds -> compose spec -> build prompts -> render ->
estimate head pose -> score -> judge -> record history -> append manifest.

Rejected frames do NOT feed the diversity history. If a frame is thrown away,
its scene and pose should still be available to the frames that follow.
"""
from __future__ import annotations

import json
import logging
import pathlib
import time
from typing import Any, Dict, List, Optional

from pipeline.compose import Composer
from pipeline.history import DiversityHistory
from pipeline.prompt import build_prompts
from pipeline.sampler import Catalogue, Sampler
from pipeline.seeds import resolve_master_seed, seed_record
from pipeline.spec import FrameSpec, SeedRecord
from qc import headpose as hp_mod
from qc.rules import apply_defect_penalties, judge
from qc.scoring import get_scorer, overall
from renderers.base import Renderer, RendererUnavailable
from renderers.registry import get_renderer

log = logging.getLogger("octavia.runner")

DETERMINISTIC_BACKENDS = {"mock"}


class Run:
    def __init__(self, root: pathlib.Path, run_id: str, config: Dict[str, Any],
                 identity: Dict[str, Any], physique: Dict[str, Any],
                 policy: Dict[str, Any]) -> None:
        self.root = root
        self.run_id = run_id
        self.config = config
        self.identity = identity
        self.physique = physique
        self.policy = policy
        self.dir = root / "runs" / run_id
        self.images_dir = self.dir / "images"
        self.sheets_dir = self.dir / "contact_sheets"
        self.manifest_path = self.dir / "manifest.jsonl"
        self.state_path = self.dir / "state.json"
        for d in (self.dir, self.images_dir, self.sheets_dir):
            d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    def _setup_logging(self) -> None:
        fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s %(message)s")
        fh = logging.FileHandler(self.dir / "studio.log", encoding="utf-8")
        fh.setFormatter(fmt)
        root_logger = logging.getLogger("octavia")
        root_logger.setLevel(getattr(logging, self.config.get("logging", {}).get("level", "INFO")))
        if not any(isinstance(h, logging.FileHandler) and
                   pathlib.Path(getattr(h, "baseFilename", "")) == (self.dir / "studio.log")
                   for h in root_logger.handlers):
            root_logger.addHandler(fh)

    # ------------------------------------------------------------------
    def execute(self, count: int, campaign: str = "wardrobe", diversity: str = "normal",
                master_seed: Optional[int] = None, backend: Optional[str] = None,
                feedback: Optional[Dict[str, Any]] = None,
                progress=None) -> Dict[str, Any]:
        self._setup_logging()
        master_seed = resolve_master_seed(master_seed)
        backend = backend or self.config.get("renderer", {}).get("backend", "mock")

        log.info("run %s start: count=%d campaign=%s diversity=%s backend=%s seed=%d",
                 self.run_id, count, campaign, diversity, backend, master_seed)

        catalogue = Catalogue()
        history = DiversityHistory(
            window=int(self.config.get("diversity", {}).get("history_window", 24)))
        sampler = Sampler(catalogue, history, self.config, feedback=feedback,
                          planned_total=count, diversity=diversity)
        composer = Composer(catalogue, sampler, self.config, self.policy)
        scorer = get_scorer(self.config)

        renderer: Renderer = get_renderer(backend, self.config, self.images_dir)
        preflight = renderer.preflight()   # may raise RendererUnavailable
        log.info("renderer preflight: %s", json.dumps(preflight, default=str)[:600])

        deterministic = backend in DETERMINISTIC_BACKENDS
        qc_cfg = self.config.get("qc", {})
        penalties = qc_cfg.get("defect_penalties", {})

        manifest: List[Dict[str, Any]] = []
        accepted = rejected = failed = 0
        started = time.time()

        with open(self.manifest_path, "a", encoding="utf-8") as mf:
            for index in range(count):
                seeds = seed_record(master_seed, self.run_id, index)
                spec = composer.compose(self.run_id, index, seeds, campaign=campaign)
                spec.prompt, spec.negative_prompt = build_prompts(
                    spec, self.identity, self.physique, self.policy, catalogue,
                    identity_cfg=self.config.get("identity", {}))

                result = renderer.generate_image(spec)
                if not result.ok:
                    failed += 1
                    log.error("frame %d render failed: %s", index, result.error)
                    record = self._record(spec, None, None, {}, None, result, 0.0)
                    manifest.append(record)
                    mf.write(json.dumps(record, default=str) + "\n")
                    mf.flush()
                    if progress:
                        progress(index, count, record)
                    continue

                head = hp_mod.estimate(spec.head, result.measured_head_pose, deterministic)
                scores, defects = scorer.score(spec, result.image_path, head, history)
                scores = apply_defect_penalties(scores, defects, penalties)
                verdict = judge(scores, defects, qc_cfg)
                headline = overall(scores)

                # History is shaped only by what we keep.
                keys = spec.category_keys()
                keys["tilt_class"] = head.tilt_class
                history.record(keys, accepted=verdict.accepted)

                if verdict.accepted:
                    accepted += 1
                else:
                    rejected += 1
                    log.warning("frame %d rejected: %s", index, "; ".join(verdict.reasons))

                record = self._record(spec, head, scores, verdict.to_dict(),
                                      scorer.kind, result, headline, keys)
                manifest.append(record)
                mf.write(json.dumps(record, default=str) + "\n")
                mf.flush()
                if progress:
                    progress(index, count, record)

        renderer.close()
        elapsed = time.time() - started

        summary = {
            "run_id": self.run_id,
            "master_seed": master_seed,
            "count": count,
            "campaign": campaign,
            "diversity": diversity,
            "backend": backend,
            "accepted": accepted,
            "rejected": rejected,
            "failed": failed,
            "elapsed_seconds": round(elapsed, 1),
            "scorer": scorer.kind,
            "scorer_placeholder_metrics": scorer.placeholder_metrics,
            "identity_mode": self.config.get("identity", {}).get("mode", "descriptive"),
            "lora": self.config.get("identity", {}).get("lora", {}),
            "renderer_preflight": preflight,
            "diversity_report": history.report(),
            "left_tilt_share": round(history.left_tilt_share(), 4),
            "left_tilt_target": self.config.get("head_pose", {}).get("left_tilt_target_share"),
        }
        self.state_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
        log.info("run %s complete: %d accepted, %d rejected, %d failed in %.1fs",
                 self.run_id, accepted, rejected, failed, elapsed)
        return summary

    # ------------------------------------------------------------------
    def _record(self, spec: FrameSpec, head, scores, verdict, scorer_kind,
                result, headline: float, keys: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "index": spec.index,
            "frame_id": spec.frame_id,
            "campaign": spec.campaign,
            "seeds": spec.seeds.to_dict(),
            "category_keys": keys or spec.category_keys(),
            "spec": spec.to_dict(),
            "prompt": spec.prompt,
            "negative_prompt": spec.negative_prompt,
            "image_path": str(result.image_path) if result.image_path else None,
            "render_ok": result.ok,
            "render_error": result.error,
            "render_seconds": round(result.duration_seconds, 2),
            "backend": result.backend,
            "head_pose": head.to_dict() if head else None,
            "scores": scores,
            "overall_score": headline,
            "verdict": verdict,
            "scorer": scorer_kind,
        }


def load_manifest(run_dir: pathlib.Path) -> List[Dict[str, Any]]:
    path = run_dir / "manifest.jsonl"
    if not path.is_file():
        return []
    out = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    # Later records for the same index (rerolls) win.
    dedup: Dict[int, Dict[str, Any]] = {}
    for rec in out:
        dedup[rec.get("index", len(dedup))] = rec
    return [dedup[k] for k in sorted(dedup)]
