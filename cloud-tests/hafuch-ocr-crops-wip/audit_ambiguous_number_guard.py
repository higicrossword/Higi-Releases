#!/usr/bin/env python3
"""Read-only HAFUCH_DEKEL numbered-boundary risk audit of 20 publisher originals.

Uses existing SHA-pinned source JPEGs and masked one-pass Android OCR geometry.
Creates REVIEW_ONLY exclusion guards; never guesses missing numbered starts,
changes crop coordinates, or writes any app/Canonical/Firebase state.
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from statistics import median

SERIES = "HAFUCH_DEKEL"
EXPECTED = {
    "H": (1,5,8,9,10,12,14,15,18,19,21,22,24,25),
    "V": (1,2,3,4,5,6,7,11,13,16,17,19,20,23),
}
NUMBER = re.compile(r"^([0-9]{1,2})[.,:]$")
COMMA_NUMBER = re.compile(r"^([0-9]{1,2}),$")
PAREN_LENGTH = re.compile(r"^\([0-9]+(?:[,;][0-9]+)*\)[.,;:]?$")
MERGED_START = re.compile(r"(?<![0-9])([0-9]{1,2})[.:](?=[;)])")
MIN_CONFIDENCE = 65

def read_tsv(z, name):
    rows = z.read(name).decode("utf-8").splitlines()
    if not rows:
        raise ValueError("Empty TSV " + name)
    fields = rows[0].split("\t")
    out = []
    for lineno, row in enumerate(rows[1:], 2):
        values = row.split("\t")
        if len(values) != len(fields):
            raise ValueError(f"Malformed TSV: {name}:{lineno}")
        out.append(dict(zip(fields, values)))
    return out

def source_rect(word, manifest):
    s = float(manifest["roi_scale"])
    if s <= 0:
        raise ValueError("Invalid ROI scale")
    x0, y0 = int(manifest["roi_left"]), int(manifest["roi_top"])
    return [round(int(word["left"]) / s + x0),
            round(int(word["top"]) / s + y0),
            round(int(word["right"]) / s + x0),
            round(int(word["bottom"]) / s + y0)]

def physical_order(words, typical_height):
    """Physical text rows top-to-bottom; tokens within a row right-to-left."""
    ordered = sorted(words, key=lambda w: (
        (w["rect"][1] + w["rect"][3]) / 2, -w["rect"][0]))
    rows = []
    for word in ordered:
        cy = (word["rect"][1] + word["rect"][3]) / 2
        if rows:
            last = rows[-1]
            row_cy = median((w["rect"][1] + w["rect"][3]) / 2 for w in last)
            if abs(cy - row_cy) <= max(2, typical_height * .48):
                last.append(word)
                continue
        rows.append([word])
    return [w for row in rows for w in sorted(row, key=lambda w: -w["rect"][0])]

def rect_intersects(a, b):
    """Strict source-pixel intersection; touching edges alone are allowed."""
    return max(a[0],b[0]) < min(a[2],b[2]) and max(a[1],b[1]) < min(a[3],b[3])

def crossing_guards(report, date, direction, proposed_rectangles):
    """Pure read-only hook for a later admin REVIEW_ONLY crop-geometry stage.

    proposed_rectangles is the actual list of SOURCE-pixel row rectangles,
    not a page-level bounding box. All intersections require manual review;
    no number is treated as an independently verified printed start here.
    """
    for source in report["sources"]:
        if source["date"] == date:
            if source["status"] == "HEADING_UNVERIFIED":
                return [{"reason":"HEADING_UNVERIFIED", "source_rect":None}]
            return [g for g in source["boundary_guards"]
                    if g["direction"] == direction
                    and any(rect_intersects(g["source_rect"], r)
                            for r in proposed_rectangles)]
    raise ValueError("Date not present in pinned 20-source archive: " + date)

def analyze_one(m, words, lines):
    date = m["date"]
    width, height = int(m["width"]), int(m["height"])
    if m["grid"] != "13x13" or width <= 0 or height <= 0:
        raise ValueError("Source grid not verified: " + date)
    heads = {d: [source_rect(l,m) for l in lines if l["heading"] == d]
             for d in ("H","V")}
    if len(heads["V"]) != 1 or len(heads["H"]) > 1 or (
        heads["H"] and heads["H"][0][1] >= heads["V"][0][1]):
        return {"date":date,"status":"HEADING_UNVERIFIED",
                "H_heading_count":len(heads["H"]),
                "V_heading_count":len(heads["V"]),
                "boundary_guards":[],"automatically_approved_crops":0}
    verified_h = len(heads["H"]) == 1
    htop = heads["H"][0][1] if verified_h else int(m["roi_top"])
    vtop = heads["V"][0][1]
    grid_right = float(m["grid_right"])
    candidates=[]
    for word in words:
        box=source_rect(word,m)
        if not (0 <= box[0] < box[2] <= width and
                0 <= box[1] < box[3] <= height):
            raise ValueError(f"Word box out of image bounds: {date} {box}")
        if box[0] < grid_right or box[1] < htop:
            continue
        direction="H" if box[1] < vtop else "V"
        token=word["masked"].strip()
        confidence=int(word["confidence"])
        if confidence < MIN_CONFIDENCE:
            continue
        numeric=NUMBER.fullmatch(token)
        comma=COMMA_NUMBER.fullmatch(token)
        merged=MERGED_START.search(token) if not PAREN_LENGTH.fullmatch(token) else None
        if not (numeric or comma or merged):
            continue
        category="NUMERIC" if numeric else ("COMMA_UNVERIFIED" if comma else "MERGED_UNVERIFIED")
        number=int((numeric or comma or merged).group(1))
        candidates.append(dict(direction=direction, number=number,
                               category=category, token=token,rect=box,
                               confidence=confidence))
    heights=[a["rect"][3]-a["rect"][1] for a in candidates]
    typical=median(heights) if heights else 20
    trace={};guards=[];monotone={"H":0,"V":0}
    for direction in ("H","V"):
        prev=0
        trace[direction]=[]
        for word in physical_order(
                [w for w in candidates if w["direction"] == direction],typical):
            number=word["number"]
            if word["category"] == "COMMA_UNVERIFIED":
                reason="PUNCTUATION_UNVERIFIED"
            elif word["category"] == "MERGED_UNVERIFIED":
                reason="OCR_MERGED_POSSIBLE_START"
            elif number not in EXPECTED[direction]:
                reason="NOT_EXPECTED_FOR_DIRECTION"
            elif number <= prev:
                reason="OUT_OF_ORDER_OR_DUPLICATE"
            else:
                reason=None
                prev=number
                monotone[direction]+=1
            entry={"token":word["token"],"candidate_number":number,
                   "source_rect":word["rect"],"ocr_confidence":word["confidence"],
                   "boundary_status":"MONOTONE_OCR_ONLY" if reason is None else "BLOCK_CROP_CROSSING_TOKEN",
                   "reason":reason}
            trace[direction].append(entry)
            if reason:
                guards.append({"direction":direction,**entry})
    return {"date":date,
            "status":"OCR_BOUNDARY_REVIEW_ONLY" if verified_h
                     else "H_HEADING_PROVISIONAL_BLOCKERS_ONLY",
            "source_sha256":m["sha256"],"H_heading_count":int(verified_h),
            "V_heading_count":1,"ocr_monotone_number_tokens":monotone,
            "boundary_guards":guards,"number_trace":trace,
            "automatically_approved_crops":0}

def audit(originals, old_ocr, destination):
    with zipfile.ZipFile(originals) as source, zipfile.ZipFile(old_ocr) as ocr:
        manifest=read_tsv(ocr,"hafuch-roi-20/manifest.tsv")
        if len(manifest)!=20 or len({m["date"] for m in manifest})!=20:
            raise ValueError("20 unique source images required")
        results=[]
        for m in manifest:
            date=m["date"]
            raw=source.read(f"hafuch-20-source-results/images/{date}.jpg")
            if hashlib.sha256(raw).hexdigest() != m["sha256"]:
                raise ValueError("SHA mismatch: " + date)
            prefix=f"hafuch-roi-20/{date}/"
            words=read_tsv(ocr,prefix+"words.tsv")
            lines=read_tsv(ocr,prefix+"lines.tsv")
            if len(words)!=int(m["ocr_words"]) or len(lines)!=int(m["ocr_lines"]):
                raise ValueError("OCR manifest mismatch: " + date)
            results.append(analyze_one(m,words,lines))
    report={"series_id":SERIES,"original_sources_sha_verified":20,
            "ocr_calls_made":0,"ai_calls_made":0,"production_changed":False,
            "firebase_writes":0,"canonical_writes":0,"new_apk_or_release":False,
            "risk_guards":sum(len(x["boundary_guards"]) for x in results),
            "guarded_sources":sum(bool(x["boundary_guards"]) for x in results),
            "sources_with_both_headings_verified":sum(x["status"]=="OCR_BOUNDARY_REVIEW_ONLY" for x in results),
            "sources_with_provisional_H_for_guards_only":sum(x["status"]=="H_HEADING_PROVISIONAL_BLOCKERS_ONLY" for x in results),
            "semantics":"Review blockers only, not validated number starts or clue rectangles",
            "sources":results}
    Path(destination).parent.mkdir(parents=True,exist_ok=True)
    Path(destination).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return report

def self_test():
    assert SERIES=="HAFUCH_DEKEL"
    assert len(EXPECTED["H"])==len(EXPECTED["V"])==14
    assert NUMBER.fullmatch("15.") and NUMBER.fullmatch("20:")
    assert not NUMBER.fullmatch("(3)")
    assert COMMA_NUMBER.fullmatch("17,")
    assert PAREN_LENGTH.fullmatch("(3,4).")
    assert not MERGED_START.search("(3,4).")
    assert MERGED_START.search("(20.;)3,2.")
    assert [w["number"] for w in physical_order(
        [{"rect":[120,101,133,117],"number":23},
         {"rect":[200,100,220,116],"number":20},
         {"rect":[180,146,202,162],"number":25}],16)] == [20,23,25]
    assert rect_intersects([10,10,20,20],[19,19,25,25])
    assert not rect_intersects([10,10,20,20],[20,20,25,25])
    fixture={"sources":[{"date":"d","status":"OCR_BOUNDARY_REVIEW_ONLY",
              "boundary_guards":[{"direction":"V","source_rect":[20,20,30,30]}]}]}
    assert len(crossing_guards(fixture,"d","V",[[0,0,21,21]]))==1
    assert crossing_guards(fixture,"d","H",[[0,0,21,21]])==[]
    assert crossing_guards(fixture,"d","V",[[0,0,20,20]])==[]
    print("PASS synthetic RTL, numeric grammar, source-pixel intersection and REVIEW_ONLY crop blockers")

if __name__=="__main__":
    if sys.argv[1:]==["--self-test"]:
        self_test()
    elif len(sys.argv)==4:
        report=audit(*sys.argv[1:])
        print(json.dumps({k:v for k,v in report.items() if k!="sources"},
                         ensure_ascii=False,indent=2))
    else:
        raise SystemExit("Usage: audit_ambiguous_number_guard.py --self-test OR originals.zip old-ocr.zip report.json")
