# Compact Octavia Handoff: Read This First

This is a bandwidth-reduced handoff requested by the user after the full ZIP
proved too large to download. **Only six core body/identity reference photos
are included.** All six retain their original bytes and resolution.

No photographs were deleted from the original workspace. The full ZIP and live
project remain there. This compact package is not a complete media backup.

## What Is Included

- Six original reference portraits, listed with paths and checksums in
  `octavia_studio/handoff/included-references.json`.
- Existing Python source, configuration, tests, generation prompts, written
  context, reports and complete wardrobe/catalog metadata.
- A **reference-only active database** at `octavia_studio/data/studio.sqlite3`.
  Its image records all resolve to included photographs. It preserves the
  original IDs and canon statuses of those records, with no canon promotion.
- A **complete metadata-only historical database** at
  `octavia_studio/handoff/history-metadata-only.sqlite3`, plus the full historical
  `snapshot.json` and `assets.jsonl`. These retain omitted assets, all wardrobe
  observations, approvals, jobs and provenance. They are history, not a runnable
  image store. Do not substitute this database for the active one.

## Photos Retained

| Original Filename | Role |
|---|---|
| `octavia-master-source-v24-1.jpg` | Full body, cyan top, cream cardigan and charcoal trousers |
| `octavia-master-source-v24-2.jpg` | Full body, green top, black skirt and tights |
| `octavia-master-source-v24-3.jpg` | Clear face and three-quarter body, black tank/skirt |
| `octavia-master-source-v24-4.jpg` | Full body, cream top, black pleated skirt and boots |
| `octavia-master-source-v24-5.jpg` | Face and upper-body anchor, freckles, hair and pendant |
| `octavia-cyan-outfit-source-v23.jpg` | User's early target look, full body in cyan skirt/wrap top |

Use the paths in `included-references.json` to inspect them. The JPEGs live in
the managed originals store, not as additional duplicated root-file aliases.
Source names and old absolute paths remain provenance, not missing extra files
that should be regenerated.

## Deliberately Omitted Media

All other photographs, generated shoots, contact sheets, outfit sheets, wardrobe
crops, thumbnails, social exports and preview pictures. This includes the latest
plum-tailoring-038 photograph. Its prompt, actual observations, quality report,
asset ID and checksums remain in the historical metadata, but its pixels are
not included. Do not claim to have inspected omitted images.

The 155-design wardrobe is preserved as text/metadata. Its former HTML photo
gallery is not included because it depends on omitted crops. Each archived
observation remains traceable to its historical asset ID and region.

## How Claude Should Continue

1. Read this file before `START_HERE.md`, `PROJECT_CONTEXT.md` and `ENGINEERING.md`.
   Their full-project counts, photo links and relocation notes describe the
   **original larger workspace**. This compact scope takes precedence.
2. Inspect the six included references. Preserve Octavia's established adult
   identity and body shape. Never estimate body measurements from images.
3. Use the active catalog for the included photos and the historical database
   or snapshot for the complete record of previous work.
4. Do not reconstruct omitted photos, approve candidates, or run four additional
   generations just because this is a handoff. Follow the user's next request.
5. The command-line pipeline is still post-generation processing, not an image
   generator. Discover the actual generation tools available to Claude.

## Commands From the Extracted Root

On the original machine use its existing virtual environment. On a new machine,
create `octavia_studio/.venv` and install `octavia_studio/requirements.txt` using
a compatible Python runtime; the pinned versions support Python 3.11.

```sh
python3 octavia.py status
python3 octavia.py --json asset list --shoot handoff-body-references
python3 octavia.py integrity --json
python3 octavia.py --json wardrobe list
```

Active counts intentionally differ from the full-project snapshot: six image
assets, five retained reference statuses and one unreviewed target-look asset.
The original seven-reference canon history is preserved in the historical
database; two image sheets are omitted, not rejected or unapproved.

The active database retains wardrobe/outfit/room definitions and only those
asset observations whose source photos are present. Full evidence for omitted
photos is in the historical database. Empty referenced library outfits do not
mean their former images were deleted from the original project.
