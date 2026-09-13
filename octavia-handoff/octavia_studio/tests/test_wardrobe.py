import json
from pathlib import Path
import zipfile

from PIL import Image
import pytest

from octavia_studio.storage import Studio, file_hash
from octavia_studio.wardrobe import ingest, catalog, evidence_for, atlas
from octavia_studio.cli import archive


@pytest.fixture
def sample(tmp_path):
    studio=Studio(tmp_path/'data')
    source=tmp_path/'reference.png'
    Image.new('RGB',(120,160),'purple').save(source)
    aid=studio.import_image(source,'sample')
    data={'schema_version':1,'reviewer':'test human',
          'items':[{'id':'plum-jacket','name':'Plum jacket','category':'outerwear','color':'plum'}],
          'sources':[{'asset':aid,'grid':[2,2],'observations':[
              {'item':'plum-jacket','cell':2,'box':[0,0.25,1,0.75]}]}]}
    manifest=tmp_path/'manifest.json'
    manifest.write_text(json.dumps(data))
    yield studio,source,aid,manifest,data
    studio.close()


def test_evidence_import_idempotent_and_no_promotion(sample):
    s,source,aid,path,data=sample
    before=file_hash(source)
    assert ingest(s,path)['new_items']==1
    assert ingest(s,path)['new_items']==0
    ev=evidence_for(s,'plum-jacket')
    assert len(ev)==1
    assert json.loads(ev[0]['region'])==[0.5,0.125,1.0,0.375]
    item=s.rows('SELECT * FROM wardrobe')[0]
    assert item['ownership']=='candidate' and item['canon_status']=='candidate'
    assert s.get(aid)['canon_status']=='unreviewed'
    assert file_hash(source)==before


@pytest.mark.parametrize('mutation',['unknown-item','bad-box','bad-cell','bad-grid','missing-evidence'])
def test_invalid_batch_never_partly_imports(sample,mutation):
    s,source,aid,path,data=sample
    obs=data['sources'][0]['observations'][0]
    if mutation=='unknown-item': obs['item']='nonexistent'
    if mutation=='bad-box': obs['box']=[0,0,3,1]
    if mutation=='bad-cell': obs['cell']=5
    if mutation=='bad-grid': data['sources'][0]['grid']=[0,2]
    if mutation=='missing-evidence': data['sources'][0]['observations']=[]
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError): ingest(s,path)
    assert not s.rows('SELECT * FROM wardrobe')
    assert not s.rows('SELECT * FROM wardrobe_evidence')


def test_catalog_pixels_lineage_and_safe_escaping(sample):
    s,source,aid,path,data=sample
    data['items'][0]['name']='<script>not markup</script>'
    path.write_text(json.dumps(data));ingest(s,path)
    result=catalog(s)
    payload=json.loads(Path(result['json']).read_text())
    preview=payload['items'][0]['preview']
    crop=s.get(preview['asset_id'])
    assert (crop['width'],crop['height'])==(60,40)
    assert crop['parent_asset_id']==aid and crop['canon_status']=='derivative'
    assert len(s.select('sample'))==1
    assert '&lt;script&gt;' in Path(result['output']).read_text()
    assert '<script>' not in Path(result['output']).read_text()
    assert catalog(s)['output']==result['output']
    assert s.db.execute("SELECT COUNT(*) FROM assets WHERE kind='wardrobe-detail'").fetchone()[0]==1


def test_new_observation_does_not_overwrite_owned_record(sample):
    s,source,aid,path,data=sample
    ingest(s,path)
    with s.db:
        s.db.execute("UPDATE wardrobe SET ownership='established',notes='Human reviewed' WHERE wardrobe_item_id='plum-jacket'")
    data['items'][0]['name']='Different name'
    path.write_text(json.dumps(data));ingest(s,path)
    item=s.rows('SELECT * FROM wardrobe')[0]
    assert item['name']=='Plum jacket'
    assert item['ownership']=='established' and item['notes']=='Human reviewed'


def test_wardrobe_evidence_survives_archive(sample):
    s,source,aid,path,data=sample
    ingest(s,path);catalog(s)
    result=archive(s,'sample')
    with zipfile.ZipFile(result['archive']) as z:
        manifest=json.loads(z.read('manifest.json'))
        assert len(manifest['wardrobe_evidence'])==1
        assert len(manifest['wardrobe_reviews'])==1
        assert any(a['kind']=='wardrobe-detail' for a in manifest['assets'])


def test_atlas_never_becomes_new_original(sample):
    s,source,aid,path,data=sample
    result=atlas(s)
    assert result['originals']==1
    assert len(result['pages'])==1
    assert atlas(s)['originals']==1
    assert s.get(result['pages'][0]['asset_id'])['canon_status']=='derivative'
