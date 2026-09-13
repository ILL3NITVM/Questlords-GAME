"""Reference-only Claude handoff; all non-reference media stays outside the ZIP."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from octavia_studio.storage import Studio, file_hash, now, write_once

REFERENCES=(
    'a-06304fd46f0a0b92', 'a-4aa958e7e4279df5', 'a-632be75ba22ce38a',
    'a-7cf41694da9b4f14', 'a-2a28a323025d1af3', 'a-c23c860ec74a2b02',
)
TEXT={'.py','.md','.json','.jsonl','.txt','.xml','.log'}


def encoded(value):
    return (json.dumps(value,indent=2,sort_keys=True)+'\n').encode()


def copy_rows(db,table,rows):
    for row in rows:
        keys=list(row)
        db.execute('INSERT INTO "'+table+'" ('+','.join('"'+k+'"' for k in keys)+') '
                   'VALUES ('+','.join('?' for _ in keys)+')',[row[k] for k in keys])


def build(destination):
    destination=Path(destination).resolve()
    if destination.exists():
        raise ValueError('Choose a new destination; existing handoffs are never replaced')
    destination.parent.mkdir(parents=True,exist_ok=True)
    data=ROOT/'octavia_studio'/'data'
    handoff=ROOT/'octavia_studio'/'handoff'
    live=Studio(data)
    backup=live.backup()
    live.close()
    history=sqlite3.connect('file:{}?mode=ro'.format(backup),uri=True)
    history.row_factory=sqlite3.Row

    def rows(table):
        return [dict(r) for r in history.execute('SELECT * FROM "'+table+'"')]

    assets=[a for a in rows('assets') if a['asset_id'] in REFERENCES]
    if len(assets)!=len(REFERENCES):
        raise ValueError('Missing required reference assets')
    hashes={a['sha256'] for a in assets}
    blobs=[b for b in rows('blobs') if b['sha256'] in hashes]
    original_by_hash={b['sha256']:b for b in blobs}
    selected=set(REFERENCES)
    files={}

    def include(path,member=None):
        path=Path(path).resolve()
        relative=path.relative_to(ROOT)
        if not path.is_file(): raise ValueError('Missing file: '+str(path))
        member=member or relative.as_posix()
        if member.startswith('/') or '..' in Path(member).parts:
            raise ValueError('Unsafe archive path')
        if member in files and files[member]!=path:
            raise ValueError('Duplicate package member')
        files[member]=path

    include(handoff/'COMPACT_CLAUDE.md','CLAUDE.md')
    for path in ROOT.glob('octavia*'):
        if path.is_file() and path.suffix in TEXT: include(path)
    package=ROOT/'octavia_studio'
    for path in package.iterdir():
        if path.is_file() and (path.suffix in TEXT or path.name=='.gitignore'): include(path)
    for folder in ('tests','production'):
        for path in (package/folder).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix in TEXT:
                include(path)
    for name in ('COMPACT_HANDOFF.md','START_HERE.md','PROJECT_CONTEXT.md','ENGINEERING.md',
                 'snapshot.json','assets.jsonl','build_compact.py'):
        include(handoff/name)
    include(backup,'octavia_studio/handoff/history-metadata-only.sqlite3')
    for blob in blobs:
        path=data/blob['path']
        if file_hash(path)!=blob['sha256']: raise ValueError('Reference checksum mismatch')
        include(path)
    documents=rows('documents')
    for doc in documents:
        path=data/doc['archive_path']
        if file_hash(path)!=doc['sha256']: raise ValueError('Document checksum mismatch')
        include(path)
    for report in rows('reports'):
        include(report['json_path']);include(report['summary_path'])
    catalogs=list((data/'wardrobe').glob('*/catalog.json'))
    if catalogs:
        latest=max(catalogs,key=lambda p:p.stat().st_mtime)
        include(latest,'octavia_studio/handoff/wardrobe-metadata-only.json')

    with tempfile.TemporaryDirectory(prefix='octavia-compact-build-') as temporary:
        target=Studio(Path(temporary)/'data')
        with target.db:
            shoot_ids={a['shoot_id'] for a in assets}
            copy_rows(target.db,'shoots',[s for s in rows('shoots') if s['shoot_id'] in shoot_ids])
            for table in ('wardrobe','outfits','outfit_items','rooms','texture_packs','canon_revisions'):
                copy_rows(target.db,table,rows(table))
            copy_rows(target.db,'blobs',blobs)
            copy_rows(target.db,'assets',assets)
            for table,key in (('origins','asset_id'),('shoot_assets','asset_id'),
                              ('wardrobe_evidence','asset_id'),('wardrobe_reviews','asset_id')):
                records=[r for r in rows(table) if r[key] in selected]
                if table=='shoot_assets': records=[r for r in records if r['shoot_id'] in shoot_ids]
                copy_rows(target.db,table,records)
            copy_rows(target.db,'asset_links',[r for r in rows('asset_links') if r['child'] in selected and r['parent'] in selected])
            copy_rows(target.db,'documents',documents)
            target.log('compact_handoff','body-references',{
                'included_assets':list(REFERENCES),'originals_deleted':False,
                'history':'Full metadata lives in handoff/history-metadata-only.sqlite3',
                'scope':'Fresh reference-only catalog; original catalog and canon decisions unchanged'})
        target.shoot('handoff-body-references','Core body and identity references')
        with target.db:
            target.db.executemany('INSERT INTO shoot_assets VALUES(?,?)',
                                 [('handoff-body-references',aid) for aid in REFERENCES])
        if target.db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or target.rows('PRAGMA foreign_key_check'):
            raise ValueError('Reference-only database integrity failed')
        target.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        active=target.root/'studio.sqlite3'
        target.close()
        files['octavia_studio/data/studio.sqlite3']=active
        index={'included_photos':[
            {'asset_id':a['asset_id'],'original_filename':a['original_filename'],
             'canon_status':a['canon_status'],'sha256':a['sha256'],'width':a['width'],'height':a['height'],
             'path':'octavia_studio/data/'+original_by_hash[a['sha256']]['path']} for a in assets],
            'omitted_media':'All other photos, generations, sheets, exports and wardrobe preview crops.',
            'original_workspace_modified':False}
        images=[name for name in files if Path(name).suffix.lower() in {'.png','.jpg','.jpeg','.webp','.gif','.tif','.tiff'}]
        if len(images)!=6: raise ValueError('Unexpected image count in compact handoff')
        inventory=[{'path':name,'bytes':path.stat().st_size,'sha256':file_hash(path)}
                   for name,path in sorted(files.items())]
        manifest={'created':now(),'mode':'reference-only','photo_count':6,'files':inventory,
                  'omitted_asset_ids':[a['asset_id'] for a in rows('assets') if a['asset_id'] not in selected],
                  'canon_promotions':0,'original_deletions':0,'active_database_integrity':'PASS'}
        history.close()
        archive=Path(temporary)/'compact.zip'
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for name,path in sorted(files.items()):
                if name=='octavia_studio/data/studio.sqlite3':
                    info=zipfile.ZipInfo.from_file(path,name)
                    info.external_attr=(0o100644 << 16)
                    z.writestr(info,path.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
                else:
                    z.write(path,name)
            z.writestr('octavia_studio/handoff/included-references.json',encoded(index))
            z.writestr('octavia_studio/handoff/compact-manifest.json',encoded(manifest))
        with zipfile.ZipFile(archive) as z:
            for entry in inventory:
                if hashlib.sha256(z.read(entry['path'])).hexdigest()!=entry['sha256']:
                    raise ValueError('Packaged file mismatch: '+entry['path'])
            if z.testzip(): raise ValueError('ZIP checksum failure')
        write_once(destination,archive.read_bytes())
    result={'archive':str(destination),'bytes':destination.stat().st_size,
            'sha256':file_hash(destination),'photos':6,'verified_files':len(inventory)+2,
            'original_photos_deleted':0}
    write_once(destination.with_suffix('.sha256'),(result['sha256']+'  '+destination.name+'\n').encode())
    write_once(handoff/('compact-result-'+result['sha256'][:12]+'.json'),encoded(result))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default=str(ROOT/'octavia-claude-handoff-compact.zip'))
    args=parser.parse_args()
    print(json.dumps(build(args.output),indent=2))
