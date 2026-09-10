#!/usr/bin/env bash
# MantraSetu voice regression suite — guards the two fixed bugs:
#   1) Proxy reconnect loop  (oversized upstream AUDIO_CHUNK frame)  [backend]
#   2) Speaker echo          (Saarthi transcribing her own greeting) [frontend]
#
# No Inworld/Groq/Gemini keys required — both tests are fully mocked.
# Usage: bash /app/run_voice_regression.sh
set -u

PY=/root/.venv/bin/python
BE="/app/final backend mantrasetu/mantrasetu-saarthi-backend-main"
FE="/app/final frontend mantrasetu/MantraSetu-Saarthi-main"
HARNESS="/app/echo_harness"
export PLAYWRIGHT_BROWSERS_PATH=/pw-browsers

pass=0; fail=0
free_port() { fuser -k "$1/tcp" >/dev/null 2>&1 || true; }

echo "=================================================================="
echo " TEST 1/2  Proxy oversized-frame (reconnect loop) — backend"
echo "=================================================================="
free_port 8000; free_port 9902; sleep 1
( cd "$BE" && mkdir -p uploads && timeout 90 "$PY" test_voice_proxy_bigframe.py )
if [ $? -eq 0 ]; then echo "TEST 1: PASS"; pass=$((pass+1)); else echo "TEST 1: FAIL"; fail=$((fail+1)); fi

echo
echo "=================================================================="
echo " TEST 2/2  Speaker echo (self-transcription) — frontend"
echo "=================================================================="
free_port 8000; free_port 3000; sleep 1

( cd "$HARNESS" && nohup "$PY" -m uvicorn mock_voice_server2:app --host 0.0.0.0 --port 8000 > /tmp/reg_mock.log 2>&1 & )
( cd "$FE" && printf 'VITE_API_BASE_URL=http://localhost:8000\n' > .env.local \
  && nohup npx vite --host 0.0.0.0 --port 3000 > /tmp/reg_vite.log 2>&1 & )

echo "Waiting for services..."
for i in $(seq 1 30); do
  m=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/voice/ticket 2>/dev/null)
  v=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/ 2>/dev/null)
  [ "$m" = "200" ] && [ "$v" = "200" ] && break
  sleep 2
done
echo "mock=$m vite=$v"

( cd "$HARNESS" && timeout 120 env LABEL=regression node speaker_echo_test.mjs > /tmp/reg_echo.log 2>&1 )
RESULT=$("$PY" - <<'EOF'
import json,sys
try:
    d=json.load(open("/app/echo_harness/result_regression.json"))["out"]
except Exception as e:
    print("PARSE_FAIL",e); sys.exit(2)
ok = (d["ECHO_DETECTED"] is False and d["ECHO_BUFFERS"]==0
      and d["frames_streamed_during_silent_greeting_phase"]==0
      and d["frames_arriving_while_tts_streaming"]==0 and d["MIC_ALIVE"] is True)
print("ECHO_DETECTED=%s MIC_ALIVE=%s greeting_frames=%s"%(
      d["ECHO_DETECTED"],d["MIC_ALIVE"],d["frames_streamed_during_silent_greeting_phase"]))
sys.exit(0 if ok else 1)
EOF
)
echo "$RESULT"
if [ $? -eq 0 ]; then echo "TEST 2: PASS"; pass=$((pass+1)); else echo "TEST 2: FAIL (see /tmp/reg_echo.log)"; fail=$((fail+1)); fi

free_port 8000; free_port 3000
echo
echo "=================================================================="
echo " SUITE RESULT: $pass passed, $fail failed"
echo "=================================================================="
[ "$fail" -eq 0 ]
