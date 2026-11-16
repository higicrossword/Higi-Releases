# Higi OCR — Hafuch al Hafuch (Dekel Beno): Series-specific crop rules V1

**Status:** SOURCE-GROUNDED DESIGN / WIP REVIEW ONLY. No production-source change, APK, release, Canonical or Firebase writes are authorized by this specification. Work on exactly **one series** `HAFUCH_DEKEL`. All Yedioth Monday/Wednesday OCR code remains frozen.

## 1. What has actually been observed

- [Original source inventory](https://github.com/higicrossword/Higi-Releases/actions/runs/43939011519): 20 consecutive weekly source JPEGs dated **2026-07-03 through 2026-11-13**, each with the **same 13×13 / 49-black / 120-white** mask (all 169 positions checked).
- [Frozen grid reference](../hafuch-grid-fallback-wip/hafuch-13x13-reference.json) is for **grid identification only**; it is *not* an OCR clue crop map.
- Visual review of original JPEGs dated **2026-11-06**, **2026-11-13**, **2026-10-23**, **2026-09-11**, and **2026-08-07** shows a dense **right-of-grid RTL text region**, with one block headed `מאוזן` and one headed `מאונך`. The printed start numbers are **often embedded in the middle of an OCR physical line**, not at the line's right edge. On 2026-08-07 the section heading appears on the *same physical line* as its first clue: heading recognition cannot require a whole-line match.
- [Actual Android OCR smoke run 43911067998](https://github.com/higicrossword/Higi-Releases/actions/runs/43911067998) for the original 2026-11-06 JPEG read **55 OCR raw lines / 269 OCR words**, found both headings, detected the correct 13×13 grid but produced **1/28** review-only crop candidates.
- Actual OCR coordinate inventory from that run (artifact `14247034401`): H heading box top **230**, V heading top **1311**, 34 numeric-like standalone OCR words. In the right-of-grid text region, confidence >=65, **11 of the 14 expected H numbers** and **13 of the 14 expected V numbers** have a matching numeric-like token. Missing in that *strictly limited standalone-token inventory* are **H8, H15, H19, V20**; they may be merged with other OCR words and must not be invented.
- Existing `OcrPrintedLineRecoveryV178.recover` accepts starts only at the beginning of high-confidence **raw OCR lines** within a narrow lane close to a whole-line heading. It cannot cover all these embedded-number cases. Later WIP diagnosis classifies 25 missing as `V178_NO_UNAMBIGUOUS_NUMBER_IN_HEADED_RTL_LANE`, and two as no proven end. Do not attribute the whole shortfall to OCR recognition or use the preliminary `NO_REFERENCE_LANE` as final root cause.

## 2. Guard and expected grid numbers

1. Call the NEW stage only if **resolved catalog series ID exactly equals `HAFUCH_DEKEL`**, never because publisher is Dekel Beno, text contains the word `הפוך`, the image has 13×13 cells, or the source resembles Yedioth.
2. The grid must have validated bounds and pixel-proven topology (ordinary grid detector or the previously validated Hafuch-only fallback). If the source grid cannot be confirmed, **stop without fabricating clue coordinates**.
3. Derive printed expected starts from the frozen 13×13 mask using the existing crossword rule (a clue must contain >=2 contiguous white squares); validate its calculated lists:
   - Across `H`: **1, 5, 8, 9, 10, 12, 14, 15, 18, 19, 21, 22, 24, 25**.
   - Down `V`: **1, 2, 3, 4, 5, 6, 7, 11, 13, 16, 17, 19, 20, 23**.
   The expected 28 keys determine *which numbered anchors are possible*, **never where the clue text physically occurs**.

## 3. Physical region segmentation

4. Use the **measured right boundary of the grid**, not hardcoded pixel `x`, to isolate the right-side clue region. Exclude any OCR word box that overlaps the grid or lies outside the source image. Use image-relative margins, adapt to source JPEG width/height, and preserve genuine word boxes.
5. Locate `מאוזן` and `מאונך` in the *actual original OCR boxes* within the clue region, in that physical top-to-bottom order. Accept a full heading-only line **or a heading at the rightmost beginning of the same physical line as clue 1**. Require unique heading ownership; a quoted heading in clue text does not open a new section.
6. Define disjoint **H and V vertical reading bands** using the verified headings. Do not use a narrow `heading.right - imageWidth/8` filter for all subsequent starts: printed numbers may be anywhere inside the **right-of-grid text paragraph**.
7. Group OCR word boxes into physical printed lines using **vertical overlap and measured font/row height**, not raw text line boundaries, then read each line **from right to left**, and the lines **top to bottom**. Preserve the first and last word's actual ink box.

## 4. Printed number ownership

8. A proposed start must have independent **source-image OCR word geometry** and its numeral must belong to the expected `H` or `V` set for the current section. Start punctuation (`N.`, `N:`, `N,`, or valid RTL/OCR reversal) must be on the same OCR token, or be a physically adjacent standalone punctuation mark **uniquely joined** to the numeral on the same baseline. A bare number by itself, `(N)` length marker, two-digit suffix, or number mentioned in clue text is **not sufficient**.
9. Check anchor uniqueness and **strict ascending expected-number order within each section**. Monotone alignment may reject ambiguous duplicates, but **must not invent a printed coordinate** from the next expected number or from the grid mask. Do not infer H8 from a standalone 8 whose printed dot is unproven.
10. If the start is ambiguous, duplicate, OCR-merged without physical boundaries, or lies in the opposite section, mark the key `HAFUCH_START_UNVERIFIED` and **show no automatic candidate**.

## 5. Rectangle boundaries and multiline clues

11. Each clue begins at its own *printed-number word box* and continues in **RTL text order** through the associated word boxes. Several clue starts **may appear on the same printed line**; split physically between their independently verified word boxes so the following clue's number is excluded.
12. A crop ends at the **first verified next printed start in the same section** (exclusive), or a physically observed parenthesized numeric answer-length marker at the end of the clue (inclusive). A marker can include multiple lengths, e.g. `(3)`, `(5,3)`, `(3,4,2)`, with OCR bidi punctuation normalization. These parentheses are an **end hint, never a new clue-start anchor**.
13. Include **all wrapped physical lines**, complete start number, clue wording and final enumeration in the crop. Construct a list of tight, non-overlapping per-row rectangles; on shared first/last rows use the *actual source word start/end X*, with a small image-scale-aware safety margin. Do **not** show the whole page or neighboring numbered clues.
14. If the next printed number exists but the expected end `(n)` was not identified, the candidate remains *manual REVIEW ONLY*, with explicit `HAFUCH_LENGTH_UNVERIFIED`. For the **last clue in each section**, absence of both a terminal marker and an independently verifiable end means **withhold the candidate**; do not extend to image bottom or into the opposite heading.
15. Fail closed on ownership conflicts: a rectangle may not include a different verified number anchor, cross a heading, overlap the grid, or assign one physical OCR word box to two clues in the same direction. If one line cannot be split safely, withhold that clue (`HAFUCH_SHARED_ROW_AMBIGUOUS`) rather than swallow the neighbor.

## 6. Test, deployment and performance policy

16. The new Hafuch stage must be **independent** of `OcrWeeklySourceAnchorsV199` and `OcrWeeklyFinalGeometryV201`; do **not** alter Yedioth Monday/Wednesday profiles or the common OCR engine's thresholds to make Hafuch pass.
17. Use **existing already-read ML Kit OCR words/lines**, **one pass per image**; no second OCR call or AI/remote OCR as a prerequisite. Operate on bounded/sorted source tokens; measure latency and memory against the old Hafuch path.
18. Show proposals in **administrator `REVIEW_ONLY`** with exact diagnostics and physical source crop coordinates. Never automatically write Canonical/Firebase or overwrite manual/verified clues. No automatic “100%” approval by count.
19. Regression before integration: on all **20** SHA-pinned source images, detect 13×13 topology, H/V separation, 28 expected starts, and compile coverage plus **manual visual comparison** of each newly proposed crop, especially shared-row and terminal cases. Reject any newly included foreign clue number or omitted terminal length. Compare 0 unexpected pixel-coordinate changes in Yedioth Monday/Wednesday golden fixtures. Performance may not be declared unchanged without same-device repeated A/B.
20. Do **not** create a version/APK/Release until a separate explicit user request.

## Next concrete gate

First test **only the 2026-11-06 image** (current 1/28 baseline) against the printed-number word-box evidence and classify the 4 missing standalone numeric tokens. The safest target is **more than 1/28 accurate candidate proposals without one foreign number, missing end or grid intrusion** — not an arbitrary 28/28. Only after a visual pass on this fixture proceed, in order, to the other 19 originals. This protects the existing working series and allows the new Hafuch rules to be corrected before any app integration.
