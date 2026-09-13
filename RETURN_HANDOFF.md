# Return Handoff — Octavia

Prepared for the assistant resuming on the user's own machine over remote SSH.
This is the counterpart to `octavia-handoff/octavia_studio/handoff/START_HERE.md`,
which came the other way. It describes what was added, what was corrected, and
what is still missing.

## The Short Version

Two Octavia codebases now exist and they are complementary, not rivals:

| | |
|---|---|
| `octavia-handoff/` | The **established** project, exactly as handed over. Post-generation: import, catalogue, continuity, wardrobe, canon, export. 82 tests. |
| `octavia-studio/` | Added here. Pre-generation: shoot planning, anti-collapse sampling, CLIP-budgeted prompts, hero selection, renderer abstraction, LoRA training prep. 211 tests. |
| `octavia-studio/bridge/` | Joins them. |

**The loop could not close in the Claude Code session and closes on your
machine.** Neither pipeline generates images. In that session there was no
image tool, no GPU, and the network policy blocked huggingface.co, so no
checkpoint could ever be loaded. You have an image tool. That is the missing
piece, and it is the only one.

## The Working Loop

```sh
# 1. PLAN — pick the frame most likely to render well, from 512 candidates
cd octavia-studio
python3 studio.py hero --candidates 512 --seed 20260911 --dry-run
#    -> runs/<RUN_ID>/hero_prompt.txt     the prompt to hand your image tool
#    -> runs/<RUN_ID>/shot_card.png       the composition, lighting and palette
#    -> runs/<RUN_ID>/hero_recipe.json    full spec and seeds, reproducible

# 2. GENERATE — your image tool. Use hero_prompt.txt verbatim.
#    Save the raw output into runs/<RUN_ID>/images/ unmodified.

# 3. CATALOGUE — hand it to the established project
python3 studio.py bridge export <RUN_ID> --shoot <shoot-id>
bash runs/<RUN_ID>/handoff/import.sh        # safe to run unattended
#    then verify each image by eye and uncomment annotate.sh
```

Step 3 is where the two halves meet. `import.sh` only moves pixels and creates
a shoot record, so it asserts nothing. `annotate.sh` is deliberately inert —
see **Intent Is Not Observation** below.

## What Was Corrected, In Your Project's Favour

The established canon is authoritative wherever the two disagreed. One real
conflict was found:

`octavia-studio` was asserting `"shoulder-to-waist ratio about 1.55"` into every
prompt. `PROJECT_CONTEXT.md` says to preserve her shape *"without estimating
numerical measurements or changing anatomy to make clothes fit. Adapt the
clothes to her instead."* The ratios were removed from prompts. They remain in
`config/physique.yaml` for a future keypoint-based QC scorer, because measuring
an output is not the same as dictating a measurement to a model. A negative
term now guards it: `"body reshaped to fit the clothing"`.

Three of `octavia-studio`'s own tests encoded the superseded expectation and
were corrected rather than the canon.

## Intent Is Not Observation

`bridge/shoot_export.py` emits annotation commands **commented out**, and
`--pendant unknown` even when the shoot asked for the pendant.

`octavia-studio` knows what a shoot *requested*. Your catalogue records what a
photograph *shows*. A renderer does not reliably obey a prompt, so writing spec
fields straight into `asset annotate` would turn intent into recorded
observation and corrupt the continuity history that everything else depends on.
Per your own canon: unknown is not absence, and a request is not evidence.

`intent.json` carries the full requested state, clearly labelled, for a human to
check against the actual image.

The same gap exists inside `octavia-studio` itself: `qc/headpose.py`
distinguishes a *measured* head pose from a *requested* one, and reports which
it used. Until a real estimator exists, its left-tilt statistic describes what
was asked for.

## The Wardrobe Now Comes From Your Catalogue

`octavia-studio` shipped 66 invented garments written to exercise the sampler.
`python3 studio.py bridge import-wardrobe` replaces them with 150 of your 155
observed garments, each keeping its `wardrobe_item_id`, ownership status and
source asset. Outfits are now clothes she demonstrably has.

Three deliberate decisions:

- The 5 `inspiration` records are excluded. They are looks from other people's
  photographs, not her clothes.
- Material is **inferred from the garment name and recorded as inferred**
  (`material_confidence: inferred_from_name`), because your catalogue states
  fibre is unknown for 143 of 155 records. Do not read it as observed fact.
- Lingerie is tagged `base_layer_only` and refused as an outermost layer;
  swimwear is tagged and restricted to outdoor scenes. Your catalogue records
  everything seen in a photograph, which is correct for a catalogue but opened
  a coverage hole in a generator.

An invented garment's colour is a free variable; a real garment's colour is a
property of the item. With your wardrobe the colour harmony now *selects*
garments whose colours agree rather than painting colours onto them.

## Verified Here, And Not

**Verified:** 211 `octavia-studio` tests pass. Your 82 pass unchanged. Your
`integrity` returns PASS. The bridge round trip was run against a *disposable
copy* of your catalogue — 6 to 30 assets, integrity PASS — and the committed
archive was left byte-identical, because the test images were placeholder cards
and importing them into the real catalogue would have polluted it. The
multi-pass render chain in `renderers/diffusers_local.py` was executed against a
tiny locally-built diffusion pipeline: base, hires fix, face detail and upscale
all run, disabled passes are honoured, a repeated seed reproduces identical
pixels.

**Not verified:** no real checkpoint was ever loaded and no photograph of
Octavia was ever produced there. Prompt quality, identity hold, and the hero
risk weights in `config/studio.yaml` are informed engineering, not measured
results. Ten of the fourteen QC metrics — including `identity_consistency`,
`physique_consistency` and `anatomy` — are deterministic placeholders pending a
vision model, and every scorer, run summary and status line says so. Do not
read them as measurements.

## The Archive Is Untouched

`octavia-handoff/` is the compact package exactly as it arrived, including the
six reference photographs, the asset database and all 53 preserved documents.
Its own `.gitignore` excluded `data/`, which was right on the original machine
where that directory was a live store rebuilt by `octavia.py init` and wrong
here where it is the archive; the rule was removed with a note. Nothing else
was changed. The latest photograph, `plum-tailoring-038`, is still absent by
design — prompt, observations and checksums only, no pixels — so nobody in that
session inspected it and no claim about it was made.

## Where The Work Is

1. **A real vision QC scorer** (`octavia-studio/qc/scoring.py`). Face embeddings
   against `octavia-handoff/.../data/originals/` for identity, body keypoint
   ratios for physique, hand and foot landmarks for anatomy. The interface and
   thresholds exist; only the measurement is missing.
2. **A measured head pose** (`qc/headpose.py`), which also makes the left-tilt
   guarantee real rather than requested.
3. **Tune the hero risk weights** against actual renders — they are priors.
4. **Train the identity LoRA** if the persona should survive long series. The
   curation pipeline is built: `studio.py dataset ingest | analyze | curate |
   caption | export`. Read the bias report before training — a skew in the
   source set becomes permanent at the weights level, where no prompt-side
   balancing can reach it.

## Commands

```sh
cd octavia-studio
python3 studio.py doctor          # environment and readiness
python3 studio.py bridge status   # wardrobe source, handoff path
python3 -m pytest tests/ -q -m "not slow"

cd ../octavia-handoff
python3 octavia.py status
python3 octavia.py integrity --json
```

`octavia-studio/AGENTS.md` carries the architecture and the invariants that must
not be broken. `octavia-studio/README.md` is the full reference.
