#!/usr/bin/env python3
"""WIP-only: audit OCR source-anchor evidence; never edit Canonical or approve crops."""
import csv
import io
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

NUM = re.compile(r"^([0-9]{1,2})([.:,]?)$")
REV = re.compile(r"^([.:])([0-9]{1,2})$")
BIDI = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]")

def numeric(text):
    t = BIDI.sub("", text).strip().replace("\uff0e", ".")
    m = NUM.fullmatch(t)
    if m:
        return int(m.group(1)), m.group(2)
    m = REV.fullmatch(t)
    if m:
        return int(m.group(2)), m.group(1)
    return None

def word_inside(word, rect):
    box = word["box"]
    x = (box[0] + box[2]) / 2
    y = (box[1] + box[3]) / 2
    return rect[0] <= x < rect[2] and rect[1] <= y < rect[3]

def parse_geometry(raw):
    image = {}
    words = []
    parts = {}
    starts = {}
    for line in raw.splitlines():
        p = line.split("\t")
        if p[0] == "IMAGE":
            width, height = map(int, p[1].split("x"))
            image = {"width":width, "height":height, "grid_left":int(p[2].split("=")[1])}
        elif p[0] == "WORD" and len(p) >= 4:
            words.append({"text":p[1], "confidence":int(p[2]),
                          "box":[int(v) for v in p[3].split(",")]})
        elif p[0] == "PART":
            parts.setdefault(p[1], []).append([int(v) for v in p[3].split(",")])
        elif p[0] == "SOURCE":
            starts[p[1]] = {"parts":int(p[2].split("=")[1]),
                             "strong":p[4] == "strongOwn=true",
                             "reason":"\t".join(p[5:])}
    assert image, "Missing image dimensions"
    return image, words, parts, starts

def evidence(label, words, strong):
    number = int(label[1:])
    tokens = [(w, *n) for w in words if (n := numeric(w["text"])) is not None]
    if strong:
        assert any(n == number and punctuation in (".", ":") and w["confidence"] >= 60
                   for w, n, punctuation in tokens), (label, "strong marker mismatch")
        return "STRONG_PRINTED_MARKER"
    if any(n == number and punctuation in (".", ":") for _, n, punctuation in tokens):
        return "LOW_CONFIDENCE_PRINTED_MARKER"
    if any(n == number and punctuation == "," for _, n, punctuation in tokens):
        return "COMMA_INSTEAD_OF_DOT"
    if any(n == number and punctuation == "" for _, n, punctuation in tokens):
        return "NUMBER_WITHOUT_PUNCTUATION"
    if number >= 10 and any(n == number % 10 for _, n, _ in tokens):
        return "LEADING_DIGIT_MISSING"
    return "NO_NUMERIC_EVIDENCE"

