# Handoff bundle — run `OBS` -> shoot `rt-test`

24 image(s) ready for the octavia_studio catalogue.

    bash import.sh        # imports pixels and creates the shoot — safe
    # then verify each image, edit and uncomment annotate.sh

## Why annotate.sh is commented out

This studio records what a shoot **requested**. The catalogue records what a
photograph **shows**. A renderer does not reliably obey a prompt, so copying
spec fields into `asset annotate` would turn intent into recorded observation
and corrupt the continuity history that depends on it.

`--pendant` is emitted as `unknown` even when the shoot asked for the pendant.
Per the project's canon: unknown is not absence, and a request is not evidence.

`intent.json` holds the full requested state for every frame, clearly labelled.

## A note on the QC scores

Any `studio_qc` score in `intent.json` comes from this studio's heuristic
scorer. Ten of its fourteen metrics are deterministic placeholders pending a
vision model. Do not read them as measurements of identity or anatomy.
