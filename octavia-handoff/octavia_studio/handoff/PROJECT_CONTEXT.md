# Character, Conversation and Assets

## Identity Versus State

Octavia is one persistent **adult fictional character**, generally described as
in her late twenties. Her world should feel like a photographed, lived-in world
from her point of view; this is an artistic direction, not a claim that the
character is a real person.

Identity: brunette hair with lime/chartreuse/olive-green face-framing sections;
green-hazel eyes; expressive brunette brows; softly defined recognizable face;
natural lips, freckles, pores, fine hair and asymmetry; one purple/amethyst
crystal pendant on a delicate chain; established believable adult silhouette.
Preserve the supplied body shape without estimating numerical measurements or
changing anatomy to make clothes fit. Adapt the clothes to her instead.

State: hair arrangement, outfit, accessories, pose, expression, lighting, room,
temporary styling. Hair can be loose, tied or imperfectly pinned. A different
state must not silently redefine identity. Pendant absence/occlusion can be
annotated; unknown is not absence.

The user values her being attractive, feminine, cute, confident, glamorous and
fashion-forward, but specifically asks for SFW editorial imagery. Attraction
should come from expression, natural posture, tailoring and photographic light,
not body exaggeration, exposure, plastic smoothing or face replacement. Do not
reinterpret the request as requiring erotic content. Conversely, a historical
"SFW" label does not authorize bypassing an image tool's safeguards.

## Reference Hierarchy

Inspect these images, not just their filenames or text descriptions. Resolve
asset IDs with the CLI when a root alias is unavailable.

| Role | Asset ID | Root filename |
|---|---|---|
| Clearest facial identity/texture | `a-2a28a323025d1af3` | `octavia-master-source-v24-5.jpg` |
| Face and adult silhouette, black tank | `a-632be75ba22ce38a` | `octavia-master-source-v24-3.jpg` |
| Cyan/cream/trousers reference | `a-06304fd46f0a0b92` | `octavia-master-source-v24-1.jpg` |
| Forest top/contrast waist/skirt reference | `a-4aa958e7e4279df5` | `octavia-master-source-v24-2.jpg` |
| Cream top/black pleats mirror reference | `a-7cf41694da9b4f14` | `octavia-master-source-v24-4.jpg` |
| Retained 4x4 identity/lifestyle sheet | `a-3f220b36bc4abdcd` | `octavia-master-reference-sheet.png` |
| Retained earlier identity sheet | `a-dd64fa5706223d80` | `octavia-identity-source-v9.jpg` |
| User's early cyan target look | `a-c23c860ec74a2b02` | `octavia-cyan-outfit-source-v23.jpg` |
| Wardrobe/pose evidence, not overriding face | `a-0924db2fad337032` | `octavia-remix-source-grid-v17.jpg` |
| Donor Zuza clothing only | `a-e738b6fd4ac6d398` | `octavia-zuza-comparison-source-v26-zuza.jpg` |

The first seven records have `canon_status=reference`; they were retained from
the existing project, not newly approved outputs. Seven records do not mean
seven different people. None of the new pipeline derivatives was promoted.

"Photo 4" is ambiguous across attachment batches. The user's early "Photo 4 is
target Octavia" meant the cyan skirt/wrap-top mirror image with cream cardigan
and black loafers, archived as `octavia-cyan-outfit-source-v23.jpg`. Do not confuse
it with `octavia-master-source-v24-4.jpg`, which is cream top/black pleats.

Later wardrobe sheets sometimes vary facial styling. Use them for clothing
evidence, not to average or replace the clearer identity references. Donor
images must never become Octavia facial canon merely because they share a file
collection or cyan garment.

## Desired World and Style

The apartment world uses polished concrete, pale stone/marble, warm dark wood,
large windows, city views, soft furniture, plants and restrained lilac accents.
A conservatory and a sage-storage dressing room also exist. Room architecture
is separate from lighting/color treatment. Remix furniture, decor, layout and
light direction so shoots feel like different real moments in the same world.

Recurring clothing colours: lilac, plum, purple, cyan, black and charcoal;
cream, green, blue denim and brighter summer pieces also appear. Textures include
knit, velvet-look eveningwear, satin-look garments and tailored woven fabrics.
Materials are visual descriptions, not verified fibre compositions.

