# Higi WIP OCR: visual review of 29 weak-number candidates (2026-11-16)

## Scope, immutable provenance
- Original Android emulator OCR: [run 43765741209](https://github.com/higicrossword/Higi-Releases/actions/runs/43765741209), artifact `higi-ocr-weekly-boundary-wip-results` (SHA-256 artifact digest `c684c59c61b81e3c812e33be0d2e1c0349b9d2c55c442e61610d6f27fa8dbe52`).
- Independent numerical evidence: [run 43811847799](https://github.com/higicrossword/Higi-Releases/actions/runs/43811847799).
- Scope: the 29 flagged crops across **14 source images**. Compared the rendered `clues/*.png` with their original source regions and corresponding `geometry-*.tsv` boxes. This is a **visual QA observation, not machine-proven correctness or app approval**.
- Each of the 29 reviewed crops visibly contains its intended printed clue number and clue text; no obvious text omission or transfer to a neighboring clue was found in these reviewed examples. This is not a guarantee about every pixel or the 275 other crops.
- OCR numerical evidence is often weak even when the **printed number in the image is correct**. Do not treat a missing leading digit in OCR as a visual-crop failure.

## Number evidence (304 REVIEW_ONLY proposals)
| OCR diagnostic | Count | Interpretation |
|---|---:|---|
| STRONG_PRINTED_MARKER | 275 | Strong OCR token evidence **only**; not independently visually certified by this review |
| LEADING_DIGIT_MISSING | 15 | OCR failed to read first digit, e.g. 13 -> 3 |
| NUMBER_WITHOUT_PUNCTUATION | 11 | OCR token lacks punctuation |
| LOW_CONFIDENCE_PRINTED_MARKER | 2 | Printed-number OCR token low confidence |
| COMMA_INSTEAD_OF_DOT | 1 | OCR punctuation substituted |
| **Total** | **304** | 19 sources × 16, all proposal-only |

## Manually inspected weak-marker crops
| Source date | Clues visually reviewed |
|---|---|
| 11-11-26 | H13, H14, V8 |
| 09-11-26 | H13, V8 |
| 04-11-26 | H11, V8 |
| 02-11-26 | H11, H13 |
| 28-10-26 | V8 |
| 26-10-26 | H14 |
| 19-10-26 | V12 |
| 14-10-26 | H1, H13, H14, V1 |
| 12-10-26 | V3, V7 |
| 07-10-26 | V12, V3, V8 |
| 05-10-26 | H14, V10, V12 |
| 16-09-26 | H11 |
| 14-09-26 | H8, V12 |
| 09-09-26 | V12, V3 |

## Independent layout triage
- Across all 304 proposals, **36** start with a narrow first crop fragment (<35 px wide in the native crop; 09-09-26 source has a different pixel scale, so this is a descriptive observation, not a universal threshold).
- **4/36** overlap the 29 weak-marker cases; **32/36** have strong OCR marker evidence. Thus number-evidence strength does not measure crop presentation quality.
- Typical visual effect: the clue number is displayed on its own line before the text, e.g. 11-11-26 V8, 14-10-26 H13/H14, 07-10-26 V8. The generated crop still includes the number and text. Whether to join fragments visually is a separate, non-blocking presentation decision; do not alter clue geometry automatically just to suppress this flag.
- No source-grid intrusion was found in the 304 proposals by the independent grid boundary test. This does **not** prove crop completeness or correct clue ownership for all 304.

## Release and data safety
- **No APK, release, or new app version is authorized by this review.**
- Do **not** mark any of the 304 clues as approved, write Canonical/Firebase, or overwrite manual/verified clues as a side effect.
- The 29 weak-marker alerts are **not a justification for loosening V201 or changing the OCR engine**.
- Remaining QA: review other higher-risk multi-fragment crops and test additional newspapers/series before considering a change to production code. Keep review-only proposals independent from user-visible canonical data.
