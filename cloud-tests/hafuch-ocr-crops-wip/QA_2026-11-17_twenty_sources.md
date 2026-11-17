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
