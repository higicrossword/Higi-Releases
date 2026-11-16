#!/usr/bin/env bash
# Isolated WIP only, no APK published. Execute this file as ONE bash script:
# the emulator action otherwise invokes multiline script entries individually.
set -Eeuo pipefail
test -n "$HIGI_ROOT" && test -n "$QA_RESULTS"
mkdir -p "$QA_RESULTS"
app="com.example.hebrewcrossword"
echo "HAFUCH_20_ANDROID_WIP_START"
adb wait-for-device
adb install -r "$HIGI_ROOT/app/build/outputs/apk/debug/app-debug.apk"
adb install -r "$HIGI_ROOT/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk"
# Capture per-image progress even if one source fails; never leak clue text.
adb logcat -c || true
adb logcat -v brief -s HAFUCH20:I '*:S' > "$QA_RESULTS/per-image-progress.log" 2>&1 &
logcat_pid=$!
set +e
timeout --signal=TERM --kill-after=30s 1000s \
    adb shell am instrument -w -r \
      -e class com.example.hebrewcrossword.HigiHafuch20OcrEvidenceTest \
      "$app.test/androidx.test.runner.AndroidJUnitRunner" \
      > "$QA_RESULTS/instrument.log" 2>&1
instrument_result=$?
set -e
kill "$logcat_pid" 2>/dev/null || true
wait "$logcat_pid" 2>/dev/null || true
tail -n 40 "$QA_RESULTS/instrument.log"
echo "Incremental source audit progress:"
tail -n 30 "$QA_RESULTS/per-image-progress.log" || true
# Always attempt to export partial evidence; crash/timeout is not proof of
# zero OCR detections for fixtures already scanned.
adb exec-out run-as "$app" tar -C files -cf - hafuch-ocr-20 | tar -C "$QA_RESULTS" -xf - || true
test -s "$QA_RESULTS/hafuch-ocr-20/manifest.tsv" || {
    echo "No reusable source word evidence after instrumentation";exit 1
}
if [ "$instrument_result" -ne 0 ] || ! grep -q 'OK (1 test)' "$QA_RESULTS/instrument.log"; then
    echo "::error::Android source evidence scan incomplete; partial per-image TSV retained"
    exit 1
fi
echo "HAFUCH_20_ANDROID_WIP_COMPLETE: only local OCR source box geometry exported"
