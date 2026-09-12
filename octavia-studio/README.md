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

## The hero frame

One image at the system's ceiling:

```bash
python studio.py hero --candidates 512 --seed 20260911
python studio.py hero --candidates 512 --dry-run     # recipe only, no render
python studio.py hero --candidates 512 --pick 3      # render the 3rd-ranked candidate
```

A campaign optimises for DIVERSITY; a hero frame optimises for QUALITY, and
the two disagree almost everywhere. Diversity sampling deliberately reaches for
the unusual crop, the awkward furniture contact, the wide lens — exactly the
choices most likely to produce an artefact.

`pipeline/hero.py` composes N candidate specs (every coherence rule still
applies) and scores each against a risk model of where diffusion models
actually fail: small faces, prominent hands, bare feet in frame, near-profile
yaw, mirrors, wide-angle distortion, complex furniture contact. Identity
legibility carries the heaviest weight — a beautiful frame of someone who is
not recognisably Octavia has failed at this system's central job.

The risk weights are **informed priors, not measurements**. They encode
well-known failure modes rather than anything measured on your renderer. Tune
`config/studio.yaml: hero.weights` against real output.

Output is `runs/<RUN_ID>/hero_recipe.json` (full spec, seeds, prompt,
budget report, render plan), `hero_prompt.txt`, and `shot_card.png`.
Re-run with the same `--seed` to reproduce the identical frame.

### The shot card

`qc/shotcard.py` renders the selected frame as a photographer would plan it:
the framing diagram at the true output aspect ratio with the subject placed by
shot type, an overhead key-light diagram, camera parameters, the wardrobe and
environment palettes as real swatches, and the identity anchors that must
survive the render.

It exists because a `FrameSpec` is a hundred lines of JSON, and JSON does not
tell you whether the composition is any good. The card does, at a glance,
before any GPU time is spent. It is the plan, not the photograph.

### Multi-pass rendering

A hero frame should not be a single sample. `pipeline/renderplan.py` declares
`base -> hires_fix -> face_detail -> upscale`; the backend executes what it
supports and **records a reason for every pass it skips**, so a hero frame
never claims a refinement that did not happen.

`hires_fix` and `face_detail` denoise are capped low (0.40 / 0.30) on purpose:
above ~0.5 the refinement resamples the face freely and walks the likeness
off-model between passes.

---

## Prompt construction

Prompts are assembled from priority-ranked `Segment` objects, not string
concatenation. That buys four things joining cannot:

**Budget awareness.** CLIP encodes 77 tokens per chunk and influence drops
sharply past chunk 1. An 800-token prompt is not "very detailed" — it is a
75-token prompt followed by 700 tokens of decreasingly-effective noise.

| tier | budget | use |
|---|---|---|
| `compact` | 1 chunk (75 tok) | maximum per-token influence, strongest identity hold |
| `standard` | 2 chunks (150 tok) | identity plus full wardrobe, pose, scene, camera |
| `full` | uncapped | everything, accepting chunk-7 dilution |

**Deduplication.** Repeating "photorealistic" or "adult woman" wastes the
highest-value token positions.

**Parenthesis safety.** In ComfyUI and A1111 `(text)` is emphasis syntax, not
punctuation. Literal parens from data files silently became unintended emphasis
groups, and comma-splitting left unbalanced ones that corrupt parsing. All
literal parens are stripped; parens now appear only where emphasis is intended.
Tight slashes (`f/2.8`) are preserved as meaningful notation.

**Grammatical integrity.** Source phrases in `config/*.yaml` are comma-free and
self-contained, so joining cannot produce orphaned adjectives with no referent.

### Round-robin selection, shot-aware ordering

Segments carry a rank within their group, and assembly takes the most important
segment of *every* group before the second of any. A tight budget then yields a
balanced prompt rather than a deep one that spends everything on identity and
describes no photograph.

Selection order follows what is actually in frame: on a close portrait the hips
are not visible, so physique descriptors are spent on pixels that do not exist
while the gaze, expression and lens that define the frame get trimmed. `face`
emphasis therefore demotes physique and promotes head, expression and camera;
`environment` does the reverse.

### What is guaranteed

Protected from both quota and budget, at every tier:

- the subject/age clause the content policy requires
- all four critical identity anchors (eyes, freckles, hair, signature highlights)
- **the head-roll clause** — the left-tilt budget in `pipeline/sampler.py` only
  reaches the renderer through this clause. Trim it and the model reverts to its
  own preferred tilt, while the manifest still records the roll we *asked* for.

