# Higi HAFUCH_DEKEL — OCR numbered-boundary guard WIP, 2026-11-19

**Scope:** exact series ID HAFUCH_DEKEL only. No Higi application, Canonical, Firebase, public APK, Release, or Yedioth Monday/Wednesday code changes.

## Read-only evidence actually checked
- 20/20 original publisher JPEG bytes match their manifest SHA-256 (GitHub Actions run 43939011519, artifact 14261977195).
- 20/20 original one-pass Android OCR geometry and masked tokens were loaded without a new OCR or AI call (run 44047765517, artifact 14312896246).
- Source mapping uses original ROI left/top/scale and the measured grid-right boundary.
- Numeric reading order is physical top-to-bottom, RTL within a shared printed row.
- In 13 sources, both headings are unique. In 3 more, H is missing but V is unique: H checks are *provisional blockers only*. In 4 sources, V is missing or duplicated: section ownership is unverified and the audit refuses to assign numbered guards.
- **36 suspect OCR numeric/merged tokens across 15 original source images** were marked for **REVIEW ONLY**. These are risk signals, not 36 proven defective crop rectangles or new correct crops.

## Six visually checked mismatches in source pixels
| Source date | Direction and printed number | Existing Android masked OCR token |
| --- | --- | --- |
| 2026-10-23 | H15 (printed 15.) | 5. |
| 2026-10-23 | H19 (printed 19.) | 9. |
| 2026-10-23 | V16 (printed 16.) | 6. |
| 2026-07-31 | H14 (printed 14.) | 4. |
| 2026-07-31 | V20 (printed 20.) | 0. |
| 2026-11-06 | H15 (printed 15.) | 5. |

The mapped boxes cover *actual printed* numbers, but the OCR label is wrong. **Never rename one of these numbers from expected sequence alone.** The safe first response is to block any preceding clue rectangle that would cross the suspicious number token, then wait for independent source-pixel proof of its correct identity.

## Implementation policy
- The tool is an **offline, read-only audit** and proposes *no* new rectangles. It maps suspicious OCR words to original image coordinates with classification BLOCK_CROP_CROSSING_TOKEN.
- A suspicious token is not a verified neighbor start and is not allowed as a substitute for one.
- High-confidence OCR is not proof that a numeral, its punctuation, or the entire neighboring clue was read correctly.
- The guards are not integrated into Higi. Performance, complete text, enumeration and same-row collision still need separate source-image and device verification.
- The previously administrator-confirmed V23 review images from 2026-07-31 and 2026-08-07 remain unchanged and retain their exact original-source-only verification.
- The frozen Monday/Wednesday series remains untouched. No new version or release has been created as a result of this audit.

## Local checks completed
- Python script syntax compiled and synthetic RTL same-row, numeric grammar tests passed.
- Both archives were read, all 20 original JPEG SHA-256 values validated, 36 guards found over 15 dates.
- The six known bad OCR tokens were present as guards at their source-pixel coordinates, not rewritten as trusted numbers.
- Zero automatically approved crops; no Canonical/Firebase/network/AI writes.

Next gate: compare actual REVIEW_ONLY clue rectangles against the guard rectangles in the administrator DRY workflow, withholding any crossing rectangle. Only then use original image pixels and existing AI clue text to recover a missing start without inventing coordinates. Verify full clue + enumeration, neighboring number exclusion, and no changes outside HAFUCH_DEKEL before considering app integration.