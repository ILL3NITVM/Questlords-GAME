# Engineering and Operations

## Scope and Environment

Root: `/home/ubuntu`. This is a shared home directory, not a dedicated clean
repository. An empty `.git` directory exists but is not a valid repository.
Do not initialize Git or reset unrelated files as a setup step.

Launcher: `python3 octavia.py`. The host has Python 3.8.10 and no `python` alias.
The launcher automatically selects `octavia_studio/.venv`, so no activation is
needed. System Pillow/NumPy were left alone. All processing is local, with no
mandatory GUI, server, API key, cloud service or publishing step.

Dependencies are pinned in `octavia_studio/requirements.txt`: Pillow 10.4.0,
NumPy 1.24.4, ImageHash 4.3.2, SciPy 1.10.1, pytest 8.3.5. Reuse the existing
environment on this machine. Modernizing the runtime/dependencies is separate
work; do not expose this old importer to untrusted public uploads first.

## Architecture

```text
MODEL DATA -> CANON -> SHOOT -> CONTINUITY -> PHOTOGRAPHIC POLISH
           -> CURATION -> REFERENCE SHEETS -> SOCIAL EXPORTS
           -> ARCHIVE / WARDROBE MEMORY
```

This is post-generation stewardship, not an image-generation replacement.
The successful photographs used Codex's built-in image tool outside this CLI.
Claude must discover its actual available generation integration; do not assume
the Python package or a transferred plugin can synthesize photographs. Do not
silently start a paid API or request/store credentials unless the user chooses it.

## Files and Ownership Boundaries

| Module | Responsibility |
|---|---|
| `storage.py` | SQLite, verified immutable blobs, lineage, atomic publication, annotations, backups, reports |
| `imaging.py` | Decode/EXIF/ICC, perceptual metrics, bounded polish, protected exports |
| `review.py` | Evidence-based continuity, repetition, curation and explained review acceptance |
| `outputs.py` | Polish/comparison outputs, paginated sheets, social exports |
| `jobs.py` | Detached worker sessions, locks, frozen inputs, checkpoint/recovery |
| `migration.py` | Existing project import/dedup, source document archiving, seed reuse |
| `seed.json` | Identity brief, seven retained refs, initial wardrobe/room data and reviewed annotations |
| `cli.py` | Compact command surface, status, archive and integrity |
| `wardrobe.py` | Validated item-evidence ingestion, audit atlas, portable HTML/JSON contextual crop catalog |
| `wardrobe_inventory.py` | Explicit reviewed visual dataset, not a semantic detector |
| `production/` | Versioned prompts, delivered sample and actual observation/state JSON |
| `tests/` | 72 core tests plus 10 wardrobe tests, 82 total |

## Storage and Integrity

`data/studio.sqlite3` uses WAL, foreign keys and synchronous FULL. Schema version
is currently 1. Wardrobe evidence/review tables were added idempotently through
the same schema, not an explicit v2 migration. Plan an actual versioned migration
before incompatible future changes.

Originals are read-only, SHA-256-addressed copies in `data/originals/`. Original
source paths are aliases in `origins`; repeated import deduplicates exact bytes.
It does not turn merely similar images into one original. `assets` stores file
names, source/date, dimensions/ratio, SHA and pHash, shoot/outfit/room, pose,
framing, expression, hair, pendant, canon/quality, notes, primary parent, kind,
state JSON, metrics and recipe key.

`asset_links` supports many-parent derivation/reference links. `shoot_assets`
supports collection membership without duplicated image content. `documents`
preserves prompt/brief/research content and checksums. `audit` records actions;
`reports` points to versioned JSON and Markdown output.

Independent records: `wardrobe`, `wardrobe_evidence`, `wardrobe_reviews`,
`outfits`, `outfit_items`, `rooms`, `texture_packs`, `canon_revisions`.
Jobs: `jobs`, `job_items`, file locks and logs. Sheets also retain `sheet_members`.

Atomic publication stages/fsyncs, verifies and hard-links a file without
replacement. Existing different bytes are rejected; matching recipes reuse
verified output. Content/lineage updates and asset deletion are blocked by
triggers. Canon changes require an explicit command, reason and DB backup.
Backup uses SQLite's online backup API, not copying a live WAL database file.

Do not modify stored original bytes, chmod the originals writable, rewrite
recorded transforms, remove a failed/review image, or clean caches as a blanket
operation. Existing historical exports and reports are retained versions.

## Implementation Limits to Preserve Honestly

- No numerical body measurements, facial geometry edits, biometric verification,
  beauty scoring or image-generation endpoint exists in the Python pipeline.
- Semantic pose/expression/wardrobe/room/pendant labels come from annotations.
  Missing labels trigger review rather than pretending to detect absence.
- Hair hue is measured only within a reviewed ROI; background plants can
  confound a poor region. It is a colour signal, not hair or identity recognition.
- Duplicates use hashes; composition uses coarse edge/crop similarity. These are
  review candidates, not definitive pose/room equivalence.
- Repetition is >=70% among >=3 annotated assets; colour drift uses comparable
  annotated cohorts, not all unrelated lighting/wardrobe states.
- PASS means available checks did not flag an issue; it is not a visual likeness
  certification. A one-image shoot cannot test diversity across four shots.
- Curation HERO/STRONG/REFERENCE/REVIEW/REJECT-CANDIDATE uses technical metrics
  and diversity signals. Do not call it an attractiveness ranking.
- Polish is bounded and non-geometric. Only sharpening 0.20 is on by default.
  Denoise, exposure, white balance, local contrast, shadow/highlight adjustment
  and resizing are individually optional. Clipped detail cannot be recovered.