def audit(folder, output):
    folder, output = Path(folder), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with (folder / "manifest.csv").open(encoding="utf8", newline="") as f:
        manifest = list(csv.DictReader(f))
    assert len(manifest) == 19, ("Missing fixtures", len(manifest))
    findings = []
    errors = []
    for item in manifest:
        date = item["date"]
        image, words, parts, starts = parse_geometry(
            (folder / f"geometry-{date}.tsv").read_text(encoding="utf8"))
        assert int(item["proposed"]) == 16 and len(starts) == len(parts) == 16, date
        with zipfile.ZipFile(folder / item["zip"]) as z:
            assert z.testzip() is None, ("Invalid ZIP", date)
            crops = list(csv.DictReader(io.StringIO(z.read("crop_coordinates.csv").decode("utf8"))))
            assert {r["key"] for r in crops} == {key[0]+key[1:].zfill(2) for key in parts}, date
        for label in sorted(starts):
            rects = parts[label]
            assert len(rects) == starts[label]["parts"], (date, label, "part count")
            first = [w for w in words if word_inside(w, rects[0])]
            kind = evidence(label, first, starts[label]["strong"])
            crosses_grid = label[0] == "H" and any(r[2] >= image["grid_left"] for r in rects)
            if crosses_grid:
                errors.append((date, label, "SOURCE_GRID_INTRUSION"))
            if kind == "NO_NUMERIC_EVIDENCE":
                errors.append((date, label, "NO_NUMERIC_EVIDENCE"))
            findings.append({
                "date":date, "key":label, "number_evidence":kind,
                "source_grid_safe":not crosses_grid, "parts":len(rects),
                "number_tokens_in_first_crop":" | ".join(
                    f'{w["text"]}({w["confidence"]})' for w in first if numeric(w["text"]) is not None),
                "reason":starts[label]["reason"]
            })
    counts = Counter(r["number_evidence"] for r in findings)
    assert len(findings) == 304, len(findings)
    assert counts["STRONG_PRINTED_MARKER"] >= 275, ("Strong markers decreased", dict(counts))
    assert not errors, ("Unanchored or crossing grid", errors[:8])
    expected = {
        "STRONG_PRINTED_MARKER":275,
        "LEADING_DIGIT_MISSING":15,
        "NUMBER_WITHOUT_PUNCTUATION":11,
        "LOW_CONFIDENCE_PRINTED_MARKER":2,
        "COMMA_INSTEAD_OF_DOT":1,
    }
    assert dict(counts) == expected, ("Unexpected WIP number-evidence baseline", dict(counts))
    result = {
        "puzzles":len(manifest), "review_only_proposals":len(findings),
        "number_evidence_counts":dict(sorted(counts.items())),
        "non_strong_number_candidates":304-counts["STRONG_PRINTED_MARKER"],
        "source_grid_violations":len(errors),
        "automatic_canonical_approval":False,
        "scope":"WIP diagnostics only; NOT visual crop correctness"
    }
    (output / "ocr-number-evidence-summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf8")
    with (output / "ocr-number-evidence.csv").open("w",encoding="utf8",newline="") as f:
        writer = csv.DictWriter(f, fieldnames=findings[0].keys())
        writer.writeheader()
        writer.writerows(findings)
    lines = ["OCR number evidence — WIP only", "",
             "19/19 sources; 304 REVIEW_ONLY crops; 29 without a strong printed-number marker", ""]
    lines += [f"{key}: {value}" for key, value in sorted(counts.items())]
    lines += ["", "Unverified printed number evidence; visual review required:", ""]
    lines += [
        f'{r["date"]} {r["key"]}: {r["number_evidence"]} | {r["number_tokens_in_first_crop"]}'
        for r in findings if r["number_evidence"] != "STRONG_PRINTED_MARKER"
    ]
    (output / "ocr-number-evidence-report.txt").write_text("\n".join(lines)+"\n",encoding="utf8")
    print(json.dumps(result, ensure_ascii=False, indent=2))

def self_test():
    def w(t,c):
        return {"text":t,"confidence":c,"box":[1,1,11,12]}
    assert numeric("8.") == (8, ".")
    assert numeric("8") == (8, "")
    assert numeric("1,") == (1, ",")
    assert numeric(".12") == (12, ".")
    assert evidence("H8", [w("8.",90)],True) == "STRONG_PRINTED_MARKER"
    assert evidence("H8", [w("8.",50)],False) == "LOW_CONFIDENCE_PRINTED_MARKER"
    assert evidence("H8", [w("8",90)],False) == "NUMBER_WITHOUT_PUNCTUATION"
    assert evidence("H13", [w("3.",90)],False) == "LEADING_DIGIT_MISSING"
    assert evidence("H1", [w("1,",50)],False) == "COMMA_INSTEAD_OF_DOT"
    assert evidence("H1", [w("93,",90)],False) == "NO_NUMERIC_EVIDENCE"
    print("PASS 10 printed-number audit regressions")

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        self_test()
    elif len(sys.argv) >= 2:
        audit(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else Path(sys.argv[1]).parent)
    else:
        raise SystemExit("Usage: audit_number_evidence.py --self-test OR <ocr-cloud-v209-dir> [out-dir]")
