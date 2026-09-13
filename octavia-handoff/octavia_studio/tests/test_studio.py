import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import zipfile

import numpy as np
from PIL import Image, ImageCms
import pytest

from octavia_studio.storage import Studio, file_hash, write_once
from octavia_studio.imaging import (POLISH_DEFAULTS, PRESETS, decode, encode, inspect_bytes,
                                    polish_image, safe_export, valid_box)
from octavia_studio.outputs import polish_one, sheet, export_one
from octavia_studio.review import analyze, rank, accept_review, continuity
from octavia_studio import jobs
from octavia_studio.cli import archive, main, status
from octavia_studio.migration import bootstrap


@pytest.fixture
def studio(tmp_path):
    s=Studio(tmp_path/'data')
    yield s
    s.close()


def photo(tmp_path,name='photo.png',seed=1,size=(640,960)):
    rng=np.random.RandomState(seed)
    y,x=np.mgrid[:size[1],:size[0]]
    a=np.empty((size[1],size[0],3),dtype='uint8')
    a[:,:,0]=np.clip(90+45*np.sin(x/22)+rng.normal(0,5,x.shape),0,255)
    a[:,:,1]=np.clip(140+40*np.sin(y/25)+rng.normal(0,4,x.shape),0,255)
    a[:,:,2]=np.clip(100+40*np.cos((x+y)/35),0,255)
    path=tmp_path/name
    Image.fromarray(a).save(path)
    return path


def annotated(studio,asset_id,pose=None,expression='soft-smile'):
    studio.annotate(asset_id,{'pose':pose or ['seated'],'framing':'full-body',
                            'expression':expression,'hair_state':'ponytail','pendant_present':True,
                            'state':{'hair_roi':[0,0,1,1]}})


def test_import_idempotent_and_aliases(studio,tmp_path):
    path=photo(tmp_path)
    duplicate=tmp_path/'copy.png';duplicate.write_bytes(path.read_bytes())
    first=studio.import_image(path,'shoot')
    assert studio.import_image(path,'shoot')==first
    assert studio.import_image(duplicate,'other')==first
    assert studio.db.execute('SELECT COUNT(*) FROM assets').fetchone()[0]==1
    assert studio.db.execute('SELECT COUNT(*) FROM origins').fetchone()[0]==2
    assert len(studio.select('other'))==1
    assert file_hash(path)==studio.get(first)['sha256']
    assert studio.path(studio.get(first)).stat().st_mode & 0o222 == 0


def test_changed_source_preserves_old_bytes(studio,tmp_path):
    path=photo(tmp_path)
    old=studio.import_image(path)
    old_bytes=studio.path(studio.get(old)).read_bytes()
    photo(tmp_path,seed=2)
    new=studio.import_image(path)
    assert old!=new
    assert studio.path(studio.get(old)).read_bytes()==old_bytes
    assert studio.db.execute("SELECT COUNT(*) FROM audit WHERE action='origin_changed'").fetchone()[0]==1


def test_atomic_refuses_overwrite(tmp_path):
    dest=tmp_path/'final.png'
    write_once(dest,b'original')
    write_once(dest,b'original')
    with pytest.raises(ValueError):
        write_once(dest,b'changed')
    assert dest.read_bytes()==b'original'
    assert not list(tmp_path.glob('.pending-*'))


def test_sqlite_immutable_core(studio,tmp_path):
    aid=studio.import_image(photo(tmp_path))
    with pytest.raises(sqlite3.IntegrityError):
        studio.db.execute("UPDATE assets SET sha256='bad' WHERE asset_id=?",(aid,))
    with pytest.raises(sqlite3.IntegrityError):
        studio.db.execute('DELETE FROM assets WHERE asset_id=?',(aid,))


def test_corrupt_source_not_imported(studio,tmp_path):
    p=tmp_path/'bad.jpg';p.write_bytes(b'not a photo')
    with pytest.raises(OSError):
        studio.import_image(p)
    assert studio.db.execute('SELECT COUNT(*) FROM assets').fetchone()[0]==0


