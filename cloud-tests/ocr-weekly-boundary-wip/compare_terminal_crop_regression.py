#!/usr/bin/env python3
"""WIP only: compare all 304 source crop geometries to pinned Android baseline."""
import csv, io, json, re, sys, zipfile
from collections import defaultdict
from pathlib import Path

TOKEN=re.compile(r"^\([1-9][0-9]?(?:,[1-9][0-9]?){0,2}\)[;:,.]?$",re.ASCII)
FIX={'11-11-26':'H05','02-11-26':'V01','21-10-26':'V01'}
FIELDS=('left','top','right','bottom')

def read(path):
    root=Path(path)
    with (root/'manifest.csv').open(encoding='utf8',newline='') as f:
        manifest=list(csv.DictReader(f))
    assert len(manifest)==19,('fixture count',len(manifest))
    all={}
    for item in manifest:
        date=item['date']
        with zipfile.ZipFile(root/item['zip']) as z:
            assert z.testzip() is None,('bad ZIP CRC',date)
            rows=list(csv.DictReader(io.StringIO(z.read('crop_coordinates.csv').decode())))
            assert len({r['key'] for r in rows})==16,('candidate count',date)
            rects=defaultdict(list)
            for r in rows:
                assert r['status']=='REVIEW_ONLY'
                rects[r['key']].append(tuple(float(r[f]) for f in FIELDS))
        all[date]={'sha':item['source_sha256'],'rects':dict(rects)}
    assert len(all)==19
    return all

def weak_words(root,date):
    lines=(Path(root)/('geometry-'+date+'.tsv')).read_text().splitlines()
    size=None;tokens=[]
    for line in lines:
        p=line.split('\t')
        if p[0]=='IMAGE':size=tuple(map(int,p[1].split('x')))
        if len(p)>=4 and p[0]=='WORD' and 15<=int(p[2])<=19 and TOKEN.fullmatch(p[1]):
            tokens.append({'text':p[1],'confidence':int(p[2]),
                           'box':tuple(map(int,p[3].split(',')))})
    assert size,('missing dimensions',date)
    return size,tokens

def contains(word,rects,size):
    x=(word['box'][0]+word['box'][2])/2/size[0]
    y=(word['box'][1]+word['box'][3])/2/size[1]
    return any(a<=x<c and b<=y<d for a,b,c,d in rects)

def compare(before,after,output):
    old=read(before);new=read(after)
    assert old.keys()==new.keys(),('fixture dates changed')
    stable=0;improved=[]
    for date in sorted(old):
        assert old[date]['sha']==new[date]['sha'],('source mismatch',date)
        assert old[date]['rects'].keys()==new[date]['rects'].keys(),('candidate keys changed',date)
        size,tokens=weak_words(after,date)
        target=FIX.get(date)
        assert len(tokens)==int(target is not None),('unexpected low-confidence marker',date,tokens)
        for key,rects in old[date]['rects'].items():
            newer=new[date]['rects'][key]
            if key!=target:
                assert rects==newer,('unrelated crop changed',date,key,rects,newer)
                stable+=1
            else:
                token=tokens[0]
                assert not contains(token,rects,size),('old crop included marker already',date,key)
                assert contains(token,newer,size),('marker still excluded after fix',date,key)
                improved.append({'date':date,'key':key,'terminal':token['text'],
                                 'old_parts':len(rects),'new_parts':len(newer),
                                 'word_box':list(token['box'])})
    assert stable==301 and len(improved)==3,(stable,improved)
    summary={'sources_verified':19,'review_only_proposals':304,
             'three_fixed_terminal_crops':improved,'unrelated_crops_identical':stable,
             'missing_terminal_before':3,'missing_terminal_after':0,
             'full_visual_accuracy':'NOT_PROVEN_BY_GEOMETRY_TEST',
             'firebase_writes':0,'canonical_writes':0,'release_modified':False}
    Path(output).write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

def self_test():
    assert TOKEN.fullmatch('(3);') and TOKEN.fullmatch('(3):')
    assert TOKEN.fullmatch('(5,3);')
    assert not TOKEN.fullmatch('3.') and not TOKEN.fullmatch('(3),2.')
    token={'box':(100,100,120,120)}
    assert contains(token,[(.095,.095,.125,.125)],(1000,1000))
    assert not contains(token,[(.12,.095,.2,.125)],(1000,1000))
    print('PASS terminal grammar and rectangle containment tests')

if __name__=='__main__':
    if sys.argv[1:]==['--self-test']: self_test()
    elif len(sys.argv)==4: compare(*sys.argv[1:])
    else: raise SystemExit('Usage: compare_terminal_crop_regression.py --self-test OR baseline current report.json')
