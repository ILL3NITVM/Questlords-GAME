# Octavia Studio — orientation for a coding agent

A local, automated photographic pipeline that generates large, diverse image
sets of one persistent fictional adult persona. The studio is the director;
an image-generation backend is the renderer. Everything above the renderer is
backend-agnostic and testable with no GPU.

## Run it

```bash
python -m pip install -r requirements.txt      # or: bash setup.sh
python studio.py doctor                        # environment + readiness
python studio.py generate --count 8            # mock renderer, zero cost
python -m pytest tests/ -q -m "not slow"       # 181 tests, ~40s
```

`studio.py` is the only entry point. `python studio.py --help` lists every
command. Nothing here needs network access except fetching model weights,
which is a deliberate, separate, opt-in step.

## Architecture in one pass

```
studio.py          CLI
pipeline/
  spec.py          FrameSpec / SeedRecord — the serialisable frame description
  seeds.py         per-axis deterministic seeds (BLAKE2b)
  sampler.py       weighted anti-collapse sampling + share caps
  compose.py       seeds -> coherent FrameSpec (furniture, focal, harmony rules)
  prompt.py        FrameSpec -> prompt, CLIP-chunk budgeted
  tokens.py        CLIP token estimation and budgeting
  hero.py          best-of-N frame selection against a failure-risk model
  renderplan.py    multi-pass declaration (base / hires / face detail / upscale)
  history.py       category frequency bookkeeping
  runner.py        campaign orchestration
renderers/         base.py + mock / diffusers_local / comfyui / api adapters
qc/                scoring, rules, head pose, contact sheets, shot card, review
training/          intake, ingest, analyze, caption, export for LoRA training
data/              wardrobe, scenes, poses, palettes, materials, cameras (JSON)
config/            identity, physique, studio, content_policy, training (YAML)
```

The studio only ever calls `renderer.generate_image(spec)`. Swapping backends
requires no change above `renderers/`.

## Invariants — do not break these

1. **Reference images are read-only.** Nothing in `assets/octavia/` may be
   modified, moved or deleted. `index-references` only reads and hashes.

2. **Identity anchors are protected in every prompt tier.** Eye colour,
   freckles, hair, and the lime-green highlights survive quota and token
   budget. So does the content-policy age clause.

3. **The head-roll clause is protected.** The left-tilt budget in
   `sampler.py` reaches the renderer *only* through that prompt clause. Trim
   it and the model reverts to its own preferred tilt while the manifest
   still records the roll that was requested — a silent divergence between
   intent and output.

4. **Left head tilt stays at or below 8% of accepted frames.** Verified
   across 30 seeds in `tests/test_headpose.py`. Treat a regression here as a
   real defect, not a flaky test.

5. **Placeholder QC scores must never be presented as measurements.** Ten of
   the fourteen metrics need a vision model and currently return
   deterministic placeholders. Every scorer declares `placeholder_metrics`;
   run summaries, `qc`, `doctor` and `status` all surface it. Keep it that
   way.

6. **Never download model weights automatically.** `scripts/fetch_models.py`
   reports size, checks disk and asks first.

7. **Content policy is not optional.** Subject is always an adult; explicit
   content is blocked in the negative prompt at every tier. See
   `config/content_policy.yaml`.

## What is verified, and what is not

**Verified in this environment:** all 186 tests pass (181 fast + 5 slow).
The full multi-pass render chain in `renderers/diffusers_local.py` was
executed against a tiny locally-built diffusion pipeline — base, hires fix,
face detail and upscale all run, disabled passes are honoured, a repeated
seed reproduces identical pixels, and failures return cleanly.

**Not verified:** no real checkpoint has ever been loaded here. The network
policy blocked huggingface.co, so the backend has never rendered an actual
photograph. Prompt quality, identity hold and the hero risk weights are
informed engineering, not measured results. The hero weights in
`config/studio.yaml` are priors encoding known failure modes; tune them
against real output.

## Where the work is

Highest-value open items, roughly in order:

1. **A real vision-based QC scorer** (`qc/scoring.py`). Face embeddings vs
   `assets/octavia/face_reference/` for identity, body keypoint ratios vs
   `config/physique.yaml` for physique, hand/foot landmarks for anatomy, and
   a measured head pose to replace the requested one in `qc/headpose.py`.
   The interface and thresholds already exist; only the measurement is
   missing.

2. **Measured head pose.** Until then the left-tilt figure reflects what was
   requested, not what was drawn — see `qc/headpose.py`.

3. **A real face detector** for the face-detail pass. `face_crop_box()` in
   `renderers/diffusers_local.py` is a geometric fallback.

4. **Tune the hero risk weights** once real renders exist.

## Conventions

- Python 3.11+, standard library first. Pillow and PyYAML are the only hard
  dependencies; torch/diffusers are optional and only for the local backend.
- Data lives in `data/*.json`, policy in `config/*.yaml`. Phrases that reach
  a prompt are comma-free and self-contained — a value with internal commas
  fragments into orphaned adjectives when joined.
- Tests that touch a real diffusion pipeline are marked `slow`.
- Run `pytest -m "not slow"` for the fast loop.
