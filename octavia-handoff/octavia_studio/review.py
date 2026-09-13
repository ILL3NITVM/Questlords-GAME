"""Explainable continuity evidence and diversity-aware curation, not biometrics."""
from collections import Counter, defaultdict
import json
import math

import numpy as np

from .imaging import decode, hair_evidence
from .storage import digest, now

POSE_TAGS = ['standing','seated','walking','leaning','over-shoulder','profile','looking-away',
             'mirror-selfie','candid','relaxed','editorial']
FRAMINGS = ['close-portrait','half-body','3/4','full-body']
EXPRESSIONS = ['soft-smile','neutral','thoughtful','playful','confident','serious-editorial','laughing','looking-away']


def distance(a,b):
    return bin(int(a,16)^int(b,16)).count('1')


def analyze(studio, assets, shoot_id=None):
    if not assets:
        raise ValueError('Shoot has no matching original assets')
    records={a['asset_id']:{'asset_id':a['asset_id'],'status':'PASS','reasons':[],
                           'evidence':{},'unknown':[]} for a in assets}
    def flag(a, reason, outlier=False):
        record=records[a['asset_id']]
        record['reasons'].append(reason)
        if outlier or record['status']!='OUTLIER':
            record['status']='OUTLIER' if outlier else 'REVIEW'

    valid=[]
    for a in assets:
        record=records[a['asset_id']]
        try:
            studio.path(a)
            valid.append(a)
        except (OSError,ValueError) as exc:
            flag(a,str(exc),True)
            continue
        m=json.loads(a['metrics'])
        record['evidence']['pixels']=m
        if min(a['width'],a['height'])<512:
            flag(a,'Low source resolution; use as reference, not a large final')
        if m['highlight_clip']>0.35 or m['shadow_clip']>0.65:
            flag(a,'Extreme encoded highlight/shadow clipping; inspect intended lighting',True)
        if m['sharpness']<8:
            flag(a,'Low edge detail; could be blur, a flat backdrop or intentional softness')
        for field in ('framing','expression','hair_state','pose'):
            if not a[field] or a[field]=='[]':
                record['unknown'].append(field)
        state=json.loads(a['state'])
        if state.get('pendant_applicable',True):
            if a['pendant_present'] is None:
                record['unknown'].append('pendant presence (not automatically detected)')
            elif not a['pendant_present']:
                flag(a,'Pendant recorded absent; check styling/occlusion against canon')
        if state.get('hair_roi'):
            evidence=hair_evidence(decode(studio.path(a).read_bytes()),state['hair_roi'])
            record['evidence']['hair']=evidence
            if evidence['green_fraction']<0.015:
                flag(a,'Little chartreuse color in reviewed hair region; lighting or streak drift candidate')
        else:
            record['unknown'].append('hair-streak color (no reviewed hair ROI)')
        if record['unknown']:
            flag(a,'Incomplete annotation: '+', '.join(record['unknown']))

    pairs=[]
    for i,a in enumerate(valid):
        ma=json.loads(a['metrics'])
        for b in valid[i+1:]:
            mb=json.loads(b['metrics'])
            d=distance(a['perceptual_hash'],b['perceptual_hash'])
            center=distance(ma['center_hash'],mb['center_hash'])
            similarity=float(np.dot(ma['composition_grid'],mb['composition_grid']))
            label=None
            if a['sha256']==b['sha256']:
                label='exact-duplicate'
            elif d<=6:
                label='near-duplicate'
            elif center<=4 and d<=18:
                label='similar-center-crop'
            elif similarity>0.998 and d<=16:
                label='composition-repetition'
            if label:
                pairs.append({'a':a['asset_id'],'b':b['asset_id'],'type':label,
                              'phash_distance':d,'center_distance':center,'edge_similarity':similarity})
                for asset,other in ((a,b),(b,a)):
                    flag(asset,'{} candidate with {}; visual check required'.format(label,other['asset_id']))
    # Compare color only within matching documented state, not across unrelated rooms/outfits.
    cohorts=defaultdict(list)
    for a in valid:
        if a['room_id'] and a['outfit_id'] and a['texture_pack_id'] and a['framing']:
            cohorts[(a['room_id'],a['outfit_id'],a['texture_pack_id'],a['framing'])].append(a)
    for group in cohorts.values():
        if len(group)<3:
            continue
        means=np.array([json.loads(a['metrics'])['mean_rgb'] for a in group])
        median=np.median(means,axis=0)
        for a,mean in zip(group,means):
            delta=float(np.linalg.norm(mean-median))
            records[a['asset_id']]['evidence']['matched_state_color_distance']=delta
            if delta>0.20:
                flag(a,'Unusual whole-image color drift against matching outfit/room/light state',delta>0.40)
    distributions={}
    repetitions=[]
    fields=['pose','framing','expression','hair_state','room_id','outfit_id']
    shoot=studio.db.execute('SELECT allowed_repetition FROM shoots WHERE shoot_id=?',
                            (shoot_id or assets[0]['shoot_id'],)).fetchone()
    allowed=json.loads(shoot[0]) if shoot else []
    for field in fields:
        counts=Counter()
        known=0
        for a in valid:
            values=json.loads(a[field]) if field=='pose' else [a[field]] if a[field] else []
            if values:
                known+=1
                counts.update(set(values))
        distributions[field]={'counts':dict(counts),'annotated':known,'total':len(valid)}
        for value,count in counts.items():
            if known>=3 and count/known>=0.70:
                item={'field':field,'value':value,'count':count,'annotated':known,
                      'ratio':count/known,'intentional':field in allowed}
                repetitions.append(item)
                if field not in allowed:
                    for a in valid:
                        match=value in json.loads(a['pose']) if field=='pose' else a[field]==value
                        if match:
                            flag(a,'Repeated {}={} in {}/{} annotated shots; may be intentional'.format(field,value,count,known))
    if len(valid)>=4:
        for a in valid:
            nearest=min(distance(a['perceptual_hash'],b['perceptual_hash']) for b in valid if b!=a)
            if nearest>28:
                flag(a,'Candidate visual outlier: unlike other images by perceptual hash; not identity evidence')
    for a in valid:
        record=records[a['asset_id']]
        retained=[]
        acknowledged=[]
        for reason in record['reasons']:
            key=digest((a['sha256']+'|'+reason).encode())
            decision=studio.db.execute('SELECT reason,created FROM review_decisions WHERE asset_id=? AND shoot_id=? AND issue_key=?',
                                      (a['asset_id'],shoot_id or a['shoot_id'],key)).fetchone()
            if decision and record['status']!='OUTLIER' and not reason.startswith('Incomplete annotation'):
                acknowledged.append({'issue':reason,'review_reason':decision[0],'reviewed':decision[1]})
            else:
                retained.append(reason)
        record['acknowledged']=acknowledged
        record['reasons']=retained
        if not retained:
            record['status']='PASS'
    result={'assets':list(records.values()),'pairs':pairs,'repetition':repetitions,
            'diversity':distributions,'expected_vocab':{'pose':POSE_TAGS,'framing':FRAMINGS,'expression':EXPRESSIONS},
            'limitations':['No biometric verification or inferred body measurements.',
                'Pose, room, wardrobe and pendant presence depend on explicit annotations.',
                'Hair color uses a manually reviewed ROI; plants and lighting can confound color.',
                'PASS means no flagged evidence in available checks, not verified identity.',
                'Unknown fields are REVIEW, not silently treated as passing.']}
    with studio.db:
        for record in result['assets']:
            studio.db.execute('UPDATE assets SET continuity_status=? WHERE asset_id=?',
                              (record['status'],record['asset_id']))
    return result


