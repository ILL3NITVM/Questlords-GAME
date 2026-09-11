# Octavia Studio

An automated photographic pipeline for generating large, diverse image sets of
a single persistent fictional adult persona, **Octavia**.

The studio is the director. An external image-generation backend is the
renderer. Everything above the renderer — identity lock, wardrobe, scenes,
poses, cameras, QC, diversity control — is renderer-agnostic and testable
without spending a single GPU-second.

---

## Status at a glance

```
python studio.py status
```

Run `python studio.py doctor` for a full readiness report including hardware,
renderer availability and blocking items.

---

## Quick start

```bash
pip install -r requirements.txt

python studio.py doctor                 # what works, what is missing
python studio.py index-references       # hash + index the Octavia reference set
python studio.py generate --count 8     # 8-frame batch through the mock renderer
python studio.py qc latest              # QC report
python studio.py stats latest           # diversity / collapse report
```

A full campaign:

```bash
python studio.py generate --count 64 --campaign wardrobe --diversity high
```

---

## The identity contract

Octavia is defined by three files. Nothing else may assert who she is.

| File | Owns |
|---|---|
| `config/identity.yaml` | face geometry, eyes, brows, skin, hair, signature props |
| `config/physique.yaml` | locked body ratios, anatomy realism, permitted vs forbidden drift |
| `config/content_policy.yaml` | adult-only guarantee, coverage rules, scene-text suppression |

`config/identity.yaml` deliberately contains **no** clothing, pose, camera,
environment, lighting or expression terms. Those are variable axes, and letting
them leak into the identity spec is how a persona becomes overfit to one look.
A test (`test_identity_spec_excludes_variable_axes`) enforces this.

### Physique conservation

Body proportions are identity; apparent body shape in a photograph is not.
`config/physique.yaml` separates the two explicitly:

- **`ratios`** — locked relationships (shoulder:waist, hip:waist, torso:leg)
  expressed as ratios rather than measurements, so they survive crop and
  focal-length changes.
- **`permitted_variation`** — perspective effects QC must *not* punish
  (24mm vs 105mm, seated compression, arms raised, structured vs draped cloth).
- **`forbidden_drift`** — genuine identity violations (mass change at matched
  focal length, limb-ratio change, apparent-age shift).

---

## Architecture

```
studio.py                CLI
pipeline/
  spec.py                FrameSpec / SeedRecord — the serialisable frame description
  seeds.py               per-axis deterministic seed derivation (BLAKE2b)
  sampler.py             weighted anti-collapse sampling + share caps
  compose.py             seeds -> coherent FrameSpec (furniture, focal, harmony rules)
  prompt.py              FrameSpec -> positive/negative prompt
  history.py             category frequency bookkeeping (window + totals)
  runner.py              campaign orchestration
renderers/
  base.py                Renderer ABC — the only surface the studio calls
  mock.py                zero-cost deterministic placeholder renderer
  comfyui.py             local/remote ComfyUI over its HTTP API
  api.py                 generic hosted HTTP endpoint
qc/
  scoring.py             metric scoring (see "QC honesty" below)
  rules.py               hard floors, defect penalties, accept/reject
  headpose.py            yaw/pitch/roll tracking + left-tilt detection
  contact_sheet.py       8-up review sheets
  review.py              review marks -> sampling feedback weights
data/                    wardrobe, scenes, poses, palettes, materials, cameras
```

The studio only ever calls `renderer.generate_image(spec)`. Swapping backends
requires no changes above `renderers/`.

---

## Reproducibility

Every frame carries a nine-axis seed record written to
`runs/<RUN_ID>/manifest.jsonl`:

```
identity_seed  wardrobe_seed  colour_seed  material_seed  scene_seed
pose_seed      camera_seed    lighting_seed              expression_seed
```

Each axis is derived independently from
`BLAKE2b(master_seed, run_id, frame_index, axis_name)`. Two consequences:

- **Reproducible** — `--seed <master_seed>` rebuilds byte-identical specs.
- **Independently rerollable** — `reroll --axes pose_seed scene_seed` changes
  only the pose and scene, leaving the wardrobe and camera untouched.

```bash
python studio.py reroll <RUN_ID> --rejected-only
python studio.py reroll <RUN_ID> --index 3 7 --axes pose_seed --salt 2
```

Rerolls append to the manifest; the latest record for an index wins.

---

## Anti-collapse

Sampling weight for a candidate on an axis:

```
w = base
  × feedback(axis, value)                        # human review
  × (1 / (1 + window_count))^pressure            # local repetition
  × (1 / (1 + 0.5·total_count))^(pressure/2)     # campaign-wide over-use
  × cap_multiplier                               # 0.02 once over its share cap
  × 1e-6  if it equals the previous frame's value  # hard block on back-to-back repeats
```

Share caps live in `config/studio.yaml` under `diversity.max_family_share`.
A candidate is capped on **every axis it implies**, not just the one being
sampled — picking a pose by `pose_id` also commits to its `pose_family`, and
the family cap has to be checked or it never binds.

`python studio.py stats <RUN_ID>` reports per-axis distribution and flags any
family over its cap.

### Left-tilt suppression

Leftward head tilt is treated as a rare pose, never a signature.

- Roll convention: **negative roll = tilt toward her left shoulder**.
  `roll <= -4°` counts as a left tilt.
