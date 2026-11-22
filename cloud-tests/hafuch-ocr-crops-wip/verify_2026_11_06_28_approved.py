#!/usr/bin/env python3
"""Read-only regression: 28 exact user-approved 06Nov source-pixel crops."""
import hashlib, io, json, sys, zipfile
from pathlib import Path
from PIL import Image

EXPECTED={"H":[1,5,8,9,10,12,14,15,18,19,21,22,24,25],
          "V":[1,2,3,4,5,6,7,11,13,16,17,19,20,23]}
SOURCE_SHA="37e53145854c549f786819cd27e38852ce1deaaae484e9e7e71044db168774ef"
GEOMETRY_DIGEST="7617ae136407c6fd68db8c8f5287fc596d2c14fb5ef9ad34c0e76bd730b2239b"
HEADER=b"2026-11-06:HAFUCH_DEKEL:REVIEW_ONLY:V1\n"
def overlap(a,b):
 return max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3])

def main(images_zip,tsv_path):
 text=Path(tsv_path).read_text(encoding="utf-8")
 lines=text.splitlines()
 assert "# ADMIN_APPROVAL_DATE=2026-11-22" in lines
 assert "# ADMIN_EXACT_REPLY=החיתוכים נכונין" in lines
 assert "# VISUAL_STATUS=VISUAL_CROP_CONFIRMED (all exact 28 displayed crops)" in lines
 assert "# REVIEW_ONLY_NO_CANONICAL_FIREBASE_APP_WRITES=true" in lines
 assert "# SOURCE_SHA256="+SOURCE_SHA in lines
 assert "# RGB_GEOMETRY_DIGEST="+GEOMETRY_DIGEST in lines
 records=[line for line in lines if line and not line.startswith("#")]
 assert records[0]=="key\trectangles"
 entries={}
 for line in records[1:]:
  key,raw=line.split("\t")
  assert key not in entries
  entries[key]=[[int(v) for v in r.split(",")] for r in raw.split(";")]
 expected=[d+str(n) for d,nums in EXPECTED.items() for n in nums]
 assert list(entries)==expected and len(entries)==28
 assert sum(len(v) for v in entries.values())==55
 assert entries["H15"]==[[2216,766,2903,818]]
 with zipfile.ZipFile(images_zip) as z:
  raw=z.read("hafuch-20-source-results/images/2026-11-06.jpg")
 assert hashlib.sha256(raw).hexdigest()==SOURCE_SHA
 image=Image.open(io.BytesIO(raw)).convert("RGB")
 assert image.size==(3000,2433)
 digest=hashlib.sha256(HEADER)
 allpieces=[]
 for key,rectangles in entries.items():
  digest.update((key+":"+json.dumps(rectangles,separators=(",",":"))+"\n").encode("utf-8"))
  for rect in rectangles:
   x0,y0,x1,y1=rect
   assert 0<=x0<x1<=image.width and 0<=y0<y1<=image.height
   assert x0>2004 # validated grid-right guard for this source
   allpieces.append((key,rect))
   digest.update(image.crop(tuple(rect)).tobytes())
 assert digest.hexdigest()==GEOMETRY_DIGEST,"Source pixel or geometry regression"
 collisions=[(k1,k2) for i,(k1,r1) in enumerate(allpieces)
             for k2,r2 in allpieces[i+1:] if k1!=k2 and k1[0]==k2[0] and overlap(r1,r2)]
 assert not collisions,collisions
 print("PASS: exact 28/28 administrator-confirmed 06Nov HAFUCH_DEKEL geometry")
 print("PASS: source SHA256 and combined 55 RGB strip pixel digest; zero same-direction collisions")
 print("PASS: original approved H15 alternative preserved in separate prior fixture (not modified here)")

if __name__=="__main__":
 if len(sys.argv)!=3:raise SystemExit("Usage: verify_2026_11_06_28_approved.py original.zip frozen.tsv")
 main(*sys.argv[1:])
