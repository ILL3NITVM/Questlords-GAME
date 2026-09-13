"""Explicit, repeatable import of this conversation, never unrelated home folders."""
import json
from pathlib import Path
import re

from .storage import digest, now, packed, write_once

CONVERSATION='01a07f9e-c104-7081-b623-5457bec1de02'
EXTENSIONS={'.png','.jpg','.jpeg','.webp','.tif','.tiff'}


def classify(path):
    name=path.name.lower()
    if 'zuza' in name and name.endswith('-zuza.jpg'):
        return 'legacy-references','inspiration'
    if any(s in name for s in ('source','identity-')):
        return 'legacy-references','reference'
    if any(s in name for s in ('sheet','proof-16','uniform-pose','head-angle-hue')):
        return 'legacy-sheets','legacy-sheet'
    if 'preview' in name:
        return 'legacy-archive','preview'
    match=re.search(r'-v(\d+)[a-z]?(?:\.|-)',name)
    if match:
        return 'legacy-v'+match.group(1),'portrait'
    return 'legacy-archive','portrait'


def add_document(studio,path):
    data=path.read_bytes()
    sha=digest(data)
    dest=studio.root/'documents'/sha[:2]/(sha+path.suffix)
    write_once(dest,data)
    text=data.decode('utf-8',errors='replace')
    found=re.search(r'^Status:\s*(.+)$',text,re.M)
    status=found.group(1)[:500] if found else 'unspecified'
    kind='prompt' if 'prompt' in path.name else 'research' if 'research' in path.name else 'brief'
    with studio.db:
        studio.db.execute('INSERT OR IGNORE INTO documents VALUES(?,?,?,?,?,?,?)',
                          ('doc-'+digest((str(path)+sha).encode())[:16],str(path),sha,
                           str(dest.relative_to(studio.root)),kind,status,now()))


def seed_library(studio,workspace):
    config=json.loads((Path(__file__).parent/'seed.json').read_text())
    if studio.db.execute("SELECT 1 FROM audit WHERE action='seed_v1'").fetchone():
        legacy_date='2026-09-08 (conversation reference, approximate)'
        if studio.db.execute('SELECT 1 FROM wardrobe WHERE first_seen=?',(legacy_date,)).fetchone():
            backup=studio.backup()
            with studio.db:
                studio.db.execute('UPDATE wardrobe SET first_seen=? WHERE first_seen=?',('2026-09-08',legacy_date))
                studio.log('date_normalization','wardrobe',{'basis':'Approximate original conversation date, formatted ISO','backup':str(backup)})
        return
    studio.backup()
    with studio.db:
        studio.db.execute('INSERT INTO canon_revisions(created,reason,identity) VALUES(?,?,?)',
                          (now(),'Imported existing user master brief; no new numerical measurements',packed(config['identity'])))
        for item in config['wardrobe']:
            item=dict(item)
            item.setdefault('notes','Description from references, not measured specifications or verified textile composition.')
            item.setdefault('canon_status','established-reference' if item['ownership']=='established' else 'candidate')
            item['first_seen']='2026-09-08'
            keys=list(item)
            studio.db.execute('INSERT OR IGNORE INTO wardrobe('+','.join(keys)+') VALUES('+','.join('?' for _ in keys)+')',list(item.values()))
        for outfit in config['outfits']:
            studio.db.execute('INSERT OR IGNORE INTO outfits VALUES(?,?,?)',(outfit['outfit_id'],outfit['name'],'Reference combination, not automatic canon promotion'))
            for item in outfit['items']:
                studio.db.execute('INSERT OR IGNORE INTO outfit_items VALUES(?,?)',(outfit['outfit_id'],item))
        for room in config['rooms']:
            studio.db.execute('INSERT OR IGNORE INTO rooms VALUES(?,?,?,?,?)',
                              (room['room_id'],room['name'],room['architecture'],room.get('furniture',''),room.get('notes','')))
        for pack in config['texture_packs']:
            studio.db.execute('INSERT OR IGNORE INTO texture_packs VALUES(?,?,?,?)',
                              (pack['texture_pack_id'],pack['room_id'],pack['name'],packed(pack['treatment'])))
    for filename in config['established_references']:
        origin=studio.db.execute('SELECT asset_id FROM origins WHERE path=?',(str(workspace/filename),)).fetchone()
        if origin:
            with studio.db:
                studio.db.execute("UPDATE assets SET canon_status='reference' WHERE asset_id=? AND canon_status='unreviewed'",(origin[0],))
                studio.log('existing_reference',origin[0],{'evidence':'User master brief/existing reference-sheet selection','filename':filename})
    for filename,values in config['annotations'].items():
        origin=studio.db.execute('SELECT asset_id FROM origins WHERE path=?',(str(workspace/filename),)).fetchone()
        if origin:
            studio.annotate(origin[0],values,'Visual review in this conversation; manual observations, not prompt assertions')
    # Establish explicit edit lineage from the saved corrected versions without guessing prompt outcomes.
    for before,after in [('octavia-ten-reference-conservatory-v37.png','octavia-ten-reference-conservatory-v37b.png'),
                         ('octavia-reclaimed-fashion-synthesis-v36.png','octavia-reclaimed-fashion-synthesis-v36b.png'),
                         ('octavia-walking-full-remix-v32.png','octavia-walking-profile-v32b.png')]:
        rows=[studio.db.execute('SELECT asset_id FROM origins WHERE path=?',(str(workspace/name),)).fetchone() for name in (before,after)]
        if all(rows):
            with studio.db:
                studio.db.execute('INSERT OR IGNORE INTO asset_links VALUES(?,?,?)',(rows[1][0],rows[0][0],'legacy-generation-edit'))
    with studio.db:
        studio.log('seed_v1','project',{'source':'seed.json','references_only':True})


