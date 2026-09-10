// Drives the real MantraSetu frontend in Chromium with a fake microphone that continuously
// plays loud speech-like audio, then reports whether any AUDIO_FRAME reached the server while
// Saarthi's TTS was playing (i.e. whether Saarthi transcribes her own replies).

import { chromium } from 'playwright';

const APP_URL = process.env.APP_URL || 'http://localhost:3000/';
const MOCK = process.env.MOCK_URL || 'http://localhost:8000';
const WAV = '/app/echo_harness/fake_mic.wav';

const browser = await chromium.launch({
  channel: 'chromium',
  args: [
    '--use-fake-ui-for-media-stream',
    '--use-fake-device-for-media-capture',
    `--use-file-for-fake-audio-capture=${WAV}`,
    '--autoplay-policy=no-user-gesture-required',
    '--no-sandbox',
  ],
});

const context = await browser.newContext({ permissions: ['microphone'] });
const page = await context.newPage();

const consoleLines = [];
page.on('console', (m) => consoleLines.push(m.text()));
page.on('pageerror', (e) => consoleLines.push('PAGEERROR: ' + e.message));
page.on('pageerror', (e) => consoleLines.push('PAGEERROR: ' + e.message));

await fetch(`${MOCK}/_reset`, { method: 'POST' });
await page.goto(APP_URL, { waitUntil: 'domcontentloaded' });

// Nudge the autoplay unblocker exactly like a real user landing on the page
await page.waitForTimeout(1500);
await page.mouse.click(10, 10);

// Greeting TTS (3s) + cooldown + a listening window long enough for the fake mic to be
// picked up and an AUDIO_END dispatched, then a second TTS turn.
await page.waitForTimeout(16000);

const report = await (await fetch(`${MOCK}/_report`)).json();
await browser.close();

const events = report.events;
const frames = events.filter((e) => e.kind === 'audio_frame');
const framesDuringTts = frames.filter((e) => e.during_tts);
const endsDuringTts = events.filter((e) => e.kind === 'audio_end' && e.during_tts);

// Frames arriving in the acoustic tail window after playback ends also count as echo,
// because the loudspeaker/room is still reproducing Saarthi's reply there.
const TAIL_MS = 700;
const playbackEnds = events.filter((e) => e.kind === 'tts_playback_end').map((e) => e.t);
const framesInTail = frames.filter((f) =>
  playbackEnds.some((end) => f.t >= end && f.t < end + TAIL_MS / 1000)
);

const micRateLine = consoleLines.find((l) => l.includes('Mic capture AudioContext sampleRate'));
const cooldownLine = consoleLines.find((l) => l.includes('Acoustic cooldown elapsed'));

// Confirm the mic is genuinely alive (otherwise "no echo" would be meaningless)
const framesWhileListening = frames.filter((e) => !e.during_tts);
const frameBytes = framesWhileListening.reduce((a, e) => a + e.bytes, 0);

const out = {
  ws_opened: events.some((e) => e.kind === 'ws_open'),
  connect_received: events.some((e) => e.kind === 'connect_received'),
  tts_turns: events.filter((e) => e.kind === 'tts_playback_start').length,
  total_audio_frames: frames.length,
  frames_while_listening: framesWhileListening.length,
  frames_during_tts_playback: framesDuringTts.length,
  audio_end_during_tts_playback: endsDuringTts.length,
  frames_in_700ms_acoustic_tail: framesInTail.length,
  listening_frame_bytes: frameBytes,
  mic_sample_rate_log: micRateLine || 'NOT FOUND',
  cooldown_log: cooldownLine || 'NOT FOUND',
  ECHO_DETECTED: framesDuringTts.length > 0 || endsDuringTts.length > 0 || framesInTail.length > 0,
  MIC_ALIVE: framesWhileListening.length > 0,
};

console.log(JSON.stringify(out, null, 2));
console.log('\n--- voice console lines ---');
for (const l of consoleLines) {
  if (/mic|Mic|Microphone|PAGEERROR|error|\[VAD-|\[VERIFY-DIAGNOSTIC|\[AUDIO-END-SENT|\[PROXIMITY|\[STATE\]/i.test(l)) {
    console.log(l);
  }
}
