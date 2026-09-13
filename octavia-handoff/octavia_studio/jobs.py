"""Detached, checkpointed jobs with process-lifetime advisory locks."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import sqlite3

from .storage import now, packed
from .outputs import export_one, polish_one, sheet
from .review import continuity, curate


def create(studio,kind,target,options):
    target=studio.resolve_target(target)
    assets=studio.select(target)
    if not assets:
        raise ValueError('No assets in target')
    job_id='j-'+uuid.uuid4().hex[:12]
    request={'options':options,'assets':[{'asset_id':a['asset_id'],'sha256':a['sha256']} for a in assets]}
    with studio.db:
        studio.db.execute('INSERT INTO jobs(job_id,kind,target,request,status,created,updated) VALUES(?,?,?,?,?,?,?)',
                          (job_id,kind,target,packed(request),'pending',now(),now()))
        for a in assets:
            studio.db.execute('INSERT INTO job_items(job_id,asset_id) VALUES(?,?)',(job_id,a['asset_id']))
    return job_id


def launch(studio,job_id):
    logs=studio.root/'logs'
    logs.mkdir(exist_ok=True)
    entry=Path(__file__).resolve().parents[1]/'octavia.py'
    with open(logs/(job_id+'.log'),'ab',buffering=0) as out:
        process=subprocess.Popen([sys.executable,str(entry),'--data',str(studio.root),'resume',job_id],
                                 stdout=out,stderr=out,stdin=subprocess.DEVNULL,start_new_session=True,
                                 close_fds=True,cwd=str(entry.parent))
    return process.pid


def run(studio,job_id):
    row=studio.db.execute('SELECT * FROM jobs WHERE job_id=?',(job_id,)).fetchone()
    if not row:
        raise ValueError('Unknown job')
    request=json.loads(row['request'])
    directory=studio.root/'locks'
    directory.mkdir(exist_ok=True)
    with open(directory/(job_id+'.lock'),'a') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Job is already running')
        if row['status']=='complete':
            return json.loads(row['result'])
        with studio.db:
            studio.db.execute("UPDATE jobs SET status='running',pid=?,updated=?,error=NULL WHERE job_id=?",
                              (os.getpid(),now(),job_id))
        try:
            # Snapshot inputs; a resumed job never silently switches source content.
            assets=[]
            for source in request['assets']:
                a=studio.get(source['asset_id'])
                if a['sha256']!=source['sha256']:
                    raise ValueError('Job input hash changed')
                studio.path(a)
                assets.append(a)
            review=continuity(studio,row['target'],assets) if row['kind']=='process' else None
            results=[]
            for source in request['assets']:
                aid=source['asset_id']
                item=studio.db.execute('SELECT * FROM job_items WHERE job_id=? AND asset_id=?',(job_id,aid)).fetchone()
                if item['status']=='complete':
                    result=json.loads(item['result'])
                    studio.path(studio.get(result['asset_id']))
                    results.append(result)
                    continue
                try:
                    result=polish_one(studio,aid,request['options'].get('polish',{}))
                    with studio.db:
                        studio.db.execute("UPDATE job_items SET status='complete',result=?,error=NULL WHERE job_id=? AND asset_id=?",
                                          (packed(result),job_id,aid))
                    results.append(result)
                except Exception as exc:
                    with studio.db:
                        studio.db.execute("UPDATE job_items SET status='failed',error=? WHERE job_id=? AND asset_id=?",
                                          (str(exc),job_id,aid))
                    raise
            output={'job_id':job_id,'polished':results,'preserved':'All original bytes and lineage; no canon promotion'}
            if row['kind']=='process':
                # Reports analyze original shoot members; derivatives cannot bias diversity counts.
                selection=curate(studio,row['target'],assets)
                sheets=sheet(studio,row['target'],request['options'].get('grid','4x4'),False,assets=assets)
                output.update(continuity=review,curation=selection,sheets=sheets)
                output['continuity_details']=json.loads(Path(review['json']).read_text())
                exports=[]
                chosen=[r for r in selection['ranking'] if r['label'] in ('HERO','STRONG')][:3]
                for r in chosen:
                    result=next(x for x in results if studio.get(x['asset_id'])['parent_asset_id']==r['asset_id'])
                    for preset in request['options'].get('exports',['instagram-portrait']):
                        if preset!='reference-sheet':
                            exports.append(export_one(studio,result['asset_id'],preset))
                if 'reference-sheet' in request['options'].get('exports',[]):
                    exports.extend(export_one(studio,page['asset_id'],'reference-sheet') for page in sheets['pages'])
                output['exports']=exports
                output['export_note']='Only HERO/STRONG individual images exported socially. Reference sheets retain review candidates for comparison; nothing is published.'
            summary='Job {} completed: {} polished. Originals/canon unchanged.\n\n'.format(job_id,len(results))
            if output.get('continuity'):
                summary+='Continuity: {}\n'.format(packed(output['continuity']['counts']))
                summary+='Candidates: {}\n'.format(', '.join(r['label']+' '+r['asset_id'] for r in output['curation']['ranking'][:5]))
                summary+='Exports: {}\n'.format(len(output.get('exports',[])))
                details=output['continuity_details']
                summary+='Composition/duplicate candidates: {}. Repetition signals: {}.\n'.format(len(details['pairs']),len(details['repetition']))
                for r in details['assets']:
                    if r['reasons']:
                        summary+='- {}: {}\n'.format(r['asset_id'],'; '.join(r['reasons']))
                if output.get('exports'):
                    summary+='\nExport locations:\n'+'\n'.join('- {}: {}'.format(e['crop']['preset'],e['path']) for e in output['exports'])+'\n'
            summary+='\n'+ '\n'.join(r['output'] for r in results)
            report=studio.report('shoot-processing',studio.target_shoot(row['target']),output,summary)
            output.update(report)
            with studio.db:
                studio.db.execute("UPDATE jobs SET status='complete',result=?,updated=? WHERE job_id=?",
                                  (packed(output),now(),job_id))
                studio.log('job_complete',job_id,{'report':report})
            return output
        except BaseException as exc:
            with studio.db:
                studio.db.execute('UPDATE jobs SET status=?,error=?,updated=? WHERE job_id=?',
                                  ('paused' if isinstance(exc,KeyboardInterrupt) else 'failed',str(exc),now(),job_id))
            try:
                studio.report('shoot-processing-failed',studio.target_shoot(row['target']),
                              {'job_id':job_id,'error':str(exc),'request':request,
                               'checkpoints':studio.rows('SELECT * FROM job_items WHERE job_id=?',(job_id,)),
                               'preserved':'Originals and completed derivatives retained'},
                              'Job {} paused/failed: {}\n\nResume: python3 octavia.py resume {}\nOriginals and completed outputs retained.'.format(job_id,exc,job_id))
            except (OSError,ValueError,sqlite3.Error):
                pass
            raise
