"""Versioned assistant visual audit of the 89 pre-existing image assets.

Design families are deliberately not claims of identical physical garments.
Sheet cells are one-based, left-to-right; local boxes are reviewed evidence crops.
"""
import json
from pathlib import Path

from .storage import write_once

ITEMS = []


def item(key, name, category, color, **extra):
    ITEMS.append(dict(id=key,name=name,category=category,color=color,**extra))


for row in [
    ('lilac-racer-crop','Lilac racer-neck ribbed crop','lilac'),
    ('lilac-mock-crop','Lilac sleeveless mock-neck crop','lilac'),
    ('lilac-ruched-mock','Lilac long-sleeve ruched mock-neck crop','lilac'),
    ('lilac-button-shirt','Lilac collared button shirt','lilac'),
    ('lilac-henley','Lilac fitted button-front knit','lilac'),
    ('mauve-henley','Mauve scoop-neck henley','mauve'),
    ('plum-scoop-long','Plum scoop-neck long-sleeve knit','plum'),
    ('plum-sport-top','Plum scoop-neck athletic crop','plum'),
    ('lilac-sport-top','Lilac scoop-neck athletic crop','lilac'),
    ('cyan-sport-top','Cyan scoop-neck athletic crop','cyan'),
    ('stone-sport-top','Stone scoop-neck athletic crop','stone'),
    ('black-crop-tank','Black fitted crop tank','black'),
    ('black-button-crop','Black button-front crop tank','black'),
    ('black-scoop-long','Black scoop-neck long-sleeve fitted top','black'),
    ('black-square-long','Black square-neck long-sleeve fitted top','black'),
    ('black-open-back','Black scoop-neck open-back long-sleeve top','black'),
    ('black-one-shoulder-top','Black one-shoulder fitted top','black'),
    ('plum-one-shoulder-top','Plum one-shoulder ribbed top','plum'),
    ('black-halter-knit','Black ribbed halter top','black'),
    ('black-mock-long','Black long-sleeve ribbed mock-neck top','black'),
    ('black-tee','Black fitted short-sleeve tee','black'),
    ('white-tee-crop','White fitted cropped tee','white'),
    ('white-tank','White scoop-neck tank','white'),
    ('cream-square-long','Cream square-neck long-sleeve crop','cream'),
    ('cream-rib-crop','Cream ribbed crop tank','cream'),
    ('lilac-rib-tank','Lilac ribbed longline tank','lilac'),
    ('sky-rib-tank','Sky-blue ribbed longline tank','sky blue'),
    ('yellow-rib-tank','Lemon-yellow ribbed tank','lemon'),
    ('mauve-crop-tank','Mauve fitted crop tank','mauve'),
    ('chocolate-tank','Chocolate scoop-neck tank','chocolate'),
    ('forest-contrast-top','Forest-green long-sleeve top with pale ribbed waistband','forest green'),
    ('cyan-knot-wrap','Cyan front-knot wrap-strap crop top','cyan'),
    ('cyan-wrap-blouse','Cyan sleeveless collared wrap blouse','cyan'),
    ('cyan-drape-blouse','Muted cyan draped-neck blouse','cyan'),
    ('plum-satin-cami','Plum satin-look camisole','plum'),
    ('cream-v-sweater','Cream V-neck knit sweater','cream'),
    ('plum-wide-sweater','Plum wide-neck relaxed sweater','plum'),
]: item(row[0],row[1],'top',row[2])

for row in [
    ('black-a-line-skirt','Black tailored A-line skirt','black'),
    ('black-cyan-pleats','Black skirt with cyan inset pleats','black/cyan'),
    ('cyan-long-pleats','Cyan knee-length pleated skirt','cyan'),
    ('plum-wrap-mini','Plum tailored wrap-front skirt','plum'),
    ('charcoal-slit-mini','Charcoal tailored side-slit skirt','charcoal'),
    ('mauve-knit-skirt','Mauve knit midi skirt','mauve'),
    ('black-cargo-jeans','Black fitted cargo-pocket jeans','black'),
    ('black-wide-jeans','Washed black wide-leg jeans','washed black'),
    ('dark-skinny-jeans','Dark indigo fitted jeans','dark indigo'),
    ('light-straight-jeans','Light blue straight-leg jeans','light blue'),
    ('blue-straight-jeans','Mid-blue straight-leg jeans','blue'),
    ('blue-ripped-jeans','Light blue distressed jeans','light blue'),
    ('black-tailored-trousers','Black pleated tailored trousers','black'),
    ('cream-tailored-trousers','Cream pleated tailored trousers','cream'),
    ('white-loose-trousers','White loose summer trousers','white'),
    ('plum-tailored-trousers','Plum tailored wide-leg trousers','plum'),
    ('black-running-shorts','Black drawstring running shorts','black'),
    ('black-piped-shorts','Black athletic shorts with pale piping','black'),
    ('gray-piped-shorts','Gray athletic shorts with white piping','gray'),
    ('gray-joggers','Gray drawstring joggers','gray'),
    ('mauve-joggers','Mauve drawstring lounge trousers','mauve'),
    ('plum-lounge-trousers','Plum ribbed lounge trousers','plum'),
    ('lilac-knit-trousers','Lilac ribbed lounge trousers','lilac'),
    ('black-knit-trousers','Black ribbed lounge trousers','black'),
    ('black-leggings','Black full-length leggings','black'),
    ('plum-leggings','Plum full-length athletic leggings','plum'),
    ('cream-drawstring-shorts','Cream drawstring summer shorts','cream'),
    ('cream-tailored-shorts','Cream tailored shorts','cream'),
    ('dark-plaid-trousers','Dark plaid lounge trousers','dark plaid'),
]: item(row[0],row[1],'bottom',row[2])

