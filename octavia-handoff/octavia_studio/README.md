# Octavia Studio

Local, non-generative image stewardship for the existing Octavia project. The CLI uses an isolated Python environment automatically; no GUI, API key, cloud upload, or image-generation replacement is involved.

## Start

Run from `/home/ubuntu`:

```sh
python3 octavia.py status
python3 octavia.py process conservatory-037 --background
python3 octavia.py jobs
python3 octavia.py sheet --shoot conservatory-037 --grid 4x4 --no-labels
python3 octavia.py wardrobe combinations
```

This host has `python3`, not a `python` alias. The top-level launcher automatically uses `octavia_studio/.venv`. For a fresh installation:

```sh
python3 -m venv octavia_studio/.venv
octavia_studio/.venv/bin/python -m pip install -r octavia_studio/requirements.txt
python3 octavia.py init
```

Use `--data /absolute/path` before the command, or `OCTAVIA_DATA`, for a separate studio. `--json` gives machine-readable output. Existing home-directory projects and their dependencies are not changed.

## Existing Work Reused

The prior project is a collection of named generated portraits, JPEG source references, master/wardrobe/gallery sheets, previews, exact prompts, research, a ZIP, generator originals, and a recovery folder. No reusable Octavia Python package or asset database was present. The former sheet layouts and identity brief are preserved; no sheet images were regenerated during migration. The interrupted v37b delivery was copied from its existing generator original without regenerating it.

`init` scans only `octavia*` images/documents at the workspace root, the generator and recovery folders for this conversation, and this conversation's attachment directory. It never scans unrelated projects or credentials. Exact duplicate image bytes share a catalog asset and blob; all original source paths remain in `origins`. Re-running import does not reset manual annotations or canon decisions. Legacy filesystem modification time is recorded as approximate creation evidence; import time is precise. Blocked/superseded prompts remain documents, never fabricated image assets.

## Layout

### Item-by-Item Wardrobe Audit

The September 2026 visual audit catalogues 154 garment/accessory design records
against 1,260 observations across all 89 pre-existing originals, including sheet
cells and explicit duplicate-layout reviews. These are visible design families,
not verified identical physical products. New records remain candidates; donor
designs remain inspiration. Exact sizes, fibres, brands, hidden surfaces and
ownership are not inferred. Jewellery and footwear are independent records.

```sh
python3 octavia.py wardrobe catalog
python3 octavia.py wardrobe evidence plum-blazer
python3 octavia.py wardrobe atlas
python3 octavia.py wardrobe ingest reviewed-items.json
```

`catalog` writes a portable HTML/JSON catalog and source-linked contextual crops.
It does not invent isolated product views or fill occluded garment regions.
Each item includes its evidence, confidence, reviewer and source asset IDs.
The HTML opens directly without a server. Regenerating it is non-destructive.
`wardrobe_inventory.py` is the versioned assistant audit, not an automatic visual
detector; a new image still requires explicit garment observations. Evidence
and source-review records are included in portable shoot archives.

The `production/` folder retains exact image-generation briefs. Generated
shoots remain unreviewed until a separate canon decision. Styling based on
Octavia's recurring colours and character brief is a creative interpretation,
not a claim of autonomous decisions by a fictional character.

```text
octavia.py                       short launcher
octavia_studio/
  storage.py                     SQLite, lineage, audit, atomic content storage
  imaging.py                     metrics, safe color processing, polish, exports
  review.py                      continuity evidence and curation suggestions
  outputs.py                     before/after reports and paginated sheets
  jobs.py                        detached workers and per-image checkpoints
  migration.py + seed.json        explicit legacy import and canon/library evidence
  cli.py                         remote-friendly commands
  tests/                         local synthetic fixtures and integration coverage
  data/
    studio.sqlite3               versioned schema; WAL and foreign keys enabled
    originals/<hash-prefix>/     content-addressed, read-only original copies
    documents/<hash-prefix>/     immutable source prompt/brief/research copies
    derivatives/<kind>/          polished images, previews, sheets, social exports
    reports/<shoot>/             paired JSON and concise Markdown reports
    backups/                     verified SQLite snapshots
    archives/                    portable shoot ZIPs with manifest and images
    logs/ + locks/               detached worker output and process locks
```

