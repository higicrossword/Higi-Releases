#!/usr/bin/env python3
"""Read-only WIP: independent ownership and integrity QA for pinned Android OCR crops."""
import csv,io,json,re,sys,zipfile
from collections import Counter,defaultdict
from pathlib import Path

TEXT=re.compile(r'[\u0590-\u05ff0-9()]')
ENUM=re.compile(r'^\((?:[0-9]{1,2}|[0-9]{1,2}(?:[,/][0-9]{1,2}){1,3})\)\s*[.;:,!?]?$',re.ASCII)
KNOWN_WEAK={('09-09-26','V08'),('19-10-26','V07'),('28-10-26','H06'),
            ('30-09-26','V07'),('30-09-26','V12')}

def geometry(raw):
    size=None;grid=None;words=[]
    for line in raw.splitlines():
        parts=line.split('\t')
        if parts[0]=='IMAGE':
            size=tuple(map(int,parts[1].split('x')))
            grid=int(parts[2].split('=')[1])
        elif parts[0]=='WORD' and len(parts)>=4:
            words.append((parts[1],int(parts[2]),tuple(map(int,parts[3].split(',')))))
    assert size and grid, 'Missing source geometry'
    return (*size,grid,words)

def check(artifact,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    totals=Counter();errors=[];no_enum=set();per_source=[]
    with zipfile.ZipFile(artifact) as root:
        manifest=list(csv.DictReader(io.StringIO(root.read('ocr-cloud-v209/manifest.csv').decode())))
        assert len(manifest)==19
        for item in manifest:
            date=item['date']
            w,h,grid,words=geometry(root.read('ocr-cloud-v209/geometry-'+date+'.tsv').decode())
            with zipfile.ZipFile(io.BytesIO(root.read('ocr-cloud-v209/'+item['zip']))) as inner:
                assert inner.testzip() is None, ('Bad inner ZIP',date)
                coords=list(csv.DictReader(io.StringIO(inner.read('crop_coordinates.csv').decode())))
            rects={'H':defaultdict(list),'V':defaultdict(list)}
            for row in coords:
                assert row['status']=='REVIEW_ONLY'
                r=tuple(float(row[k]) for k in ('left','top','right','bottom'))
                key=row['key'];rects[key[0]][key].append(r)
                if key.startswith('H') and r[2]*w>=grid:
                    errors.append((date,key,'GRID_INTRUSION'))
            keys=set(rects['H'])|set(rects['V'])
            assert len(keys)==16 and int(item['proposed'])==16
            ends=Counter();count=0
            for text,confidence,(a,b,c,d) in words:
                if confidence<15 or not TEXT.search(text):continue
                x=(a+c)/2/w;y=(b+d)/2/h
                if not (.31<y<.95):continue
                direction='H' if .31<=x<=.68 else ('V' if 0<=x<.31 else None)
                if not direction:continue
                count+=1
                matched=[key for key,rs in rects[direction].items()
                         if any(x0<=x<x1 and y0<=y<y1 for x0,y0,x1,y1 in rs)]
                if len(matched)!=1:
                    errors.append((date,text,confidence,'OWNER_COUNT',len(matched)))
                    continue
                key=matched[0]
                # Require the ENTIRE original OCR bounding box in a single piece.
                if not any(x0*w<=a and y0*h<=b and c<=x1*w and d<=y1*h
                           for x0,y0,x1,y1 in rects[direction][key]):
                    errors.append((date,key,text,confidence,'CLIPPED_WORD'))
                if ENUM.fullmatch(text.strip()):ends[key]+=1
            for key in keys:
                if ends[key]==0:no_enum.add((date,key))
                elif ends[key]!=1:errors.append((date,key,'DUPLICATE_ENUM_TOKEN',ends[key]))
            totals['source_images']+=1;totals['review_only_crops']+=len(keys)
            totals['recognized_words_checked']+=count
            per_source.append({'date':date,'crops':len(keys),'source_ocr_words_checked':count,
                'no_clean_ocr_enum':sorted(key for key in keys if ends[key]==0)})
    if totals['recognized_words_checked']!=2206 or totals['review_only_crops']!=304:
        errors.append(('OCR_BASELINE_CHANGED',dict(totals)))
    if no_enum!=KNOWN_WEAK:errors.append(('WEAK_ENUM_CASES_CHANGED',sorted(no_enum)))
    result={'totals':dict(totals),'fully_contained_ocr_words':totals['recognized_words_checked']-
           sum('CLIPPED_WORD' in e for e in errors),
           'ambiguous_or_unowned_ocr_words':sum('OWNER_COUNT' in e for e in errors),
           'unverified_by_clean_ocr_enum':sorted(no_enum),
           'errors':errors,'visual_correctness_of_unrecognized_glyphs':'NOT_ESTABLISHED',
           'per_source':per_source,'releases_created':0,'canonical_writes':0,'firebase_writes':0}
    (out/'full-word-coverage-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='per_source'},ensure_ascii=False,indent=2))
    assert not errors,('WIP OCR ownership regression',errors[:8])

def self_test():
    assert ENUM.fullmatch('(3);') and ENUM.fullmatch('(5,3).')
    assert not ENUM.fullmatch('3.') and not ENUM.fullmatch('הגדרה')
    assert TEXT.search('מילה') and TEXT.search('(3):')
    assert len(KNOWN_WEAK)==5
    print('PASS WIP OCR word-box audit self-tests')

if __name__=='__main__':
    if sys.argv[1:]==['--self-test']:self_test()
    elif len(sys.argv)==3:check(sys.argv[1],sys.argv[2])
    else:raise SystemExit('Usage: audit_full_word_coverage.py --self-test OR artifact.zip output-folder')
