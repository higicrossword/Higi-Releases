#!/usr/bin/env python3
"""Read-only evidence gate for 20 HAFUCH_DEKEL SHA-pinned originals and original OCR.
The archive masks Hebrew text, so AI-text alignment CANNOT be tested here.
"""
import csv,hashlib,io,json,re,sys,zipfile
from pathlib import Path

def audit(source_path,ocr_path,output):
    with zipfile.ZipFile(source_path) as sources, zipfile.ZipFile(ocr_path) as ocr:
        original=csv.DictReader(io.StringIO(ocr.read('hafuch-roi-20/manifest.tsv').decode('utf8')),delimiter='\t')
        rows=list(original)
        assert len(rows)==20 and len({r['date'] for r in rows})==20
        results=[]
        for row in rows:
            date=row['date']
            image=sources.read('hafuch-20-source-results/images/'+date+'.jpg')
            assert hashlib.sha256(image).hexdigest()==row['sha256']
            assert row['grid']=='13x13'
            assert float(row['grid_right'])>float(row['grid_left'])
            data=ocr.read('hafuch-roi-20/'+date+'/words.tsv').decode('utf8')
            assert re.search('[\u0590-\u05ff]',data) is None, 'Hebrew OCR was not masked'
            wordrows=list(csv.DictReader(io.StringIO(data),delimiter='\t'))
            count=int(row['ocr_words'])-len(wordrows)
            assert count in (0,1,2), (date,'manifest vs sanitized row difference',count)
            assert sum('H' in w['masked'] for w in wordrows)>=100
            results.append({'date':date,'source_sha256_match':True,'grid_13x13':True,
                            'ocr_word_rows':len(wordrows),'manifest_row_delta':count})
    result={'series_id':'HAFUCH_DEKEL','verified_source_images':20,
            'one_pass_ocr_evidence':True,'ai_transcript_in_evidence':False,
            'real_ai_text_alignment_tested':False,'sanitized_tsv_does_not_contain_hebrew_words':True,
            'production_changes':False,'firebase_writes':0,'canonical_writes':0,
            'test_restriction':'Cannot score real text match until previous AI text and unmasked in-memory OCR are supplied to isolated admin DRY review.',
            'sources':sorted(results,key=lambda x:x['date'])}
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='sources'},ensure_ascii=False))

if __name__=='__main__':
    if len(sys.argv)!=4:
        raise SystemExit('Usage: verify_ai_neighbor_20_evidence.py source.zip oldocr.zip result.json')
    audit(*sys.argv[1:])
