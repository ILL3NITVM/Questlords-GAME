"""Phone-friendly command surface. All operations are local and non-generative."""
import argparse
import io
import itertools
import json
import os
from pathlib import Path
import sqlite3
import sys
import uuid
import zipfile

from . import __version__
from . import jobs
from .imaging import POLISH_DEFAULTS, PRESETS, valid_box
from .migration import bootstrap, EXTENSIONS
from .outputs import export_one, sheet
from .review import continuity, curate, accept_review
from .storage import Studio, file_hash, identifier, now, packed, write_once


def parser():
    p=argparse.ArgumentParser(description='Octavia Studio: preserve, review, polish, curate and export.')
    p.add_argument('--data',default=os.environ.get('OCTAVIA_DATA',str(Path(__file__).parent/'data')))
    p.add_argument('--json',action='store_true',help='Machine-readable output')
    p.add_argument('--version',action='version',version=__version__)
    commands=p.add_subparsers(dest='command',required=True)
    def command(name,help):
        sub=commands.add_parser(name,help=help)
        sub.add_argument('--json',action='store_true',default=argparse.SUPPRESS)
        return sub
    command('status','Compact studio status')
    init=command('init','Import the existing project once; safe to repeat')
    init.add_argument('--workspace',default=str(Path(__file__).resolve().parents[1]))
    init.add_argument('--no-attachments',action='store_true')
    imp=command('import','Copy images into immutable storage, deduplicating exact bytes')
    imp.add_argument('paths',nargs='+')
    imp.add_argument('--shoot',default='inbox')
    imp.add_argument('--recursive',action='store_true')
    imp.add_argument('--source',default='manual-import')
    asset=command('asset','List, show or annotate an asset')
    ac=asset.add_subparsers(dest='action',required=True)
    li=ac.add_parser('list');li.add_argument('--shoot');li.add_argument('--limit',type=int,default=15)
    show=ac.add_parser('show');show.add_argument('asset')
    ann=ac.add_parser('annotate');ann.add_argument('asset');ann.add_argument('--file')
    for field in ('pose','framing','expression','hair-state','outfit-id','room-id','texture-pack-id','notes'):
        ann.add_argument('--'+field)
    ann.add_argument('--pendant',choices=['present','absent','unknown'])
    ann.add_argument('--hair-roi',type=box_arg);ann.add_argument('--subject-roi',type=box_arg)
    ann.add_argument('--evidence',default='User-reviewed annotation')
    canon=command('canon','Identity rules and explicit canon review')
    cc=canon.add_subparsers(dest='action',required=True)
    cc.add_parser('show');cc.add_parser('references')
    approve=cc.add_parser('approve');approve.add_argument('asset');approve.add_argument('--reason',required=True)
    approve.add_argument('--allow-derivative',action='store_true')
    revision=cc.add_parser('revise');revision.add_argument('--file',required=True);revision.add_argument('--reason',required=True)
    shoot=command('shoot','List or assemble shoots from existing assets')
    sc=shoot.add_subparsers(dest='action',required=True)
    sc.add_parser('list')
    create=sc.add_parser('create');create.add_argument('shoot');create.add_argument('--name');create.add_argument('--allow-repeat',default='')
    add=sc.add_parser('add');add.add_argument('shoot');add.add_argument('assets',nargs='+')
    for name in ('continuity','curate'):
        sub=command(name,'Review original shoot assets; no canon changes');sub.add_argument('target',nargs='?',default='latest')
    review=command('review','Record human acceptance of explained continuity candidates')
    review.add_argument('asset');review.add_argument('--shoot',required=True);review.add_argument('--reason',required=True)
    review.add_argument('--reviewer',choices=['human','assistant'],default='human')
    for name in ('polish','process'):
        sub=command(name,'Checkpointed '+name+' job; all originals preserved')
        sub.add_argument('target',nargs='?',default='latest')
        for field in ('denoise','sharpen','exposure','contrast','shadows','highlights'):
            sub.add_argument('--'+field,type=float,default=POLISH_DEFAULTS[field])
        sub.add_argument('--no-sharpen',dest='sharpen',action='store_const',const=0.0)
        sub.add_argument('--wb',type=gains_arg,default=[1.,1.,1.])
        sub.add_argument('--max-side',type=int,default=0)
        sub.add_argument('--format',choices=['png','jpeg'],default='png')
        sub.add_argument('--quality',type=int,default=95)
        sub.add_argument('--background',action='store_true')
        if name=='process':
            sub.add_argument('--grid',default='4x4');sub.add_argument('--export',default='instagram-portrait')
    resume=command('resume','Resume an interrupted/failed job without reprocessing completed assets')
    resume.add_argument('job');resume.add_argument('--background',action='store_true')
    js=command('jobs','List jobs and checkpoint progress')
    js.add_argument('--limit',type=int,default=8)
    sh=command('sheet','Build paginated contact sheets without cropping')
    sh.add_argument('--shoot',required=True);sh.add_argument('--grid',default='4x4')
    sh.add_argument('--no-labels',action='store_true')
    sh.add_argument('--mode',choices=['all','identity-only','body/pose','wardrobe','hair','room','expression'],default='all')
    ex=command('export','Export locally with safe padding or a reviewed crop')
    ex.add_argument('target');ex.add_argument('--preset',choices=list(PRESETS)+['all'],default='instagram-portrait')
    ex.add_argument('--fit',choices=['contain','crop'],default='contain');ex.add_argument('--box',type=box_arg)
    wardrobe=command('wardrobe','Independent garment records and recombination suggestions')
    wc=wardrobe.add_subparsers(dest='action',required=True)
    wc.add_parser('list')
    wc.add_parser('atlas')
    wc.add_parser('catalog')
    wi=wc.add_parser('ingest');wi.add_argument('file')
    we=wc.add_parser('evidence');we.add_argument('id')
    ws=wc.add_parser('show');ws.add_argument('id')
    wa=wc.add_parser('add');wa.add_argument('id');wa.add_argument('--name',required=True);wa.add_argument('--category',required=True)
    for key in ('material','primary-color','secondary-color','fit','source-reference','notes'):
        wa.add_argument('--'+key)
    wa.add_argument('--ownership',choices=['established','inspiration','candidate'],default='inspiration')
    wa.add_argument('--canon-status',default='candidate')
    comb=wc.add_parser('combinations');comb.add_argument('--limit',type=int,default=10)
    comb.add_argument('--include-inspiration',action='store_true')
    wu=wc.add_parser('update');wu.add_argument('id');wu.add_argument('--reason',required=True)
    wu.add_argument('--ownership',choices=['established','inspiration','candidate'])
    wu.add_argument('--canon-status');wu.add_argument('--notes')
    outfit=command('outfit','Store a combination without changing item ownership')
    oc=outfit.add_subparsers(dest='action',required=True)
    oc.add_parser('list')
    oa=oc.add_parser('add');oa.add_argument('id');oa.add_argument('--name',required=True);oa.add_argument('--items',required=True)
    room=command('room','Architecture separate from color/light treatments')
    rc=room.add_subparsers(dest='action',required=True)
    rc.add_parser('list')
    rs=rc.add_parser('show');rs.add_argument('id')
    ra=rc.add_parser('add');ra.add_argument('id');ra.add_argument('--name',required=True);ra.add_argument('--architecture',required=True)
    ra.add_argument('--furniture',default='');ra.add_argument('--notes',default='')
    texture=command('texture','Manage room texture packs')
    tc=texture.add_subparsers(dest='action',required=True)
    tl=tc.add_parser('list');tl.add_argument('--room')
    ta=tc.add_parser('add');ta.add_argument('id');ta.add_argument('--room',required=True);ta.add_argument('--name',required=True)
    ta.add_argument('--file',required=True,help='JSON treatment: palette, lighting, bedding, decor, plants, view, ambience')
    integrity=command('integrity','Verify every managed image and archived document')
    integrity.add_argument('--origins',action='store_true',help='Also check source paths that still exist')
    command('backup','Verified SQLite snapshot; originals already immutable')
    archive=command('archive','Write a portable shoot archive with metadata and derivatives')
    archive.add_argument('target',nargs='?',default='latest')
    return p


