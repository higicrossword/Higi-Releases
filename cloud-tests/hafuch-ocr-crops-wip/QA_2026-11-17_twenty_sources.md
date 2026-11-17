# Higi — Hafuch al Hafuch — twenty original OCR evidence results (2026-11-17)

**Only `HAFUCH_DEKEL`**. This is an analysis of pinned Android OCR evidence and source images; **NOT** an app-integrated algorithm, automatic decoded-clue approval, or a new release.

## Evidence and verified run
- [Android ROI-only OCR run 44047765517](https://github.com/higicrossword/Higi-Releases/actions/runs/44047765517): **SUCCESS**. Twenty publisher-original, SHA-pinned JPEGs dated 2026-07-03 through 2026-11-13; every image passed the source-pixel-verified 13×13 grid template. Each source's right-of-grid region was processed exactly once with the existing local Android OCR engine. The artifact `higi-hafuch-twenty-roi-ocr-word-geometry-wip` ID **14312896246** contains only sanitized OCR word and line boxes, source hashes and processing timings. No production changes.
- [Independent number audit 44052536858](https://github.com/higicrossword/Higi-Releases/actions/runs/44052536858): **SUCCESS**. Exactly **499/560** expected distinct start numbers appeared in the correct H/V section as separate OCR word tokens with a numeric prefix and punctuation. **61/560** missing as such a token, not necessarily missing in the printed JPEG. Missing `מאוזן` heading on 3/20 images and missing `מאונך` on 1/20 required provisional section split by the second printed `1.` following the across `25.` token. Those inferred section starts are **not approved printed heading coordinates**.
- Using original source JPEGs (not additional OCR), visually examined contact sheets of examples from the missing tokens. Confirmed multiple types of failure: OCR loses the leading `1` (`15.`→`5.` and `18.`→`8.`), loses the leading `2` (`20.`→`0.`), or merges the previous clue's length marker and the next number. No substitution based on expected sequence is permitted without independent printed-pixel evidence.

## Strict offline crop geometry experiment (NOT application-integrated)
A read-only independent Python trial used the exact Android OCR word boxes and their original measured ROI-to-source pixel mapping across **all 20** source images.

The experiment grouped boxes by physically OCR-detected rows, sorted words right-to-left, and required a distinct current and immediately next expected printed number token. A final clue additionally required a physically detected numeric answer-length marker. It did **not** hallucinate missing numbers and withheld clues whose next number was missing/ambiguous or out of physical order.

| Gate | Count | Interpretation |
|---|---:|---|
| Expected clues | 560 | 20 × 28 |
| Preliminary rectangular geometry candidates | **397** | not checked for collisions |
| Pairwise same-section rectangle collisions | **4 pairs** | dates 2026-10-09 (V3/V4 and V19/V20), 2026-08-21 (H24/H25), 2026-07-31 (V13/V17) |
| Clues withheld because of rectangle collision | **8** | fail closed rather than trimming ink |
| Remaining nonoverlapping REVIEW_ONLY candidate geometries | **389** | **not** visually certified |
| Of those, containing a clearly recognized numeric OCR enumeration token | **368** | marker presence does not establish clue completeness |
| Of those, without a clearly recognized numeric OCR enumeration token | **21** | may still contain a visible printed marker not recognized by OCR |
| All candidates still requiring full visual pixel review | **389** | neither clean boxes nor numeral count proves correct crop |

**CAUTION:** This is a deliberately conservative *different trial* from the single-image, source-pixel-split prototype that produced 28/28 on 2026-11-06. On this all-source independent trial, that same 2026-11-06 source yields **19/28** noncollision candidates because missing/misread numbers are withheld rather than reconstructed. Do not misrepresent these as the final same-engine application outputs. The single-image proof of 28/28 does NOT generalize automatically to every source.

## Remaining issues before a real crop implementation can be called correct
1. Recover individual OCR-missing/merged printed start numbers **only** via independently verified source ink/gutter evidence. On 2026-11-06 specifically, H8/H15/H19/V20 were recovered by the prior pixel-proof prototype. Do not assume the same per-image coordinates or that the same four labels are missing on other dates.
2. Split shared physical OCR rows at printed-word bounds without cutting a letter or including another clue's printed number. Rectangular collisions must remain withheld unless the actual source image proves disjoint word pixels.
3. Add a source-verified terminal/end-of-clue rule for the 21 possible crops with no cleanly detected OCR enumeration marker.
4. Audit all newly emitted crops against **the full original image**; correct text, printed number and length must be visible and no neighboring clue present. Until this visual QA is complete, **389 are review-only geometry candidates**, not 389 correct crops.
5. After that, port the Hafuch-only algorithm to **ephemeral Android WIP** and run regression. Do not change or alter the frozen Yedioth Monday/Wednesday algorithms; do not create APK/release or alter Canonical/Firebase without a separate user instruction.

The image manifest and numeric audit are reproducible from the pinned GitHub Actions artifacts. The experimental Python working analysis is not application source, and its results must not be treated as a published feature.

## Full-bottom ROI controlled comparison (20 source images, two real Android runs)

**Evidence:** [CI gate 44124709211](https://github.com/higicrossword/Higi-Releases/actions/runs/44124709211) PASS, artifact `higi-hafuch-bottom-roi-20-ab-wip`. Compares genuine local Android OCR geometry from source runs [44047765517](https://github.com/higicrossword/Higi-Releases/actions/runs/44047765517) (ROI stops at 97.5% source height) and [44099678598](https://github.com/higicrossword/Higi-Releases/actions/runs/44099678598) (ROI extends to image bottom). Both processed **the same 20 SHA-pinned JPEGs** with the existing OCR engine, and both recognized the pixel-proven 13×13 grid.

- Standalone numbered anchor coverage with unchanged strict grammar and H/V section split: **499/560** originally, **497/560** with full-height ROI.
- The full-height input **gains 7** individually numbered tokens and **loses 9** tokens present under the original ROI settings.
- In the **2026-08-07** original image, **V23** improves materially: the expanded Android OCR reports `23.` confidence 93 and `(3).` confidence 92 at the bottom; the old OCR did not read V23 as a complete start and misread `(3)`. The printed source does contain both. However **H24** ceases to be a clean standalone start under the expanded OCR, demonstrating a concrete same-image tradeoff.
- On **2026-08-28**, **2026-10-30** and **2026-11-06**, the total number of OCR words falls by 2, 3 and 1 respectively in the new capture. In the aggregate across all sources, word count rises from 4,386 to 4,406, but this **does not guarantee** preserved per-word recognition or correct crop boundaries.
- **Decision:** DO NOT change the global/default `HAFUCH_DEKEL` OCR region bottom from 97.5% to 100% unconditionally. This would cause a demonstrated 9-number regression even though it fixes one terminal clue.
- **Next safe design:** retain one-pass original ROI for the normal clue set; use the *original unaltered source image* to extend a **candidate terminal clue's source-pixel rectangle** only if its printed start/end and ownership are independently proven. If start/end cannot be proven without a second OCR pass, withhold that candidate for administrator review. Do not silently synthesize a `23.` OCR word from expected grid numbering. To remain within the one-OCR-pass performance requirement, no second full-page OCR fallback may be added to runtime.
- A reviewed, correct **V23** text crop has *not* yet been proven on every 20 originals, and source-line overlap/terminal completeness remain acceptance gates.

This comparator is an isolated Python/CI QA layer; no changes to Android production, any other series, Canonical, Firebase, or release.

## Targeted source-pixel proof: 2026-08-07 V23

An independent offline check took the original JPEG directly from the pinned 20-source archive (`SHA-256 dbdf0d06ca4efc843f2f593991eaf3ef0467a027b54d5a1d0df3ab67e723cd95`) and mapped actual word boxes from the full-bottom Android OCR capture back to **source pixels**.

- Printed start `23.` (confidence **93**) and trailing enumeration `(3).` (confidence **92**) lie on the same physical text line.
- The previous clue's separate terminal marker `(4);` (confidence **93**) lies immediately to the RIGHT of that start and is excluded by a measured horizontal gutter.
- Calculated source-image rectangle: **(1441,1445)–(1862,1483)** in the original **2048×1505** JPEG, outside the measured grid boundary. The resulting displayed pixel crop contains the complete printed `23.` clue and `(3)`, without the prior clue's terminal marker.
- **Only this individual clue crop has been source-verified.** The independent test used the full-bottom OCR output as *offline evidence*; there is **no app-integrated one-pass implementation** of this terminal-recovery rule yet. Do not use source-date-specific coordinates in app production.
- Across all 20 images the full-height scan is a regression risk: **7 gained and 9 lost** clean printed start tokens (499 → 497 overall). See [the comparison gate](https://github.com/higicrossword/Higi-Releases/actions/runs/44124709211). The proper production design remains fail-closed: preserve the default OCR ROI, derive any recovered terminal geometry from source-pixel proof, and withhold ambiguous crops.

No new version, APK or release. No changes to Monday/Wednesday Yedioth, common OCR source, Firebase or Canonical.
