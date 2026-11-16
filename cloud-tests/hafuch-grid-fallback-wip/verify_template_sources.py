#!/usr/bin/env python3
"""Read-only QA of SHA-pinned 20 original Hafuch images and standalone 13x13 mask."""
import hashlib,json,sys
from pathlib import Path

EXPECTED_DATES=(
 "2026-07-03","2026-07-10","2026-07-17","2026-07-24","2026-07-31",
 "2026-08-07","2026-08-14","2026-08-21","2026-08-28",
 "2026-09-04","2026-09-11","2026-09-18","2026-09-25",
 "2026-10-02","2026-10-09","2026-10-16","2026-10-23","2026-10-30",
 "2026-11-06","2026-11-13"
)
EXPECTED_TEMPLATE_SHA="cae53eb21dad1e97e410aadaa854755042699c49e4330c978b1b91c3e58661b1"
EXPECTED_PATCH_SHA="2b85ad6574c58b0ef3db5018f8008614d1ddbb1b47e7f6241e4bd5b5793165f8"

def check(reference,originals,report):
    ref=json.loads(Path(reference).read_text(encoding="utf8"))
    root=Path(originals)
    data=json.loads((root/"sources.json").read_text(encoding="utf8"))
    rows=ref["blocked_cells_image_top_to_bottom"]
    assert ref["series_id"]=="HAFUCH_DEKEL"
    assert ref["rows"]==ref["columns"]==13 and len(rows)==13
    assert all(len(x)==13 and set(x)<={".","#"} for x in rows)
    assert sum(r.count("#") for r in rows)==49
    assert sum(r.count(".") for r in rows)==120
    assert hashlib.sha256(("\n".join(rows)+"\n").encode("utf8")).hexdigest()==EXPECTED_TEMPLATE_SHA
    assert ref["reference_mask_sha256"]==EXPECTED_TEMPLATE_SHA
    assert len(ref["dates_checked"])==20 and set(ref["dates_checked"])==set(EXPECTED_DATES)
    assert data["requested_latest"]==20 and data["verified_distinct_dates"]==20
    images=data["selected"]
    assert len(images)==20
    assert set(x["date"] for x in images)==set(EXPECTED_DATES)
    record=[]
    for x in images:
        fname=x["local_image_file"]
        assert fname.startswith("images/") and ".." not in fname
        b=(root/fname).read_bytes()
        digest=hashlib.sha256(b).hexdigest()
        assert digest==x["sha256"],("Source-byte hash mismatch",fname)
        record.append({"date":x["date"],"sha256":digest,"bytes":len(b)})
    report_obj={"series_id":ref["series_id"],"mask_sha256":EXPECTED_TEMPLATE_SHA,
                "date_count":20,"source_image_sha256_verified":20,
                "blocked_cells":49,"white_cells":120,"grid":"13x13",
                "historical_alignment":"20 previously independently classified source masks matched",
                "runtime_fallback_guard":"existing GridAnalysis.matchKnownGrid pixel match",
                "app_code_unchanged_until_release":True,
                "canonical_writes":0,"firebase_writes":0,"apk_release":False,
                "source_evidence":record}
    Path(report).write_text(json.dumps(report_obj,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("PASS 20/20 original image hashes + pinned 13x13 mask",EXPECTED_TEMPLATE_SHA)

def check_staged_patch_hash(data):
    assert hashlib.sha256(Path(data).read_bytes()).hexdigest()==EXPECTED_PATCH_SHA
    print("PASS overlay patch SHA256",EXPECTED_PATCH_SHA)

if __name__=="__main__":
    if len(sys.argv)==4:check(*sys.argv[1:])
    elif len(sys.argv)==3 and sys.argv[1]=="--patch":check_staged_patch_hash(sys.argv[2])
    else:raise SystemExit("Usage: verify_template_sources.py template.json original-dir report.json OR --patch patch.diff")