Compact cannot fit all eight content groups in 75 tokens: protected content
alone costs ~38. That is arithmetic, not a tuning failure — compact fits about
five groups, chosen by what the shot shows. Use `standard` when you need
identity *and* complete scene, wardrobe and camera direction.

---

## Training on your existing photo set

If you already have a body of Octavia photographs, that set — not prompt text —
is the reliable way to hold her identity. Prompt text alone will not keep a face
consistent across 64 images.

```bash
python studio.py dataset add <paths> # bring a batch into the set (idempotent)
python studio.py dataset status      # batches received, unique images, curation state
python studio.py dataset ingest      # scan + fingerprint (read-only)
python studio.py dataset analyze     # bias report — read this before training
python studio.py dataset curate      # quality gate + duplicate capping
python studio.py dataset caption     # writes captions.csv; fill it, then re-run
python studio.py dataset export      # kohya/sd-scripts layout + dataset.toml
```

Source files are never moved, modified or deleted. Curation decisions are
metadata; only `export` materialises anything, and it copies.

### Batches arriving over time

`dataset add` is idempotent by content hash, so re-sending a batch, or sending
one that overlaps an earlier one, adds nothing. That matters more than disk:
a duplicate image silently doubles its own weight during training, which is
precisely the over-representation the curation stage exists to prevent.

```bash
python studio.py dataset add ~/shoots/monday --batch monday-shoot
python studio.py dataset add ~/shoots/tuesday ~/extra/one-off.jpg
python studio.py dataset add ~/shoots/monday          # adds 0, skips all
python studio.py dataset status
```

Each batch is recorded in `intake_ledger.json` with its date and file list, so
provenance survives. Stored filenames carry the batch name and a content hash.
Re-run `dataset ingest` after adding to bring new images into curation.

### Why `analyze` runs before training

A LoRA learns whatever is over-represented, **at the weights level**. If 40% of
the source photographs are mirror selfies with a leftward tilt in warm light, the
adapter learns "Octavia" to mean partly that — and the prompt-side pose balancing
in `pipeline/sampler.py` cannot override it. Weight-level bias beats prompt
weighting every time. So the anti-collapse discipline has to start at the dataset.

`analyze` measures what Pillow can measure honestly (near-duplicate clusters,
resolution, aspect buckets, exposure and contrast distribution) and **names the
axes it cannot**: head pose, framing, expression, wardrobe and scene variety all
need a vision model and are reported `UNMEASURED`. Those are the axes most likely
to carry the bias that matters, so a clean report is not evidence of a balanced
set. Look at the images.

It also warns when a quality flag fires on >90% of the set — that almost always
means a miscalibrated threshold, not universally bad data.

### The caption rule, which is counterintuitive

During training, **anything you name becomes a variable bound to those words;
anything you consistently omit is absorbed into the trigger token.**

So for a persistent persona the strategy inverts:

| | |
|---|---|
| **Never caption** | eyes, freckles, hair colour, the green highlights, skin tone, brows, the pendant |
| **Always caption** | framing, pose, head angle, expression, clothing, setting, lighting |

Naming "green hazel eyes" binds that trait to those words — it then appears only
when you say them, and drifts when you do not. Omitting it binds it to
`ohwx_octavia`, which is exactly what a persistent persona needs. Naming the
variable axes lets the model factor them *out* of the identity, so the token
means "Octavia" rather than "Octavia in a pink crop top indoors".

`training/caption.py` strips identity vocabulary automatically — from your own
sheet entries and from any automatic captioner you plug in via `CaptionBackend`.
Off-the-shelf captioners (BLIP2, WD14, CogVLM) will happily emit "a brunette
woman with green eyes and freckles"; `FilterCaptionBackend` removes exactly that,
clause-aware so no grammatical debris is left behind.

### After training: switch identity mode

Once a LoRA exists, the full descriptive block in the prompt becomes actively
harmful — the text encoder pushes toward its own reading of "green-hazel almond
eyes" while the adapter pushes toward the learned face, and the result drifts
off-model. Set in `config/studio.yaml`:

```yaml
identity:
  mode: lora_token          # descriptive | hybrid | lora_token
  trigger_token: "ohwx_octavia"
  lora:
    enabled: true
    name: "octavia_v1.safetensors"
    strength_model: 0.85
```

| mode | identity carried by | use when |
|---|---|---|
| `descriptive` | full prompt description | no adapter exists |
| `hybrid` | trigger token + 3 anchors | LoRA still undertrained |
| `lora_token` | trigger token alone | LoRA holds the face |