for row in [
    ('black-halter-mini','Black halter mini dress','black'),
    ('black-square-mini','Black square-neck long-sleeve mini dress','black'),
    ('black-one-shoulder-mini','Black asymmetric ruched mini dress','black'),
    ('black-asym-midi','Black one-shoulder draped midi dress','black'),
    ('black-asym-long-midi','Black asymmetric long-sleeve slit midi dress','black'),
    ('black-velvet-halter','Black velvet-look high-neck midi dress','black'),
    ('plum-knit-mock-dress','Plum ribbed mock-neck midi dress','plum'),
    ('plum-v-knit-dress','Plum V-neck ribbed midi dress','plum'),
    ('mauve-wrap-knit-dress','Mauve wrap-front knit midi dress','mauve'),
    ('plum-velvet-slip','Plum velvet-look draped midi dress','plum'),
    ('plum-velvet-long','Plum velvet-look long-sleeve midi dress','plum'),
    ('plum-satin-high-dress','Plum satin-look high-neck midi dress','plum'),
    ('plum-satin-slip','Plum satin-look slip dress','plum'),
    ('cyan-daydress','Cyan sleeveless flared day dress','cyan'),
    ('cyan-tailored-midi','Cyan square-neck tailored midi dress','cyan'),
    ('lemon-midi','Lemon square-neck slit midi dress','lemon'),
    ('cream-button-mini','Cream button-front summer mini dress','cream'),
    ('blue-floral-midi','Blue-and-white floral midi dress','blue/white'),
]: item(row[0],row[1],'dress',row[2])

for row in [
    ('purple-chunky-cardigan','Purple chunky open cardigan','purple'),
    ('cream-button-cardigan','Cream short button cardigan','cream'),
    ('cream-chartreuse-cardigan','Cream cardigan with chartreuse edging','cream/chartreuse'),
    ('mauve-long-cardigan','Mauve longline cardigan','mauve'),
    ('black-cardigan','Charcoal open knit cardigan','charcoal'),
    ('plum-satin-robe','Plum satin-look belted robe','plum'),
    ('mauve-knit-robe','Mauve belted knit robe','mauve'),
    ('black-blazer','Black tailored blazer','black'),
    ('lilac-blazer','Lilac tailored blazer','lilac'),
    ('plum-blazer','Plum tailored blazer','plum'),
    ('olive-cropped-jacket','Olive cropped collared jacket','olive'),
    ('olive-overshirt','Olive relaxed overshirt','olive'),
    ('plum-leather-jacket','Plum leather-look cropped jacket','plum'),
    ('black-long-coat','Black long tailored coat','black'),
    ('plum-long-coat','Plum satin-look long coat','plum'),
    ('printed-short-robe','Sage abstract-print short open layer','sage/charcoal'),
    ('printed-long-robe','Cream botanical-print long open layer','cream/black'),
    ('gray-zip-hoodie','Gray zip-front hoodie','gray'),
    ('gray-sweatshirt','Gray waist-tied sweatshirt','gray'),
    ('mauve-sweatshirt','Mauve waist-tied sweatshirt','mauve'),
    ('blue-cardigan-inspiration','Sky-blue open cardigan from donor sheet','sky blue'),
    ('white-open-shirt-inspiration','White open shirt from donor sheet','white'),
]: item(row[0],row[1],'outerwear',row[2],inspiration=row[0].endswith('inspiration'))

