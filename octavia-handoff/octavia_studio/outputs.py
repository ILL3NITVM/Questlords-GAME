"""Versioned sheets, polish reports and safe platform exports."""
import json
import math
import re

from PIL import Image, ImageDraw

from .imaging import comparison, decode, metrics, polish_image, safe_export, tile, validate_polish
from .storage import packed


def polish_one(studio,asset_id,options):
    a=studio.get(asset_id)
    options=validate_polish(options)
    before=decode(studio.path(a).read_bytes())
    after,meta=polish_image(before,options)
    out=studio.derivative(after,[asset_id],'polished',options,meta,
                         '.jpg' if options['format']=='jpeg' else '.png')
    preview=studio.derivative(comparison(before,after),[asset_id,out],'before_after',{'style':'side-by-side-v1'})
    changes={k:v for k,v in options.items() if (k=='wb' and v!=[1.,1.,1.]) or
             (k not in ('wb','format','quality') and v)}
    content={'source_asset_id':asset_id,'output_asset_id':out,'preview_asset_id':preview,
             'source_sha256':a['sha256'],'output_sha256':studio.get(out)['sha256'],
             'operations':options,'changed':changes,'before':metrics(before),'after':metrics(after),
             'preserved':['original bytes','face/body geometry','field of view','aspect ratio','parent lineage'],
             'metadata_policy':'Original metadata archived. Derivative: safe authorship/capture EXIF, normalized orientation/dimensions, sRGB ICC. GPS/thumbnail dropped.',
             'limitations':['Tone remapping cannot recover clipped JPEG/PNG detail.',
                            'Processing is 8-bit photographic polish, not RAW development.'],
             'output':str(studio.path(studio.get(out))),'preview':str(studio.path(studio.get(preview)))}
    summary='{} -> {}\n\nChanged: {}\n\nPreserved: original bytes, geometry, framing and lineage.\n\nBefore/after: {}'.format(
        asset_id,out,packed(changes),content['preview'])
    return dict(studio.report('polish',a['shoot_id'],content,summary),asset_id=out,preview=preview,output=content['output'])


def export_one(studio,asset_id,preset,fit='contain',box=None):
    a=studio.get(asset_id)
    if preset=='reference-sheet' and a['kind'] not in ('sheet','legacy-sheet'):
        raise ValueError('Reference-sheet export requires a sheet asset; build a sheet first')
    state=json.loads(a['state'])
    box=box if box is not None else state.get('subject_roi')
    output,meta,detail=safe_export(decode(studio.path(a).read_bytes()),preset,fit,box)
    out=studio.derivative(output,[asset_id],'export',detail,meta,'.jpg')
    path=str(studio.path(studio.get(out)))
    result={'asset_id':out,'parent_asset_id':asset_id,'path':path,'crop':detail,'uploaded':False}
    report=studio.report('export',a['shoot_id'],result,
                        '{}: {}\n\n{}; no upload.\n\n{}'.format(preset,out,detail.get('reason',detail['fit']),path))
    return dict(result,**report)


def sheet(studio,target,grid='4x4',labels=True,mode='all',assets=None):
    match=re.fullmatch(r'([1-8])x([1-8])',grid)
    if not match:
        raise ValueError('Grid must be columns x rows, each 1..8')
    cols,rows=map(int,match.groups())
    assets=studio.select(target) if assets is None else assets
    if mode=='identity-only':
        assets=[a for a in assets if a['canon_status'] in ('reference','approved')]
    elif mode=='body/pose':
        assets=[a for a in assets if a['framing'] in ('full-body','3/4','half-body')]
    elif mode in ('wardrobe','hair','room','expression'):
        key={'wardrobe':'outfit_id','hair':'hair_state','room':'room_id','expression':'expression'}[mode]
        assets=sorted([a for a in assets if a[key]],key=lambda a:(a[key],a['asset_id']))
    elif mode!='all':
        raise ValueError('Unknown sheet mode')
    if not assets:
        raise ValueError('No assets match sheet mode; annotate the required fields first')
    pages=[]
    count=cols*rows
    for page in range(math.ceil(len(assets)/count)):
        group=assets[page*count:(page+1)*count]
        cw,ch,gap=320,440,8
        canvas=Image.new('RGB',(cols*cw+(cols+1)*gap,rows*ch+(rows+1)*gap),(244,245,246))
        draw=ImageDraw.Draw(canvas)
        members=[]
        for index,a in enumerate(group):
            image=decode(studio.path(a).read_bytes())
            x=gap+(index%cols)*(cw+gap)
            y=gap+(index//cols)*(ch+gap)
            height=ch-24 if labels else ch
            canvas.paste(tile(image,(cw,height)),(x,y))
            if labels:
                draw.text((x+5,y+ch-19),a['asset_id'],fill=(30,30,30))
            members.append({'asset_id':a['asset_id'],'position':index,'row':index//cols,'column':index%cols,
                            'bounds':[x,y,x+cw,y+height]})
        recipe={'grid':grid,'labels':labels,'mode':mode,'page':page+1,'members':members}
        out=studio.derivative(canvas,[a['asset_id'] for a in group],'sheet',recipe)
        with studio.db:
            for m in members:
                studio.db.execute('INSERT OR IGNORE INTO sheet_members VALUES(?,?,?,?)',
                                  (out,m['asset_id'],m['position'],packed(m['bounds'])))
        pages.append({'asset_id':out,'path':str(studio.path(studio.get(out))),'members':members})
    report=studio.report('sheet',studio.target_shoot(target),{'pages':pages,'grid':grid,'labels':labels,'mode':mode},
                        '{} images on {} page(s), {} grid. Labels {}. IDs retained in JSON and database.\n\n{}'.format(
                            len(assets),len(pages),grid,'on' if labels else 'off','\n'.join(p['path'] for p in pages)))
    return dict(report,pages=pages)
