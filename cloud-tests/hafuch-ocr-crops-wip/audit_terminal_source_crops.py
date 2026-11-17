#!/usr/bin/env python3
"""HAFUCH_DEKEL only: propose source-pixel terminal row crops WITHOUT re-running OCR.
Read-only QA. Never guess a missing printed number or approve a canonical clue.
"""
import csv,hashlib,io,json,re,sys,zipfile
from pathlib import Path
import numpy as np
from PIL import Image
from audit_bottom_ink_20 import scan,tab

SERIES='HAFUCH_DEKEL'
CLIPPED={'2026-07-31','2026-08-07'}  # frozen 20-fixture expectation, NOT geometry coordinates
NUM=re.compile(r'^([0-9]{1,2})[.,:]$')
LENGTH=re.compile(r'^\([0-9]+(?:[,;][0-9]+)*\)[.;]?$')
V={1,2,3,4,5,6,7,11,13,16,17,19,20,23}

def rect(w,m):
    scale=float(m['roi_scale'])
    return [round(int(w['left'])/scale+int(m['roi_left'])),
            round(int(w['top'])/scale+int(m['roi_top'])),
            round(int(w['right'])/scale+int(m['roi_left'])),
            round(int(w['bottom'])/scale+int(m['roi_top']))]

def is_overlap(a,b):
    return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])

