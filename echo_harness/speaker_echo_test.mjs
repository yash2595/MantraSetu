// Speaker Echo Test — does Saarthi transcribe her own replies?
//
// Real MantraSetu frontend + mock voice backend + virtual loudspeaker room
// (0.18s playout latency, ~1s reverb tail, full-gain mic coupling).
// Saarthi's TTS = broadband noise 2500-5000 Hz. Simulated user = broadband noise 200-1500 Hz.
// Verdict comes from band-energy analysis of the audio the frontend actually streamed to STT.

import { chromium } from 'playwright';
import fs from 'fs';

const APP_URL = process.env.APP_URL || 'http://localhost:3000/';
const MOCK = process.env.MOCK_URL || 'http://localhost:8000';
const LABEL = process.env.LABEL || 'run';
const roomSim = fs.readFileSync('/app/echo_harness/room_sim2.js', 'utf8');

const browser = await chromium.launch({
  channel: 'chromium',
  args: ['--no-sandbox', '--autoplay-policy=no-user-gesture-required', '--disable-gpu'],
});
const context = await browser.newContext({ permissions: ['microphone'] });
await context.addInitScript(roomSim);
const page = await context.newPage();

const consoleLines = [];
page.on('console', (m) => consoleLines.push(m.text()));
page.on('pageerror', (e) => consoleLines.push('PAGEERROR: ' + e.message));

await fetch(`${MOCK}/_reset`, { method: 'POST' });
await page.goto(APP_URL, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(800);
await page.mouse.click(10, 10);
await page.evaluate(() => window.__ROOM.resume());

// ── Phase 1: Saarthi greets (3s) with the user completely silent. ──
// Any audio the frontend streams in this phase is, by construction, Saarthi's own voice.
await page.waitForTimeout(9000);
const phase1 = await (await fetch(`${MOCK}/_report`)).json();

// ── Phase 2: the user speaks for real, proving the mic still works ──
await page.evaluate(() => window.__ROOM.speak(2.0));
await page.waitForTimeout(4500);

// ── Phase 3: Saarthi replies again; re-check the silent-user echo case ──
await page.waitForTimeout(9000);

const report = await (await fetch(`${MOCK}/_report`)).json();
const roomInfo = await page.evaluate(() => ({
  bridged: window.__ROOM.bridgedContexts,
  errors: window.__ROOM.errors,
  state: window.__ROOM.state(),
}));
await browser.close();

const THRESHOLD = 0.004; // ambient noise floor measures well below this

function summarise(t) {
  const a = t.analysis;
  return {
    index: t.index ?? 'pending',
    duration_sec: a.duration_sec,
    rms: a.rms,
    saarthi_band: a.saarthi_band,
    user_band: a.user_band,
    head1s_saarthi_band: a.head1s_saarthi_band,
    head1s_user_band: a.head1s_user_band,
    verdict:
      a.saarthi_band > THRESHOLD
        ? 'CONTAINS SAARTHI VOICE (echo)'
        : a.user_band > THRESHOLD
          ? 'user speech only (clean)'
          : 'near-silence',
  };
}

const allBuffers = [...report.turns, ...(report.pending ? [report.pending] : [])];
const summaries = allBuffers.map(summarise);
const ev = report.events;

const echoBuffers = summaries.filter((s) => s.saarthi_band > THRESHOLD);
const cleanUserBuffers = summaries.filter(
  (s) => s.user_band > THRESHOLD && s.saarthi_band <= THRESHOLD
);

const out = {
  label: LABEL,
  room: { bridged_audio_contexts: roomInfo.bridged, ctx_state: roomInfo.state, errors: roomInfo.errors },
  tts_turns_sent: ev.filter((e) => e.kind === 'tts_send_start').length,
  total_frames_streamed_to_stt: ev.filter((e) => e.kind === 'audio_frame').length,
  frames_arriving_while_tts_streaming: ev.filter((e) => e.kind === 'audio_frame' && e.during_tts_send).length,
  frames_streamed_during_silent_greeting_phase: phase1.events.filter((e) => e.kind === 'audio_frame').length,
  buffers_sent_to_stt: summaries,
  ECHO_BUFFERS: echoBuffers.length,
  ECHO_DETECTED: echoBuffers.length > 0,
  CLEAN_USER_BUFFERS: cleanUserBuffers.length,
  MIC_ALIVE: cleanUserBuffers.length > 0,
  mic_sample_rate_log:
    consoleLines.find((l) => l.includes('Mic capture AudioContext sampleRate')) || 'NOT FOUND',
  cooldown_log: consoleLines.find((l) => l.includes('Acoustic cooldown elapsed')) || 'NOT FOUND',
};

fs.writeFileSync(`/app/echo_harness/result_${LABEL}.json`, JSON.stringify({ out, report }, null, 2));
console.log(JSON.stringify(out, null, 2));
console.log('\n--- key console lines ---');
for (const l of consoleLines) {
  if (/PAGEERROR|Mic capture|VERIFY-DIAGNOSTIC \(b\)|ECHO-TAIL|AUDIO-END-SENT|PROXIMITY-SPEECH|VAD-CALIBRATED|VAD-DISCARD|Microphone error/.test(l)) {
    console.log(l);
  }
}