def box_arg(value):
    try:
        return valid_box([float(x) for x in value.split(',')])
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc))


def gains_arg(value):
    try:
        values=[float(v) for v in value.split(',')]
        if len(values)!=3:
            raise ValueError()
        return values
    except ValueError:
        raise argparse.ArgumentTypeError('Use three gains such as 1.02,1,0.98')


def load_json(path):
    return json.loads(Path(path).expanduser().read_text())


def status(studio):
    counts={}
    queries={
        'Canon':"SELECT COUNT(*) FROM assets WHERE canon_status IN ('reference','approved')",
        'Inbox':"SELECT COUNT(*) FROM assets WHERE shoot_id='inbox' AND canon_status='unreviewed'",
        'Shoots':'SELECT COUNT(*) FROM shoots',
        'Selected':"SELECT COUNT(*) FROM assets WHERE quality_status IN ('HERO','STRONG')",
        'Final':"SELECT COUNT(*) FROM assets WHERE kind='export'",
        'Wardrobe':'SELECT COUNT(*) FROM wardrobe',
        'Rooms':'SELECT COUNT(*) FROM rooms',
        'Outliers':"SELECT COUNT(*) FROM assets WHERE continuity_status='OUTLIER'",
        'Assets':'SELECT COUNT(*) FROM assets',
    }
    for key,sql in queries.items():
        counts[key]=studio.db.execute(sql).fetchone()[0]
    last=studio.db.execute("SELECT shoot_id FROM shoots WHERE shoot_id NOT IN ('inbox','legacy-references','legacy-sheets','legacy-archive') ORDER BY created DESC,rowid DESC LIMIT 1").fetchone()
    counts['Last shoot']=last[0] if last else '-'
    counts['Jobs']=studio.rows('SELECT job_id,status FROM jobs ORDER BY created DESC,rowid DESC LIMIT 3')
    counts['data']=str(studio.root)
    return counts