The SQLite catalog stores every generated image, including before/after previews and reference sheets. Existing ZIPs and recovery logs are left in place; duplicate recovery images are indexed rather than recopied repeatedly. `asset_links` holds many-parent relationships, while `parent_asset_id` is the primary derivative parent. Legacy edit relationships are recorded as links without guessing unavailable parentage. `shoot_assets` allows the same original in multiple collections without duplicated image records.

## Canon Is Not State

The user master brief and explicitly supplied reference selections seed a versioned identity record and seven `reference` assets. These are retained existing references, not new automatic approvals. Identity contains facial/hair-color/eye/skin/pendant/silhouette descriptions, never estimated body measurements. Hairstyles, wardrobe, pose, room, lighting and expression are per-asset state.

```sh
python3 octavia.py canon show
python3 octavia.py canon references
python3 octavia.py canon approve a-... --reason "Reviewed against existing reference"
python3 octavia.py canon approve d-... --allow-derivative --reason "Explicit human promotion"
python3 octavia.py canon revise --file identity.json --reason "User-approved clarification"
```

Only explicit canon commands change approvals. Generic annotation rejects `canon_status`. Pipeline outputs always start as `derivative`, even when their parent is approved. Every canon mutation is audited and preceded by a verified database backup. Revisions append; they do not replace identity history. A different hairstyle never updates identity canon.

## Import and Annotate

```sh
python3 octavia.py import /path/to/photos --shoot fit-038
python3 octavia.py asset list --shoot fit-038
python3 octavia.py asset show a-...
python3 octavia.py asset annotate a-... --pose seated,relaxed --framing full-body --expression soft-smile --hair-state ponytail --pendant present
python3 octavia.py asset annotate a-... --hair-roi 0.25,0.02,0.65,0.30 --subject-roi 0.10,0.01,0.90,0.99
python3 octavia.py asset annotate a-... --file reviewed-state.json
python3 octavia.py shoot create fit-038 --allow-repeat outfit_id,room_id
python3 octavia.py shoot add fit-038 a-... a-...
```

An asset ID, unambiguous ID prefix, or unique original filename can identify an asset. JSON annotation keys: `pose` (list), `framing`, `expression`, `hair_state`, `pendant_present` (true/false/null), `outfit_id`, `room_id`, `texture_pack_id`, `notes`, `state`. Normalized ROIs are `[left, top, right, bottom]` in display-oriented coordinates. Never use guessed body measurements. `state.pendant_applicable=false` records deliberate occlusion/non-applicability rather than inventing pendant detection. Manual annotations carry evidence and an audit history. Pose tags include standing, seated, walking, leaning, over-shoulder, profile, looking-away, mirror-selfie, candid, relaxed, editorial; additional descriptive tags are allowed.

## Polish

```sh
python3 octavia.py polish fit-038 --background
python3 octavia.py polish a-... --no-sharpen
python3 octavia.py polish a-... --denoise 0.1 --sharpen 0.25 --exposure 0.15 --wb 1.02,1,0.98 --contrast 0.05 --shadows 0.08 --highlights 0.08
python3 octavia.py polish a-... --max-side 2048 --format jpeg --quality 97
```

Every operation is independently switchable by setting its value to zero; neutral white balance is `1,1,1`. Defaults: only restrained sharpening at 0.20; denoise, tone shifts, white balance and local contrast are off. Controls are bounded. Denoise blends at most 30% of a median-filter result; sharpening has a threshold to avoid amplifying very small texture variations. White-balance gains are explicit, not automatic skin-color judgments. Exposure is applied in linearized sRGB. Highlight/shadow controls remap existing tones; **they cannot recover clipped JPEG/PNG detail**. Resize never upsizes a polish master and never changes aspect ratio. No warping, facial landmarks, anatomy edits, beauty filters or generative filling exist in this code.

Polish supports 8-bit display images; RAW/HDR/high-bit originals may be cataloged but are not silently reduced by the polish command. Every output has parent lineage, a recipe hash, before/after technical metrics and a visual comparison image. Originals retain all metadata byte-for-byte. Polish normalizes EXIF orientation and ICC color, preserves a safe authorship/capture EXIF whitelist, updates dimensions, and drops GPS/stale thumbnails. Exports strip EXIF/GPS and retain normalized sRGB ICC. JPEG exports use high quality and 4:4:4 chroma; PNG polish is lossless encoding of the resulting pixels, not lossless processing. Invalid ICC profiles fail visibly.