- Left-tilt head positions carry a low base weight (`base_left_weight: 0.25`).
- A per-run budget caps them at **8% of accepted frames**; once spent, the
  weight is multiplied by `0.02`.
- Rejected frames do not consume the budget.

Verified across 30 independent seeds by
`test_left_tilt_stays_within_budget_across_many_seeds`.

**Caveat:** a diffusion model does not always obey a requested head angle.
`qc/headpose.py` prefers a *measured* pose from the renderer and marks the
source (`measured` vs `requested`) on every frame. Until a real estimator is
implemented, the left-tilt figure for a non-deterministic backend reflects what
was *asked for*, not what was *drawn*. `studio.py qc` warns when this applies.

---

## QC honesty

The fourteen QC metrics split into two groups, and the studio never blurs them.

**Genuinely computed today** — real measurements:
`novelty`, `head_pose_novelty`, `composition`, `scene_quality`

**Requires a vision model — currently deterministic placeholders:**
`identity_consistency`, `face_consistency`, `physique_consistency`, `anatomy`,
`hands`, `feet`, `pose_naturalness`, `clothing_integrity`, `photorealism`,
`lighting`

Every scorer declares `placeholder_metrics`; run summaries record which metrics
were placeholders; `studio.py qc` marks them `*placeholder` in the report; and
`doctor`/`status` list this as a blocking item. **Do not read a placeholder
identity score as evidence that identity held.**

To make them real, implement `Scorer` in `qc/scoring.py` with:

| Metric group | Approach |
|---|---|
| identity / face consistency | face embeddings (ArcFace / InsightFace) vs `assets/octavia/face_reference/` |
| physique consistency | body keypoint ratios vs `config/physique.yaml` ratios, normalised for focal length |
| anatomy, hands, feet, pose naturalness | keypoint + hand-landmark models (MediaPipe, DWPose) |
| head pose (measured) | face-mesh solvePnP -> real yaw/pitch/roll |
| photorealism, lighting | aesthetic / realism classifier |

Then register it in `get_scorer()`.

---

## Human review loop

```bash
python studio.py generate --count 64      # writes contact_sheets/NN.jpg + review.csv
# mark the MARK column in runs/<RUN_ID>/review.csv
python studio.py review <RUN_ID>          # folds marks into data/feedback.json
python studio.py generate --count 64      # next run reads those weights
```

Marks: `KEEP`, `REJECT`, `IDENTITY_DRIFT`, `BODY_DRIFT`, `POSE_DUPLICATE`,
`WARDROBE_BAD`, `SCENE_BAD`.

Marks are **targeted** — `WARDROBE_BAD` moves only wardrobe and colour weights,
`SCENE_BAD` only scene, palette and lighting. One bad outfit does not poison the
room it was shot in. Weights are clamped to `[0.15, 3.0]`.

---

## Renderer backends

| Backend | Use |
|---|---|
| `mock` | pipeline testing, zero cost, fully deterministic |
| `comfyui` | local or remote ComfyUI over its HTTP API |
| `api` | generic hosted HTTP endpoint |

Set `renderer.backend` in `config/studio.yaml`, or pass `--backend`.

### ComfyUI setup

The studio ships **no** workflow graph. Workflows differ substantially between
model families, so hard-coding one would make the adapter obsolete on your next
checkpoint change. Instead:

1. Build a working text-to-image workflow in the ComfyUI UI.
2. Export it with **Save (API Format)**.
3. Point `renderer.comfyui.workflow_template` at the JSON.
4. Declare which node fields receive the studio's values:

```yaml
renderer:
  comfyui:
    workflow_template: "config/workflows/octavia_txt2img.json"
    node_map:
      positive: {node: "6", field: "text"}
      negative: {node: "7", field: "text"}
      seed:     {node: "3", field: "seed"}
      width:    {node: "5", field: "width"}
      height:   {node: "5", field: "height"}
```

`doctor` probes the server and reports which optional capabilities it has —
IPAdapter / InstantID / PuLID (reference conditioning), ControlNet and OpenPose
(pose conditioning), LoRA loaders, upscalers, face restoration.

**The studio never downloads models.** `doctor` detects your hardware, reports
VRAM/RAM/storage and recommends suitable model classes. Installing them is your
decision.

---

## Testing

```bash
python -m pytest tests/ -q
```

74 tests covering seed reproducibility, left-tilt budget across 30 seeds, share
caps, scene/pose furniture coherence, focal/shot agreement, outfit colour
harmony, identity and policy terms reaching every prompt, QC floors and defect
routing, review feedback targeting, and a full end-to-end mock run.

---

## Directory layout

```
octavia-studio/
  assets/octavia/{reference,face_reference,body_reference}/
  config/       identity.yaml physique.yaml studio.yaml content_policy.yaml
  data/         wardrobe/ scenes/ poses/ palettes/ materials/
  renderers/    base.py mock.py comfyui.py api.py registry.py
  pipeline/     spec.py seeds.py sampler.py compose.py prompt.py history.py runner.py
  qc/           scoring.py rules.py headpose.py contact_sheet.py review.py
  scripts/      detect_hardware.py
  runs/<RUN_ID>/  manifest.jsonl state.json review.csv studio.log
                  images/ contact_sheets/
  tests/
```

Reference images are read-only inputs. No command in this studio modifies,
overwrites or deletes them; `index-references` only reads and hashes them.