def test_integrity_guard(studio,tmp_path):
    aid=studio.import_image(photo(tmp_path))
    stored=studio.path(studio.get(aid));stored.chmod(0o644);stored.write_bytes(b'changed')
    with pytest.raises(ValueError,match='Integrity mismatch'):
        studio.path(studio.get(aid))
    report=analyze(studio,[studio.get(aid)])
    assert report['assets'][0]['status']=='OUTLIER'


def test_orientation_normalized_without_touching_original(studio,tmp_path):
    p=tmp_path/'rotated.jpg'
    im=Image.new('RGB',(100,60),'green');exif=Image.Exif();exif[274]=6
    im.save(p,exif=exif)
    before=p.read_bytes()
    aid=studio.import_image(p)
    a=studio.get(aid)
    assert (a['width'],a['height'])==(60,100)
    assert p.read_bytes()==before


def test_animated_input_rejected(tmp_path):
    a=Image.new('RGB',(40,40),'red');b=Image.new('RGB',(40,40),'blue')
    p=tmp_path/'movie.gif';a.save(p,save_all=True,append_images=[b])
    with pytest.raises(ValueError,match='Animated'):
        inspect_bytes(p.read_bytes())


def test_all_operations_off_are_pixel_exact(tmp_path):
    before=decode(photo(tmp_path).read_bytes())
    after,_=polish_image(before,{'sharpen':0})
    assert np.array_equal(np.array(before),np.array(after))


@pytest.mark.parametrize('field,value',[('denoise',0.2),('sharpen',0.4),('exposure',0.2),
    ('contrast',0.1),('shadows',0.15),('highlights',0.15),('wb',[1.03,1,0.98])])
def test_independent_polish_operations(tmp_path,field,value):
    before=decode(photo(tmp_path).read_bytes())
    after,_=polish_image(before,dict({'sharpen':0},**{field:value}))
    assert after.size==before.size
    assert not np.array_equal(np.array(before),np.array(after))


@pytest.mark.parametrize('options',[{'sharpen':2},{'exposure':float('nan')},{'wb':[4,1,1]},
                                  {'denoise':-1},{'max_side':-2},{'quality':40}])
def test_polish_bounds(tmp_path,options):
    with pytest.raises(ValueError):
        polish_image(decode(photo(tmp_path).read_bytes()),options)


def test_metadata_preserved_safely_and_alpha():
    im=Image.new('RGB',(80,120),'green');exif=Image.Exif();exif[315]='Artist';exif[274]=1
    im.info['exif']=exif.tobytes()
    out,meta=polish_image(im,{'sharpen':0,'max_side':60})
    restored=decode(encode(out,'.jpg',meta))
    assert restored.getexif()[315]=='Artist'
    assert restored.getexif().get_ifd(34665)[40962]==40
    assert restored.size==(40,60)
    assert restored.info.get('icc_profile')
    rgba=Image.new('RGBA',(80,80),(100,120,140,80))
    out,_=polish_image(rgba,{'sharpen':0})
    assert out.mode=='RGBA' and out.getpixel((20,20))[3]==80


def test_invalid_icc_fails_not_silent():
    im=Image.new('RGB',(100,100),'red');im.info['icc_profile']=b'bad-profile'
    with pytest.raises(ValueError,match='ICC'):
        polish_image(im,{})


def test_derivative_lineage_not_canon(studio,tmp_path):
    aid=studio.import_image(photo(tmp_path),'s')
    studio.approve(aid,'Explicit fixture selection')
    source_hash=studio.get(aid)['sha256']
    result=polish_one(studio,aid,{})
    d=studio.get(result['asset_id'])
    assert d['parent_asset_id']==aid
    assert d['canon_status']=='derivative'
    assert studio.get(aid)['sha256']==source_hash
    with pytest.raises(ValueError,match='allow-derivative'):
        studio.approve(d['asset_id'],'Looks suitable')
    studio.approve(d['asset_id'],'Human selected derivative deliberately',True)
    assert studio.get(d['asset_id'])['canon_status']=='approved'
    assert len(list((studio.root/'backups').glob('*.sqlite3')))==2


def test_noop_derivative_stays_separate(studio,tmp_path):
    aid=studio.import_image(photo(tmp_path))
    result=polish_one(studio,aid,{'sharpen':0})
    assert result['asset_id']!=aid
    assert studio.get(result['asset_id'])['canon_status']=='derivative'


