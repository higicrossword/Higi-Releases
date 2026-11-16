#!/usr/bin/env python3
"""Hafuch-only, read-only evidence audit; does NOT produce or approve OCR crops."""
import csv,json,sys
from pathlib import Path

def grid_numbering(mask):
    assert len(mask)==13 and all(len(r)==13 for r in mask)
    across,down=[],[]
    n=0
    for row in range(13):
        for col in range(12,-1,-1): # printed Hebrew grid numbers run right-to-left
            if mask[row][col]=='#':
                continue
            starts_h=(col==12 or mask[row][col+1]=='#') and col>0 and mask[row][col-1]=='.'
            starts_v=(row==0 or mask[row-1][col]=='#') and row<12 and mask[row+1][col]=='.'
            if not (starts_h or starts_v):
                continue
            n+=1
            if starts_h:across.append(n)
            if starts_v:down.append(n)
    return across,down

def load_tsv(path):
    with Path(path).open(encoding="utf8",newline="") as f:
        return list(csv.DictReader(f,delimiter='\t'))

def audit(reference,artifact_folder,destination):
    j=json.loads(Path(reference).read_text(encoding="utf8"))
    assert j["series_id"]=="HAFUCH_DEKEL"
    rows=j["blocked_cells_image_top_to_bottom"]
    across,down=grid_numbering(rows)
    expected={"H":[1,5,8,9,10,12,14,15,18,19,21,22,24,25],
              "V":[1,2,3,4,5,6,7,11,13,16,17,19,20,23]}
    assert across==expected["H"],("Grid across sequence changed",across)
    assert down==expected["V"],("Grid down sequence changed",down)
    assert len(across)+len(down)==28
    root=Path(artifact_folder)
    manifest=load_tsv(root/"ocr-cross-series-wip/summary.tsv")
    entry=next(x for x in manifest if x["series"]=="HAFUCH_DEKEL")
    assert int(entry["grid_start_numbers"])==28 and entry["grid"]=="13x13"
    assert int(entry["ocr_lines"])>0
    width,height=int(entry["image_w"]),int(entry["image_h"])
    headings=load_tsv(root/"ocr-cross-series-wip/headings-HAFUCH_DEKEL.tsv")
    assert len(headings)==2 and [x["direction"] for x in headings]==["H","V"]
    assert 0<int(headings[0]["top"])<int(headings[1]["top"])<height
    numeric=load_tsv(root/"ocr-cross-series-wip/number-tokens-HAFUCH_DEKEL.tsv")
    observed={}
    details=[]
    for direction in ("H","V"):
        section_start=int(headings[0 if direction=="H" else 1]["top"])
        section_end=int(headings[1]["top"]) if direction=="H" else height
        candidates=[]
        for token in numeric:
            if int(token["confidence"])<65: continue
            # PROVISIONAL numeric-token inventory only, NOT a crop rule:
            # this bounds the text region beyond the approx grid right for 6Nov.
            if int(token["left"])<int(width*.67): continue
            if not section_start<=int(token["top"])<section_end:continue
            val=int(token["number"])
            if val not in expected[direction]:continue
            candidates.append(token)
        matched=sorted(set(int(t["number"]) for t in candidates))
        missing=sorted(set(expected[direction])-set(matched))
        observed[direction]={"expected":expected[direction],
             "numeric_token_matches":matched,"count":len(matched),
             "missing_numeric_token_candidates":missing,
             "warning":"Dots/printed punctuation NOT VERIFIED by this sanitized report."}
        for t in candidates:
            details.append({"dir":direction,"number":int(t["number"]),
              "confidence":int(t["confidence"]),"box":[int(t[k]) for k in
                  ("left","top","right","bottom")]})
    assert observed["H"]["count"]==11 and observed["V"]["count"]==13
    assert observed["H"]["missing_numeric_token_candidates"]==[8,15,19]
    assert observed["V"]["missing_numeric_token_candidates"]==[20]
    report={"source":"2026-11-06 actual Android OCR, run 43911067998",
      "series":"HAFUCH_DEKEL",
      "grid_key_counts":{"H":len(across),"V":len(down)},
      "raw_ocr_lines":int(entry["ocr_lines"]),
      "source_width":width,"source_height":height,
      "observed_section_headings":[{"direction":x["direction"],"bbox":
         [int(x[k]) for k in ("left","top","right","bottom")]} for x in headings],
      "numeric_candidates":observed,"numeric_candidate_boxes":details,
      "already_emitted_review_only_crops":int(entry["unique_proposals"]),
      "not_tested":"Same-line N punctuation, OCR-merged starts, exact crop bounds, multiple-image consistency",
      "assumption":"0.67*width only for this offline numerical inventory; production must use actual measured grid RIGHT edge",
      "automatic_approval":False,
      "user_edited_or_verified_modified":False,
      "firebase_writes":0,"canonical_writes":0,
      "release_created":False}
    Path(destination).parent.mkdir(parents=True,exist_ok=True)
    Path(destination).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({k:v for k,v in report.items() if k!="numeric_candidate_boxes"},ensure_ascii=False,indent=2))
def self_test():
    mask=[".....#.......",".#.#.#.#.#.#.",".......#.....",
      ".#.#.#.#.###.","...#........#",".#.###.#.#.#.",
      "......#......",".#.#.#.###.#.","#........#...",
      ".###.#.#.#.#.",".....#.......",".#.#.#.#.#.#.",
      ".......#....."]
    h,v=grid_numbering(mask)
    assert h==[1,5,8,9,10,12,14,15,18,19,21,22,24,25]
    assert v==[1,2,3,4,5,6,7,11,13,16,17,19,20,23]
    print("PASS Hebrew grid numbering 14 across, 14 down, 28 total")
if __name__=="__main__":
    if sys.argv[1:]==["--self-test"]:self_test()
    elif len(sys.argv)==4:audit(*sys.argv[1:])
    else:raise SystemExit("Usage: audit_printed_number_evidence.py --self-test OR template.json artifact_folder report.json")
