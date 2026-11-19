#!/usr/bin/env python3
"""Read-only QA for exact 28 HAFUCH_DEKEL source-pixel review proposals.
The two manually source-inspected anchors remain *review-only*.
No application, OCR/AI, Firebase, canonical, or release operation.
"""
import hashlib, io, json, sys, zipfile
from pathlib import Path
from PIL import Image

EXPECTED = {
 "H": [1,5,8,9,10,12,14,15,18,19,21,22,24,25],
 "V": [1,2,3,4,5,6,7,11,13,16,17,19,20,23],
}
HEADER = b"2026-11-13:HAFUCH_DEKEL:READ_ONLY:V1\n"

def overlap(a,b):
 return max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3])

def check(zip_name, manifest_name):
 m=json.loads(Path(manifest_name).read_text(encoding="utf-8"))
 assert m["series_id"]=="HAFUCH_DEKEL" and m["date"]=="2026-11-13"
 assert m["status"]=="REVIEW_ONLY_NOT_ADMIN_APPROVED"
 assert m["proposed_count"]==28 and m["from_existing_ocr"]==26
 assert m["manual_pixel_number_recoveries"]==["V19","V20"]
 assert m["canonical_writes"]==m["firebase_writes"]==0
 assert not m["automatic_approval"] and not m["release_created"]
 with zipfile.ZipFile(zip_name) as z:
  raw=z.read("hafuch-20-source-results/images/2026-11-13.jpg")
 assert hashlib.sha256(raw).hexdigest()==m["source_sha256"]
 with Image.open(io.BytesIO(raw)) as source:
  assert source.size==(m["image_width"],m["image_height"])
  im=source.convert("RGB")
  ordered=sorted(m["crops"],key=lambda c: (c["key"][0],int(c["key"][1:])))
  assert len(ordered)==28
  assert [c["key"] for c in ordered]==[d+str(n) for d,nums in EXPECTED.items() for n in nums]
  digest=hashlib.sha256(HEADER)
  all_pieces=[]
  for c in ordered:
   key=c["key"]
   assert c["method"]==("SOURCE_PIXEL_MANUAL_NUMBER" if key in ("V19","V20") else "ORIGINAL_ONE_PASS_OCR_WORDS")
   rects=c["rectangles"]
   assert 1<=len(rects)<=5
   digest.update((key+":"+json.dumps(rects,separators=(",",":"))+"\n").encode("utf8"))
   for r in rects:
    assert len(r)==4 and all(isinstance(v,int) for v in r)
    x0,y0,x1,y1=r
    assert 0<=x0<x1<=im.width and 0<=y0<y1<=im.height
    # No cropped portion of the verified grid: all clues printed to right.
    assert x0>2004
    all_pieces.append((key,r))
    digest.update(im.crop(tuple(r)).tobytes())
  assert digest.hexdigest()==m["rgb_all_rectangles_sha256"], "Pixel/coordinates regression"
  bad=[(a,b) for i,(a,ar) in enumerate(all_pieces)
       for b,br in all_pieces[i+1:]
       if a[0]==b[0] and a!=b and overlap(ar,br)]
  assert not bad, f"Cross-clue overlap: {bad}"
 print("PASS 28/28 pinned REVIEW_ONLY geometries; 55 source row rectangles; zero same-section overlap")
 print("PASS source JPEG SHA-256 and 28 geometry/pixel combined SHA-256")

if __name__=="__main__":
 if len(sys.argv)!=3: raise SystemExit("Usage: verify_2026_11_13_28_review.py originals.zip manifest.json")
 check(*sys.argv[1:])