def test_derivative_is_idempotent(studio,tmp_path):
    aid=studio.import_image(photo(tmp_path),'s')
    one=polish_one(studio,aid,{})
    total=studio.db.execute('SELECT COUNT(*) FROM assets').fetchone()[0]
    two=polish_one(studio,aid,{})
    assert one['asset_id']==two['asset_id']
    assert total==studio.db.execute('SELECT COUNT(*) FROM assets').fetchone()[0]
    assert len(studio.select('s'))==1


def test_canon_not_generic_annotation(studio,tmp_path):
    aid=studio.import_image(photo(tmp_path))
    with pytest.raises(ValueError):
        studio.annotate(aid,{'canon_status':'approved'})
    studio.annotate(aid,{'hair_state':'different-hairstyle'})
    assert studio.get(aid)['canon_status']=='unreviewed'


def test_unknown_is_review_not_false_absence(studio,tmp_path):
    aid=studio.import_image(photo(tmp_path),'s')
    review=analyze(studio,[studio.get(aid)])
    r=review['assets'][0]
    assert r['status']=='REVIEW'
    assert any('not automatically detected' in x for x in r['unknown'])
    assert not any('recorded absent' in x for x in r['reasons'])


def test_pose_repetition_and_explicit_absence(studio,tmp_path):
    assets=[]
    for i in range(4):
        aid=studio.import_image(photo(tmp_path,'p{}.png'.format(i),i),'s')
        annotated(studio,aid)
        assets.append(studio.get(aid))
    studio.annotate(assets[0]['asset_id'],{'pendant_present':False})
    review=analyze(studio,studio.select('s'))
    assert any(r['field']=='pose' and r['value']=='seated' for r in review['repetition'])
    assert any('recorded absent' in s for r in review['assets'] for s in r['reasons'])
    assert review['pairs']


def test_annotated_hair_evidence(studio,tmp_path):
    p=tmp_path/'green.png';Image.new('RGB',(600,800),(140,170,65)).save(p)
    aid=studio.import_image(p,'s');annotated(studio,aid)
    review=analyze(studio,studio.select('s'))
    hair=review['assets'][0]['evidence']['hair']
    assert hair['green_fraction']>0.9
    assert 45<=hair['median_green_hue']<=105


@pytest.mark.parametrize('box',[[0,0,0,1],[-1,0,1,1],[0,0,float('nan'),1],[0,1,1,0],[0,1,2]])
def test_bad_rois(box):
    with pytest.raises(ValueError):
        valid_box(box)


def test_sheet_pagination_hidden_ids(studio,tmp_path):
    for i in range(5):
        studio.import_image(photo(tmp_path,'p{}.png'.format(i),i),'s')
    result=sheet(studio,'s','2x2',False)
    assert len(result['pages'])==2
    members=[m for p in result['pages'] for m in p['members']]
    assert len(members)==5
    assert len({m['asset_id'] for m in members})==5
    assert studio.db.execute('SELECT COUNT(*) FROM sheet_members').fetchone()[0]==5
    assert all(studio.get(p['asset_id'])['canon_status']=='derivative' for p in result['pages'])
    assert len(studio.select('s'))==5


@pytest.mark.parametrize('grid',['4x4','4x2','3x3','2x4'])
def test_requested_sheet_grids(studio,tmp_path,grid):
    studio.import_image(photo(tmp_path),'s')
    result=sheet(studio,'s',grid,False)
    cols,rows=map(int,grid.split('x'))
    with Image.open(result['pages'][0]['path']) as image:
        assert image.size==(cols*320+(cols+1)*8,rows*440+(rows+1)*8)


def test_identity_sheet_excludes_unapproved(studio,tmp_path):
    a=studio.import_image(photo(tmp_path),'s')
    studio.import_image(photo(tmp_path,'two.png',2),'s')
    studio.approve(a,'Fixture canon')
    result=sheet(studio,'s','2x2',False,'identity-only')
    assert [m['asset_id'] for m in result['pages'][0]['members']]==[a]


