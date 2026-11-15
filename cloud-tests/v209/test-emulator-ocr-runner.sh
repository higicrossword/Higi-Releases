#!/usr/bin/env bash
# Test shell syntax, full coverage, stdin isolation, and failure reporting without Android.
set -Eeuo pipefail
root="$(cd "$(dirname "$0")" && pwd)"
bash -n "$root/emulator-ocr-run.sh"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/bin" "$work/app/app/src/androidTest/assets/higi-fixtures" \
  "$work/app/app/build/outputs/apk/debug" \
  "$work/app/app/build/outputs/apk/androidTest/debug" \
  "$work/mockapp/ocr-cloud-v209"
printf 'stub' > "$work/app/app/build/outputs/apk/debug/app-debug.apk"
printf 'stub' > "$work/app/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk"
for i in $(seq -w 1 19); do
  printf '202611%s\t%s.jpg\tdummysha\n' "$i" "$i"
done > "$work/app/app/src/androidTest/assets/higi-fixtures/manifest.tsv"
printf 'date,source_sha256,status\n' > "$work/mockapp/ocr-cloud-v209/manifest.csv"
cat > "$work/bin/adb" <<'MOCK'
#!/usr/bin/env bash
set -Eeuo pipefail
case "$1" in
  install) printf 'Success\n';;
  shell)
    if [ "${2-}" = am ] && [ "${3-}" = instrument ]; then
      cat >/dev/null
      if [ "${MOCK_FAIL_DATE-}" != '' ] && [[ " $* " == *" $MOCK_FAIL_DATE "* ]]; then
        printf 'INSTRUMENTATION_RESULT: failed\n'
      else
        printf 'INSTRUMENTATION_RESULT: stream=\nOK (1 test)\n'
      fi
    fi;;
  logcat) printf 'Mock OCR log\n';;
  exec-out) tar -C "$MOCK_APP" -cf - ocr-cloud-v209;;
  *) printf 'Unexpected adb call: %s\n' "$*" >&2; exit 1;;
esac
MOCK
chmod +x "$work/bin/adb"
run() {
  PATH="$work/bin:$PATH" MOCK_APP="$work/mockapp" \
    HIGI_ROOT="$work/app" QA_RESULTS="$work/out" \
    MOCK_FAIL_DATE="${1-}" bash "$root/emulator-ocr-run.sh"
}
mkdir "$work/out"
run > "$work/ok.log" 2>&1
test "$(grep -c '^START fixture=' "$work/out/fixture-status.log")" -eq 19
test "$(grep -c '^END fixture=' "$work/out/fixture-status.log")" -eq 19
grep -q 'OCR_ANDROID_TOTAL=19 OCR_ANDROID_FAILED=0' "$work/out/fixture-status.log"
rm -rf "$work/out"
mkdir "$work/out"
if run 20261107 > "$work/failure.log" 2>&1; then
  echo 'ERROR: a failed OCR fixture was not propagated' >&2
  exit 1
fi
test "$(grep -c '^START fixture=' "$work/out/fixture-status.log")" -eq 19
test "$(grep -c '^END fixture=' "$work/out/fixture-status.log")" -eq 19
grep -q 'OCR_ANDROID_TOTAL=19 OCR_ANDROID_FAILED=1' "$work/out/fixture-status.log"
echo 'PASS: bash -n, all 19 fixtures, stdin-isolating adb calls, failure reporting'
