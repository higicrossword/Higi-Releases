#!/usr/bin/env python3
"""Independent OCR gate benchmark. Never counts this as Android/Canonical crop accuracy."""
import os,re,json,csv,collections
from pathlib import Path
import pytesseract
from PIL import Image, ImageOps, ImageEnhance
ROOT=Path('yedioth-20-fixtures')
rows=json.loads((ROOT/'manifest.json').read_text())
EXPECTED={'H':[1,5,6,8,9,11,13,14], 'V':[1,2,3,4,7,8,10,12]}
report=[]
for record in rows:
 if record['status']!='downloaded': continue
 date=record['date'];img=Image.open(ROOT/record['file']).convert('RGB');w,h=img.size
 for d in ['H','V']:
  xl,xr=(.315,.635) if d=='H' else (.0,.312)
  yt,yb=.29,.94
  xa,xb=int(w*xl),int(w*xr);ya,yb=int(h*yt),int(h*yb)
  crop=img.crop((xa,ya,xb,yb))
  # Original appears small; upsample to make Tesseract 2-4x more reliable.
  fac=2 if w>1700 else 4
  enlarged=crop.resize((crop.width*fac,crop.height*fac))
  result=pytesseract.image_to_data(enlarged,lang='heb+eng',config='--psm 6',output_type=pytesseract.Output.DICT)
  tokens=[]
  for i,s in enumerate(result['text']):
   s=s.strip();c=float(result['conf'][i]);
   if not s or c<0:continue
   x=xa+result['left'][i]/fac;y=ya+result['top'][i]/fac
   xx=x+result['width'][i]/fac;yy=y+result['height'][i]/fac
   tokens.append({'text':s,'conf':round(c,1),'x':round(x,1),'y':round(y,1),'right':round(xx,1),'bottom':round(yy,1)})
  def num(s):
   s=s.replace('．','.').strip().strip('[]{}')
   if re.fullmatch(r'[0-9]{1,2}[.,:]',s):return int(s[:-1])
   if re.fullmatch(r'[.,:][0-9]{1,2}',s):return int(s[1:])
   return None
  anchors=[{**t,'n':num(t['text'])} for t in tokens if num(t['text']) is not None and t['conf']>=70]
  # V197 uses the next expected clue number as boundary, with a confidence threshold and geometry gates.
  expected=EXPECTED[d];paired=0;elig=[]
  for n,next_n in zip(expected,expected[1:]):
   a=[z for z in anchors if z['n']==n]
   b=[z for z in anchors if z['n']==next_n]
   if len(a)==1 and len(b)==1:
    ap,bp=a[0],b[0]
    good=(bp['y']>ap['y']+4 and bp['y']-ap['y']<=h/9 and abs((ap['x']+ap['right'])/2-(bp['x']+bp['right'])/2)<=w/4)
    if good:paired+=1;elig.append(f'{n}->{next_n}')
  rec={
   'date':date,'direction':d,'weekday':record['weekday'],'source_size':f'{w}x{h}',
   'tesseract_tokens':len(tokens),'valid_printed_numbers':len(anchors),
   'unique_expected_numbers':sum(sum(z['n']==n for z in anchors)==1 for n in expected),
   'number_pair_geometry_gates_passed':paired,'number_pairs':','.join(elig),
   'android_v197_profile_enabled':record['v197_new_boundary_pass_enabled'],
   'full_crop_precision':'not_measured',
   'all_detected_number_texts':','.join(f"{x['n']}:{x['conf']}" for x in anchors)[:240]
  }
  report.append(rec)
 print('OCR_FIXTURE',date,d,'markers',len(anchors),'unique',rec['unique_expected_numbers'],'pairs',paired,'v197_enabled',record['v197_new_boundary_pass_enabled'],flush=True)
cols=list(report[0]);p=ROOT/'ocr_gate_benchmark.csv'
with p.open('w',encoding='utf-8-sig',newline='') as f:
 wr=csv.DictWriter(f,fieldnames=cols);wr.writeheader();wr.writerows(report)
summary={
 'tested_images':len(rows),'tested_ocr_columns':len(report),
 'monday_images':sum(r['weekday']=='Monday' for r in rows),
 'wednesday_images':sum(r['weekday']=='Wednesday' for r in rows),
 'monday_ocr_geometry_pairs':sum(r['number_pair_geometry_gates_passed'] for r in report if r['weekday']=='Monday'),
 'wednesday_ocr_geometry_pairs':sum(r['number_pair_geometry_gates_passed'] for r in report if r['weekday']=='Wednesday'),
 'number_pair_geometry_gates_passed_total':sum(r['number_pair_geometry_gates_passed'] for r in report),
 'full_app_pipeline_ran':False,
 'full_crop_accuracy_measured':False,
 'reason':'Independent Linux Tesseract OCR differs from Android OCR, and historical V178 candidate map not available. These are upper-bound OCR anchor and gating diagnostics, not true crop acceptance.'
}
(ROOT/'ocr_benchmark_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print('OCR_BENCHMARK_SUMMARY',json.dumps(summary,ensure_ascii=False),flush=True)