@pytest.mark.parametrize('preset',list(PRESETS))
def test_all_exports_are_safe_by_default(preset):
    im=Image.new('RGB',(600,1000),'green')
    out,meta,detail=safe_export(im,preset)
    assert out.size==PRESETS[preset]
    assert detail['crop_box'] is None
    assert 'exif' not in meta
    x1,y1,x2,y2=detail['placement']
    assert 0<=x1<x2<=out.width and 0<=y1<y2<=out.height


def test_safe_crop_and_fallback():
    im=Image.new('RGB',(1000,1600),'green')
    with pytest.raises(ValueError,match='ROI'):
        safe_export(im,'instagram-square','crop')
    _,_,detail=safe_export(im,'instagram-square','crop',[0.2,0.02,0.8,0.98])
    assert detail['fit']=='contain'
    _,_,detail=safe_export(im,'instagram-square','crop',[0.3,0.2,0.7,0.5])
    assert detail['fit']=='crop'
    left,top,right,bottom=detail['crop_box']
    assert left<=300 and right>=700 and top<=320 and bottom>=800


def test_export_parent_and_metadata(studio,tmp_path):
    aid=studio.import_image(photo(tmp_path),'s')
    result=export_one(studio,aid,'story')
    assert studio.get(result['asset_id'])['parent_asset_id']==aid
    assert studio.get(result['asset_id'])['canon_status']=='derivative'


def test_jobs_resume_completed_checkpoints(studio,tmp_path,monkeypatch):
    for i in range(2):
        studio.import_image(photo(tmp_path,'p{}.png'.format(i),i),'s')
    job=jobs.create(studio,'polish','s',{'polish':{}})
    real=jobs.polish_one
    calls=[]
    def failing(s,aid,options):
        calls.append(aid)
        if len(calls)==2:
            raise OSError('simulated interruption')
        return real(s,aid,options)
    monkeypatch.setattr(jobs,'polish_one',failing)
    with pytest.raises(OSError):
        jobs.run(studio,job)
    assert studio.db.execute('SELECT status FROM jobs WHERE job_id=?',(job,)).fetchone()[0]=='failed'
    assert studio.db.execute("SELECT COUNT(*) FROM job_items WHERE status='complete'").fetchone()[0]==1
    monkeypatch.setattr(jobs,'polish_one',real)
    result=jobs.run(studio,job)
    assert len(result['polished'])==2
    count=studio.db.execute('SELECT COUNT(*) FROM assets').fetchone()[0]
    assert jobs.run(studio,job)==result
    assert studio.db.execute('SELECT COUNT(*) FROM assets').fetchone()[0]==count


def test_complete_process_and_archive(studio,tmp_path):
    aid=studio.import_image(photo(tmp_path),'s')
    annotated(studio,aid)
    job=jobs.create(studio,'process','s',{'polish':{},'grid':'2x2','exports':['instagram-square']})
    result=jobs.run(studio,job)
    assert 'continuity' in result and 'curation' in result and 'sheets' in result
    # A green-region fixture may still need review; the export gate must never silently bypass it.
    if result['curation']['ranking'][0]['label']=='HERO':
        assert len(result['exports'])==1
    bundle=archive(studio,'s')
    with zipfile.ZipFile(bundle['archive']) as z:
        assert z.testzip() is None
        manifest=json.loads(z.read('manifest.json'))
        assert any(a['asset_id']==aid for a in manifest['assets'])
    assert bundle['deleted']==0


def test_bootstrap_repeat_does_not_reset_metadata(studio,tmp_path):
    workspace=tmp_path/'workspace';workspace.mkdir()
    path=photo(workspace,'octavia-master-source-v24-3.jpg')
    (workspace/'octavia-example-v1-prompt.md').write_text('Status: Blocked; no image returned.\n')
    one=bootstrap(studio,workspace,False)
    aid=studio.import_image(path,'legacy-references')
    studio.annotate(aid,{'notes':'Human correction retained'})
    two=bootstrap(studio,workspace,False)
    assert two['new_assets']==0
    assert studio.get(aid)['notes']=='Human correction retained'
    assert studio.db.execute('SELECT COUNT(*) FROM documents').fetchone()[0]==1
    assert studio.db.execute('SELECT COUNT(*) FROM canon_revisions').fetchone()[0]==1
    assert studio.db.execute('SELECT COUNT(*) FROM wardrobe').fetchone()[0]==11


