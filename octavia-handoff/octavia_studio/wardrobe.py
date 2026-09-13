"""Evidence-based garment catalog. Visual labels are reviewed data, not a detector."""
import html
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .imaging import decode, valid_box
from .storage import digest, identifier, now, packed, write_once


def font(size=15):
    try:
        return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', size)
    except OSError:
        return ImageFont.load_default()


def atlas(studio):
    """Review all original assets, including sheets and compressed reference aliases."""
    assets = studio.rows('SELECT * FROM assets WHERE recipe_key IS NULL ORDER BY original_filename,asset_id')
    pages = []
    for start in range(0, len(assets), 20):
        selected = assets[start:start + 20]
        canvas = Image.new('RGB', (1400, 2080), '#f3f3f3')
        draw = ImageDraw.Draw(canvas)
        for i, asset in enumerate(selected):
            im = decode(studio.path(asset).read_bytes()).convert('RGB')
            im.thumbnail((340, 355))
            x, y = (i % 4) * 350, (i // 4) * 416
            canvas.paste(im, (x + (350-im.width)//2, y))
            draw.text((x+5, y+358), '{} {}'.format(start+i+1, asset['asset_id']), font=font(14), fill='black')
            name = asset['original_filename']
            draw.text((x+5, y+378), name[:38], font=font(12), fill='black')
            draw.text((x+5, y+394), name[38:], font=font(12), fill='black')
        aid = studio.derivative(canvas, [a['asset_id'] for a in selected], 'sheet',
                                {'purpose':'wardrobe-audit','page':start//20+1})
        pages.append({'asset_id':aid,'path':str(studio.path(studio.get(aid)))})
    return {'pages':pages,'originals':len(assets)}


def ingest(studio, path):
    """Validate the entire batch before changing SQLite; never promote ownership."""
    data = json.loads(Path(path).read_text())
    if data.get('schema_version') != 1:
        raise ValueError('Unsupported wardrobe manifest')
    reviewer = data.get('reviewer', '').strip()
    if not reviewer:
        raise ValueError('An explicit reviewer is required')
    known = {r['wardrobe_item_id'] for r in studio.rows('SELECT wardrobe_item_id FROM wardrobe')}
    new = []
    for item in data.get('items', []):
        identifier(item['id'])
        if not item.get('name') or item.get('category') not in ('top','bottom','dress','outerwear','footwear','accessory','hosiery','one-piece'):
            raise ValueError('Item name and a supported category are required')
        if item['id'] in known:
            continue
        known.add(item['id']); new.append(item)
    evidence, reviews = [], []
    for row in data.get('sources', []):
        asset = studio.get(row['asset'])
        studio.path(asset)
        grid = row.get('grid', [1,1])
        if len(grid)!=2 or any(not isinstance(x,int) or not 1<=x<=8 for x in grid):
            raise ValueError('Grid must contain two integers from 1 to 8')
        for obs in row.get('observations', []):
            item_id = obs['item']
            if item_id not in known:
                raise ValueError('Unknown garment: '+item_id)
            cell = obs.get('cell', 1)
            if not isinstance(cell,int) or not 1<=cell<=grid[0]*grid[1]:
                raise ValueError('Invalid sheet cell')
            box = valid_box(obs.get('box', [0,0,1,1]))
            col, rr = (cell-1)%grid[0], (cell-1)//grid[0]
            region = valid_box([(col+box[0])/grid[0],(rr+box[1])/grid[1],
                                (col+box[2])/grid[0],(rr+box[3])/grid[1]])
            confidence = obs.get('confidence', 'visible-design')
            if confidence not in ('visible-design','possible-match','inspiration'):
                raise ValueError('Invalid observation confidence')
            evidence.append((item_id,asset['asset_id'],packed(region),confidence,
                             obs.get('notes','Visible design only; exact fibre, brand, size and hidden construction unknown.')))
        status = row.get('status','reviewed-visible')
        if status not in ('reviewed-visible','duplicate-layout','inspiration-only','partial'):
            raise ValueError('Invalid source review status')
        reviews.append((asset['asset_id'], status, row.get('notes','Assistant visual inspection; garment matches are design families, not physical-object verification.')))
    backup = studio.backup()
    with studio.db:
        for item in new:
            first = next((e[1] for e in evidence if e[0]==item['id']), None)
            if first is None:
                raise ValueError('Every new item needs visible source evidence: '+item['id'])
            studio.db.execute('''INSERT INTO wardrobe(wardrobe_item_id,name,category,material,primary_color,
                secondary_color,fit,source_reference,first_seen,canon_status,ownership,notes)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                (item['id'],item['name'],item['category'],item.get('material','Visual appearance only; fibre unknown'),
                 item.get('color','unknown'),item.get('secondary_color',''),item.get('fit','visible design'),
                 first,now(),'candidate','inspiration' if item.get('inspiration') else 'candidate',
                 item.get('notes','Catalogued from visual evidence; not an ownership or canon approval.')))
        for item, asset, region, confidence, notes in evidence:
            eid = 'we-'+digest(packed([item,asset,region]).encode())[:20]
            studio.db.execute('INSERT OR IGNORE INTO wardrobe_evidence VALUES(?,?,?,?,?,?,?,?)',
                              (eid,item,asset,region,confidence,reviewer,notes,now()))
        for asset, status, notes in reviews:
            studio.db.execute('INSERT OR IGNORE INTO wardrobe_reviews VALUES(?,?,?,?,?)',
                              (asset,status,reviewer,notes,now()))
        studio.log('wardrobe_ingest',str(path),{'new_items':len(new),'observations':len(evidence),'backup':str(backup),'reviewer':reviewer})
    return {'new_items':len(new),'observations':len(evidence),'sources':len(reviews),'ownership_changed':False,'backup':str(backup)}


def evidence_for(studio, item):
    return studio.rows('SELECT e.*,a.original_filename,a.sha256 FROM wardrobe_evidence e JOIN assets a USING(asset_id) '
                       'WHERE wardrobe_item_id=? ORDER BY e.created,e.evidence_id',(item,))


def catalog(studio):
    """Portable HTML/JSON with one contextual crop per item; no synthesized surfaces."""
    items = studio.rows('SELECT * FROM wardrobe ORDER BY category,name')
    entries, parents = [], []
    for item in items:
        observations = evidence_for(studio,item['wardrobe_item_id'])
        entry = dict(item, observations=observations, preview=None)
        if observations:
            # Prefer explicit garment regions over broad full-frame observations.
            def area(e):
                b=json.loads(e['region']); return (b[2]-b[0])*(b[3]-b[1])
            ev=min(observations,key=lambda e:(e['confidence']=='possible-match',area(e)))
            asset=studio.get(ev['asset_id']); im=decode(studio.path(asset).read_bytes())
            b=json.loads(ev['region'])
            pixels=(int(b[0]*im.width),int(b[1]*im.height),max(int(b[0]*im.width)+1,int(b[2]*im.width)),max(int(b[1]*im.height)+1,int(b[3]*im.height)))
            crop=im.crop(pixels)
            aid=studio.derivative(crop,[asset['asset_id']],'wardrobe-detail',
                                 {'item':item['wardrobe_item_id'],'region':b,'evidence':ev['evidence_id'],'purpose':'contextual evidence, not an isolated product photo'})
            entry['preview']={'asset_id':aid,'path':str(studio.path(studio.get(aid))),'region':b,'source':asset['asset_id']}
            parents.append(aid)
        entries.append(entry)
    key=digest(packed(entries).encode())[:16]
    dest=studio.root/'wardrobe'/key
    cards=[]
    for entry in entries:
        preview=entry['preview']; image_html=''
        if preview:
            source=Path(preview['path'])
            name=entry['wardrobe_item_id']+source.suffix
            write_once(dest/'items'/name,source.read_bytes())
            image_html='<img loading="lazy" src="items/{}" alt="{}">'.format(name,html.escape(entry['name']))
            entry['preview']['portable_path']='items/'+name
        cards.append('<article>'+image_html+'<h2>'+html.escape(entry['name'])+'</h2><p>'+html.escape(entry['wardrobe_item_id'])+'</p><p>'+html.escape(entry['ownership'])+' | '+str(len(entry['observations']))+' observations</p><details><summary>Source evidence</summary>'+''.join('<p>'+html.escape(e['asset_id']+' | '+e['confidence']+' | '+e['notes'])+'</p>' for e in entry['observations'])+'</details></article>')
    document='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Octavia Wardrobe</title><style>body{font:15px system-ui;margin:24px;color:#222;background:#f5f5f7}header{max-width:1000px}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}article{background:white;padding:12px;border:1px solid #ddd;border-radius:6px;min-width:0}img{width:100%;height:280px;object-fit:contain;background:#eee}h1{font-size:28px}h2{font-size:17px}p{overflow-wrap:anywhere}summary{cursor:pointer}details{font-size:12px}</style><header><h1>Octavia Wardrobe</h1><p>One record per visible garment design. Contextual reference crops, not reconstructed product photographs. New entries remain candidates; sizes, fibres and hidden details are unknown.</p></header><main>'''+''.join(cards)+'</main></html>'
    write_once(dest/'index.html',document.encode())
    write_once(dest/'catalog.json',json.dumps({'schema_version':1,'items':entries},indent=2).encode())
    coverage=studio.rows('SELECT status,COUNT(*) AS count FROM wardrobe_reviews GROUP BY status')
    report={'items':len(items),'evidence':studio.db.execute('SELECT COUNT(*) FROM wardrobe_evidence').fetchone()[0],
            'reviewed_sources':studio.db.execute('SELECT COUNT(*) FROM wardrobe_reviews').fetchone()[0],
            'coverage':coverage,'output':str(dest/'index.html'),'json':str(dest/'catalog.json')}
    with studio.db:
        studio.log('wardrobe_catalog',key,report)
    return report
