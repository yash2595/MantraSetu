#!/usr/bin/env bash
# Speaker Echo Test runner.
#
#   ./run_echo_test.sh fixed     -> test the current (fixed) code
#   ./run_echo_test.sh prefix    -> checkout the pre-fix code and test it (positive control)
#   ./run_echo_test.sh restore   -> restore the fixed code
#
# Requires the mock backend (port 8000) and vite (port 3000) to be running; see below.
set -e
FE="/app/final frontend mantrasetu/MantraSetu-Saarthi-main"
HOOK="$FE/src/hooks/useSaarthiVoice.ts"
PREFIX_COMMIT=49d133b

start_services() {
  pgrep -f mock_voice_server2 >/dev/null || {
    cd /app/echo_harness
    nohup /root/.venv/bin/uvicorn mock_voice_server2:app --host 0.0.0.0 --port 8000 > /tmp/mock2.log 2>&1 &
  }
  curl -sf -o /dev/null http://localhost:3000/ || {
    cd "$FE"
    printf 'VITE_API_BASE_URL=http://localhost:8000\n' > .env.local
    nohup npx vite --host 0.0.0.0 --port 3000 > /tmp/vite.log 2>&1 &
  }
  sleep 10
}

case "$1" in
  prefix)
    cd "$FE" && git show "$PREFIX_COMMIT:./src/hooks/useSaarthiVoice.ts" > "$HOOK"
    echo "Checked out PRE-FIX hook (positive control)"
    start_services; sleep 5
    cd /app/echo_harness && LABEL=prefix node speaker_echo_test.mjs
    ;;
  restore)
    cp /app/echo_harness/FIXED_final.ts "$HOOK"
    echo "Restored FIXED hook"
    ;;
  *)
    cp /app/echo_harness/FIXED_final.ts "$HOOK"
    start_services; sleep 5
    cd /app/echo_harness && LABEL=fixed node speaker_echo_test.mjs
    ;;
esac