for row in [
    ('white-sneakers','White low-top sneakers','white'),
    ('black-sneakers','Black athletic sneakers with light sole','black'),
    ('black-lace-boots','Black lace-up ankle boots','black'),
    ('black-knee-boots','Black knee-high block-heel boots','black'),
    ('black-mary-janes','Black platform Mary Jane shoes','black'),
    ('black-platform-pumps','Black platform ankle-strap pumps','black'),
    ('black-strappy-heels','Black ankle-strap sandals','black'),
    ('white-strappy-heels','White ankle-strap sandals','white'),
    ('black-bit-loafers','Black loafers with metal bit detail','black'),
    ('black-pointed-pumps','Black pointed-toe pumps','black'),
    ('nude-strappy-heels','Nude ankle-strap sandals','nude'),
]: item(row[0],row[1],'footwear',row[2])

for row in [
    ('black-tights','Black fine-gauge tights','black'),
    ('cream-socks','Cream ribbed ankle socks','cream'),
    ('lilac-socks','Lilac ribbed ankle socks','lilac'),
    ('gray-knee-socks','Gray knee-high ribbed socks','gray'),
]: item(row[0],row[1],'hosiery',row[2])

for row in [
    ('black-belt','Black rectangular-buckle belt','black'),
    ('brown-belt','Brown buckle belt','brown'),
    ('red-shoulder-bag','Red structured shoulder bag','red'),
    ('black-shoulder-bag','Black small shoulder bag','black'),
    ('black-handbag','Black structured top-handle bag','black'),
    ('black-tote','Black roomy tote','black'),
    ('brown-tote','Brown slouchy shoulder tote','brown'),
    ('stone-handbag','Stone structured top-handle bag','stone'),
    ('cream-shoulder-bag','Cream small shoulder bag','cream'),
    ('woven-bag','Natural woven basket handbag','natural'),
    ('black-evening-clutch','Black evening clutch','black'),
    ('black-sparkle-clutch','Black embellished evening clutch','black/silver'),
    ('sunglasses','Dark sunglasses','black'),
]: item(row[0],row[1],'accessory',row[2])

item('black-halter-jumpsuit','Black belted halter jumpsuit','one-piece','black')
item('plum-one-piece','Plum square-neck one-piece swim garment','one-piece','plum')
item('cyan-tie-bottom-inspiration','Cyan side-tie swim bottom, donor design','bottom','cyan',inspiration=True)
item('cyan-wrap-swim-inspiration','Cyan knot-front wrap-strap swim top, donor design','top','cyan',inspiration=True)
item('plum-lace-bra','Plum embroidered lace bra','top','plum',notes='Underwear archive only; excluded from the four fashion shoots.')
item('black-lace-bra','Black embroidered lace bra','top','black',notes='Underwear archive only; excluded from the four fashion shoots.')
item('plum-lace-bottom','Plum lace brief','bottom','plum',notes='Underwear archive only; excluded from the four fashion shoots.')
item('black-lace-bottom','Black lace brief','bottom','black',notes='Underwear archive only; excluded from the four fashion shoots.')
item('plum-patterned-cami','Plum floral-pattern camisole','top','plum',notes='Partial neckline only; garment length and hidden design unknown.')

SOURCES=[]


def scene(asset, cells, grid=(1,1), **kwargs):
    observations=[]
    for cell, names in enumerate(cells,1):
        for name in names.split():
            observations.append({'item':name,'cell':cell})
    SOURCES.append(dict(asset=asset,grid=list(grid),observations=observations,**kwargs))


