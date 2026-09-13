# Octavia Ten-Reference Synthesis v37

Status: Generated successfully; first pass retained. A focused pose correction is recorded as v37b.
Mode: Built-in image_gen; reference-based generation.
Use case: photorealistic-natural.

## User Request

"Process" with ten Octavia images. Interpreted in the ongoing workflow as one new portrait synthesizing the references, not ten separate edits or a collage.

## Reviewed Inputs

All ten attached images were visually reviewed. Five representative images are passed to the generator to emphasize identity, clothing and the new conservatory composition. The first invocation failed argument validation because six paths were supplied; no generation occurred. The input list was reduced to the supported maximum of five.

- Photo 1: Low-resolution cyan athletic top and black shorts; color and casual styling cue only, not a facial detail source.
- Photo 2: Cyan square-neck top and pleated coordinates; cyan and pleat construction reference.
- Photo 3: Lilac knit, cream cardigan, charcoal tailoring and black shoes; layering and finish reference.
- Photo 4: Cream top, black pleated skirt, tights, boots and small shoulder bag; skirt and accessories reference.
- Photo 5: Forest-green top, ribbed waist and black skirt; continuity and textile reference.
- Photo 6: Clearest direct facial and natural body reference in this upload.
- Photo 7: Studio gallery with varied expressions and poses; personality and posture reference.
- Photo 8: Conservatory portrait; environmental and seated-composition reference.
- Photo 9: Facial and outfit gallery; corroborating continuity reference.
- Photo 10: Apartment lifestyle gallery; lived-in styling and room atmosphere reference.

## Generator Reference Order

1. `/tmp/codex-remote-attachments/01a07f9e-c104-7081-b623-5457bec1de02/589074E5-3BD5-4E1D-B552-21148DBFD16A/6-Photo-6.jpg`
2. `/tmp/codex-remote-attachments/01a07f9e-c104-7081-b623-5457bec1de02/589074E5-3BD5-4E1D-B552-21148DBFD16A/2-Photo-2.jpg`
3. `/tmp/codex-remote-attachments/01a07f9e-c104-7081-b623-5457bec1de02/589074E5-3BD5-4E1D-B552-21148DBFD16A/4-Photo-4.jpg`
4. `/tmp/codex-remote-attachments/01a07f9e-c104-7081-b623-5457bec1de02/589074E5-3BD5-4E1D-B552-21148DBFD16A/8-Photo-8.jpg`
5. `/tmp/codex-remote-attachments/01a07f9e-c104-7081-b623-5457bec1de02/589074E5-3BD5-4E1D-B552-21148DBFD16A/7-Photo-7.jpg`

## Exact Prompt

Generate one high-resolution photorealistic editorial portrait of Octavia, the same fictional adult woman in her late twenties shown across these references. One image of one woman, no collage. Preserve her recognizable face and natural body proportions.

REFERENCE ROLES in supplied order: image 1 (black tank at a window) is the primary facial and body identity reference. Preserve her specific green-hazel eyes, expressive dark brows, subtle freckles, warm natural skin, softly defined features, brunette hair and lime/olive-green face-framing sections. Image 2 supplies cyan color, square neckline and tailored pleats. Image 3 supplies the black pleated skirt and black ankle boots. Image 4 supplies the conservatory setting and physically relaxed seated atmosphere. Image 5 supplies lilac knitwear and is a gallery of the SAME woman, used for natural personality, anatomy and expression variation, never reproduced as a collage. Do not average her into a different generic model.

WARDROBE: A fitted, fully opaque cyan square-neck sleeveless top whose hem meets a high waistband; a black tailored pleated skirt of ordinary above-knee fashion length with secure opaque lining and a neat waistband; matte black opaque tights; polished black leather ankle boots with comfortable low block heels. An open soft lilac knit cardigan ending at the high hip, with small buttons, both sleeves worn naturally and lightly pushed up. The clothes fit her existing body rather than altering it. Include her single small amethyst crystal pendant on its silver chain. Elegant, cute, sophisticated contemporary fashion, comfortably SFW, real fabric thickness and weight, no added cutouts. Fine rib texture, plausible seams, small folds and compression where she sits.

COMPLETELY NEW COMPOSITION AND POSE: A candid seated fashion photograph, full head-to-boots visible. She sits naturally on a charcoal upholstered bench at the end of a small pale-stone conservatory table. Her body is angled three-quarter to the camera, shoulders relaxed, spine comfortable and upright. Knees together and angled gently toward one side, feet planted individually on the floor, ankles UNcrossed. The skirt lies naturally over and securely covers her lap. One forearm rests on the table next to a closed unprinted book; the other hand rests loosely on her knee. Her head is upright, eyes approximately level, face turning slightly toward the photographer in a spontaneous warm smile, lips softly parted as if amused by an ordinary conversation. No repeated sideways head tilt, hand-in-hair pose, mirror selfie, crossed legs or stiff mannequin posture. Hands and feet anatomically plausible and incidental. She is the compositional focus, not any isolated body part.

HAIR: A lived-in loose low ponytail with a few wavy lengths over one shoulder and distinctive green front locks free around her face. Preserve brunette color, naturally irregular hairline and flyaways. Change the hairstyle without changing the face, age or physique.

ROOM REMIX: A new enclosed conservatory adjoining her upscale apartment: slender dark window frames, a pale-stone table, warm walnut cabinetry, charcoal bench cushions, a muted lilac woven throw, and leafy plants with a few white blossoms. A glimpse of the city beyond the glass. Different layout from the reference conservatory, no copy of its bench, table position or camera angle. Restrained lived-in details: a ceramic cup and closed plain-cover book on the table, her small deep-plum shoulder bag on an empty chair. Coherent daylight from one side, gentle warm interior fill, soft leaf shadows falling on the floor without obscuring her face.

PHOTOGRAPHY: Premium full-frame fashion photograph, natural normal-to-short-telephoto perspective from a comfortable seated chest-to-eye camera height, no wide-angle distortion. Enough depth of field to read her face and entire outfit, with a gently softened real environment. Visible pores, subtle freckles, peach fuzz, individual hair strands, natural skin variation, realistic knees, hands and fabric contact. Attractive through expression, styling and flattering physically coherent light, not reshaped anatomy or heavy retouching. No plastic skin, CGI, beauty-filter composite, unrealistic symmetry, added captions, logos, watermark or collage borders. Deliver one polished image.

## Output

- Workspace image: `/home/ubuntu/octavia-ten-reference-conservatory-v37.png`
- Raw image: `/home/ubuntu/.codex/generated_images/01a07f9e-c104-7081-b623-5457bec1de02/exec-ad594b61-b2fc-4f37-b7c9-36533a890883.png`
- Resolution: 1024 x 1536 PNG.
- Review: face and hair continuity cues, cyan top, lilac cardigan, black pleats and boots, new conservatory setting and seated composition are present. The tool introduced crossed knees and a head supported by one hand, contrary to the intended pose; v37b targets only these deviations.
