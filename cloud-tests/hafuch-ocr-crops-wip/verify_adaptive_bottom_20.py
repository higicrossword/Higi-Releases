#!/usr/bin/env python3
"""Validate pixel-only selective bottom ROI against original 20-image Android OCR.

Safety contract: exactly two independently source-proven clipped-text originals
may change. All other 18 OCR word/line files MUST remain byte-for-byte identical.
No new app version, Canonical writes or Firebase changes.
"""
import csv,io,json,sys,zipfile
from pathlib import Path

ALLOW={"2026-07-31","2026-08-07"}

def rows(z,name):
    data=z.read(name).decode('utf8').splitlines()
    assert data,name
    header=data[0].split('\t')
    out=[]
    for line in data[1:]:
        p=line.split('\t')
        assert len(p)==len(header),(name,'TSV row width')
        out.append(dict(zip(header,p)))
    return out

def validate(baseline,adaptive,output):
    with zipfile.ZipFile(baseline) as a,zipfile.ZipFile(adaptive) as b:
        old={x['date']:x for x in rows(a,'hafuch-roi-20/manifest.tsv')}
        new={x['date']:x for x in rows(b,'hafuch-roi-20/manifest.tsv')}
        assert len(old)==len(new)==20 and set(old)==set(new)
        result=[]
        for date in sorted(old):
            x=old[date];y=new[date]
            assert x['sha256']==y['sha256'] and x['grid']==y['grid']=='13x13'
            expected_extension=date in ALLOW
            assert y['bottom_extended']==str(expected_extension).lower(),(
                'Unexpected image-only bottom-ink decision',date,y['bottom_extended'])
            difference=[]
            for name in ('words.tsv','lines.tsv'):
                p=f'hafuch-roi-20/{date}/{name}'
                if a.read(p)!=b.read(p):
                    difference.append(name)
            if not expected_extension:
                assert not difference,('OCR regression in non-clipped source',date,difference)
                assert x['roi_width']==y['roi_width'] and x['roi_height']==y['roi_height']
            else:
                assert difference,('Expected modified OCR evidence',date)
                assert int(y['roi_height'])>=int(x['roi_height'])
            result.append({'date':date,'extended':expected_extension,
                'ocr_tsv_files_changed':difference,'old_words':int(x['ocr_words']),
                'new_words':int(y['ocr_words']),'old_ms':int(x['ocr_millis']),
                'new_ms':int(y['ocr_millis'])})
        assert sum(x['extended'] for x in result)==2
    summary={'series':'HAFUCH_DEKEL','original_images':20,
      'source_pixel_guard_decisions_verified':20,
      'adaptive_extension_sources':sorted(ALLOW),
      'unchanged_ocr_word_line_files_in_other_18':18,
      'baseline_total_words':sum(x['old_words'] for x in result),
      'adaptive_total_words':sum(x['new_words'] for x in result),
      'not_a_clue_crop_visual_approval':True,
      'source_project_modified':False,'published_apk':False,
      'firebase_writes':0,'canonical_writes':0,
      'per_source':result}
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    Path(output).write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='per_source'},indent=2))
def self_test():
    assert len(ALLOW)==2 and '2026-09-04' not in ALLOW
    print('PASS selective bottom ROI safety expectations')
if __name__=='__main__':
    if sys.argv[1:]==['--self-test']:self_test()
    elif len(sys.argv)==4:validate(*sys.argv[1:])
    else:raise SystemExit('Usage: verify_adaptive_bottom_20.py --self-test OR old.zip new.zip report.json')