scene('octavia-clothing-sheet-01-polished-daywear.png',[
    'black-one-shoulder-top light-straight-jeans black-shoulder-bag amethyst-pendant',
    'black-halter-mini black-sparkle-clutch amethyst-pendant',
    'printed-short-robe chocolate-tank light-straight-jeans black-ankle-boots amethyst-pendant',
    'black-crop-tank black-leggings white-sneakers amethyst-pendant',
    'black-square-long black-tailored-trousers black-belt black-tote black-loafers amethyst-pendant',
    'lilac-cardigan black-square-top black-wide-jeans amethyst-pendant',
    'cream-button-cardigan black-square-top black-wide-jeans black-shoulder-bag amethyst-pendant',
    'black-square-mini black-ankle-boots black-evening-clutch amethyst-pendant',
    'black-halter-knit cream-tailored-trousers black-belt black-handbag amethyst-pendant',
    'cream-cardigan black-square-top black-wide-jeans black-lace-boots amethyst-pendant',
    'plum-one-shoulder-top black-tailored-trousers black-evening-clutch amethyst-pendant',
    'black-blazer black-square-top light-straight-jeans black-ankle-boots sunglasses black-handbag amethyst-pendant',
],(4,3))
scene('octavia-clothing-sheet-02-resort-cafe.png',[
    'lemon-midi cream-shoulder-bag white-strappy-heels amethyst-pendant',
    'sky-rib-tank white-loose-trousers brown-belt amethyst-pendant',
    'cream-button-mini woven-bag amethyst-pendant',
    'lilac-rib-tank light-straight-jeans brown-belt amethyst-pendant',
    'black-one-shoulder-mini black-sparkle-clutch amethyst-pendant',
    'white-tee-crop cream-tailored-shorts black-belt woven-bag amethyst-pendant',
    'lilac-cardigan cream-rib-crop mauve-knit-skirt amethyst-pendant',
    'cream-chartreuse-cardigan white-tank white-loose-trousers brown-belt cream-shoulder-bag amethyst-pendant',
    'mauve-crop-tank mauve-knit-skirt white-strappy-heels amethyst-pendant',
    'black-tee cream-tailored-trousers black-belt black-shoulder-bag amethyst-pendant',
    'blue-floral-midi woven-bag amethyst-pendant',
    'cream-chartreuse-cardigan yellow-rib-tank light-straight-jeans sunglasses amethyst-pendant',
],(4,3))
scene('octavia-clothing-sheet-03-penthouse-evening.png',[
    'black-asym-long-midi black-strappy-heels black-evening-clutch amethyst-pendant',
    'plum-v-knit-dress amethyst-pendant',
    'black-square-top charcoal-trousers amethyst-pendant',
    'cream-cardigan black-square-top black-wide-jeans cream-socks amethyst-pendant',
    'mauve-knit-robe amethyst-pendant',
    'black-halter-jumpsuit black-belt black-evening-clutch amethyst-pendant',
    'plum-satin-robe plum-satin-slip amethyst-pendant',
    'purple-chunky-cardigan lilac-rib-tank lilac-knit-trousers cream-socks amethyst-pendant',
    'black-mock-long charcoal-slit-mini black-tights black-knee-boots black-shoulder-bag amethyst-pendant',
    'cream-button-cardigan black-square-top charcoal-trousers cream-socks amethyst-pendant',
    'mauve-wrap-knit-dress black-strappy-heels black-evening-clutch amethyst-pendant',
    'black-cardigan black-square-top black-knit-trousers cream-socks amethyst-pendant',
],(4,3))
scene('octavia-clothing-sheet-04-off-duty-athleisure.png',[
    'printed-long-robe chocolate-tank light-straight-jeans black-ankle-boots',
    'black-square-top black-leggings gray-sweatshirt white-sneakers black-shoulder-bag amethyst-pendant',
    'olive-overshirt white-tank light-straight-jeans white-sneakers brown-tote amethyst-pendant',
    'cream-cardigan black-square-top black-wide-jeans cream-socks amethyst-pendant',
    'plum-scoop-long black-tailored-trousers black-belt black-loafers black-tote amethyst-pendant',
    'black-square-top cream-tailored-trousers black-handbag amethyst-pendant',
    'printed-long-robe chocolate-tank light-straight-jeans black-ankle-boots brown-tote',
    'gray-zip-hoodie black-crop-tank gray-joggers white-sneakers amethyst-pendant',
    'mauve-long-cardigan white-tank light-straight-jeans black-tote amethyst-pendant',
    'black-scoop-long black-wide-jeans black-lace-boots amethyst-pendant',
    'cream-cardigan chocolate-tank black-wide-jeans amethyst-pendant',
    'black-crop-tank black-leggings mauve-sweatshirt white-sneakers amethyst-pendant',
],(4,3))

MASTER=[
    'black-scoop-long plum-tailored-trousers black-pointed-pumps amethyst-pendant',
    'black-scoop-long dark-skinny-jeans black-ankle-boots amethyst-pendant',
    'black-scoop-long amethyst-pendant',
    'lilac-cardigan black-crop-tank black-leggings cream-socks amethyst-pendant',
    'plum-wide-sweater black-leggings amethyst-pendant',
    'lilac-cardigan black-crop-tank black-leggings amethyst-pendant',
    'plum-sport-top gray-joggers amethyst-pendant',
    'black-scoop-long plum-tailored-trousers amethyst-pendant',
    'lilac-henley dark-skinny-jeans black-belt black-handbag amethyst-pendant',
    'cream-cardigan mauve-crop-tank mauve-joggers amethyst-pendant',
    'black-crop-tank black-leggings lilac-socks amethyst-pendant',
    'plum-satin-slip plum-satin-robe amethyst-pendant',
    'black-scoop-long amethyst-pendant',
    'black-open-back dark-skinny-jeans amethyst-pendant',
    'plum-wide-sweater amethyst-pendant',
    'black-scoop-long gray-joggers amethyst-pendant',
]
scene('octavia-master-reference-sheet.png',MASTER,(4,4))
for alias in ['octavia-identity-source-v9.jpg','octavia-preview-master-ref-chat.jpg','a-ef505fc45709c6f1']:
    scene(alias,MASTER,(4,4),status='duplicate-layout')

