# Octavia Studio Handoff

Prepared for Claude Code from the existing project and the conversation context
available to the departing assistant. This is a curated context transfer, **not
a verbatim export of every chat message**, not a transfer of hidden model state,
and not a claim that Claude inherits this environment's tools or plugins.

## User Intent

Continue the persistent Octavia project rather than starting over. The user
primarily works through ChatGPT Remote on iPhone, prefers short commands and
compact reports, and wants to see actual photographic results, not only plans.

Most recent sequence:

1. Implement a real Python post-generation continuity/curation/asset pipeline.
2. Inventory clothing one item at a time from all existing Octavia photographs.
3. Use her established character/style to guide distinct photoshoots. Four
   separate generations were initially requested, not a four-panel collage.
4. The user then narrowed the immediate deliverable to **one quality-check
   photograph**. One was delivered. Do not automatically queue three more.
5. The current request is to hand all context, assets and implemented work to
   Claude Code. No new generation, canon promotion or publication is requested.

## Start Reading

- `PROJECT_CONTEXT.md`: character, reference hierarchy, conversation history,
  user preferences, wardrobe semantics, successes/failures and unfinished work.
- `ENGINEERING.md`: implementation, commands, storage, tests, traps, portability.
- `../README.md`: full CLI and algorithm reference.
- `snapshot.json`: captured tables, counts, verification and filesystem inventory.
- `assets.jsonl`: one searchable record per asset, including its managed path.
- `../../octavia-master-prompt-v24.md`: retained user master brief (from the root
  of this package use `octavia-master-prompt-v24.md`).

Paths in these documents are project-root-relative unless explicitly absolute.
The original root is `/home/ubuntu`; in a relocated package use the extracted
root instead. For a live handoff, the database is authoritative over snapshot
counts because later work can legitimately change the catalog.

## Current Deliverables

| Deliverable | Project-root-relative location |
|---|---|
| Latest individual photograph | `octavia_studio/production/octavia-plum-tailoring-038.png` |
| Successful generation brief | `octavia_studio/production/plum-tailoring-038-prompt.md` |
| Latest observed state | `octavia_studio/production/plum-tailoring-038-state.json` |
| Latest item evidence | `octavia_studio/production/plum-tailoring-038-observations.json` |
| Wardrobe HTML | `octavia_studio/data/wardrobe/db4ef25d6dd8acb0/index.html` |
| Wardrobe JSON | `octavia_studio/data/wardrobe/db4ef25d6dd8acb0/catalog.json` |
| CLI | `octavia.py` |
| Live database | `octavia_studio/data/studio.sqlite3` |
| Recorded 82-test result | `octavia_studio/test-results.xml` |

Latest photo: asset `a-5d75bc683f0c6c4a`, shoot `plum-tailoring-038`, native
1024 x 1536 PNG. It was generated with the built-in image tool, copied into the
workspace, imported, annotated and continuity-checked. No Python retouching,
upscaling or geometric reshaping was applied to this delivered photo.

## Snapshot Counts

```text
OCTAVIA STUDIO
Canon:        7
Inbox:       17
Shoots:      33
Selected:     1
Final:        8
Wardrobe:    155
Rooms:        3
Outliers:     0
Assets:     265
Last shoot: plum-tailoring-038
```

The 265 database assets share 238 distinct stored blobs. There are 90 imported
original image assets (89 legacy plus the new quality sample), 53 preserved
source documents, 1,265 wardrobe observations and 90 source-level wardrobe
reviews. Counts do not mean all assets are canon or all garments are owned.
All four recorded processing jobs are complete; no unfinished job is waiting
for Claude to resume.

## Verification

- Recorded complete suite: **82 passed, zero failures/errors/skips**.
- Integrity rechecked during handoff: see `snapshot.json` for the actual result.
- Last generation's available continuity checks: PASS, **not** verified identity.
- Explicit visual caveat: a small head tilt remains despite an upright-head
  instruction. It is recorded in the state file; do not assert perfect fidelity.

## What To Do Next

Read the documents, inspect the latest photo and the primary identity references,
run status/jobs, then follow the user's next concrete request. Do not restyle
Octavia, rewrite the pipeline, or approve the current photo just because a
handoff took place.

For a future new shoot: use clear identity references, select individually
catalogued garments, deliberately vary pose/expression/room, create a separate
image for each requested shoot, inspect it, preserve the raw generation, import
it, and record actual visible state rather than copying the prompt as truth.
