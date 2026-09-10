import { chromium } from 'playwright';

const variants = [
  ['--use-fake-device-for-media-capture', '--disable-features=AudioServiceOutOfProcess'],
  ['--use-fake-device-for-media-capture', '--disable-features=AudioServiceOutOfProcess,AudioServiceSandbox'],
  ['--use-fake-device-for-media-capture', '--audio-service-quit-timeout-ms=1000', '--disable-features=AudioServiceOutOfProcess'],
  ['--use-fake-device-for-media-capture', '--use-fake-ui-for-media-stream', '--disable-features=AudioServiceOutOfProcess', '--disable-gpu'],
];
for (const variant of variants) {
  const b = await chromium.launch({ channel: 'chromium', args: [...variant, '--no-sandbox', '--autoplay-policy=no-user-gesture-required'] });
  const ctx = await b.newContext({ permissions: ['microphone'] });
  const p = await ctx.newPage();
  await p.goto('http://localhost:3000/');
  const r = await p.evaluate(async () => {
    try {
      const s = await navigator.mediaDevices.getUserMedia({ audio: true });
      const ac = new AudioContext({ sampleRate: 16000 });
      const src = ac.createMediaStreamSource(s);
      const an = ac.createAnalyser();
      src.connect(an);
      await new Promise((r) => setTimeout(r, 1200));
      const d = new Uint8Array(an.frequencyBinCount);
      an.getByteFrequencyData(d);
      const avg = d.reduce((a, v) => a + v, 0) / d.length;
      return { ok: true, label: s.getAudioTracks()[0].label, rate: ac.sampleRate, vadAvg: Number(avg.toFixed(2)) };
    } catch (e) { return { ok: false, err: String(e) }; }
  });
  console.log(JSON.stringify(variant), '->', JSON.stringify(r));
  await b.close();
}