def test_bad_room_pack_combination(studio,tmp_path):
    aid=studio.import_image(photo(tmp_path))
    with studio.db:
        studio.db.execute("INSERT INTO rooms VALUES('r','R','windows','','')")
        studio.db.execute("INSERT INTO rooms VALUES('s','S','stone','','')")
        studio.db.execute("INSERT INTO texture_packs VALUES('t','r','Warm','{}')")
    with pytest.raises(ValueError,match='belong'):
        studio.annotate(aid,{'room_id':'s','texture_pack_id':'t'})


def test_cli_short_commands_and_errors(tmp_path,capsys):
    data=str(tmp_path/'data')
    assert main(['--data',data,'status'])==0
    assert 'OCTAVIA STUDIO' in capsys.readouterr().out
    assert main(['--data',data,'wardrobe','add','test','--name','Test','--category','top'])==0
    s=Studio(data)
    assert s.db.execute('SELECT ownership FROM wardrobe').fetchone()[0]=='inspiration'
    s.close()
    assert main(['--data',data,'sheet','--shoot','missing'])==2
    assert main(['--data',data,'integrity','--json'])==0


def test_backup_database_integrity(studio,tmp_path):
    studio.import_image(photo(tmp_path))
    backup=studio.backup()
    with sqlite3.connect(str(backup)) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert db.execute('SELECT COUNT(*) FROM assets').fetchone()[0]==1


def test_one_pixel_import(studio,tmp_path):
    p=tmp_path/'tiny.png';Image.new('RGB',(1,1),'red').save(p)
    aid=studio.import_image(p)
    assert studio.get(aid)['width']==1


def test_empty_shoot_error(studio):
    studio.shoot('empty')
    with pytest.raises(ValueError,match='no matching'):
        continuity(studio,'empty')


def test_collection_report_context(studio,tmp_path):
    path=photo(tmp_path)
    aid=studio.import_image(path,'original-shoot')
    studio.import_image(path,'collection')
    result=continuity(studio,'collection')
    assert json.loads(Path(result['json']).read_text())['shoot_id']=='collection'


def test_resume_uses_frozen_membership_and_latest(studio,tmp_path):
    a=studio.import_image(photo(tmp_path),'s')
    job=jobs.create(studio,'process','latest',{'polish':{},'grid':'2x2','exports':[]})
    b=studio.import_image(photo(tmp_path,'later.png',2),'s')
    studio.shoot('new-latest')
    result=jobs.run(studio,job)
    assert len(result['polished'])==1
    assert studio.get(result['polished'][0]['asset_id'])['parent_asset_id']==a
    assert len(result['curation']['ranking'])==1
    report=json.loads(Path(result['json']).read_text())
    assert report['shoot_id']=='s'


def test_recovery_after_publication_before_db_commit(studio,tmp_path,monkeypatch):
    aid=studio.import_image(photo(tmp_path),'s')
    real=studio.log
    def fail(action,*args,**kwargs):
        if action=='polished':
            raise RuntimeError('simulated database interruption after publication')
        return real(action,*args,**kwargs)
    monkeypatch.setattr(studio,'log',fail)
    with pytest.raises(RuntimeError):
        polish_one(studio,aid,{})
    assert len(list((studio.root/'derivatives/polished').glob('*.png')))==1
    assert not studio.rows("SELECT * FROM assets WHERE kind='polished'")
    monkeypatch.setattr(studio,'log',real)
    out=polish_one(studio,aid,{})
    assert studio.path(studio.get(out['asset_id'])).exists()
    assert len(list((studio.root/'derivatives/polished').glob('*.png')))==1