STUDIO=[
    'lilac-mock-crop black-wide-jeans black-ankle-boots amethyst-pendant',
    'lilac-mock-crop black-wide-jeans amethyst-pendant',
    'lilac-mock-crop amethyst-pendant',
    'black-square-top charcoal-trousers amethyst-pendant',
    'plum-velvet-slip black-strappy-heels amethyst-pendant',
    'black-asym-midi black-strappy-heels amethyst-pendant',
    'plum-blazer black-square-top plum-tailored-trousers amethyst-pendant',
    'lilac-button-shirt amethyst-pendant',
    'lilac-sport-top black-piped-shorts amethyst-pendant',
    'black-crop-tank plum-leggings amethyst-pendant',
    'black-cardigan black-crop-tank blue-straight-jeans amethyst-pendant',
    'mauve-henley charcoal-trousers amethyst-pendant',
    'purple-chunky-cardigan black-square-top blue-straight-jeans amethyst-pendant',
    'cream-v-sweater charcoal-trousers amethyst-pendant',
    'lilac-henley amethyst-pendant',
    'plum-scoop-long plum-lounge-trousers amethyst-pendant',
]
scene('octavia-remix-source-grid-v17.jpg',STUDIO,(4,4))
scene('octavia-studio-proof-16-v13.png',STUDIO,(4,4),status='duplicate-layout')
ALT=[STUDIO[0],STUDIO[7],'black-cardigan lilac-racer-crop dark-skinny-jeans black-sneakers amethyst-pendant',
     'cream-v-sweater plum-lounge-trousers amethyst-pendant',STUDIO[12],STUDIO[4],STUDIO[6],STUDIO[5],
     'black-crop-tank plum-leggings black-sneakers amethyst-pendant',STUDIO[1],'black-crop-tank amethyst-pendant',
     'purple-chunky-cardigan black-wide-jeans amethyst-pendant',STUDIO[8],
     'cream-cardigan amethyst-pendant','plum-scoop-long plum-lounge-trousers white-sneakers amethyst-pendant',
     'purple-chunky-cardigan black-square-top amethyst-pendant']
for alias in ['a-f902c47d905e3713','a-541e337d602b5d7b','octavia-head-angle-hue-remix-v18.png']:
    scene(alias,ALT,(4,4))
scene('octavia-uniform-pose-remix-v17.png',[
    STUDIO[1],STUDIO[3],STUDIO[5],STUDIO[6],STUDIO[13],STUDIO[8],STUDIO[4],
    'lilac-button-shirt black-wide-jeans amethyst-pendant',STUDIO[11],
    'black-crop-tank plum-leggings black-sneakers amethyst-pendant',
    'black-cardigan lilac-racer-crop blue-straight-jeans black-sneakers amethyst-pendant',STUDIO[12],
    'lilac-button-shirt charcoal-trousers amethyst-pendant',
    'black-scoop-long plum-tailored-trousers amethyst-pendant',STUDIO[15],
    'lilac-henley black-wide-jeans amethyst-pendant'],(4,4))

GLAM=[
    'cream-cardigan lilac-ruched-mock charcoal-trousers black-loafers amethyst-pendant',
    'lilac-cardigan black-crop-tank black-cargo-jeans black-belt black-loafers amethyst-pendant',
    'plum-knit-mock-dress black-loafers amethyst-pendant',
    'plum-leather-jacket black-one-shoulder-mini black-tights black-loafers amethyst-pendant',
    'black-long-coat plum-satin-high-dress black-tights black-platform-pumps amethyst-pendant',
    'plum-long-coat black-velvet-halter black-platform-pumps amethyst-pendant',
]
for i,name in enumerate(['01-soft-lounge','02-city-lounge','03-plum-knit-dress','04-black-plum-mini','05-plum-satin-evening','06-peak-black-velvet']):
    scene('octavia-glamour-progression-'+name+'.png',[GLAM[i]])
for alias in ['octavia-glamour-progression-master-2x3.png','octavia-preview-glamour-2x3-chat.jpg','a-5fc5f0dffa04c943']:
    scene(alias,GLAM,(3,2),status='duplicate-layout')

