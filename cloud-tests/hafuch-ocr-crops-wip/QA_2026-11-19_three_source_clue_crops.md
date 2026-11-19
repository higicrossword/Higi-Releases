# HAFUCH_DEKEL — three source-pixel REVIEW_ONLY crop proposals, 2026-11-19

**Scope:** independent offline geometry experiment on HAFUCH_DEKEL. Not a new application version, not Canonical data, not Firebase, and **not administrator-confirmed**. These fixed coordinates are test fixtures only; never use them as per-series hardcoded production crop coordinates.

## Source evidence and bounded crop rectangles

Coordinates are in the **original publisher JPEG pixel space** [left, top, right, bottom]; ROI-to-source mapping used the existing, masked Android OCR word-box manifest. Images are from pinned 20-source artifact run 43939011519 and existing OCR run 44047765517.

| Date | Clue | Printed number inspected visually | Misread OCR token | Inclusive enumeration OCR token | Neighboring next OCR start excluded | Original source crop | Image size |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-06 | H15 | 15. | 5. | (6); | 18. | (2218,765)–(2905,820) | 3000×2433 |
| 2026-10-23 | H19 | 19. | 9. | (5,3): | 21. | (2262,780)–(2848,829) | 3008×2366 |
| 2026-07-31 | H14 | 14. | 4. | (4,2); | 15. | (1473,449)–(2005,490) | 2048×1544 |

### Checks performed

- Read each *original* publisher JPEG and one-pass original Android OCR word geometry without extra OCR or AI calls.
- All three numbered starts were confirmed from visible printed digits, **not re-numbered by expected grid sequence alone**.
- The start word box and the original OCR-detected closing answer-length marker fall completely inside the proposed source-pixel crop.
- The independently measured next numbered start in the same physical row is outside the crop.
- Pixel-ink column counts in the number-to-number gutter were checked for clean separation; all three have a blank source-pixel lane between the left edge of the last included marker and the next clue.
- The three resulting source-image crops were reviewed visually for complete wording and enumeration.

### Restrictions

These are **3 individually visually inspected case fixtures**, not evidence that every one of the previous 389 geometry proposals is correct, not automatic rule discovery, and not user-approved verified crop state. In particular:

- Do not classify H15 or H19 by replacing the OCR text 5./9. based on crossword expected-number sequence; the printed-source evidence was inspected separately.
- Do not copy these hardcoded coordinates into application source. An eventual HAFUCH-only matcher must derive start/end positions from actual source pixels and verified neighbor anchors, and withhold ambiguous cases.
- Do not modify the two administrator-confirmed 2026-07-31 and 2026-08-07 V23 crops, or any frozen Yedioth Monday/Wednesday algorithm.
- No Canonical/Firebase writes or release/APK actions.

Next: use the same independent source-pixel/adjacent-number/terminal-marker checks to test candidate split rectangles on the remaining 20-source set. App integration requires in-memory OCR words plus existing AI text on an isolated admin DRY build; the public OCR TSV masks Hebrew text.


## Three additional source-pixel REVIEW_ONLY crops (manual original-image inspection)

The same tests and original-source visual review were also completed for the other three observed lost-leading-digit examples. These are **multiple physical row rectangles** when needed, not single page-level bounding boxes.

| Date | Clue | Printed number / original OCR | Existing final length | Next printed start excluded | Source-pixel row rectangles |
| --- | --- | --- | --- | --- | --- |
| 2026-10-23 | H15 | 15. / 5. | (6); | H18 | (2125,653)–(2856,717); (2620,716)–(2856,773) |
| 2026-10-23 | V16 | 16. / 6. | (7); | V17 (OCR 17, at confidence 54) | (2120,1805)–(2862,1863); (2790,1865)–(2862,1919) |
| 2026-07-31 | V20 | 20. / 0. | (4); | V23 | (1576,1427)–(2006,1475) |

For each, the original rendered crop was inspected and the expected printed number, complete text, terminal length marker and separation from the following numbered clue were visible. Existing OCR word geometry independently confirmed inclusion of the terminal marker and exclusion of the next number's observed OCR box. In H15/V16, per-row rectangles avoid ingesting neighboring clues on their last shared row. The source image retains original pixel coordinates.

**Result of 2026-11-19 offline audit:** 6 individual, visually reviewed source-pixel REVIEW_ONLY crop examples across 3 publisher dates, derived from six actual OCR-digit-loss observations. They are *not* a complete batch, not an algorithm success rate, and not administrator-approved. The previously user-confirmed V23 crops remain separate. The two WIP example montages exist only in the temporary QA workspace; they are not shipped with the application.