## Continuity and Curation

```sh
python3 octavia.py continuity fit-038
python3 octavia.py curate fit-038
python3 octavia.py review a-... --shoot fit-038 --reason "Intentional alternate take; composition checked"
```

- `PASS`: no flagged evidence in the available checks; not verified identity.
- `REVIEW`: missing annotations, near duplicates, repetition, potential drift or ambiguity.
- `OUTLIER`: strong technical anomaly such as corrupt storage or extreme encoded clipping; human review, never auto-delete.

Evidence includes SHA-256 equality, perceptual/center-crop hash distances, coarse edge-grid composition similarity, resolution, edge detail, encoded exposure clipping, recorded pose/framing/expression/hair/room/outfit distributions, and chartreuse color inside a **human-annotated hair ROI**. It does not detect hair, poses, rooms, garments or pendants semantically. A green plant in a badly drawn hair ROI can confound the check. Pose and expression distributions flag >=70% repetition among at least three annotated assets. Intentional repeat fields can be declared at shoot creation. Color drift is compared only within matching annotated outfit, architecture, texture pack and framing cohorts of at least three; it is not compared indiscriminately across different rooms. Unknowns are visible, not interpreted as absence or identity drift.

Curation returns `HERO`, `STRONG`, `REFERENCE`, `REVIEW`, `REJECT-CANDIDATE`. Rankings use image resolution, edge detail, exposure, continuity and a modest diversity penalty. These are **technical suggestions, never mathematical beauty scores**. Near-duplicate selection prefers higher resolution/detail. The batch pipeline only exports HERO/STRONG suggestions; unknown/outlier assets require annotation/review. Nothing is deleted, and curation never promotes canon.

`review` records acceptance of specific candidate warnings, bound to the image hash, issue and shoot. Original evidence remains in the report under `acknowledged`. Missing annotations and strong outlier/integrity failures cannot be waived with this command. Reviews identify their source: `--reviewer human` (default) or `--reviewer assistant`. Neither changes canon. The corrected v37b composition was explicitly reviewed by the assistant as an intentional correction of v37, not silently exempted from repetition checks.

## Wardrobe and Rooms

```sh
python3 octavia.py wardrobe list
python3 octavia.py wardrobe show lilac-cardigan
python3 octavia.py wardrobe add jacket-038 --name "Lilac jacket" --category outerwear --primary-color lilac --source-reference a-... --ownership inspiration
python3 octavia.py wardrobe combinations
python3 octavia.py wardrobe update jacket-038 --ownership established --reason "Confirmed in Octavia's wardrobe"
python3 octavia.py outfit add look-038 --name "Lilac and cyan" --items cyan-square-top,black-pleated-skirt,lilac-cardigan,black-ankle-boots
python3 octavia.py room show conservatory
python3 octavia.py texture list --room conservatory
python3 octavia.py texture add evening-038 --room conservatory --name "Evening" --file treatment.json
```

Garment ownership (`established`, `inspiration`, `candidate`) is distinct from canon approval. `established` means established in the fictional wardrobe, not a claim of a physical purchase. Material descriptions are visual, not fabric testing. Donor Zuza imagery is inspiration, never identity canon. Combinations are category-compatible proposals; they do not change garment ownership. Architecture lives in `rooms`; palette, bedding, light, daytime, decor, plants, view and ambience live in `texture_packs`. A new color treatment does not create another room identity.

## Sheets and Exports

```sh
python3 octavia.py sheet --shoot fit-038 --grid 4x4 --no-labels
python3 octavia.py sheet --shoot legacy-references --grid 4x2 --mode identity-only --no-labels
python3 octavia.py sheet --shoot fit-038 --grid 2x4 --mode body/pose
python3 octavia.py export a-... --preset all
python3 octavia.py export a-... --preset profile --fit crop --box 0.30,0.04,0.68,0.28
```