SINGLES={
 'octavia-master-source-v24-1.jpg':'cyan-knot-wrap cream-cardigan charcoal-trousers black-loafers amethyst-pendant',
 'octavia-master-source-v24-2.jpg':'forest-contrast-top black-a-line-skirt black-tights amethyst-pendant',
 'octavia-master-source-v24-3.jpg':'black-square-top black-a-line-skirt black-tights amethyst-pendant',
 'octavia-master-source-v24-4.jpg':'cream-square-long black-pleated-skirt black-tights black-ankle-boots red-shoulder-bag',
 'octavia-master-source-v24-5.jpg':'lilac-racer-crop black-wide-jeans amethyst-pendant',
 'octavia-genesis-seed-fullbody.png':'lilac-ruched-mock black-cargo-jeans black-belt black-loafers amethyst-pendant',
 'octavia-photographic-realism-v2.png':'lilac-ruched-mock black-cargo-jeans black-belt amethyst-pendant',
 'octavia-realistic-hd-portrait-20260908-01.png':'lilac-ruched-mock black-cargo-jeans black-belt amethyst-pendant',
 'octavia-lilac-conservatory-v14.png':'lilac-ruched-mock black-wide-jeans black-belt amethyst-pendant',
 'octavia-conservatory-seated-v15.png':'lilac-ruched-mock black-wide-jeans black-belt black-bit-loafers amethyst-pendant',
 'octavia-conservatory-source-face-v14.jpg':'lilac-ruched-mock black-wide-jeans amethyst-pendant',
 'octavia-plum-velvet-evening-v3.png':'plum-velvet-long black-tights amethyst-pendant',
 'octavia-satin-loungewear-v5.png':'plum-satin-slip black-cardigan amethyst-pendant',
 'octavia-standing-loungewear-v6.png':'plum-satin-cami black-running-shorts amethyst-pendant',
 'octavia-lilac-crop-v7.png':'lilac-mock-crop black-running-shorts amethyst-pendant',
 'octavia-fitness-reference-v9.png':'lilac-sport-top black-running-shorts white-sneakers amethyst-pendant',
 'octavia-overhead-stretch-v16.png':'lilac-sport-top black-running-shorts white-sneakers amethyst-pendant',
 'octavia-stretch-source-v16.jpg':'lilac-sport-top black-running-shorts white-sneakers amethyst-pendant',
 'octavia-beach-onepiece-shorts-v10.png':'plum-one-piece cream-drawstring-shorts sunglasses amethyst-pendant',
 'octavia-beach-reality-v12.png':'lilac-sport-top black-piped-shorts sunglasses amethyst-pendant',
 'octavia-sporty-swimwear-v11.png':'lilac-sport-top black-piped-shorts sunglasses amethyst-pendant',
 'octavia-black-top-daylight-v21.png':'black-square-top black-a-line-skirt black-tights amethyst-pendant',
 'octavia-black-top-room-source-v21.jpg':'black-square-top',
 'octavia-cream-pleated-outfit-source-v22.jpg':'cream-square-long black-pleated-skirt black-tights black-ankle-boots red-shoulder-bag',
 'octavia-cream-pleated-turn-v22.png':'cream-square-long black-pleated-skirt black-tights black-ankle-boots red-shoulder-bag amethyst-pendant',
 'octavia-cyan-outfit-source-v23.jpg':'cyan-knot-wrap cyan-pleated-skirt cream-cardigan black-loafers amethyst-pendant',
 'octavia-cyan-daydress-lilac-v23b.png':'cyan-daydress lilac-cardigan black-loafers amethyst-pendant',
 'octavia-covered-cyan-coordinates-v25.png':'cyan-wrap-blouse cyan-long-pleats lilac-cardigan amethyst-pendant',
 'octavia-cyan-tailored-editorial-v28.png':'cyan-tailored-midi black-loafers amethyst-pendant',
 'octavia-cyan-tailored-separates-v30.png':'cyan-drape-blouse charcoal-trousers lilac-blazer black-ankle-boots amethyst-pendant',
 'octavia-fused-reference-outfit-v31.png':'cyan-square-top forest-contrast-top black-cyan-pleats cream-cardigan black-tights black-lace-boots red-shoulder-bag amethyst-pendant',
 'octavia-lilac-cyan-standing-v33b.png':'lilac-racer-crop cyan-long-pleats black-blazer black-mary-janes amethyst-pendant',
 'octavia-signature-synthesis-v34.png':'cyan-square-top cyan-pleated-skirt lilac-cardigan black-loafers black-handbag amethyst-pendant',
 'octavia-after-shopping-trousers-v35b.png':'cyan-square-top charcoal-trousers lilac-cardigan black-loafers black-shoulder-bag amethyst-pendant',
 'octavia-reclaimed-fashion-synthesis-v36.png':'cyan-square-top cyan-long-pleats lilac-cardigan black-mary-janes black-shoulder-bag amethyst-pendant',
 'octavia-reclaimed-fashion-synthesis-v36b.png':'cyan-square-top cyan-long-pleats lilac-cardigan black-mary-janes black-shoulder-bag amethyst-pendant',
 'octavia-ten-reference-conservatory-v37.png':'cyan-square-top black-pleated-skirt lilac-cardigan black-tights black-ankle-boots amethyst-pendant',
 'octavia-ten-reference-conservatory-v37b.png':'cyan-square-top black-pleated-skirt lilac-cardigan black-tights black-ankle-boots amethyst-pendant',
 'octavia-walking-full-remix-v32.png':'olive-cropped-jacket black-crop-tank plum-wrap-mini black-tights black-knee-boots stone-handbag amethyst-pendant',
 'octavia-walking-profile-v32b.png':'olive-cropped-jacket black-crop-tank plum-wrap-mini black-tights black-knee-boots stone-handbag amethyst-pendant',
 'octavia-zuza-comparison-source-v26-octavia.jpg':'cyan-square-top cyan-pleated-skirt white-sneakers amethyst-pendant',
 'octavia-zuza-comparison-source-v26-zuza.jpg':'zuza-cyan-inspiration cyan-tie-bottom-inspiration',
 'octavia-room-outfit-source-detail-v19.jpg':'forest-contrast-top black-a-line-skirt black-tights',
 'octavia-room-outfit-source-front-v19.jpg':'forest-contrast-top black-a-line-skirt black-tights',
 'octavia-room-outfit-source-side-v19.jpg':'forest-contrast-top black-a-line-skirt black-tights',
 'octavia-room-outfit-v19.png':'forest-contrast-top black-a-line-skirt black-tights amethyst-pendant',
 'octavia-room-retexture-upright-v20.png':'forest-contrast-top black-a-line-skirt black-tights amethyst-pendant',
 'octavia-lilac-cardigan-source-v23.jpg':GLAM[1],
 'a-e222bfc3fc0b4822':'lilac-mock-crop cream-cardigan charcoal-trousers black-loafers amethyst-pendant',
 'a-e4712a3c65121aa7':'black-crop-tank black-running-shorts amethyst-pendant',
 'a-268c5f9e080a29b2':'stone-sport-top black-piped-shorts amethyst-pendant',
 'a-3a90a4d5c3004fda':'cyan-sport-top black-piped-shorts amethyst-pendant',
 'a-d1e7b704ea11055a':'plum-patterned-cami amethyst-pendant',
 'a-cf03adfa6ef11027':GLAM[0],
 'a-575a6062293ce91a':'lilac-ruched-mock black-cargo-jeans black-belt black-loafers amethyst-pendant',
 'a-ab5083adb884567a':'forest-contrast-top black-a-line-skirt black-tights amethyst-pendant',
 'a-b892c8bb47441519':'lilac-ruched-mock black-wide-jeans black-belt amethyst-pendant',
 'a-159cb258a1c790e0':'lilac-ruched-mock black-wide-jeans black-belt black-bit-loafers amethyst-pendant',
}
for name, clothes in SINGLES.items():
    scene(name,[clothes],status='inspiration-only' if name.endswith('v26-zuza.jpg') else 'reviewed-visible')