The physique lock and the adult-age clause survive **every** mode — a face LoRA
carries neither, so dropping them would be a policy hole, not an optimisation.

Setting `lora_token` or `hybrid` without a trigger token raises rather than
silently rendering a generic person.

### No-training alternative

```bash
python studio.py dataset export --target ipadapter
```

Exports a small, deliberately spread reference subset (highest-quality member of
each distinct near-duplicate cluster) for IPAdapter / InstantID conditioning.
Weaker identity hold than a LoRA, but immediate and free.

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
| `diffusers` | **pure Python** — loads a checkpoint into this process, no server |
| `comfyui` | local or remote ComfyUI over its HTTP API |
| `api` | generic hosted HTTP endpoint |

### Pure-Python backend (no server)

`renderers/diffusers_local.py` runs the whole multi-pass chain in-process:
base txt2img, then img2img hires fix, then a face-detail pass that crops the
face region, resamples it at full resolution and composites it back through a
feathered mask. No ComfyUI, no HTTP, no external process.

```bash
pip install -r requirements-local.txt
# CPU-only machines: install torch from the CPU index first to skip ~2 GB of
# unused CUDA libraries
#   pip install torch --index-url https://download.pytorch.org/whl/cpu

python scripts/fetch_models.py --list          # recommendations for THIS machine
python scripts/fetch_models.py --model stabilityai/stable-diffusion-xl-base-1.0
```

Then in `config/studio.yaml`:

```yaml
renderer:
  backend: diffusers
  diffusers:
    model_id: "stabilityai/stable-diffusion-xl-base-1.0"
    device: auto            # auto | cuda | mps | cpu
    local_files_only: true  # never touch the network at render time
    cpu_offload: false      # set true under ~8 GB VRAM
```

```bash
python studio.py hero --candidates 512 --seed 20260911 --backend diffusers
```

The studio still never downloads weights on its own. `fetch_models.py` reports
size, checks free disk and asks before touching the network; `preflight()`
names exactly what is missing rather than silently reaching out.

**Expect these speeds.** A 40-step pass at 896x1152, three passes:

| device | per pass | full chain |
|---|---|---|
| RTX 4090 / A100 | ~3 s | under a minute |
| RTX 3060, 12 GB | ~12 s | ~1 minute |
| Apple M-series (MPS) | ~30 s | 2-3 minutes |
| CPU, 4 cores | 15-45 min | **an hour or more** |

CPU is supported but not practical for a hero frame. Drop `hero.passes.base.steps`
and the output resolution if you must run without a GPU.

Device and dtype are selected automatically — fp16 on CUDA, fp32 on MPS (fp16
VAE decode is unreliable there) and fp32 on CPU.

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

186 tests covering seed reproducibility, left-tilt budget across 30 seeds, share
caps, scene/pose furniture coherence, focal/shot agreement, outfit colour
harmony, identity and policy terms reaching every prompt, identity-mode
switching, QC floors and defect routing, review feedback targeting, a full
end-to-end mock run, the training subsystem (perceptual hashing, duplicate
clustering, quality gating, identity-term stripping, kohya export), token
budgeting, tier guarantees, hero-objective ranking, render-plan capability
resolution, and the pure-Python backend (crop geometry, device selection,
dimension snapping, plus the full multi-pass chain executed against a tiny
locally-built pipeline).

Tests marked `slow` run a real diffusion pipeline. Skip them with
`pytest -m "not slow"`.

---

## Directory layout

```
octavia-studio/
  assets/octavia/{reference,face_reference,body_reference}/
  config/       identity.yaml physique.yaml studio.yaml content_policy.yaml
  data/         wardrobe/ scenes/ poses/ palettes/ materials/
  renderers/    base.py mock.py diffusers_local.py comfyui.py api.py registry.py
  pipeline/     spec.py seeds.py sampler.py compose.py prompt.py tokens.py
                hero.py renderplan.py history.py runner.py
  qc/           scoring.py rules.py headpose.py contact_sheet.py shotcard.py
                review.py
  training/     ingest.py analyze.py caption.py export.py
  scripts/      detect_hardware.py fetch_models.py
  runs/<RUN_ID>/  manifest.jsonl state.json review.csv studio.log
                  images/ contact_sheets/
  tests/
```

Reference images are read-only inputs. No command in this studio modifies,
overwrites or deletes them; `index-references` only reads and hashes them.
