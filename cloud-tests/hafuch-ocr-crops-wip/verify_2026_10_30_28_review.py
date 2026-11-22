#!/usr/bin/env python3
"""HAFUCH_DEKEL 30Oct source-pixel QA: read-only; no auto-crop approvals."""
import hashlib, io, json, sys, zipfile
from pathlib import Path
from PIL import Image

H=[1,5,8,9,10,12,14,15,18,19,21,22,24,25]
V=[1,2,3,4,5,6,7,11,13,16,17,19,20,23]
IMAGE_SHA='cd4307f741b99dfd21fe9773c7aa6b7e403e349fff82e402676118597b773a7e'
DIGEST='f8edad55a4b8275c7978c7a9af0bcc510ea892220b684b69973ef4bba6b99bab'
HEADER=b'2026-10-30:HAFUCH_DEKEL:REVIEW_ONLY:V1\n'

def tsv(z,n):
 lines=z.read(n).decode('utf8').splitlines();hdr=lines[0].split('\t');out=[]
 for lineno,x in enumerate(lines[1:],2):
  parts=x.split('\t');assert len(parts)==len(hdr),(n,lineno)
  out.append(dict(zip(hdr,parts)))
 return out

def intersect(a,b):
 return max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3])

def inside(a,b):
 return a[0]<=b[0] and a[1]<=b[1] and b[2]<=a[2] and b[3]<=a[3]

def validate(original_zip,ocr_zip,fixture_tsv):
 src=Path(fixture_tsv).read_text('utf8');lines=src.splitlines()
 assert lines[0].startswith('# Higi HAFUCH_DEKEL 2026-10-30')
 assert 'NOT administrator-approved' in lines[0]
 assert '# SOURCE_SHA256='+IMAGE_SHA in lines
 assert '# RGB_GEOMETRY_DIGEST='+DIGEST in lines
 assert '# MANUAL_VISUAL_CONFIRMATION_REQUIRED_FOR_ALL_28=true' in lines
 assert '# NO_CANONICAL_FIREBASE_APP_RELEASE_WRITES=true' in lines
 noncomments=[s for s in lines if s.strip() and not s.startswith('#')]
 assert noncomments[0]=='key\tanchor_id\tend_length_id\trectangles'
 entries=[]
 for s in noncomments[1:]:
  key,a,b,rs=s.split('\t')
  rectangles=[[int(v) for v in r.split(',')] for r in rs.split(';')]
  entries.append((key,int(a),int(b),rectangles))
 expected=[d+str(n) for d,ns in [('H',H),('V',V)] for n in ns]
 assert [e[0] for e in entries]==expected
 assert len(entries)==28 and sum(len(e[3]) for e in entries)==54
 assert len(set(e[1] for e in entries))==len(set(e[2] for e in entries))==28
 assert dict((k,a) for k,a,_,rs in entries)['H18']==68
 assert dict((k,a) for k,a,_,rs in entries)['V20']==199
 with zipfile.ZipFile(original_zip) as z:
  raw=z.read('hafuch-20-source-results/images/2026-10-30.jpg')
 assert hashlib.sha256(raw).hexdigest()==IMAGE_SHA
 with zipfile.ZipFile(ocr_zip) as z:
  meta=next(m for m in tsv(z,'hafuch-roi-20/manifest.tsv') if m['date']=='2026-10-30')
  words={int(w['id']):w for w in tsv(z,'hafuch-roi-20/2026-10-30/words.tsv')}
  ll=tsv(z,'hafuch-roi-20/2026-10-30/lines.tsv')
 assert meta['sha256']==IMAGE_SHA and meta['grid']=='13x13'
 assert len(words)==int(meta['ocr_words'])==217 and len(ll)==int(meta['ocr_lines'])==37
 assert not any(l['heading']=='H' for l in ll)
 assert sum(l['heading']=='V' for l in ll)==1
 assert words[68]['masked']=='8.' and words[199]['masked']=='0.'
 scale=float(meta['roi_scale']);xoff=int(meta['roi_left']);yoff=int(meta['roi_top'])
 def orig_box(w):
  return [round(int(w['left'])/scale+xoff),round(int(w['top'])/scale+yoff),
          round(int(w['right'])/scale+xoff),round(int(w['bottom'])/scale+yoff)]
 with Image.open(io.BytesIO(raw)) as source:
  assert source.size==(3053,2448)
  im=source.convert('RGB')
  hashobj=hashlib.sha256(HEADER);parts=[]
  for key,aid,eid,rectangles in entries:
   hashobj.update((key+':'+json.dumps(rectangles,separators=(',',':'))+'\n').encode())
   for r in rectangles:
    x0,y0,x1,y1=r
    assert 2033<=x0<x1<im.width and 0<=y0<y1<=im.height
    hashobj.update(im.crop(tuple(r)).tobytes())
    parts.append((key,r))
   for wordid in (aid,eid):
    box=orig_box(words[wordid])
    assert any(inside(r,box) for r in rectangles),(key,wordid,box)
   for otherkey,otherid,_,_ in entries:
    if key[0]!=otherkey[0] or key==otherkey:continue
    box=orig_box(words[otherid])
    assert not any(intersect(r,box) for r in rectangles),(key,'foreign anchor',otherkey)
  assert hashobj.hexdigest()==DIGEST,('pixel hash mismatch',hashobj.hexdigest())
  for i,(ka,a) in enumerate(parts):
   for kb,b in parts[i+1:]:
    if ka!=kb and ka[0]==kb[0]:assert not intersect(a,b),(ka,kb,'collision')
 print('PASS 28 distinct HAFUCH_DEKEL REVIEW_ONLY proposals, 54 separate source-pixel strips')
 print('PASS publisher JPEG SHA256, original OCR evidence, and exact RGB geometry SHA256')
 print('PASS anchor/length boxes included; zero foreign starts and same-direction collisions')
 print('No new OCR/AI, Canonical/Firebase writes or release')

if __name__=='__main__':
 if len(sys.argv)!=4:raise SystemExit('Usage: verify_2026_10_30_28_review.py originals.zip ocr.zip fixture.tsv')
 validate(*sys.argv[1:])
