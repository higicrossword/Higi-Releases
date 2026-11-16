#!/usr/bin/env python3
"""WIP-only pixel test: does a suffix-only OCR token come from a cropped RIGHT edge?

Does not validate printed numbers, change existing crops or write Canonical.
Read-only and reproducible against SHA-verified 19-source GitHub OCR artifacts.
"""
import csv
import io
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path
from PIL import Image

OCR_SUFFIX_ONLY = "LEADING_DIGIT_MISSING"  # historic OCR-token category, NOT physical crop status

def ink_metrics(img, box, cutoff=130):
    x0,y0,x1,y1=map(int,box)
    if x1<=x0 or y1<=y0:
        return 0,0,0
    cropped=img.crop((x0,y0,x1,y1)).convert("L")
    raw=0
    nonruling=0
    ruling_cols=0
    full_line_threshold=max(6,int(cropped.height*0.85))
    for x in range(cropped.width):
        dark=sum(cropped.getpixel((x,y))<cutoff for y in range(cropped.height))
        raw+=dark
        if dark>=full_line_threshold:
            ruling_cols+=1
        else:
            nonruling+=dark
    return raw,nonruling,ruling_cols

def run(root_dir, evidence_csv, out_dir):
    root=Path(root_dir)
    out=Path(out_dir)
    out.mkdir(parents=True,exist_ok=True)
    evidence=list(csv.DictReader(Path(evidence_csv).open(encoding="utf8",newline="")))
    targets=[r for r in evidence if r["number_evidence"]==OCR_SUFFIX_ONLY]
    assert len(evidence)==304 and len(targets)==15,(len(evidence),len(targets))
    results=[]
    grids={}
    for row in targets:
        date,key=row["date"],row["key"]
        if date not in grids:
            raw=(root/f"geometry-{date}.tsv").read_text(encoding="utf8")
            grids[date]=int(raw.split("gridLeft=",1)[1].split("\n",1)[0])
        with zipfile.ZipFile(root/(date.replace("-","")+".zip")) as z:
            image=Image.open(io.BytesIO(z.read("source.png"))).convert("L")
            pieces=list(csv.DictReader(io.StringIO(z.read("crop_coordinates.csv").decode("utf8"))))
            first=next(p for p in pieces if p["key"]==f"{key[0]}{int(key[1:]):02d}")
            w,h=image.size
            rect={name:round(float(first[name])*(w if name in ("left","right") else h))
                  for name in ("left","top","right","bottom")}
            x0,x1,y0,y1=(rect[n] for n in ("left","right","top","bottom"))
            assert 0<=x0<x1<=w and 0<=y0<y1<=h,(date,key,rect)
            # Hypothetical rightward extension. It must not intrude into the
            # measured grid or the adjacent text column.
            pad=max(15,min(90,int((y1-y0)*1.1)))
            cap=grids[date]-8 if key.startswith("H") else int(.315*w)-5
            proposed_right=min(cap,x1+pad)
            external=(x1,y0+3,max(x1,proposed_right),y1-3)
            internal=(max(x0,x1-12),y0+3,x1,y1-3)
            dark,nonruling,rulecols=ink_metrics(image,external)
            innerdark,_,_=ink_metrics(image,internal)
            kind=("EXTRA_TEXTLIKE_INK" if nonruling else
                  "VERTICAL_RULING_ONLY" if dark else "BLANK")
            results.append({
                "date":date,"key":key,
                "ocr_evidence":row["number_tokens_in_first_crop"],
                "crop_right_px":x1,"safe_column_right_px":cap,
                "right_extension_examined_px":max(0,proposed_right-x1),
                "external_dark_raw":dark,"external_dark_nonruling":nonruling,
                "ruling_line_columns":rulecols,
                "inner_right_12px_dark":innerdark,
                "external_pixel_class":kind,
                "actual_printed_number_verified":"NO",
                "review_only":"YES"
            })
    assert len(results)==15
    counts=Counter(r["external_pixel_class"] for r in results)
    summary={
        "sources_with_suffix_only_tokens":len({r["date"] for r in results}),
        "suffix_only_ocr_candidates":len(results),
        "blank_beyond_crop_right":counts["BLANK"],
        "vertical_column_rule_only":counts["VERTICAL_RULING_ONLY"],
        "extra_textlike_ink_to_right":counts["EXTRA_TEXTLIKE_INK"],
        "verified_number_by_ocr":False,
        "new_ocr_calls":0,
        "canonical_writes":0,
        "review_only":True,
        "interpretation":"Test of right-side pixels ONLY. No claim that the number itself or entire clue has been visually verified."
    }
    with (out/"ocr-number-right-edge-pixels.csv").open("w",encoding="utf8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    (out/"ocr-number-right-edge-summary.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    (out/"ocr-number-right-edge-report.txt").write_text(
        "WIP OCR number suffix vs crop boundaries\n\n"+
        "Leading-digit-missing is an OCR token classification, not a claim of printed pixel loss.\n"+
        json.dumps(summary,ensure_ascii=False,indent=2)+"\n\n"+
        "\n".join(f'{r["date"]} {r["key"]}: OCR={r["ocr_evidence"]}, outside={r["external_pixel_class"]}, dark_textlike={r["external_dark_nonruling"]}' for r in results)+"\n",
        encoding="utf8")
    assert summary["extra_textlike_ink_to_right"]==0,summary
    print(json.dumps(summary,ensure_ascii=False,indent=2))

def self_test():
    img=Image.new("L",(80,30),255)
    assert ink_metrics(img,(40,5,60,25))==(0,0,0)
    for x in range(54,57):
        for y in range(9,14):
            img.putpixel((x,y),0)
    assert ink_metrics(img,(50,5,70,25))==(15,15,0)
    assert ink_metrics(img,(40,5,50,25))==(0,0,0)
    for y in range(5,25):
        img.putpixel((65,y),0)
    assert ink_metrics(img,(60,5,70,25))==(20,0,1)
    print("PASS: blank ink, missing glyph ink, and vertical ruler are distinct")

if __name__=="__main__":
    if len(sys.argv)==2 and sys.argv[1]=="--self-test":
        self_test()
    elif len(sys.argv)==4:
        run(*sys.argv[1:])
    else:
        raise SystemExit("Usage: audit_number_crop_integrity.py --self-test | <ocr-data-dir> <number-evidence.csv> <output-dir>")
