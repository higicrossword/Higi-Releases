#!/usr/bin/env python3
"""Series-only, pre-OCR source-pixel test for cropped final printed definition rows.

Operates on original JPEG bytes and pixel-proven grid bounds only; it does NOT
perform OCR, guess clue numbers, modify app/Cannonical/Firebase, or create APKs.
"""
import csv,io,hashlib,json,sys,zipfile
from pathlib import Path
import numpy as np
from PIL import Image

KNOWN={"2026-07-31","2026-08-07"}

def tab(z,path):
    data=z.read(path).decode('utf8').splitlines()
    h=data[0].split('\t')
    return [dict(zip(h,r)) for line in data[1:] if len(r:=line.split('\t'))==len(h)]

def scan(image,grid_right):
    src=np.asarray(image.convert('L'))
    height,width=src.shape
    x0=max(0,min(width-2,int(grid_right+width*.012)))
    x1=max(x0+1,min(width,int(width-width*.018)))
    y0=int(height*.10)
    values=(src[y0:,x0:x1]<125).sum(axis=1)
    threshold=max(9,(x1-x0)*.016)
    spans=[]
    first=None
    for k,v in enumerate(values):
        dark=v>threshold
        if dark and first is None:first=k
        if first is not None and (not dark or k==len(values)-1):
            end=k+1 if dark and k==len(values)-1 else k
            if end-first>=2:spans.append((first+y0,end+y0))
            first=None
    body=sorted(b-a for a,b in spans
        if a>=int(height*.15) and b<=int(height*.90) and b-a>=5)
    median=body[len(body)//2] if body else 0
    cutoff=int(height*.975)
    crossing=[{'top':a,'bottom':b,'height':b-a}
        for a,b in spans if b>cutoff]
    real=[v for v in crossing if v['height']>=max(8,.6*median)]
    return {'image_height':height,'image_width':width,'original_cutoff_y':cutoff,
       'median_printed_line_height_px':median,'bands_crossing_original_cutoff':crossing,
       'needs_bottom_extension':bool(real)}

def main(original_zip,ocr_zip,output):
    with zipfile.ZipFile(original_zip) as original, zipfile.ZipFile(ocr_zip) as ocr:
        meta={r['date']:r for r in tab(ocr,'hafuch-roi-20/manifest.tsv')}
        assert len(meta)==20
        checks=[]
        for date,record in sorted(meta.items()):
            name='images/'+date+'.jpg'
            raw=original.read(name)
            assert hashlib.sha256(raw).hexdigest()==record['sha256'],('original source changed',date)
            with Image.open(io.BytesIO(raw)) as source:
                verdict=scan(source,float(record['grid_right']))
            checks.append({'date':date,'sha256':record['sha256'],**verdict})
    selected={x['date'] for x in checks if x['needs_bottom_extension']}
    assert selected==KNOWN,('Source-only clipped-text decisions changed',sorted(selected))
    diagnostic=next(x for x in checks if x['date']=='2026-09-04')
    assert diagnostic['bands_crossing_original_cutoff'] and not diagnostic['needs_bottom_extension']
    result={'series_id':'HAFUCH_DEKEL','sources_checked':20,
      'extension_dates':sorted(selected),'false_footer':"2026-09-04 printer dotted border excluded",
      'decision':'extend source ROI only on verified bottom text ink; preserve standard ROI otherwise',
      'restriction':'Source textline ink is not a verified clue boundary or decoded clue number',
      'one_ocr_pass_at_runtime':True,'canonical_writes':0,'firebase_writes':0,'new_apk_or_release':False,
      'per_source':checks}
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='per_source'},ensure_ascii=False,indent=2))
def self_test():
    assert KNOWN=={'2026-07-31','2026-08-07'}
    print('PASS Hafuch-only 20-source baseline and decorative-footer guard')
if __name__=='__main__':
    if sys.argv[1:]==['--self-test']:self_test()
    elif len(sys.argv)==4:main(*sys.argv[1:])
    else:raise SystemExit('Usage: audit_bottom_ink_20.py --self-test or sources.zip original-ocr.zip out.json')