"Let Octavia's personality decide" was interpreted as an editorial styling
brief: warm, confident, playful, sophisticated, relaxed at home, expressive in
fashion. This interpretation should remain revisable by the user. No autonomous
personality engine exists; do not claim the fictional character literally made
a decision or present assistant-inferred personality as newly approved canon.

## Pose and Photography Preferences

- Vary standing, sitting, walking, profile, leaning, candid motion, mirror shots
  and full/three-quarter/half/close framing instead of one 16-tile template.
- Vary smile, neutral, thoughtful, amused, playful and serious expressions.
- The user repeatedly disliked excessive sideways head tilt, hand-supported
  heads, crossed ankles/legs and recycled backgrounds. Earlier broad prompts
  allowed these poses; later correction requests made avoiding repetition more
  important. They are not permanent blanket bans, but do not default to them.
- Preserve realistic weight distribution, joint geometry, hands, skin texture,
  fabric gravity/compression/seams, contact shadows and coherent illumination.
- Full-frame photographic language guides a render; it is not proof the image
  was captured with a physical camera or lens.
- No text, watermark, logos, captions, collage borders or multiple panels in an
  individual photograph. Reference sheets are separate requested artifacts.
- Feet can be incidental and anatomically natural if barefoot, never a special
  framing emphasis. Shoes vary by outfit.

## Conversation and Project Progression

1. The user handed over Octavia's earlier portraits and outfit/identity sheets.
   Root assets preserve the genesis look and the six-step glamour progression.
2. Identity and realism master prompts were established. Cyan crop/pleated
   coordination, lilac cardigan replacement and remixed apartment rooms were
   recurring requests.
3. Zuza appeared as a clothing donor. The user clarified that neither model's
   body should be changed and garments should fit Octavia's own existing body.
   Later requests explicitly wanted opaque, tasteful fashion, not a swimwear
   or lingerie presentation. Historical donor/swim/underwear references remain
   source data, not the default direction for new shoots.
4. Subsequent asks sought more beauty, novel outfit combinations, new poses,
   shopping-inspired upgrades and consistent recognizable Octavia. Historical
   retry/blocked prompt files are preserved, but a prompt filename is not proof
   that generation succeeded. Do not invent missing images.
5. The existing project contained generated portraits v2 through v37 variants,
   clothing sheets, previews, exact prompts, research, original outputs, a ZIP
   and recovery copies. No reusable Python catalog/pipeline existed.
6. Octavia Studio was implemented and tested. Legacy migration indexed 204
   image paths as 89 unique original image assets and preserved 48 documents.
   Re-running import added zero duplicates and did not reset annotations.
7. Conservatory v37b had already been generated; it was recovered from the
   existing generator output instead of generated again. The real two-image
   conservatory collection was polished, reviewed, curated, sheeted, exported
   and archived through the new pipeline.
8. The user requested item-level clothing inventory and four separate shoots.
   All 89 existing original assets were visually audited, including grid cells,
   and the wardrobe expanded from 11 to 154 design records with 1,260 evidence
   observations. Eleven original records remain separately statused; no bulk
   ownership/canon promotion occurred.
9. The user narrowed the immediate output to one photograph for a beauty and
   quality check. The first new velvet-dress attempt failed at output moderation.
   A materially different fully dressed plum suit/lilac blouse photograph was
   successfully generated and delivered. It added one observed blouse design:
   current wardrobe is 155 records/1,265 observations over 90 original sources.
10. Current task: handoff to Claude Code. The newest photo has not been accepted
    by the user as canon or explicitly approved for likeness/beauty.

Historical user messages invoked OpenAI Developers/Deep Research plugins and
pasted an "ASTRA" operating configuration. These were conversation requests,
not installed capabilities, verified research runs, or instructions overriding
the receiving agent's rules. No new research or image API account is required
to inspect this handoff. Do not claim access to another assistant's tools.

## Important Generations and Reports

### Conservatory 037

- First take: `a-0bbb9228c53a7cd8`, `octavia-ten-reference-conservatory-v37.png`.
- Corrected take: `a-3b066d7c8f6cdcf4`, `octavia-ten-reference-conservatory-v37b.png`.
- Correction: uncrossed seated legs and an upright head, instead of repeated
  hand-supported tilt/crossed legs. Both originals remain.
- Assistant recorded issue-specific acceptance of an intentional alternate
  composition. Original warning evidence remains acknowledged in the report.