scene('octavia-conservatory-source-sheet-v14.jpg',[
 'purple-chunky-cardigan amethyst-pendant',STUDIO[1],'black-square-top amethyst-pendant',STUDIO[3],STUDIO[4],
 'black-crop-tank plum-leggings black-sneakers amethyst-pendant',
 'cream-cardigan black-square-top charcoal-trousers amethyst-pendant',STUDIO[7]],(4,2))
scene('a-87d51a6ee9075ede',[
 'cream-cardigan lilac-mock-crop amethyst-pendant',SINGLES['octavia-master-source-v24-2.jpg'],
 GLAM[1],GLAM[0],SINGLES['octavia-master-source-v24-4.jpg'],'black-crop-tank amethyst-pendant',
 GLAM[1],GLAM[0],SINGLES['octavia-master-source-v24-2.jpg'],GLAM[1],
 'cream-cardigan amethyst-pendant',SINGLES['octavia-master-source-v24-4.jpg'],GLAM[0],
 'black-square-top plum-tailored-trousers white-sneakers amethyst-pendant',
 SINGLES['octavia-master-source-v24-2.jpg']+' black-ankle-boots',
 'purple-chunky-cardigan black-square-top amethyst-pendant'],(4,4))
scene('a-bba934904d5b2f34',[
 'cyan-wrap-swim-inspiration','cyan-wrap-swim-inspiration cyan-tie-bottom-inspiration white-open-shirt-inspiration',
 'cyan-wrap-swim-inspiration cyan-tie-bottom-inspiration',
 'cyan-wrap-swim-inspiration cyan-tie-bottom-inspiration cream-cardigan',
 'cyan-wrap-swim-inspiration cyan-tie-bottom-inspiration blue-cardigan-inspiration',
 'cyan-wrap-swim-inspiration','cyan-wrap-swim-inspiration cyan-tie-bottom-inspiration white-open-shirt-inspiration',
 'cyan-wrap-swim-inspiration cyan-tie-bottom-inspiration blue-cardigan-inspiration',
 'cyan-wrap-swim-inspiration cyan-tie-bottom-inspiration',
 'cyan-wrap-swim-inspiration cyan-tie-bottom-inspiration white-open-shirt-inspiration nude-strappy-heels',
 'blue-cardigan-inspiration','cyan-wrap-swim-inspiration cyan-tie-bottom-inspiration',
 'cyan-wrap-swim-inspiration cyan-tie-bottom-inspiration',
 'cyan-wrap-swim-inspiration cyan-tie-bottom-inspiration blue-cardigan-inspiration',
 'cyan-wrap-swim-inspiration cyan-tie-bottom-inspiration','cyan-wrap-swim-inspiration'],(4,4),status='inspiration-only',notes='Donor/remix sheet: clothing inspiration only, never identity evidence.')
