// Injected BEFORE any app script. Builds a virtual "room": everything the page sends to the
// speakers is fed back into a synthetic microphone at full gain (worst-case loudspeaker echo,
// no hardware AEC). getUserMedia is replaced by that microphone.
//
// This models the reported bug exactly: Saarthi's TTS reaching her own mic input.
(() => {
  const RealAudioContext = window.AudioContext || window.webkitAudioContext;

  const roomCtx = new RealAudioContext({ sampleRate: 48000 });
  const micMix = roomCtx.createGain();
  micMix.gain.value = 1.0;

  // Loudspeaker -> microphone coupling
  const speakerBleed = roomCtx.createGain();
  speakerBleed.gain.value = 1.0;
  speakerBleed.connect(micMix);

  // Ambient room noise, kept low so it never trips the VAD on its own
  const noiseBuf = roomCtx.createBuffer(1, 48000 * 2, 48000);
  const nd = noiseBuf.getChannelData(0);
  for (let i = 0; i < nd.length; i++) nd[i] = (Math.random() * 2 - 1) * 0.0015;
  const noise = roomCtx.createBufferSource();
  noise.buffer = noiseBuf;
  noise.loop = true;
  noise.connect(micMix);
  noise.start();

  const micDest = roomCtx.createMediaStreamDestination();
  micMix.connect(micDest);

  // ── The human speaking into the mic (switchable) ──
  const voiceGain = roomCtx.createGain();
  voiceGain.gain.value = 0;
  voiceGain.connect(micMix);
  for (const [f, a] of [[200, 0.45], [600, 0.3], [1800, 0.2], [3000, 0.1]]) {
    const o = roomCtx.createOscillator();
    o.type = 'sawtooth';
    o.frequency.value = f;
    const g = roomCtx.createGain();
    g.gain.value = a;
    o.connect(g);
    g.connect(voiceGain);
    o.start();
  }
  // 4 Hz syllable envelope
  const lfo = roomCtx.createOscillator();
  lfo.frequency.value = 4;
  const lfoGain = roomCtx.createGain();
  lfoGain.gain.value = 0.5;
  lfo.connect(lfoGain);
  lfo.start();

  const bridged = new WeakSet();

  function bridgeToRoom(ctx) {
    // Route this context's speaker output into the room so the microphone hears it.
    if (bridged.has(ctx)) return;
    bridged.add(ctx);
    try {
      const tap = ctx.createMediaStreamDestination();
      Object.defineProperty(ctx, 'destination', { value: tap, configurable: true });
      const roomIn = roomCtx.createMediaStreamSource(tap.stream);
      roomIn.connect(speakerBleed);
      window.__ROOM.bridgedContexts++;
    } catch (e) {
      window.__ROOM.errors.push('bridge: ' + e);
    }
  }

  function PatchedAudioContext(...args) {
    const ctx = new RealAudioContext(...args);
    bridgeToRoom(ctx);
    return ctx;
  }
  PatchedAudioContext.prototype = RealAudioContext.prototype;

  window.AudioContext = PatchedAudioContext;
  window.webkitAudioContext = PatchedAudioContext;

  navigator.mediaDevices.getUserMedia = async () => micDest.stream;

  window.__ROOM = {
    bridgedContexts: 0,
    errors: [],
    resume: () => roomCtx.resume(),
    state: () => roomCtx.state,
    // Simulate the user speaking for `sec` seconds
    speak: (sec) => {
      const now = roomCtx.currentTime;
      voiceGain.gain.setValueAtTime(0.9, now);
      voiceGain.gain.setValueAtTime(0, now + sec);
    },
    micLevel: () => {
      if (!window.__ROOM._an) {
        const an = roomCtx.createAnalyser();
        an.fftSize = 512;
        micMix.connect(an);
        window.__ROOM._an = an;
      }
      const d = new Uint8Array(window.__ROOM._an.frequencyBinCount);
      window.__ROOM._an.getByteFrequencyData(d);
      return +(d.reduce((a, v) => a + v, 0) / d.length).toFixed(2);
    },
  };
})();
