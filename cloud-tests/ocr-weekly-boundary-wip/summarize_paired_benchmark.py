#!/usr/bin/env python3
"""WIP only: paired same-Android-process V199 baseline/terminal source-anchor timings."""
import csv,json,statistics,sys
from pathlib import Path
TARGET={"11-11-26":"H5","02-11-26":"V1","21-10-26":"V1"}
def analyze(source,out):
    with Path(source).open(encoding="utf-8",newline="") as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==19,("Expected 19 source images",len(rows))
    assert len({r["date"] for r in rows})==19
    for r in rows:
        assert int(r["samples"])==30 and int(r["warmups"])==10
        assert r["changed_source_keys"]==TARGET.get(r["date"],""),r
        for key in ("baseline_median_ns","patched_median_ns","baseline_p95_ns","patched_p95_ns","ratio_median"):
            assert float(r[key])>0,("Invalid timing",r,key)
    ratios=[float(r["ratio_median"]) for r in rows]
    old=[float(r["baseline_median_ns"]) for r in rows]
    new=[float(r["patched_median_ns"]) for r in rows]
    report={"scope":"Source-anchor inspect only; excludes OCR, grid scan, full crop pipeline, I/O and UI",
      "design":"Same emulator/process, two code copies, identical OCR inputs, 10 warmups and 30 AB/BA timed pairs per fixture",
      "sources":len(rows),"timed_pairs":sum(int(r["samples"]) for r in rows),
      "median_old_us":round(statistics.median(old)/1000,3),
      "median_new_us":round(statistics.median(new)/1000,3),
      "median_per_source_ratio":round(statistics.median(ratios),5),
      "three_changed_keys":TARGET,"results":rows,
      "release_modified":False,"firebase_writes":0,"canonical_writes":0,
      "limitation":"Cannot infer app end-to-end latency or user-perceived performance from this microbenchmark"}
    Path(out).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({k:v for k,v in report.items() if k!="results"},ensure_ascii=False,indent=2))
def self_test():
    assert len(TARGET)==3 and statistics.median([1,2,3])==2
    print("PASS paired source-anchor benchmark summarizer smoke tests")
if __name__=="__main__":
    if sys.argv[1:]==["--self-test"]:self_test()
    elif len(sys.argv)==3:analyze(*sys.argv[1:])
    else:raise SystemExit("Usage: summarize_paired_benchmark.py --self-test OR input.csv report.json")
