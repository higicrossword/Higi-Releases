#!/usr/bin/env bash
# One shell invocation from android-emulator-runner; bounded, per-source Android OCR runs.
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
echo "::notice::OCR fixture count: $total (each source has a 150-second deadline)"
adb install -r "$apk"
adb install -r "$testapk"
n=0
failed=0
while IFS=$'\t' read -r date filename sha; do
  test -n "$date" || continue
  n=$((n+1))
  log="$QA_RESULTS/instrument-$date.log"
  printf '::group::OCR %s/%s - %s\n' "$n" "$total" "$date"
  printf 'START fixture=%s index=%s/%s\n' "$date" "$n" "$total" | tee -a "$QA_RESULTS/fixture-status.log"
  result=FAIL
  if timeout --signal=TERM --kill-after=10s 150s \
      adb shell am instrument -w -r \
      -e class "com.example.hebrewcrossword.HigiCloudOcrRegressionTest" \
      -e higi.fixture.date "$date" \
      "$app.test/androidx.test.runner.AndroidJUnitRunner" > "$log" 2>&1; then
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
    # Stop any orphaned OCR native activity before testing the next fixture.
    adb shell am force-stop "$app.test" || true
    adb shell am force-stop "$app" || true
  fi
  echo '::endgroup::'
done < "$fixtures"
echo "::notice::OCR finished: total=$n failed=$failed"
echo "OCR_ANDROID_TOTAL=$n OCR_ANDROID_FAILED=$failed" >> "$QA_RESULTS/fixture-status.log"
# Even after fixture failures, preserve completed diagnostics from internal debug-only storage.
if ! adb exec-out run-as "$app" tar -C files -cf - ocr-cloud-v209 | tar -C "$QA_RESULTS" -xf -; then
  echo "::error::Cannot export internal OCR diagnostic folder via run-as"
  exit 1
fi
test -s "$QA_RESULTS/ocr-cloud-v209/manifest.csv"
if [ "$failed" -ne 0 ]; then
  echo "::error::$failed of $n OCR fixture instrumentations failed or timed out"
  exit 1
fi