def test_active_job_lock_blocks_second_runner(studio,tmp_path):
    import fcntl
    studio.import_image(photo(tmp_path),'s')
    job=jobs.create(studio,'polish','s',{'polish':{}})
    directory=studio.root/'locks';directory.mkdir(exist_ok=True)
    with open(directory/(job+'.lock'),'a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with pytest.raises(ValueError,match='already running'):
            jobs.run(studio,job)


def test_review_cannot_waive_unknowns(studio,tmp_path):
    aid=studio.import_image(photo(tmp_path),'s')
    with pytest.raises(ValueError,match='missing annotations'):
        accept_review(studio,aid,'s','Approve unknown fields')


def test_review_retains_evidence_without_canon_promotion(studio,tmp_path):
    ids=[]
    for i in range(2):
        aid=studio.import_image(photo(tmp_path,'p{}.png'.format(i),i),'s')
        annotated(studio,aid)
        ids.append(aid)
    before=analyze(studio,studio.select('s'),'s')
    assert before['pairs']
    accept_review(studio,ids[0],'s','Assistant review: intentional variant')
    after=analyze(studio,studio.select('s'),'s')
    r=next(r for r in after['assets'] if r['asset_id']==ids[0])
    assert r['status']=='PASS' and r['acknowledged']
    assert studio.get(ids[0])['canon_status']=='unreviewed'


def test_archive_derivative_includes_ancestor(studio,tmp_path):
    aid=studio.import_image(photo(tmp_path),'s')
    d=polish_one(studio,aid,{})['asset_id']
    result=archive(studio,d)
    with zipfile.ZipFile(result['archive']) as z:
        manifest=json.loads(z.read('manifest.json'))
        assert {aid,d} <= {r['asset_id'] for r in manifest['assets']}


def test_detached_job_completes_and_is_resumable(studio,tmp_path):
    import time
    studio.import_image(photo(tmp_path),'s')
    job=jobs.create(studio,'polish','s',{'polish':{}})
    pid=jobs.launch(studio,job)
    assert pid>0
    deadline=time.monotonic()+45
    state='pending'
    while time.monotonic()<deadline:
        state=studio.db.execute('SELECT status FROM jobs WHERE job_id=?',(job,)).fetchone()[0]
        if state in ('complete','failed'):
            break
        time.sleep(.2)
    assert state=='complete',(studio.root/'logs'/(job+'.log')).read_text()
    assert jobs.run(studio,job)['polished']


def test_nested_capture_exif_without_gps():
    im=Image.new('RGB',(100,200),'green')
    exif=Image.Exif();exif[315]='Author'
    exif[34665]={36867:'2026:09:09 12:00:00',42036:'Example lens'}
    exif[34853]={1:'N'}
    im.info['exif']=exif.tobytes()
    out,metadata=polish_image(im,{'sharpen':0})
    saved=decode(encode(out,'.jpg',metadata)).getexif()
    assert saved.get_ifd(34665)[36867]=='2026:09:09 12:00:00'
    assert saved.get_ifd(34665)[42036]=='Example lens'
    assert 34853 not in saved


def test_decode_limit_is_compact_error(tmp_path,monkeypatch):
    path=photo(tmp_path)
    monkeypatch.setattr(Image,'MAX_IMAGE_PIXELS',1000)
    with pytest.raises(ValueError,match='safe decode limit'):
        decode(path.read_bytes())


def test_narrow_roi_has_finite_evidence():
    from octavia_studio.imaging import hair_evidence
    result=hair_evidence(Image.new('RGB',(4,4),'green'),[0.1,0.1,0.11,0.11])
    assert np.isfinite(result['green_fraction'])


def test_reference_sheet_export_requires_real_sheet(studio,tmp_path):
    aid=studio.import_image(photo(tmp_path),'s')
    with pytest.raises(ValueError,match='sheet asset'):
        export_one(studio,aid,'reference-sheet')
    page=sheet(studio,'s','2x2',False)['pages'][0]
    out=export_one(studio,page['asset_id'],'reference-sheet')
    assert studio.get(out['asset_id'])['parent_asset_id']==page['asset_id']


def test_process_exports_built_sheet(studio,tmp_path):
    studio.import_image(photo(tmp_path),'s')
    job=jobs.create(studio,'process','s',{'polish':{},'grid':'2x2','exports':['reference-sheet']})
    result=jobs.run(studio,job)
    assert len(result['exports'])==1
    assert result['exports'][0]['parent_asset_id']==result['sheets']['pages'][0]['asset_id']