def audit_one(image,ocr,m,date):
    grid_right=float(m['grid_right'])
    judge=scan(image,grid_right)
    out={'date':date,'source_sha256':m['sha256'],'decision':'UNCHANGED'}
    if not judge['needs_bottom_extension']:
        return out
    height,width=image.height,image.width
    cutoff=judge['original_cutoff_y']
    band=[(r['top'],r['bottom']) for r in judge['bands_crossing_original_cutoff']
          if r['height']>=max(8,.6*judge['median_printed_line_height_px'])]
    assert len(band)==1 and band[0][0]<cutoff<band[0][1],(date,band)
    last_a,last_b=band[0]
    x0=int(grid_right+width*.012);x1=int(width-width*.018)
    gray=np.asarray(image.convert('L'))
    def ink_x(a,b,lo,hi):
        ys,xs=np.where(gray[a:b,lo:hi]<125)
        assert len(xs)>10
        return (lo+int(xs.min()),lo+int(xs.max())+1)
    out.update({'bottom_ink_y':[last_a,last_b],
                'pixels_beyond_old_ocr_bottom':last_b-cutoff,
                'decision':'ADMIN_REVIEW_ONLY_START_UNVERIFIED'})
    words=tab(ocr,f'hafuch-roi-20/{date}/words.tsv')
    lines=tab(ocr,f'hafuch-roi-20/{date}/lines.tsv')
    vheads=[int(a['top']) for a in lines if a['heading']=='V']
    if len(vheads)!=1:
        return out
    anchor=[w for w in words if w['masked'].strip()=='23.'
            and int(w['top'])>vheads[0] and int(w['confidence'])>=65]
    if len(anchor)!=1:
        return out
    start=rect(anchor[0],m)
    if not(x0<=start[0]<start[2]<=x1 and start[1]<last_b):
        return out
    # Locate physically printed start row, not the synthetic OCR line.
    y=int((start[1]+start[3])/2)
    counts=(gray[:,x0:x1]<125).sum(axis=1)
    threshold=max(9,(x1-x0)*.016)
    if counts[y]<=threshold:
        return out
    top=y
    while top>0 and counts[top-1]>threshold:top-=1
    bottom=y+1
    while bottom<height and counts[bottom]>threshold:bottom+=1
    if last_a-top>2.5*judge['median_printed_line_height_px']*2:
        return out
    lengths=[(w,rect(w,m)) for w in words
             if LENGTH.fullmatch(w['masked'].strip()) and int(w['confidence'])>=65]
    finals=[b for w,b in lengths if abs(b[1]-last_a)<=max(8,judge['median_printed_line_height_px']//2)]
    prev=[b for w,b in lengths if abs(b[1]-top)<=max(8,judge['median_printed_line_height_px']//2)
          and b[0]>start[2]]
    if len(finals)!=1 or not prev:
        return out
    preceding=min(prev,key=lambda b:b[0]-start[2])
    if preceding[0]-start[2]<6:
        return out
    xmin,_=ink_x(top,bottom,x0,start[2])
    rects=[[max(x0,xmin-2),top-2,min(start[2]+2,preceding[0]-2),bottom+2]]
    if last_a!=top:
        assert last_a>bottom,(date,'unexpected lines share range')
        assert last_a-bottom<2.5*judge['median_printed_line_height_px'],(date,'intervening printed lines')
        l,r=ink_x(last_a,last_b,x0,x1)
        rects.append([max(x0,l-2),last_a-2,min(x1,r+2),last_b+2])
    else:
        # A single printed row: the full clue's left boundary is physically observed.
        l,r=ink_x(last_a,last_b,x0,start[2])
        rects[0][0]=max(x0,l-2)
        rects[0][3]=last_b+2
    assert all(a[0]<a[2] and a[1]<a[3] for a in rects)
    if not any(is_overlap(finals[0],r) for r in rects):
        return out
    # Fail closed for any OTHER trusted numbered start inside our proposed strips.
    for w in words:
        hit=NUM.fullmatch(w['masked'].strip())
        if hit and int(w['top'])>vheads[0] and int(hit.group(1)) in V-{23}:
            if any(is_overlap(rect(w,m),r) for r in rects):
                return out
    out.update({'decision':'REVIEW_ONLY_V23_SOURCE_CROP',
                'printed_start_box':start,'prior_clue_length_box':preceding,
                'terminal_length_box':finals[0],
                'original_source_row_rectangles':rects,
                'automatic_approval':False})
    return out

def run(source_file,ocr_file,dest):
    with zipfile.ZipFile(source_file) as source,zipfile.ZipFile(ocr_file) as ocr:
        items=tab(ocr,'hafuch-roi-20/manifest.tsv')
        assert len(items)==20 and len({x['date'] for x in items})==20
        allresults=[]
        for m in items:
            date=m['date'];key=f'hafuch-20-source-results/images/{date}.jpg'
            raw=source.read(key)
            assert hashlib.sha256(raw).hexdigest()==m['sha256']
            assert m['grid']=='13x13'
            with Image.open(io.BytesIO(raw)) as im:
                allresults.append(audit_one(im,ocr,m,date))
    changed={x['date'] for x in allresults if x['decision']!='UNCHANGED'}
    assert changed==CLIPPED,('unexpected source crop change',changed)
    assert sum(x['decision']=='UNCHANGED' for x in allresults)==18
    result={'series_id':SERIES,'sources_checked':20,'changed_old_ocr_words':False,
            'used_second_ocr':False,'changed_yedioth_algorithms':False,
            'firebase_writes':0,'canonical_writes':0,'new_apk':False,
            'automatic_approval':False,'sources':allresults}
    Path(dest).parent.mkdir(parents=True,exist_ok=True)
    Path(dest).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'series':SERIES,'sources':20,'old_ocr_preserved':True,
        'proposed':[r['date'] for r in allresults if r['decision'].startswith('REVIEW_ONLY_V23')],
        'blocked':[r['date'] for r in allresults if r['decision'].startswith('ADMIN_REVIEW')],
        'unchanged':18},ensure_ascii=False))

def self_test():
    assert SERIES=='HAFUCH_DEKEL' and len(CLIPPED)==2
    assert NUM.fullmatch('23.') and not NUM.fullmatch('(3)')
    assert LENGTH.fullmatch('(3).') and not LENGTH.fullmatch('(3]')
    print('PASS no guessing and HAFUCH-only terminal audit')

if __name__=='__main__':
    if sys.argv[1:]==['--self-test']:self_test()
    elif len(sys.argv)==4:run(*sys.argv[1:])
    else:raise SystemExit('Use --self-test or originals.zip old_ocr.zip output.json')
