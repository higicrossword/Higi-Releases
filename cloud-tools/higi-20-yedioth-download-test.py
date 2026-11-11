#!/usr/bin/env python3
import os,re,io,json,hashlib,urllib.request,datetime,statistics,collections,csv,zipfile
from pathlib import Path
from html import unescape
from PIL import Image
import numpy as np
ROOT=Path('yedioth-20-fixtures');ROOT.mkdir(exist_ok=True)
items=[('11-11-26','Ssfvru-AF_M'),('09-11-26','NN18xXMLejw'),('04-11-26','S3MXmJUvMeI'),('02-11-26','mdgNYH_c-sI'),('28-10-26','gKBWpunfnKE'),('26-10-26','GQ_Ky7GNPDg'),('21-10-26','Ow4e2CNldmY'),('19-10-26','wPlCV9vk3Ug'),('14-10-26','8pClK26imJM'),('12-10-26','Y5GOmBaE2jg'),('07-10-26','3OeGJaH0xJY'),('05-10-26','6YwI1nCQoVw'),('30-09-26','w7RmmwK0nS0'),('28-09-26','us_S-ar_tq4'),('23-09-26','RqE3a2DoSfA'),('16-09-26','VAeSjtjjPDI'),('14-09-26','WiijOr6Zz2E'),('09-09-26','oJpU3qqddr8'),('07-09-26','rcUA9u0nuK4'),('02-09-26','XhIGFf_Vnp4')]
headers={'User-Agent':'Mozilla/5.0 Chrome/126.0.0.0'}
rows=[]; seen=set()
for date,thread in items:
    t=f'https://groups.google.com/g/tartey_mashma/c/{thread}'
    row={'date':date,'thread':t,'status':'failed'}
    try:
        req=urllib.request.Request(t,headers=headers)
        with urllib.request.urlopen(req,timeout=22) as r:html=unescape(r.read().decode('utf-8','replace'))
        titles=re.findall(r'<title>(.*?)</title>',html,re.S)
        title=re.sub('<[^>]+>','',titles[0]) if titles else ''
        row['title']=title
        if 'דקל בנו' not in title or 'ידיעות' not in title or 'תרתי' in title or 'הפוך על הפוך' in title:
            row['status']='wrong-series';rows.append(row);print('EXCLUDED WRONG SERIES',date,title,flush=True);continue
        hrefs=re.findall(r'<a[^>]+href="(https://groups.google.com/group/tartey_mashma/attach/[^"<>]+)"[^>]*>',html,re.S)
        hrefs=list(dict.fromkeys(x.replace('&amp;','&') for x in hrefs))
        images=[x for x in hrefs if re.search(r'\.(jpe?g|png)(\?|$)',x,re.I)]
        row['attachment_candidates']=len(images)
        if not images: row['status']='no-image';rows.append(row);print('NO IMAGE',date,flush=True);continue
        for url in images:
            try:
                request=urllib.request.Request(url,headers=headers)
                with urllib.request.urlopen(request,timeout=24) as r:b=r.read(9000000)
                im=Image.open(io.BytesIO(b));im.load()
                if im.width<500 or im.height<240:continue
                if hashlib.sha256(b).hexdigest() in seen:continue
                seen.add(hashlib.sha256(b).hexdigest());name=date+'.'+('png' if im.format=='PNG' else 'jpg')
                (ROOT/name).write_bytes(b)
                row.update(status='downloaded',file=name,attachment_url=url,width=im.width,height=im.height,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),format=im.format)
                break
            except Exception as e:row['last_download_error']=str(e)[:130]
        rows.append(row)
        print('FETCH',date,row['status'],row.get('width'),row.get('height'),row.get('bytes'),len(images),flush=True)
    except Exception as e:
        row['error']=str(e)[:200];rows.append(row);print('FAIL',date,str(e)[:130],flush=True)

# The existing V197 series profile currently targets Monday only.  Wednesday is detected
# by the title but mondayBoundaryReview=false.  These are testable code-level conditions.
for row in rows:
    if row['status']!='downloaded':continue
    img=Image.open(ROOT/row['file']).convert('RGB');w,h=img.size
    a=np.asarray(img)
    # dark pixel grid occurrence in region right of image (normalized): black grid is rightmost 36-38%.
    gray=np.asarray(img.convert('L'))
    grid=(gray[int(h*.21):int(h*.90),int(w*.63):int(w*.99)]<75)
    grid_frac=float(grid.mean()) if grid.size else 0.
    row['grid_dark_fraction']=round(grid_frac,4)
    row['right_grid_detected']=grid_frac>.10
    row['landscape']=bool(w/h>1.6)
    row['same_layout_geometry']=bool(row['landscape'] and grid_frac>.10 and w>=900)
    row['weekday']=datetime.datetime.strptime(row['date'],'%d-%m-%y').strftime('%A')
    row['v197_profile']='YEDIOTH_MONDAY_DEKEL' if row['weekday']=='Monday' else 'YEDIOTH_WEDNESDAY_DEKEL'
    row['v197_new_boundary_pass_enabled']=row['weekday']=='Monday'
    row['v197_actual_android_ocr_executed']=False
    # Upper bound for V197 numeric crossing given 4-line max: unknown until Android OCR lines available.
    row['v197_crop_accuracy']='not_measured: Android OCR/ClueGeometry/canonical baselines unavailable for historical image'

manifest=ROOT/'manifest.json';manifest.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
with open(ROOT/'results.csv','w',encoding='utf-8-sig',newline='') as f:
    cols=['date','weekday','status','width','height','bytes','right_grid_detected','grid_dark_fraction','v197_profile','v197_new_boundary_pass_enabled','v197_crop_accuracy','attachment_url','thread']
    writer=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
valid=[x for x in rows if x['status']=='downloaded']
print('SUMMARY downloaded',len(valid),'of',len(rows),'Monday',sum(x.get('weekday')=='Monday' for x in valid),'Wednesday',sum(x.get('weekday')=='Wednesday' for x in valid),'matching layout heuristics',sum(x.get('same_layout_geometry') for x in valid),flush=True)
with zipfile.ZipFile('Yedioth-Dekel-20-fixtures.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
    for f in ROOT.iterdir():z.write(f,arcname=f.name)
print('ZIP',Path('Yedioth-Dekel-20-fixtures.zip').stat().st_size,flush=True)