def archive(studio,target):
    assets=studio.select(target,derivatives=True)
    if not assets:
        raise ValueError('No assets to archive')
    # Include all derivative descendants even if the shoot is a collection membership.
    ids={a['asset_id'] for a in assets}
    all_assets={a['asset_id']:a for a in studio.rows('SELECT * FROM assets')}
    all_links=studio.rows('SELECT * FROM asset_links')
    changed=True
    while changed:
        changed=False
        for a in studio.rows('SELECT * FROM assets WHERE parent_asset_id IS NOT NULL'):
            if a['parent_asset_id'] in ids and a['asset_id'] not in ids:
                assets.append(a);ids.add(a['asset_id']);changed=True
        for link in all_links:
            if link['child'] in ids and link['parent'] not in ids:
                assets.append(all_assets[link['parent']]);ids.add(link['parent']);changed=True
        for a in list(assets):
            if a['parent_asset_id'] and a['parent_asset_id'] not in ids:
                parent=all_assets[a['parent_asset_id']]
                assets.append(parent);ids.add(parent['asset_id']);changed=True
    documents=studio.rows('SELECT * FROM documents')
    manifest={'schema_version':1,'assets':assets,'wardrobe':studio.rows('SELECT * FROM wardrobe'),
              'rooms':studio.rows('SELECT * FROM rooms'),'outfits':studio.rows('SELECT * FROM outfits'),
              'outfit_items':studio.rows('SELECT * FROM outfit_items'),'texture_packs':studio.rows('SELECT * FROM texture_packs'),
              'wardrobe_evidence':studio.rows('SELECT * FROM wardrobe_evidence'),
              'wardrobe_reviews':studio.rows('SELECT * FROM wardrobe_reviews'),
              'canon_revisions':studio.rows('SELECT * FROM canon_revisions'),
              'documents':documents,
              'origins':[r for r in studio.rows('SELECT * FROM origins') if r['asset_id'] in ids],
              'review_decisions':[r for r in studio.rows('SELECT * FROM review_decisions') if r['asset_id'] in ids],
              'asset_links':[r for r in studio.rows('SELECT * FROM asset_links') if r['child'] in ids],
              'sheet_members':[r for r in studio.rows('SELECT * FROM sheet_members') if r['sheet_id'] in ids]}
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_STORED) as z:
        z.writestr('manifest.json',json.dumps(manifest,indent=2))
        for doc in {r['archive_path']:r for r in documents}.values():
            path=studio.root/doc['archive_path']
            if file_hash(path)!=doc['sha256']:
                raise ValueError('Archived document integrity mismatch')
            z.write(path,doc['archive_path'])
        seen=set()
        for a in assets:
            if a['sha256'] not in seen:
                path=studio.path(a)
                z.write(path,'images/'+a['sha256']+path.suffix)
                seen.add(a['sha256'])
    data=buffer.getvalue()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if z.testzip():
            raise ValueError('Archive verification failed')
    dest=studio.root/'archives'/('shoot-'+uuid.uuid4().hex[:16]+'.zip')
    write_once(dest,data)
    backup=studio.backup()
    with studio.db:
        studio.log('archive',target,{'path':str(dest),'assets':len(assets),'backup':str(backup)})
    return {'archive':str(dest),'assets':len(assets),'backup':str(backup),'deleted':0}