def accept_review(studio,asset_id,target,reason):
    if not reason.strip():
        raise ValueError('A human review reason is required')
    asset=studio.get(asset_id)
    shoot_id=studio.target_shoot(target)
    result=analyze(studio,studio.select(target),shoot_id)
    record=next((r for r in result['assets'] if r['asset_id']==asset['asset_id']),None)
    if not record:
        raise ValueError('Asset is not in the shoot')
    if record['status']=='OUTLIER' or record['unknown']:
        raise ValueError('Resolve integrity/outlier issues or missing annotations before accepting candidates')
    with studio.db:
        for issue in record['reasons']:
            key=digest((asset['sha256']+'|'+issue).encode())
            studio.db.execute('INSERT OR IGNORE INTO review_decisions VALUES(?,?,?,?,?)',
                              (asset['asset_id'],shoot_id,key,reason,now()))
        studio.log('continuity_human_review',asset['asset_id'],
                   {'shoot':shoot_id,'issues':record['reasons'],'reason':reason,'canon_changed':False})
    return {'reviewed':asset['asset_id'],'acknowledged':len(record['reasons']),'canon_changed':False}


def continuity(studio,target,assets=None):
    assets=studio.select(target) if assets is None else assets
    shoot_id=studio.target_shoot(target)
    result=analyze(studio,assets,shoot_id)
    counts=Counter(r['status'] for r in result['assets'])
    summary='Assets: {} | PASS {} | REVIEW {} | OUTLIER {}\n\n'.format(len(assets),counts['PASS'],counts['REVIEW'],counts['OUTLIER'])
    summary+='Duplicate/composition candidates: {}. Repetition signals: {}.\n'.format(len(result['pairs']),len(result['repetition']))
    for r in result['assets']:
        summary+='\n- {} {}: {}'.format(r['asset_id'],r['status'],'; '.join(r['reasons']) or 'No flags in available checks')
    report=studio.report('continuity',shoot_id,result,summary)
    return dict(report,counts=dict(counts),assets=len(assets))


