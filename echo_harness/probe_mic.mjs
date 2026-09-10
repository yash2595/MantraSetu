import { chromium } from 'playwright';

for (const variant of [
  ['--use-fake-device-for-media-capture'],
  ['--use-fake-device-for-media-capture', '--use-fake-ui-for-media-stream'],
  ['--use-fake-device-for-media-capture', '--use-file-for-fake-audio-capture=/app/echo_harness/fake_mic.wav'],
  ['--use-fake-device-for-media-capture', '--alsa-input-device=default'],
]) {
  for (const channel of ['chromium', undefined]) {
    const b = await chromium.launch({ channel, args: [...variant, '--no-sandbox', '--autoplay-policy=no-user-gesture-required'] });
    const ctx = await b.newContext({ permissions: ['microphone'] });
    const p = await ctx.newPage();
    await p.goto('http://localhost:3000/');
    const r = await p.evaluate(async () => {
      try {
        const s = await navigator.mediaDevices.getUserMedia({ audio: true });
        return { ok: true, tracks: s.getAudioTracks().map(t => t.label) };
      } catch (e) { return { ok: false, err: String(e) }; }
    });
    console.log(channel || 'headless-shell', JSON.stringify(variant), '->', JSON.stringify(r));
    await b.close();
  }
}
