#!/usr/bin/env bash
# Offline Higi Android OCR fixture runner. Each fixture is isolated and bounded.
# FD 3 isolates the manifest from adb commands that may consume stdin.
set -Eeuo pipefail
app="com.example.hebrewcrossword"
fixtures="$HIGI_ROOT/app/src/androidTest/assets/higi-fixtures/manifest.tsv"
testapk="$HIGI_ROOT/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk"
apk="$HIGI_ROOT/app/build/outputs/apk/debug/app-debug.apk"
test -s "$fixtures"
test -s "$apk"
test -s "$testapk"
mkdir -p "$QA_RESULTS"
total="$(wc -l < "$fixtures" | tr -d ' ')"
if [ "$total" -lt 13 ] || [ "$total" -gt 20 ]; then
  echo "::error::Invalid number of OCR fixtures: $total"
  exit 1
fi
echo "::notice::OCR fixture count: $total (each source has a 150-second deadline)"
adb install -r "$apk"
adb install -r "$testapk"
n=0
failed=0
while read -r date filename sha <&3; do
  [ -n "$date" ] || continue
  n=$((n+1))
  log="$QA_RESULTS/instrument-$date.log"
  printf '::group::OCR %s/%s - %s\n' "$n" "$total" "$date"
  printf 'START fixture=%s index=%s/%s\n' "$date" "$n" "$total" | tee -a "$QA_RESULTS/fixture-status.log"
  result=FAIL
  if timeout --signal=TERM --kill-after=10s 150s \
      adb shell am instrument -w -r \
      -e class "com.example.hebrewcrossword.HigiCloudOcrRegressionTest" \
      -e higi.fixture.date "$date" \
      "$app.test/androidx.test.runner.AndroidJUnitRunner" </dev/null > "$log" 2>&1; then
    if grep -q 'OK (1 test)' "$log"; then
      result=PASS
    else
      result=FAIL_INSTRUMENTATION
    fi
  else
    result=FAIL_OR_TIMEOUT
  fi
  tail -n 18 "$log" || true
  adb logcat -d -s 'HIGI_CLOUD_OCR:I' '*:S' | tail -n 18 || true
  printf 'END fixture=%s index=%s/%s result=%s\n' "$date" "$n" "$total" "$result" | tee -a "$QA_RESULTS/fixture-status.log"
  if [ "$result" != PASS ]; then
    failed=$((failed+1))
    adb shell am force-stop "$app.test" || true
    adb shell am force-stop "$app" || true
  fi
  echo '::endgroup::'
done 3< "$fixtures"
echo "::notice::OCR finished: total=$n expected=$total failed=$failed"
if [ "$n" -ne "$total" ]; then
  echo "::error::Fixture loop stopped early: processed $n out of $total"
  echo "OCR_INCOMPLETE=$n/$total" >> "$QA_RESULTS/fixture-status.log"
  failed=$((failed+1))
fi
echo "OCR_ANDROID_TOTAL=$n OCR_ANDROID_FAILED=$failed" >> "$QA_RESULTS/fixture-status.log"
if ! adb exec-out run-as "$app" tar -C files -cf - ocr-cloud-v209 | tar -C "$QA_RESULTS" -xf -; then
  echo "::error::Cannot export internal OCR diagnostic folder via run-as"
  exit 1
fi
test -s "$QA_RESULTS/ocr-cloud-v209/manifest.csv"
if [ "$failed" -ne 0 ]; then
  echo "::error::$failed of $n OCR fixture instrumentations failed or timed out"
  exit 1
fi
