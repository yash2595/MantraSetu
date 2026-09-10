import { chromium } from 'playwright';
const b = await chromium.launch({ channel: 'chromium', args: ['--no-sandbox', '--disable-features=AudioServiceSandbox,AudioServiceOutOfProcess', '--autoplay-policy=no-user-gesture-required'], env: { ...process.env, XDG_RUNTIME_DIR: '/run/user/0', PULSE_SERVER: 'unix:/run/user/0/pulse/native' } });
const ctx = await b.newContext({ permissions: ['microphone'] });
const p = await ctx.newPage();
await p.goto('http://localhost:3000/');
const r = await p.evaluate(async () => {
  try {
    const s = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
    const ac = new AudioContext({ sampleRate: 16000 });
    const src = ac.createMediaStreamSource(s);
    const an = ac.createAnalyser(); an.fftSize = 512;
    src.connect(an);
    await new Promise((r) => setTimeout(r, 1500));
    const d = new Uint8Array(an.frequencyBinCount); an.getByteFrequencyData(d);
    return { ok: true, label: s.getAudioTracks()[0].label, ctxRate: ac.sampleRate, vadAvg: +(d.reduce((a,v)=>a+v,0)/d.length).toFixed(2) };
  } catch (e) { return { ok: false, err: String(e) }; }
});
console.log(JSON.stringify(r));
await b.close();
