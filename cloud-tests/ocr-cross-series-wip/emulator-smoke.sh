#!/usr/bin/env bash
# Read-only two-series Android emulator OCR smoke. Does not publish APK or data.
set -Eeuo pipefail
app="com.example.hebrewcrossword"
apk="$HIGI_ROOT/app/build/outputs/apk/debug/app-debug.apk"
testapk="$HIGI_ROOT/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk"
test -s "$apk"
test -s "$testapk"
mkdir -p "$QA_RESULTS"
adb install -r "$apk"
adb install -r "$testapk"
failed=0
for series in TARTEY_DEKEL HAFUCH_DEKEL MAARIV_ODED_ROZEN; do
  log="$QA_RESULTS/instrument-$series.log"
  echo "::group::Android OCR series $series"
  if timeout --signal=TERM --kill-after=10s 210s \
    adb shell am instrument -w -r \
      -e class "com.example.hebrewcrossword.HigiOtherSeriesOcrSmokeTest" \
      -e higi.series.id "$series" \
      "$app.test/androidx.test.runner.AndroidJUnitRunner" \
      </dev/null > "$log" 2>&1 && grep -q 'OK (1 test)' "$log"; then
    echo "SMOKE_PASS $series" | tee -a "$QA_RESULTS/status.log"
  else
    echo "SMOKE_FAIL $series" | tee -a "$QA_RESULTS/status.log"
    failed=$((failed+1))
  fi
  tail -n 16 "$log" || true
  echo "::endgroup::"
done
# Preserve read-only diagnostic TSV even if one series fails.
if ! adb exec-out run-as "$app" tar -C files -cf - ocr-cross-series-wip \
   | tar -C "$QA_RESULTS" -xf -; then
  echo "::error::Failed to export independent OCR smoke counters"
  exit 1
fi
test -s "$QA_RESULTS/ocr-cross-series-wip/summary.tsv"
if [ "$failed" -ne 0 ]; then
  echo "::error::$failed independent series OCR smoke tests failed"
  exit 1
fi