def dispatch(studio,a):
    if a.command=='status':
        return status(studio)
    if a.command=='init':
        return bootstrap(studio,a.workspace,not a.no_attachments)
    if a.command=='import':
        paths=[]
        for value in a.paths:
            path=Path(value).expanduser()
            if path.is_dir():
                paths.extend(p for p in (path.rglob('*') if a.recursive else path.iterdir()) if p.suffix.lower() in EXTENSIONS)
            else:
                paths.append(path)
        if not paths:
            raise ValueError('No matching images')
        imported=[];errors=[]
        for path in sorted(paths):
            try:
                imported.append(studio.import_image(path,a.shoot,a.source))
            except (ValueError,OSError) as exc:
                errors.append({'path':str(path),'error':str(exc)})
        report=studio.report('import',a.shoot,{'assets':imported,'errors':errors},
                            '{} images cataloged; {} errors. Originals unchanged.'.format(len(imported),len(errors)))
        return dict(report,assets=imported,errors=errors)
    if a.command=='asset':
        if a.action=='list':
            rows=studio.select(a.shoot) if a.shoot else studio.rows('SELECT * FROM assets ORDER BY imported_at DESC,rowid DESC LIMIT ?',(max(1,a.limit),))
            return [{k:r[k] for k in ('asset_id','original_filename','kind','canon_status','quality_status')} for r in rows[:max(1,a.limit)]]
        row=studio.get(a.asset)
        if a.action=='show':
            row['path']=str(studio.path(row));row['origins']=studio.rows('SELECT * FROM origins WHERE asset_id=?',(row['asset_id'],))
            for field in ('state','metrics','pose'):
                row[field]=json.loads(row[field])
            return row
        values=load_json(a.file) if a.file else {}
        for field in ('framing','expression','hair_state','outfit_id','room_id','texture_pack_id','notes'):
            if getattr(a,field) is not None:
                values[field]=getattr(a,field)
        if a.pose is not None:
            values['pose']=[x.strip() for x in a.pose.split(',') if x.strip()]
        if a.pendant:
            values['pendant_present']={'present':True,'absent':False,'unknown':None}[a.pendant]
        for field in ('hair_roi','subject_roi'):
            if getattr(a,field):
                values.setdefault('state',{})[field]=getattr(a,field)
        studio.annotate(row['asset_id'],values,a.evidence)
        return {'annotated':row['asset_id'],'fields':list(values),'canon_changed':False}
    if a.command=='canon':
        if a.action=='references':
            return studio.rows("SELECT asset_id,original_filename,canon_status FROM assets WHERE canon_status IN ('reference','approved')")
        if a.action=='show':
            row=studio.db.execute('SELECT * FROM canon_revisions ORDER BY revision_id DESC LIMIT 1').fetchone()
            return json.loads(row['identity']) if row else {'message':'Run init to import the existing canon'}
        if a.action=='approve':
            studio.approve(a.asset,a.reason,a.allow_derivative)
            return {'approved':studio.get(a.asset)['asset_id'],'reason':a.reason}
        identity=load_json(a.file)
        if not isinstance(identity,dict) or not a.reason.strip():
            raise ValueError('Identity must be a JSON object with an explicit revision reason')
        if set(identity)&{'outfit_id','room_id','pose','hair_state','expression','lighting','texture_pack_id'}:
            raise ValueError('Transient state does not belong in identity canon')
        backup=studio.backup()
        with studio.db:
            studio.db.execute('INSERT INTO canon_revisions(created,reason,identity) VALUES(?,?,?)',(now(),a.reason,packed(identity)))
            studio.log('canon_revision','Octavia',{'reason':a.reason,'backup':str(backup)})
        return {'revision':studio.db.execute('SELECT MAX(revision_id) FROM canon_revisions').fetchone()[0]}
    if a.command=='shoot':
        if a.action=='list':
            return studio.rows('SELECT s.shoot_id,s.name,COUNT(sa.asset_id) AS assets FROM shoots s LEFT JOIN shoot_assets sa USING(shoot_id) GROUP BY s.shoot_id ORDER BY s.created DESC,s.rowid DESC')
        studio.shoot(a.shoot,getattr(a,'name',None),getattr(a,'allow_repeat','').split(',') if getattr(a,'allow_repeat','') else [])
        if a.action=='add':
            with studio.db:
                for value in a.assets:
                    studio.db.execute('INSERT OR IGNORE INTO shoot_assets VALUES(?,?)',(a.shoot,studio.get(value)['asset_id']))
                studio.log('shoot_membership',a.shoot,{'assets':a.assets})
        return {'shoot':a.shoot,'assets':len(studio.select(a.shoot))}
    if a.command=='continuity':
        return continuity(studio,a.target)
    if a.command=='curate':
        return curate(studio,a.target)
    if a.command=='review':
        return accept_review(studio,a.asset,a.shoot,a.reviewer+' review: '+a.reason)
    if a.command in ('polish','process'):
        from .imaging import validate_polish
        options={'polish':validate_polish({k:getattr(a,k) for k in POLISH_DEFAULTS})}
        if a.command=='process':
            presets=list(PRESETS) if a.export=='all' else a.export.split(',')
            if any(x not in PRESETS for x in presets):
                raise ValueError('Unknown export preset')
            options.update(grid=a.grid,exports=presets)
        job=jobs.create(studio,a.command,a.target,options)
        if a.background:
            return {'job_id':job,'pid':jobs.launch(studio,job),'status':'launched','resume':'python3 octavia.py resume '+job}
        return jobs.run(studio,job)
    if a.command=='resume':
        if a.background:
            return {'job_id':a.job,'pid':jobs.launch(studio,a.job),'status':'launched'}
        return jobs.run(studio,a.job)
    if a.command=='jobs':
        return studio.rows('SELECT j.job_id,j.kind,j.target,j.status,j.error,COUNT(i.asset_id) AS total,'
                          "SUM(CASE WHEN i.status='complete' THEN 1 ELSE 0 END) AS done FROM jobs j LEFT JOIN job_items i USING(job_id) "
                          'GROUP BY j.job_id ORDER BY j.created DESC,j.rowid DESC LIMIT ?',(max(1,a.limit),))
    if a.command=='sheet':
        return sheet(studio,a.shoot,a.grid,not a.no_labels,a.mode)
    if a.command=='export':
        presets=list(PRESETS) if a.preset=='all' else [a.preset]
        assets=studio.select(a.target)
        results=[export_one(studio,r['asset_id'],preset,a.fit,a.box) for r in assets for preset in presets if preset!='reference-sheet']
        if 'reference-sheet' in presets:
            if all(r['kind'] in ('sheet','legacy-sheet') for r in assets):
                sheets=assets
            else:
                sheets=sheet(studio,a.target,'4x4',False)['pages']
            results.extend(export_one(studio,r['asset_id'],'reference-sheet') for r in sheets)
        return results
    if a.command=='wardrobe':
        from . import wardrobe
        if a.action=='atlas':
            return wardrobe.atlas(studio)
        if a.action=='catalog':
            return wardrobe.catalog(studio)
        if a.action=='ingest':
            return wardrobe.ingest(studio,a.file)
        if a.action=='evidence':
            return wardrobe.evidence_for(studio,a.id)
        if a.action=='list':
            return studio.rows('SELECT wardrobe_item_id,name,category,ownership,canon_status FROM wardrobe ORDER BY category,name')
        if a.action=='show':
            row=studio.rows('SELECT * FROM wardrobe WHERE wardrobe_item_id=?',(a.id,))
            if not row:
                raise ValueError('Unknown garment')
            row[0]['appearances']=studio.rows('SELECT a.asset_id,a.shoot_id FROM assets a JOIN outfit_items i USING(outfit_id) WHERE i.wardrobe_item_id=?',(a.id,))
            return row[0]
        if a.action=='add':
            identifier(a.id)
            fields=['name','category','material','primary_color','secondary_color','fit','source_reference','ownership','canon_status','notes']
            with studio.db:
                studio.db.execute('INSERT INTO wardrobe(wardrobe_item_id,first_seen,'+','.join(fields)+') VALUES('+','.join('?' for _ in range(len(fields)+2))+')',
                                  [a.id,now()]+[getattr(a,k) or '' for k in fields])
                studio.log('wardrobe_add',a.id,{'ownership':a.ownership,'source_reference':a.source_reference})
            return {'wardrobe_item_id':a.id,'ownership':a.ownership}
        if a.action=='update':
            rows=studio.rows('SELECT * FROM wardrobe WHERE wardrobe_item_id=?',(a.id,))
            if not rows or not a.reason.strip():
                raise ValueError('Existing garment and a review reason required')
            values={k:getattr(a,k) for k in ('ownership','canon_status','notes') if getattr(a,k) is not None}
            if not values:
                raise ValueError('Specify a field to update')
            backup=studio.backup()
            with studio.db:
                studio.db.execute('UPDATE wardrobe SET '+','.join(k+'=?' for k in values)+' WHERE wardrobe_item_id=?',list(values.values())+[a.id])
                studio.log('wardrobe_review',a.id,{'before':rows[0],'after':values,'reason':a.reason,'backup':str(backup)})
            return {'wardrobe_item_id':a.id,'changed':values}
        rows=studio.rows('SELECT * FROM wardrobe'+('' if a.include_inspiration else " WHERE ownership='established'"))
        groups=[[r['wardrobe_item_id'] for r in rows if r['category']==cat] for cat in ('top','bottom','outerwear','footwear')]
        choices=[list(c) for c in itertools.islice(itertools.product(*groups),min(100,max(1,a.limit)))]
        return {'combinations':choices,'basis':'Garment category compatibility, not aesthetic ranking','ownership_changed':False}
    if a.command=='outfit':
        if a.action=='list':
            return studio.rows('SELECT * FROM outfits')
        identifier(a.id)
        with studio.db:
            studio.db.execute('INSERT INTO outfits VALUES(?,?,?)',(a.id,a.name,''))
            for item in a.items.split(','):
                studio.db.execute('INSERT INTO outfit_items VALUES(?,?)',(a.id,item.strip()))
            studio.log('outfit_add',a.id,{'items':a.items})
        return {'outfit':a.id}
    if a.command=='room':
        if a.action=='list':
            return studio.rows('SELECT * FROM rooms')
        if a.action=='show':
            rows=studio.rows('SELECT * FROM rooms WHERE room_id=?',(a.id,))
            if not rows:
                raise ValueError('Unknown room')
            rows[0]['texture_packs']=studio.rows('SELECT * FROM texture_packs WHERE room_id=?',(a.id,))
            return rows[0]
        identifier(a.id)
        with studio.db:
            studio.db.execute('INSERT INTO rooms VALUES(?,?,?,?,?)',(a.id,a.name,a.architecture,a.furniture,a.notes))
            studio.log('room_add',a.id,{'architecture':a.architecture})
        return {'room':a.id}
    if a.command=='texture':
        if a.action=='list':
            return studio.rows('SELECT * FROM texture_packs'+(' WHERE room_id=?' if a.room else ''),(a.room,) if a.room else ())
        identifier(a.id)
        treatment=load_json(a.file)
        if not isinstance(treatment,dict):
            raise ValueError('Texture treatment must be a JSON object')
        with studio.db:
            studio.db.execute('INSERT INTO texture_packs VALUES(?,?,?,?)',(a.id,a.room,a.name,packed(treatment)))
            studio.log('texture_add',a.id,{'room':a.room,'treatment':treatment})
        return {'texture_pack':a.id,'room':a.room}
    if a.command=='integrity':
        errors=[]
        blobs=studio.rows('SELECT * FROM blobs')
        for row in blobs:
            try:
                if file_hash(studio.root/row['path'])!=row['sha256']:
                    errors.append(row['path']+': hash mismatch')
            except OSError as exc:
                errors.append(str(exc))
        documents=studio.rows('SELECT * FROM documents')
        for row in documents:
            try:
                if file_hash(studio.root/row['archive_path'])!=row['sha256']:
                    errors.append(row['archive_path']+': document hash mismatch')
            except OSError as exc:
                errors.append(str(exc))
        db_check=studio.db.execute('PRAGMA integrity_check').fetchone()[0]
        origins_checked=0;missing_origins=[]
        if a.origins:
            for row in studio.rows('SELECT o.path,a.sha256 FROM origins o JOIN assets a USING(asset_id)'):
                path=Path(row['path'])
                if not path.exists():
                    missing_origins.append(str(path))
                elif file_hash(path)!=row['sha256']:
                    errors.append(str(path)+': source path content changed since import (managed original retained)')
                else:
                    origins_checked+=1
        foreign=studio.rows('PRAGMA foreign_key_check')
        return {'blobs_checked':len(blobs),'documents_checked':len(documents),'database':db_check,
                'foreign_key_errors':foreign,'errors':errors,
                'origins_checked':origins_checked,'missing_origins':missing_origins,
                'status':'PASS' if not errors and not foreign and db_check=='ok' else 'FAIL'}
    if a.command=='backup':
        return {'backup':str(studio.backup())}
    if a.command=='archive':
        return archive(studio,a.target)
    raise ValueError('Unsupported command')


