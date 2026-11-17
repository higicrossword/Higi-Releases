#!/usr/bin/env python3
"""Offline QA for *original* Hafuch Android OCR geometry from 20 SHA-pinned images.
Does not derive, approve, or overwrite clue crops; never expands to other series.
All image source pixels and Hebrew clue text remain untouched.
"""
import csv,io,json,re,statistics,sys,zipfile
from pathlib import Path

H={1,5,8,9,10,12,14,15,18,19,21,22,24,25}
V={1,2,3,4,5,6,7,11,13,16,17,19,20,23}
EXACT=re.compile(r"^(\d{1,2})[.,:]$")
def read_tsv(z,path):
    # These TSVs contain raw OCR punctuation, including unescaped double
    # quotes. The writer emits literal TAB-separated columns, not CSV quoting.
    # csv.DictReader would silently swallow several entire rows as multiline
    # quoted fields. Split physical lines strictly and verify column counts.
    lines=z.read(path).decode('utf8').splitlines()
    assert lines,('Empty evidence',path)
    header=lines[0].split('\t')
    out=[]
    for i,line in enumerate(lines[1:],2):
        parts=line.split('\t')
        assert len(parts)==len(header),(path,i,'wrong TSV field count')
        out.append(dict(zip(header,parts)))
    return out
def audit(artifact,destination):
    rows=[];raw_counts=[]
    with zipfile.ZipFile(artifact) as z:
        m=read_tsv(z,'hafuch-roi-20/manifest.tsv')
        assert len(m)==20 and len({i['date'] for i in m})==20
        for info in m:
            date=info['date']
            assert info['grid']=='13x13',(date,info['grid'])
            path='hafuch-roi-20/'+date+'/'
            words=read_tsv(z,path+'words.tsv')
            lines=read_tsv(z,path+'lines.tsv')
            assert len(words)==int(info['ocr_words']) and len(lines)==int(info['ocr_lines'])
            headings={d:sorted(int(x['top']) for x in lines if x['heading']==d) for d in ('H','V')}
            numbered=[]
            for w in words:
                match=EXACT.fullmatch(w['masked'].strip())
                if match:
                    numbered.append({'number':int(match.group(1)),'y':int(w['top']),
                                     'confidence':int(w['confidence']),'left':int(w['left'])})
            across25=sorted(x['y'] for x in numbered if x['number']==25)
            one=sorted(x['y'] for x in numbered if x['number']==1)
            # An independent heading location takes precedence. If a heading is
            # missing, a SECOND physical 1. found after H25 is only a diagnostic
            # section *candidate* -- never an automatically approved boundary.
            second_one=[y for y in one if across25 and y>across25[0]]
            heading_start=headings['V'][0] if headings['V'] else None
            section_start=heading_start if heading_start is not None else (
                second_one[0] if second_one else None)
            if section_start is not None and across25 and section_start<across25[0]:
                section_start=second_one[0] if second_one else None
            if section_start is None:
                identified_h=set();identified_v=set()
            else:
                identified_h={w['number'] for w in numbered
                              if w['y']<section_start and w['number'] in H}
                identified_v={w['number'] for w in numbered
                              if w['y']>=section_start and w['number'] in V}
            # Duplicates and punctuation ambiguity are NOT resolved by counting.
            dups={d:sorted({x['number'] for x in numbered if
                            x['number'] in keys and
                            ((x['y']<section_start) if d=='H' else (x['y']>=section_start))
                            and sum(int(y['number']==x['number']) for y in numbered if
                            (y['y']<section_start if d=='H' else y['y']>=section_start))>1})
                 for d,keys in [('H',H),('V',V)]} if section_start is not None else {}
            rows.append({
                'date':date,
                'grid_detected':info['grid'],
                'source_sha256':info['sha256'],
                'ocr_words':len(words),
                'ocr_lines':len(lines),
                'heading_H_count':len(headings['H']),
                'heading_V_count':len(headings['V']),
                'V_section_start_y':section_start,
                'V_section_boundary_source':'HEADING_OCR' if heading_start is not None else (
                    'SECOND_1_AFTER_H25_PROVISIONAL' if section_start else 'UNVERIFIED'),
                'standalone_H_numbers':sorted(identified_h),
                'standalone_V_numbers':sorted(identified_v),
                'H_count':len(identified_h),
                'V_count':len(identified_v),
                'missing_H_token':sorted(H-identified_h),
                'missing_V_token':sorted(V-identified_v),
                'duplicates':dups,
                'review_only':True,
                'pixel_verified_starts':0,
                'visually_verified_crops':0
            })
    total=sum(x['H_count']+x['V_count'] for x in rows)
    assert total==499,('The pinned Android OCR numeric baseline changed',total)
    assert sum(x['heading_H_count']==0 for x in rows)==3
    assert sum(x['heading_V_count']==0 for x in rows)==1
    assert len(rows)==20
    report={
        'series_id':'HAFUCH_DEKEL',
        'sources':len(rows),
        'expected_clue_starts':560,
        'recognized_standalone_number_tokens':total,
        'remaining_starts_without_standalone_number_token':560-total,
        'important_limitation':'A number token is NOT a validated clue start, safe crop, or proof of completeness. When V heading is absent, the fallback section split is provisional.',
        'written_to_canonical':False,
        'firebase_writes':0,
        'source_algorithm_modified':False,
        'apk_or_release_created':False,
        'per_source':rows}
    Path(destination).parent.mkdir(parents=True,exist_ok=True)
    Path(destination).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('20 SOURCE SHA-PINNED ANDROID OCR AUDIT:',total,'/560 standalone starts; missing',560-total)
    print('Header H missing sources:',[x['date'] for x in rows if x['heading_H_count']==0])
    print('Header V missing sources:',[x['date'] for x in rows if x['heading_V_count']==0])
    for x in rows: print(x['date'],x['H_count'],x['V_count'],
       x['V_section_boundary_source'])
def smoke():
    assert len(H)==len(V)==14 and len(H|V)==25
    assert EXACT.fullmatch('15.') and EXACT.fullmatch('20:')
    assert not EXACT.fullmatch('(3)') and not EXACT.fullmatch('H15.')
    print('PASS independent Hafuch numeric token parser, no speculative starts')
if __name__=='__main__':
    if sys.argv[1:]==['--self-test']:smoke()
    elif len(sys.argv)==3:audit(sys.argv[1],sys.argv[2])
    else:raise SystemExit('Usage: audit_twenty_source_numbers.py --self-test or input.zip report.json')
