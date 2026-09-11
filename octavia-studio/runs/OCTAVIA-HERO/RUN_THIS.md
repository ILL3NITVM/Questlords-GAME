# Octavia — Hero Frame, ready to render

Selected from 512 scored candidates. Hero score **97.3/100**.

    85mm close portrait · beauty dish key · standing contrapposto, hands at sides
    chin down, eyes to camera, neutral head roll · small closed-mouth smile
    monochrome charcoal gallery · f/5.6 · 896 x 1152

Prompt: 132 tokens / 2 CLIP chunks. All ten content groups present.

---

## Fastest path — hosted API, no GPU needed

```bash
export OCTAVIA_API_ENDPOINT="https://<your-provider>/v1/images/generations"
export OCTAVIA_API_KEY="<your-key>"

# match your provider's response shape in config/studio.yaml:
#   renderer.api.model          e.g. an SDXL or Flux model id
#   renderer.api.response_kind  b64 | url | raw
#   renderer.api.response_path  e.g. data.0.b64_json

python studio.py hero --candidates 512 --seed 20260911 --backend api
```

## Local ComfyUI

```bash
# 1. build a text-to-image workflow in ComfyUI, export via Save (API Format)
# 2. point config/studio.yaml at it:
#      renderer.comfyui.workflow_template: config/workflows/octavia_txt2img.json
#      renderer.comfyui.node_map:
#        positive: {node: "6", field: "text"}
#        negative: {node: "7", field: "text"}
#        seed:     {node: "3", field: "seed"}
#        width:    {node: "5", field: "width"}
#        height:   {node: "5", field: "height"}

python studio.py hero --candidates 512 --seed 20260911 --backend comfyui
```

With ComfyUI the `hires_fix` and `face_detail` passes activate automatically
if the server reports those nodes — worth having, since the face occupies few
pixels in the base sample and the detail pass is the single largest quality
gain for portraiture.

## Or just paste it

`hero_prompt.txt` works in any generator. Suggested settings:

| | |
|---|---|
| size | 896 x 1152 |
| steps | 40 |
| CFG | 5.0 |
| sampler | DPM++ 2M SDE, Karras |
| hires fix | 1.5x, denoise **0.40** |
| face detail | denoise **0.30** |

Keep the refinement denoise at or below 0.5. Above that the pass resamples the
face freely and walks the likeness off-model between passes.

---

## Expect identity drift on the first run

This prompt asserts identity with **text only** — `identity.mode: descriptive`,
no LoRA configured. Text alone will not hold a face across repeated renders.
For a persistent Octavia, train the adapter on your existing photo set:

```bash
python studio.py dataset ingest
python studio.py dataset analyze     # read the bias report before training
python studio.py dataset curate
python studio.py dataset caption
python studio.py dataset export
```

Then set `identity.mode: lora_token` and `identity.lora.enabled: true`, and
re-run the same command with the same seed.

Reproduce this exact frame any time with `--seed 20260911`.
