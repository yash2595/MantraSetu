// Virtual room injected before app scripts.
//
// Models a phone/laptop on loudspeaker: whatever the page renders to its AudioContext
// destination is delayed (output + hardware latency), given a decaying reverb tail, and fed
// back into a synthetic microphone. getUserMedia returns that microphone.
//
// The simulated user speaks a pure 350 Hz tone. Saarthi's TTS is a pure 1000 Hz tone, so the
// server can tell whose voice reached STT.
(() => {
  const RealAudioContext = window.AudioContext || window.webkitAudioContext;

  const roomCtx = new RealAudioContext({ sampleRate: 48000 });
  const micMix = roomCtx.createGain();
  micMix.gain.value = 1.0;

  // ── Loudspeaker -> microphone coupling ──
  const speakerIn = roomCtx.createGain();
  speakerIn.gain.value = 1.0;

  // Output + hardware playout latency before the sound exists in the room
  const playoutDelay = roomCtx.createDelay(1.0);
  playoutDelay.delayTime.value = 0.18;

  const direct = roomCtx.createGain();
  direct.gain.value = 0.9;

  // Decaying reverb tail: comb delay with feedback (~1s RT60)
  const reverbDelay = roomCtx.createDelay(1.0);
  reverbDelay.delayTime.value = 0.11;
  const reverbFb = roomCtx.createGain();
  reverbFb.gain.value = 0.62;
  const reverbDamp = roomCtx.createBiquadFilter();
  reverbDamp.type = 'lowpass';
  reverbDamp.frequency.value = 4000;
  const reverbOut = roomCtx.createGain();
  reverbOut.gain.value = 0.55;

  speakerIn.connect(playoutDelay);
  playoutDelay.connect(direct);
  direct.connect(micMix);

  playoutDelay.connect(reverbDelay);
  reverbDelay.connect(reverbDamp);
  reverbDamp.connect(reverbFb);
  reverbFb.connect(reverbDelay);
  reverbDelay.connect(reverbOut);
  reverbOut.connect(micMix);

  // ── Ambient room noise (low; must never trip the VAD alone) ──
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

  // ── The human user: broadband noise in the 200-1500 Hz band, switchable ──
  const voiceGain = roomCtx.createGain();
  voiceGain.gain.value = 0;
  voiceGain.connect(micMix);
  for (let f = 200; f <= 1500; f += 130) {
    const o = roomCtx.createOscillator();
    o.type = 'sine';
    o.frequency.value = f;
    const g = roomCtx.createGain();
    g.gain.value = 0.9 / 11;
    o.connect(g);
    g.connect(voiceGain);
    o.start();
  }

  const bridged = new WeakSet();
  function bridgeToRoom(ctx) {
    if (bridged.has(ctx)) return;
    bridged.add(ctx);
    try {
      const tap = ctx.createMediaStreamDestination();
      Object.defineProperty(ctx, 'destination', { value: tap, configurable: true });
      roomCtx.createMediaStreamSource(tap.stream).connect(speakerIn);
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
    speak: (sec) => {
      const now = roomCtx.currentTime;
      voiceGain.gain.setValueAtTime(0.85, now);
      voiceGain.gain.setValueAtTime(0, now + sec);
    },
  };
})();
