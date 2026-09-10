// Echo test: does Saarthi transcribe her own replies?
//
// Runs the real MantraSetu frontend against a mock voice backend, inside a virtual room where
// the microphone hears the loudspeaker at full gain. Measures whether any audio reaches the
// server (STT) while Saarthi's TTS is playing, and whether the mic still hears the real user.

import { chromium } from 'playwright';
import fs from 'fs';

const APP_URL = process.env.APP_URL || 'http://localhost:3000/';
const MOCK = process.env.MOCK_URL || 'http://localhost:8000';
const roomSim = fs.readFileSync('/app/echo_harness/room_sim.js', 'utf8');

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

// ── Turn 1: Saarthi greets (3s TTS). Mic hears it at full gain. ──
await page.waitForTimeout(7000);
const roomInfo = await page.evaluate(() => ({
  bridged: window.__ROOM.bridgedContexts,
  errors: window.__ROOM.errors,
  state: window.__ROOM.state(),
}));

// ── Now the user actually speaks: the mic must still work ──
await page.evaluate(() => window.__ROOM.speak(2.0));
await page.waitForTimeout(3500);
const midReport = await (await fetch(`${MOCK}/_report`)).json();

// ── Turn 2: Saarthi replies again (3s TTS) — check echo a second time ──
await page.waitForTimeout(7000);

const report = await (await fetch(`${MOCK}/_report`)).json();
await browser.close();

const events = report.events;
const frames = events.filter((e) => e.kind === 'audio_frame');
const framesDuringTts = frames.filter((e) => e.during_tts);
const endsDuringTts = events.filter((e) => e.kind === 'audio_end' && e.during_tts);

const TAIL_MS = 700;
const playbackEnds = events.filter((e) => e.kind === 'tts_playback_end').map((e) => e.t);
const framesInTail = frames.filter((f) =>
  playbackEnds.some((end) => f.t >= end && f.t < end + TAIL_MS / 1000)
);

const framesWhileListening = frames.filter((e) => !e.during_tts);
const listeningBytes = framesWhileListening.reduce((a, e) => a + e.bytes, 0);

const micRateLine = consoleLines.find((l) => l.includes('Mic capture AudioContext sampleRate'));
const audioEnds = events.filter((e) => e.kind === 'audio_end');

// Effective PCM rate of what the frontend streamed (expect ~32000 B/s => 16kHz * 2 bytes)
let byteRate = null;
if (framesWhileListening.length > 1) {
  const span = framesWhileListening.at(-1).t - framesWhileListening[0].t;
  if (span > 0) byteRate = Math.round(listeningBytes / span);
}

const out = {
  room_bridged_audio_contexts: roomInfo.bridged,
  room_ctx_state: roomInfo.state,
  room_errors: roomInfo.errors,
  tts_turns_played: events.filter((e) => e.kind === 'tts_playback_start').length,

  ECHO_frames_during_tts_playback: framesDuringTts.length,
  ECHO_audio_end_during_tts_playback: endsDuringTts.length,
  ECHO_frames_in_700ms_tail: framesInTail.length,
  ECHO_DETECTED: framesDuringTts.length > 0 || endsDuringTts.length > 0 || framesInTail.length > 0,

  MIC_frames_while_listening: framesWhileListening.length,
  MIC_audio_end_dispatched: audioEnds.length,
  MIC_listening_bytes: listeningBytes,
  MIC_effective_byte_rate: byteRate,
  MIC_ALIVE: framesWhileListening.length > 0 && audioEnds.length > 0,

  mic_sample_rate_log: micRateLine || 'NOT FOUND',
};

console.log(JSON.stringify(out, null, 2));
console.log('\n--- key console lines ---');
for (const l of consoleLines) {
  if (/PAGEERROR|Mic capture|VERIFY-DIAGNOSTIC|AUDIO-END-SENT|PROXIMITY-SPEECH|VAD-CALIBRATED|VAD-DISCARD|Microphone error|\[STATE\] idle/.test(l)) {
    console.log(l);
  }
}
