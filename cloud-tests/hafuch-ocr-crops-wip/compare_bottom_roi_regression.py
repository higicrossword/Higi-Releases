#!/usr/bin/env python3
"""HAFUCH_DEKEL only; compare two real Android OCR artifact ZIPs without OCR reruns.

Do NOT replace the old 97.5%-height capture based on a single recovered
terminal clue. An altered ROI scale can change tokenization elsewhere.
"""
import csv,io,json,re,sys,zipfile
from pathlib import Path
H={1,5,8,9,10,12,14,15,18,19,21,22,24,25}
V={1,2,3,4,5,6,7,11,13,16,17,19,20,23}
START=re.compile(r"^([0-9]{1,2})[.,:]$")
def table(z,p):
    rows=z.read(p).decode("utf8").splitlines()
    assert rows,p
    cols=rows[0].split("\t")
    parsed=[]
    for i,line in enumerate(rows[1:],2):
        values=line.split("\t")
        assert len(values)==len(cols),(p,i,"invalid literal TSV width")
        parsed.append(dict(zip(cols,values)))
    return parsed
def detected(z,date):
    w=table(z,f"hafuch-roi-20/{date}/words.tsv")
    l=table(z,f"hafuch-roi-20/{date}/lines.tsv")
    heading=sorted(int(i["top"]) for i in l if i["heading"]=="V")
    twentyfive=sorted(int(i["top"]) for i in w if i["masked"].strip()=="25.")
    ones=sorted(int(i["top"]) for i in w if i["masked"].strip()=="1.")
    second=[y for y in ones if twentyfive and y>twentyfive[0]]
    boundary=heading[0] if heading else (second[0] if second else None)
    if boundary is not None and twentyfive and boundary<twentyfive[0]:
        boundary=second[0] if second else None
    assert boundary is not None,("unverified H/V split",date)
    results={"H":set(),"V":set()}
    for i in w:
        m=START.fullmatch(i["masked"].strip())
        if not m:continue
        n=int(m.group(1))
        d="H" if int(i["top"])<boundary else "V"
        if n in (H if d=="H" else V):
            results[d].add(n)
    return results,w
def run(oldfile,newfile,output):
    result=[]
    with zipfile.ZipFile(oldfile) as old,zipfile.ZipFile(newfile) as new:
        a={r["date"]:r for r in table(old,"hafuch-roi-20/manifest.tsv")}
        b={r["date"]:r for r in table(new,"hafuch-roi-20/manifest.tsv")}
        assert len(a)==len(b)==20 and set(a)==set(b)
        for day in sorted(a):
            x,y=a[day],b[day]
            assert x["sha256"]==y["sha256"],("different source",day)
            assert x["grid"]==y["grid"]=="13x13"
            before,_=detected(old,day)
            after,_=detected(new,day)
            for d in ("H","V"):
                gone=sorted(before[d]-after[d])
                added=sorted(after[d]-before[d])
                result.append({"date":day,"direction":d,
                     "old_number_count":len(before[d]),"full_height_number_count":len(after[d]),
                     "old_only_numbers":gone,"full_height_only_numbers":added})
    gained=sum(len(x["full_height_only_numbers"]) for x in result)
    lost=sum(len(x["old_only_numbers"]) for x in result)
    oldtotal=sum(x["old_number_count"] for x in result)
    newtotal=sum(x["full_height_number_count"] for x in result)
    assert (oldtotal,newtotal,gained,lost)==(499,497,7,9),(
        "Pinned ROI evidence has changed",oldtotal,newtotal,gained,lost)
    source0807=next(x for x in result if x["date"]=="2026-08-07" and x["direction"]=="V")
    assert 23 in source0807["full_height_only_numbers"],source0807
    same0807=next(x for x in result if x["date"]=="2026-08-07" and x["direction"]=="H")
    assert 24 in same0807["old_only_numbers"],same0807
    summary={"series_id":"HAFUCH_DEKEL","original_images":20,
      "old_ocr_number_tokens":oldtotal,"full_height_number_tokens":newtotal,
      "full_height_newly_recognized_start_tokens":gained,
      "old_starts_not_recognized_at_full_height":lost,
      "verified_terminal_recovery":"2026-08-07 V23 recognized in full height (old image OCR lost number)",
      "verified_regression":"2026-08-07 H24 standalone number lost by full-height OCR",
      "decision":"REJECT blanket full-height replacement; prefer default original ROI and source-pixel-bounded terminal exception",
      "limitations":"OCR token counts are not crop validity; this report does not prove correct V23 crop bounds or every printed start",
      "other_series_modified":False,"firebase_writes":0,"canonical_writes":0,"release_created":False,
      "comparisons":result}
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    Path(output).write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({k:v for k,v in summary.items() if k!="comparisons"},ensure_ascii=False,indent=2))
def self_test():
    assert START.fullmatch("23.") and START.fullmatch("24:")
    assert not START.fullmatch("(3)") and not START.fullmatch("H23.")
    assert len(H)==len(V)==14
    print("PASS frozen Hafuch token grammar and fixture expectations")
if __name__=="__main__":
    if sys.argv[1:]==["--self-test"]:self_test()
    elif len(sys.argv)==4:run(*sys.argv[1:])
    else:raise SystemExit("Usage: compare_bottom_roi_regression.py --self-test OR before.zip after.zip result.json")