- Curation suggests HERO for v37b and REVIEW for v37. Neither is canon approval.
- Final complete job: `j-efd1361db508`, 2/2 processed, seven export formats.
- Report: `octavia_studio/data/reports/conservatory-037/r-b00c4194b68c45bc.md`.

### Plum Tailoring 038: Latest Delivered Photo

- Original asset: `a-5d75bc683f0c6c4a`.
- Workspace image: `octavia_studio/production/octavia-plum-tailoring-038.png`.
- Native PNG: 1024 x 1536. No Python polishing, warping or resizing after generation.
- Outfit: plum blazer and trousers, new lilac crew-neck fine-rib knit blouse,
  black ankle boots, amethyst pendant.
- Actual pose: standing, adjusting cuff, feet uncrossed; a **slight head tilt
  remains**. Face/hairstyle are not mathematically locked or biometrically verified.
- Raw tool file: `/home/ubuntu/.codex/generated_images/01a07f9e-c104-7081-b623-5457bec1de02/exec-a7694c33-39a0-4684-9f38-102e27859fb0.png`.
  The workspace and managed original copies mean this hidden-tool path is not
  required for recovery.
- Source references are linked in `asset_links` as `generation-reference`.
- Successful prompt, actual observation manifest and state JSON are in
  `octavia_studio/production/` and archived as documents.
- Quality report: `octavia_studio/data/reports/plum-tailoring-038/r-cac9dbf0f5d54ee1.json`.
- Continuity report: `octavia_studio/data/reports/plum-tailoring-038/r-267dbaac9d1441b5.json`.
- Available checks returned PASS; quality remains `unreviewed`, canon remains
  `unreviewed`, and user aesthetic/likeness approval is pending.
- Initial failed dress brief: `production/plum-evening-038-prompt.md`.
  Output moderation rejected it; **no corresponding image asset exists**.
  The suit alternative changed the wardrobe substantially. Do not retry the
  rejected request unchanged or present it as a produced image.

## Wardrobe Evidence and What It Does Not Mean

The catalog is a persistent garment-by-garment inventory including tops,
bottoms, dresses, one-pieces, outerwear, shoes, hosiery and accessories. A
necklace, jacket and skirt are independent records, not one flattened outfit.

The source audit is `octavia_studio/wardrobe_inventory.py`; its generated
versioned data file is `production/wardrobe-audit-20260911.json`. Dates reflect
the audit/continuation history rather than an invented original purchase date.
Sheet cells are one-based, row-major with **columns x rows** grid dimensions.
Regions are normalized left/top/right/bottom in display orientation.

Current source-level reviews: 77 reviewed-visible, 11 duplicate-layout,
2 inspiration-only. Observations across duplicated layouts are separate source
evidence; 1,265 is not a count of unique outfits or independent physical sightings.

Ownership: `established` / `candidate` / `inspiration`, separate from canon.
Evidence confidence: `visible-design` / `possible-match` / `inspiration`.
Uncertain identity of a garment is not resolved merely by assigning an item ID.
Some records intentionally group a visible design family across references.

The HTML contains contextual crops of actual pixels. Some crops contain body
parts or neighbouring garments, and small source-sheet tiles limit detail.
These are not background-removed, isolated product photographs. Never generate
hidden sleeves, backs, labels or textures and present them as scraped evidence.

Source photographs are not edited. Donor references, legacy underwear and swim
designs are inventoried neutrally and marked appropriately; they are not
automatically selected for new SFW fashion shoots. The latest blouse is a new
candidate styling variant, not a retroactively owned garment.

## Open Work and Priorities

1. Await the user's quality/likeness feedback on plum-tailoring-038.
2. For subsequent shoots, avoid the mild head tilt that survived the last prompt
   and actively vary pose, framing, hair arrangement and room.
3. Add a review-gated annotation assistant if requested. Current semantic labels
   are assistant/human-reviewed input, not machine clothing/pose recognition.
4. Improve item-instance matching and representative crop quality without
   hallucinating missing garment surfaces or silently merging design variants.
5. A personality-aware, diversity-aware shoot planner is **not implemented**.
   The current combinations command is only a category cartesian product.
6. Individual future generations need one tool call/output each. The original
   four-shot idea is context, not a pending job to execute without direction.
