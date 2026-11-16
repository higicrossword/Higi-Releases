#!/usr/bin/env python3
"""Download only SHA-pinned user/public source bytes into ephemeral Android test assets."""
import hashlib,io,json,sys,urllib.request
from pathlib import Path
from PIL import Image
def main(metadata,assets,report):
    obj=json.loads(Path(metadata).read_text(encoding="utf8"))
    data=obj["fixtures"]; assert len(data)==2
    dest=Path(assets);dest.mkdir(parents=True,exist_ok=True)
    out=[]
    for record in data:
        req=urllib.request.Request(record["url"],headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req,timeout=30) as r:
            raw=r.read(10000001)
        assert len(raw)<=10000000,record["series"]
        actual=hashlib.sha256(raw).hexdigest()
        assert actual==record["sha256"],("SHA changed; abort without silently substituting",record["series"],actual)
        with Image.open(io.BytesIO(raw)) as image:
            image.load()
            assert image.format=="JPEG" and (image.width,image.height)==(record["width"],record["height"])
        assert record["filename"].endswith(".jpg")
        (dest/record["filename"]).write_bytes(raw)
        out.append(record["series"]+"\t"+record["filename"]+"\t"+actual+"\t"+
                   record["date"]+"\t"+record["title"]+"\t"+str(record["reported_expected"]))
        print("SHA_VERIFIED_REAL_IMAGE",record["series"],actual,len(raw),flush=True)
    (dest/"manifest.tsv").write_text("\n".join(out)+"\n",encoding="utf8")
    Path(report).parent.mkdir(parents=True,exist_ok=True)
    # Report metadata, not copyrighted JPG bytes.
    Path(report).write_text(json.dumps(
        {"verified_sources":2,"actual_SHA256":[r["sha256"] for r in data],
         "series":[r["series"] for r in data],
         "missing_series":"TARTEY_DEKEL","persisted_original_images":False,
         "canonical_writes":0,"firebase_writes":0},indent=2)+"\n",encoding="utf8")
if __name__=="__main__":
    if len(sys.argv)!=4:raise SystemExit("Usage: fetch_pinned_sources.py pinned.json assets_dir report.json")
    main(*sys.argv[1:])
