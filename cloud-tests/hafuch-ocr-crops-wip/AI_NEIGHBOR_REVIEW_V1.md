# HAFUCH_DEKEL: existing-AI + verified-neighbor crop experiment (read-only WIP)

**Scope:** only exact series ID `HAFUCH_DEKEL`. Do not alter the finished Dekel Monday/Wednesday or any common production algorithm. No new APK/release, no Firebase/Canonical writes.

## What has been implemented (isolated Kotlin source)
Bundle: `hafuch-ai-neighbor-review-v1.tar.br.b64`, containing `HafuchAiNeighborReviewV1.kt` and `HafuchAiNeighborReviewV1Test.kt`. Expanded source stays outside the Android application and is not called by the current recrop activity.

- Use existing decoded clue text as a *reference*, never as coordinates or proof of printed text.
- Use the existing local OCR **word bounding boxes** and two independently verified H/V section bands; require the physical grid right boundary.
- Require an exact, physically anchored OCR printed number on the neighboring clue(s). Reject non-monotonic starts, wrong sections and conflicting/duplicate number anchors.
- Verify the first actual OCR words of the neighbor against its preexisting AI transcript before using that neighbor as a boundary.
- Compare Hebrew text inside the bounded neighbor interval against the missing clue's existing AI text. Resolve RTL word order and preserve distinct source-pixel row rectangles (including multiline clues).
- A candidate never proves that its **own** missing printed number or answer-length marker is present. Those two evidence flags are explicitly false; every proposal requires manual visual review. Never silently insert `N.`, text, or a final `(N)`.
- Rejected ambiguity, missing AI text, bad neighbor order, missing headings, wrong grid bound and foreign OCR anchors fail closed.

## Tests actually performed (2026-11-17)

**Local JVM Kotlin:** the two-source prototype compiled with Kotlin 1.9.0 / Java 21. 12 synthetic safety assertions passed. These include a same-row missing number, neighbor-text disagreement, bad ordering, missing section, missing both neighbors, incorrect series, missing/wrong AI text, grid boundary intrusion, a two-row physical clue and repeated/ambiguous AI wording. **These are synthetic cases, not proof of real-world crop accuracy.**

**20 publisher-original JPEGs + pinned original local OCR TSVs:** all 20 JPEG SHA-256 hashes matched the original read-only Android OCR manifest, and the 13x13 grid was recorded for all 20. This verifies inventory integrity **only**, not AI-text matching. The published evidence deliberately masks all Hebrew OCR words to `H`, and contains no original AI-decoded clue transcript. The OCR manifest word counts on some dates exceed the serialized TSV row counts by 1–2; this was observed and must not be silently treated as exact equality.

**Result:** real 20-source AI/text fusion **not yet evaluated**, because original AI transcript + unmasked original OCR text are not jointly available in the public artifacts. Do not claim 20/20 successful cuts or 560/560 clue coverage.

## Correct next integration and benchmark

Inside a disposable **administrator DRY** instrumentation build only, at the existing post-AI, post-one-pass OCR boundary:
1. Pass `crossword.clues` (already-decoded text) to the isolated Hafuch-only matcher.
2. Pass the **in-memory** OCR word strings/boxes, independently source-verified start anchors and heading bands. Do not export clue text to public artifacts or make a second AI/OCR request.
3. Run real 20 fixtures in memory. Record only masked key, stage, geometry, reject reason, total milliseconds and optional local-only visual montage. Include the already-known 2026-07-31 and 2026-08-07 V23 terminal failures.
4. Require original source-pixel start, complete text and terminal enumeration, zero foreign numbered clues, zero same-section ink overlap; preserve all manually verified/canonical crops.
5. Compare against frozen Monday/Wednesday algorithms and same-process OCR timing. No production integration or release until specifically instructed.

Existing related source: `OcrTextLocatorV033.kt` already consumes original `crossword.clues` text; `OcrSequenceGapV154.kt` previously inferred physical gaps without comparing clue text. They must not be modified as part of this isolated experiment.

**Bundle checksum:** SHA-256 of compressed Brotli TAR bytes:
`e9bd7c3773a7fd3a0fc933c808fd4b4f2115f67f7276e9fdb73c4d04a5354584`.
