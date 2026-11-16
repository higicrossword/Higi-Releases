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

## Additional full-set risk-screen of all 304 candidates (2026-11-16)
- Reviewed native `crop_coordinates.csv` and pixel dimensions for all 304 candidate images; 47 are single-part, 222 two-part, and 35 three-part crops.
- Nine three-part candidates exceed **0.14 of source-image height in summed fragment heights**: 02-09-26 H1, 28-10-26 H14/H6, 14-10-26 V4/V8, 30-09-26 H1, 26-10-26 V8, 07-09-26 V12, and 07-10-26 H13.
- Opened the rendered `clues/*.png` for those nine; the printed clue number, wrapped text and terminal enumeration are visibly present. No obvious unrelated next-clue text is visible.
- This geometry metric is **a triage heuristic, not an error threshold**. Multiline clues naturally require several image fragments. Do not reject or truncate them based on a fixed height cutoff.
- Combined distinct items visually inspected in this work: 29 weak-marker candidates and 9 additional multiline candidates. Their overlap is zero, yielding **38/304** individually inspected clue renderings. Remaining **266/304** lack this specific visual certification.

## 2026-11-16: Full 304-crop contact-sheet scan revealed 3 genuine omissions

**Correction to earlier apparent 304/304 coverage:** that figure counts *review-only proposals*, not complete visual clues. A first-pass visual contact-sheet scan of all 304 candidate renderings identified three candidates with their answer-length enumeration `(3)` absent. These were then **cross-checked against the original source images** (not simply the OCR string):

| Date | Clue key | Original printed token omitted from candidate | OCR confidence | OCR word pixel box |
|---|---|---|---:|---|
| 11-11-26 | H5 | `(3)` | 17 | (440,224)-(466,241) |
| 02-11-26 | V1 | `(3)` | 17 | (40,180)-(66,196) |
| 21-10-26 | V1 | `(3)` | 17 | (109,175)-(135,191) |

- All three markers are present and visible in their original source images; each sits immediately before the next clue's printed number on a shared physical text line.
- In the pinned Android run 43765741209, the word boxes are absent from the relevant proposal geometry because `OcrWeeklySourceAnchorsV199.rows()` uses a minimum OCR confidence of 20. The three markers each have confidence 17.
- Across all 19 pinned OCR geometry files, these are the only low-confidence (confidence <20) tokens matching the *strict terminal-enumeration grammar* `(N)` with optional `;:` or similar OCR punctuation. Their existence does not prove their ownership without image/box verification; ownership here was checked against the printed images.
- A WIP-only emulator experiment now accepts this **specific terminal-enumeration grammar at confidence 15–19 for row geometry only**. It does **not** broaden start-number inference, alter original OCR readings, or bypass grid safety. Test must verify the final crop contains the printed token, plus compare all 301 other crop geometries exactly with the pinned baseline.
- Until that experiment's Android tests and 301-crop regression pass, this is a **proposed fix, not an approved code correction**.
- This contact-sheet check does not imply pixel-by-pixel or clue-by-clue ground-truth certification of every other 301 result. At least these 3 errors were concretely verified.

### Safety
- QA only, no APK or release, no Canonical/Firebase writes, no automatic approval of proposals or overwrite of manually/verified edited clues.

## Android emulator result: three printed enumeration tokens recovered (2026-11-16)

- **WIP run:** [43875417354](https://github.com/higicrossword/Higi-Releases/actions/runs/43875417354), successful after restoring the original release asset access permission. Previous run 43875258403 failed with HTTP 403 while fetching the source archive, *before* building or running OCR; it was an authorization regression and not evidence of an OCR failure.
- Artifact `higi-ocr-weekly-boundary-wip-results`, ID `14230751178`, digest SHA-256 `eb3adb6a68c957ce1b2986276c30a0309cb88b5d524bc91e3f6b36e8163102e6`.
- The **actual Android instrumentation** checks that all 19 SHA-verified sources produce their 304 REVIEW_ONLY proposals, exactly the three confidence-17 enumeration tokens are present, and their word box centers are now included in the original source-anchor crop *and the final proposed crop*. The release wasn't modified.
- Strict comparer `compare_terminal_crop_regression.py` read the 19 independent baseline nested ZIPs and 19 new nested ZIPs, matched source SHA-256 and all 304 keys, and reported:
  - **02-11-26 V01**: OCR `(3):` is included (previously omitted), number of crop pieces 1 -> 1
  - **11-11-26 H05**: OCR `(3);` is included (previously omitted), crop pieces 2 -> 2
  - **21-10-26 V01**: OCR `(3);` is included (previously omitted), crop pieces 1 -> 1
  - **301/301 other crop coordinate sets exactly equal**, zero unrelated coordinate changes
  - no Firebase/Canonical writes and no new APK/release
- **Additional pixel regression outside CI:** extracted every actual rendered `clues/*.png` from both artifact sets. Their SHA-256 hashes were identical for exactly **301/301 unaffected crops**, while only the above **three** intended crop PNGs changed. Visually opened the three before/after pairs; all three now display the missing printed `(3)` and their existing clue text. No neighboring clue number is included in these new rendered samples.
- This proves the three known enumeration omissions are corrected **within the ephemeral WIP Android OCR test**. It does *not* prove all 304 crops are universally complete, nor does it publish the change to the regular manager/admin APK. A release requires a separate explicit user instruction.