- High-bit/RAW/HDR processing is not silently reduced to 8-bit polish support.
- Preserve original metadata; derived outputs normalize orientation/ICC and
  use a safe EXIF subset. Social exports remove EXIF/GPS. C2PA/generation
  provenance in the raw image must not be treated as proof of a physical camera.
- Wardrobe crops use actual source pixels, not invented product cutouts.
- `wardrobe show` appearances come from assigned outfit metadata; use
  `wardrobe evidence <id>` for the richer source-cell evidence table.
- `wardrobe combinations` is a simple cartesian product of established item
  categories. It is not personality-aware; dresses, seasonality and complex
  layering are not a sophisticated styling engine. `--include-inspiration`
  broadens the pool, but neither command changes ownership.
- `wardrobe ingest` is idempotent and preserves prior records/decisions. It
  does not silently overwrite an existing observation's notes/confidence or
  ownership; an explicit reviewed update workflow remains future work.
- `wardrobe-detail`, sheet, before/after, polish and export derivatives are
  excluded from original-photo shoot selection.
- New room layouts in generated photos are state interpretations, not exact
  architecture reconstruction. Existing room families are not a 3D scene model.

## Commands

Run from the project root. Put `--json` before nested commands, for example
`python3 octavia.py --json wardrobe list`. A trailing `--json` after `list` is
not accepted by nested argparse parsers. Top-level commands also accept it.

```sh
python3 octavia.py status
python3 octavia.py jobs
python3 octavia.py --json asset show a-5d75bc683f0c6c4a
python3 octavia.py --json canon references
python3 octavia.py --json wardrobe evidence plum-blazer
python3 octavia.py wardrobe catalog
python3 octavia.py wardrobe combinations
python3 octavia.py continuity plum-tailoring-038
python3 octavia.py integrity --origins --json
```

For later authorized processing, not a requirement to rerun now:

```sh
python3 octavia.py import /path/to/new-photo.png --shoot next-shoot --source generator-name
python3 octavia.py asset annotate a-... --file actual-observations.json --evidence "Assistant visual review"
python3 octavia.py wardrobe ingest reviewed-items.json
python3 octavia.py process next-shoot --export all --background
python3 octavia.py resume j-... --background
python3 octavia.py sheet --shoot next-shoot --grid 4x4 --no-labels
python3 octavia.py backup
python3 octavia.py archive next-shoot
```

No canon approval command is part of routine processing. If the user explicitly
approves an image, see the README for the reasoned canon workflow. Never mark an
assistant review as a human review; `review --reviewer assistant` exists.

## Jobs, Reports, Exports

Background workers detach with `start_new_session`, use lifetime/recipe locks,
and persist each input/checkpoint. Membership and hashes are frozen at job
creation, including resolving `latest`. Resumes verify and reuse completed
assets. A stale running label after a killed process is recoverable; there is
no automatically managed daemon or scheduled service.

Grid order is columns x rows. Overflow is paginated. Hidden visual labels do
not remove source asset IDs. Individual images are fitted, not arbitrarily
cropped. Export crop requests need a reviewed region; otherwise padding safely
preserves the subject. Actual reference-sheet exports use real sheets.

`Final=8` counts retained export versions, not published posts. The initial
proof exported one portrait to a reference-sheet canvas; that behavior was
fixed, a proper sheet export was produced, and the old version was retained.
The final conservatory job has seven current format exports. The newest plum
sample was not run through a full polish/export batch; its raw PNG is delivered.

Archive contains original/derivative lineage, source documents and metadata.
Historical absolute output/log paths are retained as provenance. On another
machine, locate actual content via `blobs.path` under the new data root rather
than blindly following `/home/ubuntu` paths stored in an old report.

## Tests

```sh
octavia_studio/.venv/bin/python -m pytest octavia_studio/tests -q
octavia_studio/.venv/bin/python -m pip check
python3 octavia.py integrity --origins --json
```

Recorded complete run after the wardrobe implementation: 82 passed in 82.63 s,
no failures/errors/skips, in `test-results.xml`. Coverage includes dedup/aliases,
immutable/atomic storage, original mutations, bad images, orientation/ICC/EXIF,
alpha, independent polish bounds, canon gates, annotated continuity/diversity,
sheet grids/pagination, export crop protection, jobs/locks/resume/crash recovery,
archives, migration idempotence, item observation validation/rollback, no
ownership promotion, crop lineage, HTML escaping and repeated catalog builds.

Test fixtures are synthetic. Passing tests do not prove every manual wardrobe
match is correct or that users find the latest portrait attractive.

## Portable Package

`build_bundle.py` in this handoff folder makes a verified local ZIP containing
project code/config/tests, current clean SQLite snapshot, all managed image
blobs and source documents, reports, production artifacts, current wardrobe
HTML with its image files, and named legacy Octavia image/brief aliases.
It also writes searchable snapshots and per-file hashes.

Excluded: `.venv`, caches, credentials, unrelated home-directory files, duplicate
historical ZIPs/recovery copies, old DB backups, inactive runtime locks and old
HTML catalog versions. Their underlying image/document content is retained in
the managed store or named project files. No source files are deleted.
The manifest states this scope; the ZIP is not a literal home-directory backup.

On this same machine, use the live project directly. On another machine:

1. Extract into a fresh directory; do not merge over another project.
2. Read `CLAUDE.md` from that extracted root.
3. Recreate a compatible Python environment using `requirements.txt`; a Python
   3.11 environment is compatible with these pinned dependency versions.
4. Run `python3 octavia.py status` and integrity. The launcher derives its data
   root relative to the script. Missing old origin aliases are expected after a
   move; managed original hashes must still pass.
5. Do not run `init` as a repair step: the bundled DB is already populated.
   Do not resume completed historical jobs or treat old absolute paths as live
   destinations. Make new jobs only for new user-authorized processing.
