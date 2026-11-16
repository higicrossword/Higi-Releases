# Higi OCR — same-process performance and other-series QA (2026-11-16)

## Controlled source-anchor performance experiment (WIP only)
- Android emulator run: [43904138260](https://github.com/higicrossword/Higi-Releases/actions/runs/43904138260), **success**.
- 19 SHA-verified original Dekel Monday/Wednesday images. App test compiled the exact V199 source-anchor parser from immediately **before** the confidence-15..19 terminal enumeration change alongside the new parser. Both received identical recorded OCR word boxes **in the same Android process**.
- 10 warmup pairs and 30 AB/BA-alternated timed pairs per source; **570 paired measurements**.
- Median of 19 per-source old implementation medians: **49.727 ms**. New: **50.538 ms**. Median of per-source new/old ratios: **1.00947**, or approx **+0.95%**.
- Strong variability: 11-11-26 had ratio **1.337** (+33.7% for this isolated step), while other sources were faster or slower. No causal claim of whole-app slowdown or lack thereof follows.
- Source-anchor geometry changes were limited to the three intended clues: 11-11-26 H5, 02-11-26 V1, 21-10-26 V1. The existing final-geometry comparison still verifies the other **301/304 crop coordinate sets** unchanged.
- **Limitation:** This benchmarks **V199.inspect** only; it does not include image decoding, grid recognition, ML Kit, final geometry, saving, UI, startup or cloud. A full app speed claim requires an additional controlled end-to-end benchmark.

## Source discovery for three other series
[Source-byte discovery run 43906882287](https://github.com/higicrossword/Higi-Releases/actions/runs/43906882287) SHA-verified original public source bytes for 06-11-2026:
| Series | Source JPEG dimensions | SHA-256 | Notes |
|---|---|---|---|
| HAFUCH_DEKEL | 3000×2433 | `37e53145854c549f786819cd27e38852ce1deaaae484e9e7e71044db168774ef` | Source previously supplied |
| MAARIV_ODED_ROZEN | 1000×1519 | `2d588cff84f568d78d04569cd1d3c0704adb32d6c5692f0e1c6578f3bf7b51f8` | Google Groups thread title matches series and date |
| TARTEY_DEKEL | 1062×1115 | `5fe4bc049368db305eda25b0209549a19f95e02c02f9a1de34ee23712a7d2de6` | **Unresolved issue-number mismatch:** thread title says 2234, filename says 2236. Do not silently harmonize or edit puzzle metadata |

The source files were downloaded into disposable CI workspaces, not checked into the public repository or distributed in a Release. The pinned SHA and source URL are recorded in `cloud-tests/ocr-cross-series-wip/pinned_sources.json`.

## First real Android smoke outside Yedioth (two originals)
[Run 43906001062](https://github.com/higicrossword/Higi-Releases/actions/runs/43906001062) completed successfully as an execution smoke test, **not a crop-accuracy certification**:
| Series | Grid | Clue starts expected from actual grid | Source OCR lines | Trusted | Review-only proposals | Coverage |
|---|---|---:|---:|---:|---:|---:|
| HAFUCH_DEKEL | 13×13 | 28 | 55 | 0 | 1 | **1/28** |
| MAARIV_ODED_ROZEN | 11×11 | 24 | 20 | 0 | 23 | **23/24** |

- The 1/28 result for `HAFUCH_DEKEL` is a serious **candidate-generation/selection coverage gap**, even though grid detection and local OCR ran. The exact bottleneck still requires per-clue rejection reasons and source visual QA; do not guess its root cause from count alone.
- For `MAARIV_ODED_ROZEN`, 23/24 is the number of review-only candidate geometries. Their completeness and ownership have **not** been visually established.
- Both have **zero approved/trusted** crops; no source text was published or Canonical/Firebase data changed.

## Next gate and safety
- A new WIP Android suite tests **all three** with each series' own layout profile, without Yedioth-specific 9×9 or 16-clue assumptions. It also exports per-clue rejection **codes**, not copyrighted clue text or original images. Preserve discrepancies instead of auto-repair.
- None of these test findings authorize a new version, APK Release, automatic approval, or edits to Firebase/Canonical.

## Three-series Android smoke, pinned source bytes (run 43908126826)

[GitHub run 43908126826](https://github.com/higicrossword/Higi-Releases/actions/runs/43908126826), **success**. Full compiler, JVM regressions, Android 34 emulator, three distinct profiles. Output artifact `higi-ocr-other-series-smoke-wip-results`, artifact ID `14247315269`. All read-only, no source images or clue texts uploaded, no APK release.

| Source series | SHA verified original | Grid | OCR lines | Candidate crop count | Missing expected starts | Trusted/approved |
|---|---|---|---:|---:|---:|---:|
| `TARTEY_DEKEL` | `5fe4bc04...` | 11×11 | 62 | 17/24 | 7 | 0 |
| `HAFUCH_DEKEL` | `37e53145...` | 13×13 | 55 | **1/28** | **27** | 0 |
| `MAARIV_ODED_ROZEN` | `2d588cf...` | 11×11 | 20 | 23/24 | 1 | 0 |

All three were `DIAGNOSTIC_ONLY`, zero invalid normalized geometries among emitted candidates. This is **not** a claim that emitted crops are complete or visually correct.

Missing-clue code distributions from the actual artifact:
- **Tartey:** H9, H11, H14, H18, H19, H21, V12 → primary `V180_WORD_SPLIT_ADMIN_REVIEW_ONLY` (7).
- **Hafuch:** 27 missing H/V keys → primary `NO_REFERENCE_LANE` (27).
- **Maariv:** H17 → primary `V180_WORD_SPLIT_ADMIN_REVIEW_ONLY` (1).

**Nuance:** `NO_REFERENCE_LANE` originates in the early V042 neighbor-based recovery when it finds no accepted same-direction reference candidates. It **does not** prove why later independent V178/V179/V180/... passes did not rescue those 27 keys. Likewise `V180_WORD_SPLIT_ADMIN_REVIEW_ONLY` is a preliminary/unresolved label, **not** proof that V180 successfully produced or rejected a final safe rectangle. The reason-code exporter previously selected the first code from concatenated early and late diagnoses, potentially obscuring the later causal stage. A follow-up **WIP-only diagnostic update** exports these into distinct columns `unresolved_status` and `preview_pipeline_codes`; do not relax geometry or change profiles without examining those independent results.

The fact that zero are in `trusted` is expected in this DRY review run and must not be misreported as 0 OCR recognized clues. A separate visual review and geometry ownership gate are required before accepting any new proposal. No Firebase/Canonical writes.
