# Higi 0.15.210 DRY — HAFUCH_DEKEL AI retry evidence, 17 November 2026

## Source evidence, local administrator ZIPs

- First export: `Higi_HAFUCH_AI_Text_20_20261117_221923.zip` (createdAt UTC 20:19:23).
- Second export: `Higi_HAFUCH_AI_Text_20_20261117_224527.zip` (createdAt UTC 20:45:27).
- Second archive integrity: 103 entries, no ZIP CRC errors. First: 100 entries.
- All 20 `source.jpg` entries match the pinned SHA-256 in `manifest.json`, both archives.
- 20 original `local-ocr.json` and original JPEGs are byte-identical across exports.
- 17 of 20 `transcription.json` and `clues.csv` are byte-identical, including all 476 combined CSV clue rows.
- Only these filenames changed across common entries: the three dates' `ai-attempt.json` and `ai-error.json`, plus the createdAt in `manifest.json`. Three new `ai-attempt-prior-*.json` files preserve previous request attempts. All other 93 common files remained byte-for-byte unchanged.

| Source date | First error | Retry error, after explicit administrator action |
| --- | --- | --- |
| 2026-10-02 | AiAttemptTimeoutException | ServerException — Firebase App Check token is invalid. |
| 2026-08-21 | AiAttemptTimeoutException | ServerException — Firebase App Check token is invalid. |
| 2026-07-10 | AiAttemptTimeoutException | ServerException — Firebase App Check token is invalid. |

The three retry failures occurred promptly (roughly 1–3 seconds each) compared to ~90-second first-attempt timeouts. **No new successful transcripts.** Do not automatically resend requests; original timeouts may already have incurred Gemini consumption. The original 17 successful results remain usable for crop investigation.

## Code evidence

`GeminiSmartOcr.transcribeCluesVerbatimForAdmin(...)` uses `generateJsonResilient(..., useLimitedUseAppCheckTokens=true)`, passing through `adminBenchmarkAi = Firebase.ai(..., useLimitedUseAppCheckTokens=true)`. The ordinary production `ai` instance uses `useLimitedUseAppCheckTokens=false` (session tokens).

Local `FIREBASE_AI_LOGIC_SETUP.md` documents baseline protection Enforced, replay protection Monitoring **at the time of that document**, and previous field failures after globally enabling limited-use tokens (rolled back in 0.15.39). These are versioned configuration notes, **not independent verification of the current Firebase Console settings**. The project uses a reCAPTCHA Enterprise App Check provider, which is installed at entry to MainActivity and some other activities. The new `AdminHafuchAiBatchActivity` itself does not explicitly call `AppCheckSetup.initialize()` in its `onCreate`. It is not proven whether it was reached through MainActivity after process recreation.

## Inference, not established root cause

Repeated invalid App Check tokens indicate an attestation / token-provider / server-verification path problem. Possible causes to isolate:

1. Provider initialisation on direct Admin Activity restoration after a process restart.
2. Limited-use attestation failure; this is a distinct path from ordinary session token Gemini calls.
3. Current Firebase AI Logic App Check baseline and replay settings or reCAPTCHA Enterprise Android package/sideload configuration not matching the application's token mode.

We have NOT inspected live Firebase Console metrics or a sanitized device log. Do not assume replay protection is currently on/off solely from old documentation, and do not disable App Check or loosen Firebase enforcement.

## Minimum safe next gate, before another billable AI retry

- Inspect Firebase Console > Security > App Check > APIs > Firebase AI Logic around 2026-11-17 20:45 UTC for Verified / Invalid / Reused and current Replay protection status; check Apps registration / provider if invalid.
- In the DRY admin path, initialize App Check before any Firebase SDK request, and add masked diagnostic of whether the SDK obtains a valid session / limited-use token (no token values in logs). Avoid changing shared production Gemini or frozen crossword-series code.
- If replay protection is still Monitoring, compare administrator requests using the existing session-token path vs limited-use path on an instrumented **non-billable attestation preflight**, not by automatically sending more Gemini calls. If replay protection is enforced, a session token is unsuitable: follow the documented limited-use setup instead.
- After fixing the root cause and obtaining explicit confirmation, do only ONE deliberate AI retry; preserve first-attempt data; proceed with the other two only if the first succeeded.

Do not create new APK/release or write to Canonical/Firebase based on this evidence alone. The two previously user-confirmed V23 crops on 2026-07-31 and 2026-08-07 remain verified and unrelated.
