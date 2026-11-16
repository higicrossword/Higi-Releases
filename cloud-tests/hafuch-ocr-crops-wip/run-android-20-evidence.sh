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
if timeout --signal=TERM --kill-after=30s 1000s \
    adb shell am instrument -w -r \
      -e class com.example.hebrewcrossword.HigiHafuch20OcrEvidenceTest \
      "$app.test/androidx.test.runner.AndroidJUnitRunner" \
      > "$QA_RESULTS/instrument.log" 2>&1; then
    tail -n 24 "$QA_RESULTS/instrument.log"
else
    tail -n 90 "$QA_RESULTS/instrument.log"
    exit 1
fi
grep -q 'OK (1 test)' "$QA_RESULTS/instrument.log" || {
    echo "Instrumentation did not finish its sole twenty-source test"
    exit 1
}
adb exec-out run-as "$app" tar -C files -cf - hafuch-ocr-20 | tar -C "$QA_RESULTS" -xf -
test -s "$QA_RESULTS/hafuch-ocr-20/manifest.tsv"
echo "HAFUCH_20_ANDROID_WIP_COMPLETE: only local OCR source box geometry exported"