scene('a-2f6f0e7eb8aa6f8c',[
 'plum-lace-bra cream-cardigan gray-knee-socks amethyst-pendant',
 'black-button-crop gray-piped-shorts amethyst-pendant',
 'plum-lace-bra plum-lace-bottom amethyst-pendant',
 'black-lace-bra black-cardigan amethyst-pendant','plum-lace-bra black-leggings amethyst-pendant',
 'plum-lace-bra plum-scoop-long amethyst-pendant','black-lace-bra dark-plaid-trousers amethyst-pendant',
 'lilac-henley plum-lace-bra blue-ripped-jeans amethyst-pendant',
 'black-lace-bra black-lace-bottom amethyst-pendant',
 'plum-lace-bra cream-cardigan lilac-socks amethyst-pendant'],(5,2),notes='Neutral garment inventory of an earlier underwear reference sheet; not a brief for new imagery.')

for name in ['octavia-all-core-generation-images-4x3.png','octavia-all-generation-images-contact-sheet.png',
             'octavia-preview-all-core-chat.jpg','octavia-preview-genesis-chat.jpg']:
    scene(name,[],status='duplicate-layout',notes='Overview/preview of individually catalogued original sources; no new garment designs added from repeated thumbnails.')

# Tight representative regions are deliberate crops of actual visible pixels.
# Hidden garment parts are never filled in or presented as known construction.
DETAILS={
 'octavia-master-source-v24-5.jpg':{'lilac-racer-crop':[0.20,0.35,0.63,0.88],'amethyst-pendant':[0.38,0.40,0.56,0.58],'black-wide-jeans':[0.63,0.55,0.97,0.98]},
 'octavia-master-source-v24-3.jpg':{'black-square-top':[0.26,0.29,0.77,0.63],'black-a-line-skirt':[0.23,0.59,0.78,0.92],'black-tights':[0.27,0.91,0.78,0.99]},
 'octavia-cyan-outfit-source-v23.jpg':{'cyan-knot-wrap':[0.40,0.22,0.54,0.38],'cyan-pleated-skirt':[0.39,0.37,0.58,0.56],'black-loafers':[0.43,0.83,0.63,0.99]},
 'octavia-lilac-cardigan-source-v23.jpg':{'lilac-cardigan':[0.31,0.18,0.82,0.44]},
 'octavia-master-source-v24-4.jpg':{'cream-square-long':[0.34,0.14,0.59,0.42],'black-pleated-skirt':[0.34,0.39,0.61,0.61],'red-shoulder-bag':[0.54,0.31,0.63,0.47],'black-ankle-boots':[0.41,0.82,0.62,0.99]},
 'octavia-master-source-v24-1.jpg':{'cream-cardigan':[0.36,0.16,0.62,0.63],'charcoal-trousers':[0.36,0.37,0.61,0.92]},
}
for row in SOURCES:
    for ob in row['observations']:
        if ob['item'] in DETAILS.get(row['asset'],{}):
            ob['box']=DETAILS[row['asset']][ob['item']]
        if row.get('status')=='inspiration-only':
            ob['confidence']='inspiration'
        elif ob['item'] in ('forest-contrast-top',) and row['asset']=='octavia-fused-reference-outfit-v31.png':
            ob['confidence']='possible-match'
            ob['notes']='Only the pale ribbed waistband motif is visible; not evidence that the complete green top is worn.'


def manifest():
    return {'schema_version':1,'reviewer':'assistant visual audit, 2026-09-11',
            'scope':'All 89 original assets at audit start; previews and contact-sheet duplicates are explicitly marked.',
            'items':ITEMS,'sources':SOURCES}


if __name__=='__main__':
    dest=Path(__file__).parent/'production'/'wardrobe-audit-20260911.json'
    write_once(dest,json.dumps(manifest(),indent=2).encode())
    print(dest)