Grid notation is **columns x rows**. Overflow creates additional pages rather than silently dropping assets. Modes: all, identity-only, body/pose, wardrobe, hair, room, expression. Metadata-required modes report no matches when annotations are missing. Every tile has an internal asset ID, position and bounds in SQLite and the JSON report even with labels hidden. Whole images are fitted, not cropped into tiles.

Export presets are versioned practical delivery choices, not universal maximum platform limits:

| Preset | Pixels |
|---|---|
| x | 1600 x 900 |
| instagram-square | 1080 x 1080 |
| instagram-portrait | 1080 x 1350 |
| story | 1080 x 1920 |
| profile | 400 x 400 |
| banner | 1500 x 500 |
| reference-sheet | 2048 x 2048 |

Default padding preserves the entire image, with extra protection for profile-circle and banner trims. Cropping requires an explicit reviewed subject region. If the target ratio cannot contain that region plus margin, the export falls back to padding and explains why. Upscaling, crop boxes and pixel placement are recorded. Platform overlays can still vary by app; inspect the preview before publishing. The application never uploads or publishes anything.

The `reference-sheet` export operates on actual sheet pages, not a portrait relabeled as a sheet. `export --preset all` builds 4x4 sheets if the input is not already a sheet; `process` reuses the sheets it just built. Review sheets can contain REVIEW candidates for comparison, while automatic individual social exports remain limited to HERO/STRONG suggestions. `Final` counts retained export versions, not posted items.

X officially recommends [400 x 400 profiles and 1500 x 500 headers](https://help.x.com/en/managing-your-account/common-issues-when-uploading-profile-photo), and notes possible header trim. The other sizes are conservative studio presets, not claims of current exclusive platform requirements. The Instagram Help page required login during verification. Color/orientation operations follow [Pillow ImageOps](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html) and [ImageCms](https://pillow.readthedocs.io/en/stable/reference/ImageCms.html). Preset/source review: 2026-09-10.

## Jobs, Reports and Recovery

```sh
python3 octavia.py process fit-038 --export instagram-square,instagram-portrait,story --background
python3 octavia.py jobs
python3 octavia.py resume j-...
python3 octavia.py integrity
python3 octavia.py backup
python3 octavia.py archive fit-038
```

Workers detach from the Remote shell with their own process session and log. SQLite persists job requests and per-image checkpoints. A process-lifetime file lock prevents simultaneous execution of the same job; after an interruption or reboot, `resume` reuses verified completed assets. A stale `running` label after SIGKILL is recoverable with `resume`; there is no automatic system service. A finished job is idempotent. Different recipes create sibling derivatives. A repeated recipe reuses the existing verified result. File creation is staged, fsynced, verified, then atomically published without replacing existing content. DB backups use SQLite's online backup API, not copying an open WAL file.

Jobs freeze asset membership at submission, including resolving `latest` immediately. Continuity runs before polish, then curation, sheets and exports. Per-recipe locks prevent duplicate publication across different jobs; an image published just before a database interruption can be recovered after checking its decoded pixels against the same recipe. Failed jobs write checkpoint reports where storage remains available.

Every processing job writes JSON and Markdown reports with changes, preserved originals, continuity/repetition evidence, ranking suggestions, sheet paths and export paths. Archive writes a verified ZIP containing the selected shoot, its derivative descendants and a portable metadata manifest, plus a verified catalog snapshot. No archive or cleanup action deletes anything. Back up the entire `data/` folder together with code/configuration for complete studio recovery.

## Verification and Limits

```sh
octavia_studio/.venv/bin/python -m pytest octavia_studio/tests -q
python3 octavia.py integrity --json
```

Tests cover immutable storage, duplicate aliasing, source mutation, corrupt inputs, EXIF orientation, independent polish operations and bounds, metadata/alpha, explicit canon promotion, unknown-vs-absent annotations, repetition, ROI validation, sheet grids/pagination, every export preset, protected crop fallback, checkpoint resumption, end-to-end processing, archives and repeatable migration.

The highest-value next upgrade is a reviewed annotation workflow that can suggest pose, framing, garment IDs, pendant visibility and hair/subject regions, then require human acceptance before saving them. The MVP deliberately does not disguise missing semantic detectors as working identity verification. Also plan migration from this host's Python 3.8 environment to a supported Python runtime before exposing the importer to untrusted remote uploads.
