# HAFUCH_DEKEL — administrator visual crop verification (2026-11-17)

Scope: **HAFUCH_DEKEL only**. This record documents the administrator's explicit confirmation in the project chat. It is **not** a change to Firebase, Canonical, production OCR, or APK.

| Original crossword date | Clue | Proposed review image in QA ZIP | Administrator result | Verification scope |
| --- | --- | --- | --- | --- |
| 2026-07-31 | V23 (מאונך 23) | `2026-07-31-V23-review.png` | **VISUAL_CROP_CONFIRMED** | Proposed cut boundaries/content are correct as shown |
| 2026-08-07 | V23 (מאונך 23) | `2026-08-07-V23-review.png` | **VISUAL_CROP_CONFIRMED** | Proposed cut boundaries/content are correct as shown |

QA package originally shown to administrator: `Higi_HAFUCH_AI20_QA_20261117.zip`.

Evidence: administrator's direct reply: **"שני החיתוכים המוצעים נכונים"** after viewing the two proposed review crops.

## Consequences for subsequent DRY evaluation

- Treat these **two exact proposed crops** as administrator-verified positive examples (regression fixtures), rather than unverified candidates.
- Preserve the original source identity and pixel coordinates associated with those images. Do not apply this approval to different cut coordinates, new OCR output, or other dates.
- A future batch comparison can count these two as **2 visually verified examples**; they do not establish accuracy for remaining clues or missing AI transcription.
- If future transformations alter any of these crops, require re-verification.
- Keep all other proposals `REVIEW_ONLY` until explicitly confirmed.
- Freeze Dekel Monday and Wednesday series code as agreed. No changes to Canonical/Firebase or an APK/release are authorized by this visual confirmation alone.
