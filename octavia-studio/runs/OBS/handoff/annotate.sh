#!/usr/bin/env bash
# Annotation commands pre-filled from the SHOOT INTENT.
#
# Every line is commented out on purpose. This studio knows what it
# ASKED FOR, not what was rendered, and the octavia_studio catalogue
# is a record of observed state. Open each image, check the values,
# correct them, then uncomment the line.
#
# --pendant is 'unknown' rather than 'present' even when the shoot
# requested it: unknown is not absence, and a request is not evidence.
set -euo pipefail

# Replace <ASSET_ID> with the id printed by import.sh.

# frame OBS_000  (OBS_000.png)
#   requested room: planted garden terrace
#   requested garments: cream-rib-crop, black-a-line-skirt, black-loafers
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'low crouch, balanced on the balls of the feet' --framing 'close portrait, head and upper shoulders' --expression 'a subtle closed-mouth grin' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_001  (OBS_001.png)
#   requested room: warm cafe interior
#   requested garments: black-mock-long, mauve-joggers, mauve-knit-robe, black-lace-boots
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'mid-stride, walking naturally' --framing 'full body in frame' --expression 'thoughtful, slightly distant expression' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_002  (OBS_002.png)
#   requested room: deep burgundy and black lounge
#   requested garments: black-asym-long-midi, black-loafers
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'seated upright, hands in lap' --framing 'head-and-shoulders framing' --expression 'candid, caught between expressions' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_003  (OBS_003.png)
#   requested room: sage and natural timber loft
#   requested garments: lilac-button-shirt, black-leggings, lilac-cardigan, black-sneakers
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'seated with legs crossed on a chair' --framing 'waist-up framing' --expression 'a quiet natural laugh' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_004  (OBS_004.png)
#   requested room: city rooftop at dusk
#   requested garments: chocolate-tank, black-knit-trousers, white-strappy-heels
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'standing with hands in pockets' --framing 'three-quarter length, mid-thigh crop' --expression 'playful look with a hint of a smile' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_005  (OBS_005.png)
#   requested room: forest green and gold hotel suite
#   requested garments: black-halter-jumpsuit, black-lace-boots
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'standing with one hand resting on furniture' --framing 'mirror selfie framing' --expression 'a small closed-mouth smile' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_006  (OBS_006.png)
#   requested room: sunlit apartment balcony
#   requested garments: plum-sport-top, lilac-knit-trousers, black-loafers
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'standing turned away, torso rotated back' --framing 'full body small in a wide environment' --expression 'slightly mischievous, one brow marginally raised' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_007  (OBS_007.png)
#   requested room: monochrome charcoal gallery space
#   requested garments: stone-sport-top, charcoal-slit-mini, lilac-cardigan, white-sneakers
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'leaning shoulder against a wall' --framing 'head-and-shoulders framing' --expression 'confident level gaze, composed mouth' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_008  (OBS_008.png)
#   requested room: warm walk-in wardrobe
#   requested garments: plum-patterned-cami, cyan-pleated-skirt, black-strappy-heels
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'standing, adjusting a sleeve or hem' --framing 'full body small in a wide environment' --expression 'neutral and soft, lips relaxed and closed' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_009  (OBS_009.png)
#   requested room: sunlit apartment balcony
#   requested garments: blue-floral-midi, black-mary-janes
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'standing relaxed, weight even' --framing 'seated full-length framing' --expression 'a warm genuine smile with slight eye crinkle' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_010  (OBS_010.png)
#   requested room: white stone apartment with cobalt accents
#   requested garments: cyan-daydress, black-ankle-boots
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'perched on the edge of a seat, leaning forward' --framing 'candid detail crop, subject partially framed' --expression 'slightly mischievous, one brow marginally raised' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_011  (OBS_011.png)
#   requested room: fashion dressing room
#   requested garments: white-tank, gray-piped-shorts, black-bit-loafers
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'standing contrapposto, weight on one hip' --framing 'seated full-length framing' --expression 'calm and serene, fully relaxed features' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_012  (OBS_012.png)
#   requested room: fashion studio seamless backdrop
#   requested garments: sky-rib-tank, gray-joggers, black-ankle-boots
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'walking and turning back toward camera' --framing 'full body small in a wide environment' --expression 'lips just barely parted, relaxed' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_013  (OBS_013.png)
#   requested room: terracotta and linen sunroom
#   requested garments: cream-v-sweater, black-wide-jeans, black-long-coat, black-sneakers
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'standing with arms softly folded' --framing 'full body in frame' --expression 'neutral and soft, lips relaxed and closed' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_014  (OBS_014.png)
#   requested room: cream and lavender soft bedroom
#   requested garments: cream-square-long, light-straight-jeans, black-long-coat, white-strappy-heels
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'standing, one hand lifted to her hair' --framing 'candid detail crop, subject partially framed' --expression 'slightly mischievous, one brow marginally raised' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_015  (OBS_015.png)
#   requested room: dark modern hotel lobby
#   requested garments: cyan-tailored-midi, white-strappy-heels
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'seated with one arm draped over the sofa back' --framing 'mirror selfie framing' --expression 'lips just barely parted, relaxed' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_016  (OBS_016.png)
#   requested room: modern stone and steel kitchen
#   requested garments: cream-rib-crop, plum-tailored-trousers, olive-cropped-jacket, white-strappy-heels
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'reaching up toward a shelf or rail' --framing 'close portrait, head and upper shoulders' --expression 'a small closed-mouth smile' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_017  (OBS_017.png)
#   requested room: historic stone architecture
#   requested garments: plum-velvet-long, black-ankle-boots
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'caught turning toward the camera' --framing 'three-quarter length, mid-thigh crop' --expression 'softly downcast, calm expression' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_018  (OBS_018.png)
#   requested room: modern stone and steel kitchen
#   requested garments: cyan-square-top, cyan-long-pleats, nude-strappy-heels
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'leaning back against a counter or island' --framing 'waist-up framing' --expression 'a warm genuine smile with slight eye crinkle' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_019  (OBS_019.png)
#   requested room: marble bathroom vanity
#   requested garments: black-square-top, black-tailored-trousers, black-bit-loafers
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'standing, one hand lifted to her hair' --framing 'close portrait, head and upper shoulders' --expression 'a small closed-mouth smile' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_020  (OBS_020.png)
#   requested room: deep burgundy and black lounge
#   requested garments: plum-velvet-slip, black-strappy-heels
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'perched on the edge of a seat, leaning forward' --framing 'candid detail crop, subject partially framed' --expression 'candid, caught between expressions' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_021  (OBS_021.png)
#   requested room: botanical stone courtyard
#   requested garments: black-tee, light-straight-jeans, black-lace-boots
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'standing, adjusting a sleeve or hem' --framing 'close portrait, head and upper shoulders' --expression 'a quiet natural laugh' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_022  (OBS_022.png)
#   requested room: cool concrete and chrome minimal studio
#   requested garments: plum-v-knit-dress, black-bit-loafers
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'seated on the floor, legs tucked' --framing 'head-and-shoulders framing' --expression 'playful look with a hint of a smile' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'

# frame OBS_023  (OBS_023.png)
#   requested room: navy and warm oak study lounge
#   requested garments: lilac-mock-crop, blue-ripped-jeans, black-sneakers
# cd /tmp/claude-0/-home-user-Questlords-GAME/6e3a84e4-e4b3-5fbe-83c5-dc2bc10c63a0/scratchpad/roundtrip && python3 octavia.py asset annotate <ASSET_ID> --pose 'seated sideways, torso turned to camera' --framing 'waist-up framing' --expression 'confident level gaze, composed mouth' --pendant unknown --notes 'octavia-studio run OBS; values are INTENT until verified'