def display(result,command):
    if command=='status':
        print('OCTAVIA STUDIO')
        for key in ('Canon','Inbox','Shoots','Selected','Final','Wardrobe','Rooms','Outliers','Assets','Last shoot'):
            print('{:12}{}'.format(key+':',result[key]))
        for job in result['Jobs']:
            print('Job:        {} {}'.format(job['job_id'],job['status']))
        return
    if isinstance(result,list):
        for row in result:
            if 'path' in row and 'asset_id' in row:
                print('{} {}'.format(row['asset_id'],row['path']))
            else:
                print(' | '.join(str(v) for v in row.values() if not isinstance(v,(dict,list))))
        return
    if isinstance(result,dict):
        if 'combinations' in result:
            for i,combo in enumerate(result['combinations'],1):
                print('{}: {}'.format(i,' + '.join(combo)))
            print('Suggestions only; ownership unchanged.')
            return
        for key in ('job_id','status','new_assets','unique_assets','scanned_images','counts','annotated','approved','shoot','wardrobe_item_id','room','texture_pack','archive','backup','output','summary','json'):
            if key in result:
                print('{}: {}'.format(key,result[key]))
        if 'ranking' in result:
            for row in result['ranking'][:8]:
                print('{} {}'.format(row['label'],row['asset_id']))
        if 'pages' in result:
            for page in result['pages']:
                print('Sheet: '+page['path'])
        if result.get('errors'):
            print('Errors: '+packed(result['errors']))
        if not any(k in result for k in ('job_id','summary','ranking','pages','status','annotated','approved','shoot','archive','backup','room','wardrobe_item_id','texture_pack')):
            print(json.dumps(result,indent=2))


def main(argv=None):
    a=parser().parse_args(argv)
    studio=None
    try:
        studio=Studio(a.data)
        result=dispatch(studio,a)
        if a.json:
            print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))
        else:
            display(result,a.command)
        return 1 if isinstance(result,dict) and (result.get('errors') or result.get('status')=='FAIL') else 0
    except KeyboardInterrupt:
        print('Paused. Use jobs, then resume <job-id>.',file=sys.stderr)
        return 130
    except (ValueError,OSError,sqlite3.Error) as exc:
        print('Octavia: '+str(exc),file=sys.stderr)
        return 2
    finally:
        if studio:
            studio.close()