def rank(studio,assets,review):
    statuses={r['asset_id']:r for r in review['assets']}
    duplicate=set()
    for p in review['pairs']:
        if p['type'] in ('exact-duplicate','near-duplicate'):
            a=next(a for a in assets if a['asset_id']==p['a'])
            b=next(a for a in assets if a['asset_id']==p['b'])
            poorer=min((a,b),key=lambda x:(x['width']*x['height'],json.loads(x['metrics'])['sharpness'],x['asset_id']))
            duplicate.add(poorer['asset_id'])
    remaining=[]
    for a in assets:
        m=json.loads(a['metrics'])
        score=35*min(1,a['width']*a['height']/1_500_000)
        score+=25*min(1,math.log1p(m['sharpness'])/math.log(301))
        score+=20*max(0,1-m['highlight_clip']-m['shadow_clip'])
        score+=20 if statuses[a['asset_id']]['status']=='PASS' else 8
        remaining.append((a,score))
    selected=[]
    pose_seen=Counter()
    framing_seen=Counter()
    while remaining:
        def adjusted(pair):
            a,score=pair
            penalty=3*framing_seen[a['framing']]+sum(3*pose_seen[v] for v in json.loads(a['pose']))
            return score-min(penalty,18)
        a,score=max(remaining,key=adjusted)
        diversity_score=adjusted((a,score))
        remaining.remove((a,score))
        r=statuses[a['asset_id']]
        reasons=list(r['reasons'])
        if min(a['width'],a['height'])<256 or any('Integrity mismatch' in x for x in reasons):
            label='REJECT-CANDIDATE'
        elif a['asset_id'] in duplicate:
            label='REFERENCE'
            reasons.append('Redundant visual candidate; keep for reference, never deleted')
        elif r['status']!='PASS':
            label='REVIEW'
        elif not any(x['label']=='HERO' for x in selected):
            label='HERO' if score>=60 else 'REFERENCE'
        else:
            label='STRONG' if diversity_score>=60 else 'REFERENCE'
        selected.append({'asset_id':a['asset_id'],'label':label,'technical_score':round(score,2),
                         'diversity_adjusted_score':round(diversity_score,2),'reasons':reasons})
        if label in ('HERO','STRONG'):
            pose_seen.update(json.loads(a['pose']))
            framing_seen[a['framing']]+=1
    return selected


def curate(studio,target,assets=None):
    assets=studio.select(target) if assets is None else assets
    shoot_id=studio.target_shoot(target)
    review=analyze(studio,assets,shoot_id)
    ranking=rank(studio,assets,review)
    with studio.db:
        for r in ranking:
            studio.db.execute('UPDATE assets SET quality_status=? WHERE asset_id=?',(r['label'],r['asset_id']))
        studio.log('curation',shoot_id,{'ranking':ranking,'deletions':0})
    summary='Technical and diversity suggestions only; no beauty score or automatic deletion.\n\n'
    summary+='\n'.join('- {} {} ({})'.format(r['label'],r['asset_id'],r['technical_score']) for r in ranking)
    report=studio.report('curation',shoot_id,{'ranking':ranking,'continuity':review,'deleted':[]},summary)
    return dict(report,ranking=ranking)