def bootstrap(studio,workspace,include_attachments=True):
    workspace=Path(workspace).expanduser().resolve()
    sources=[]
    for path in sorted(workspace.glob('octavia*')):
        if path.is_file() and path.suffix.lower() in EXTENSIONS:
            shoot,kind=classify(path)
            sources.append((path,shoot,'legacy-workspace',kind))
        elif path.is_file() and path.suffix=='.md':
            add_document(studio,path)
    raw=workspace/'.codex/generated_images'/CONVERSATION
    recovery=workspace/'octavia-codex-recovery-20260908-093432/generated_images'
    for folder,source in ((raw,'generation-original'),(recovery,'recovery-copy')):
        if folder.exists():
            sources.extend((p,'legacy-archive',source,'unclassified') for p in sorted(folder.iterdir()) if p.suffix.lower() in EXTENSIONS)
    attachments=Path('/tmp/codex-remote-attachments')/CONVERSATION
    if include_attachments and attachments.exists():
        sources.extend((p,'inbox','conversation-attachment','unclassified') for p in sorted(attachments.rglob('*')) if p.suffix.lower() in EXTENSIONS)
    before=studio.db.execute('SELECT COUNT(*) FROM assets').fetchone()[0]
    errors=[]
    imported=[]
    for path,shoot,source,kind in sources:
        try:
            imported.append(studio.import_image(path,shoot,source,kind))
        except (OSError,ValueError) as exc:
            errors.append({'path':str(path),'error':str(exc)})
    seed_library(studio,workspace)
    # A stable current collection containing both reviewed original v37 outputs.
    studio.shoot('conservatory-037','Conservatory continuity and pose correction',
                 ['room_id','outfit_id','framing','expression','hair_state'])
    for filename in ('octavia-ten-reference-conservatory-v37.png','octavia-ten-reference-conservatory-v37b.png'):
        row=studio.db.execute('SELECT asset_id FROM origins WHERE path=?',(str(workspace/filename),)).fetchone()
        if row:
            with studio.db:
                studio.db.execute('INSERT OR IGNORE INTO shoot_assets VALUES(?,?)',('conservatory-037',row[0]))
    total=studio.db.execute('SELECT COUNT(*) FROM assets').fetchone()[0]
    result={'scanned_images':len(sources),'new_assets':total-before,'unique_assets':total,
            'exact_duplicate_paths_reused':len(imported)-len(set(imported)),'errors':errors,
            'originals_modified':0,'scope':'Octavia-prefixed workspace files and this conversation only',
            'existing_artifacts':'Portraits, reference sheets, previews, prompts, research, raw generations and recovery copies',
            'date_basis':'Import time is precise; legacy creation time is source filesystem mtime, not a claimed render date.'}
    return dict(studio.report('migration','legacy-archive',result,
                             'Scanned {} images; {} new / {} unique assets; {} errors. Originals unchanged.\nExact duplicates use shared storage; unknown sources remain unreviewed.'.format(
                                 len(sources),total-before,total,len(errors))),**result)
