import { useState, useEffect, useRef, useCallback } from 'react';
import { useSaarthi } from '../components/saarthi/SaarthiContext';
import { useNavigate } from 'react-router-dom';

// ---------- Helper utilities -------------------------------------------------
/** Convert Float32Array audio samples to 16‑bit PCM (little‑endian) */
function float32ToPCM16(buffer: Float32Array): Uint8Array {
  const l = buffer.length;
  const result = new Uint8Array(l * 2);
  for (let i = 0; i < l; i++) {
    let s = Math.max(-1, Math.min(1, buffer[i]));
    s = s < 0 ? s * 0x8000 : s * 0x7fff;
    const int16 = Math.round(s);
    result[i * 2] = int16 & 0xff; // little‑endian lower byte
    result[i * 2 + 1] = (int16 >> 8) & 0xff;
  }
  return result;
}

/** Resample an AudioBuffer to the target sample rate (16 kHz) */
function resampleAudioBuffer(audioCtx: AudioContext, buffer: AudioBuffer, targetRate = 16000): Promise<AudioBuffer> {
  if (buffer.sampleRate === targetRate) return Promise.resolve(buffer);
  const offline = new OfflineAudioContext(buffer.numberOfChannels, Math.ceil(buffer.duration * targetRate), targetRate);
  const source = offline.createBufferSource();
  source.buffer = buffer;
  source.connect(offline.destination);
  source.start(0);
  return offline.startRendering();
}

/** Encode Uint8Array (PCM16) to base64 string */
function uint8ArrayToBase64(u8: Uint8Array): string {
  let binary = '';
  const len = u8.byteLength;
  for (let i = 0; i < len; i++) binary += String.fromCharCode(u8[i]);
  return btoa(binary);
}

// ---------------------------------------------------------------------------

export function useSaarthiVoice() {
  const { state, setDialogueText, setSaarthiState, minimizeSaarthi, forceMinimize } = useSaarthi();
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioQueueRef = useRef<AudioBuffer[]>([]);
  const isPlayingRef = useRef(false);
  const isFinalChunkReceived = useRef(false);
  const fallbackTimeoutRef = useRef<number | NodeJS.Timeout | null>(null);
  const sequenceQueueRef = useRef<any[]>([]);
  const isExecutingSequenceRef = useRef(false);

  const processNextStep = useCallback(() => {
    if (sequenceQueueRef.current.length === 0) {
      isExecutingSequenceRef.current = false;
      const cursor = document.getElementById('saarthi-cursor');
      if (cursor) {
          cursor.style.opacity = '0';
          setTimeout(() => {
             cursor.style.transform = 'scale(1)';
             cursor.style.backgroundColor = 'rgba(238, 124, 43, 0.6)';
          }, 300);
      }
      return;
    }

    isExecutingSequenceRef.current = true;
    const step = sequenceQueueRef.current.shift()!;
    console.log('[NAV-DEBUG] Executing step:', step);

    let cursor = document.getElementById('saarthi-cursor');
    if (!cursor) {
      cursor = document.createElement('div');
      cursor.id = 'saarthi-cursor';
      cursor.style.position = 'fixed';
      cursor.style.width = '24px';
      cursor.style.height = '24px';
      cursor.style.borderRadius = '50%';
      cursor.style.backgroundColor = 'rgba(238, 124, 43, 0.6)';
      cursor.style.border = '2px solid #ee7c2b';
      cursor.style.boxShadow = '0 0 10px rgba(238, 124, 43, 0.5)';
      cursor.style.zIndex = '99999';
      cursor.style.pointerEvents = 'none';
      cursor.style.transition = 'all 0.8s ease-in-out';
      cursor.style.left = '50vw';
      cursor.style.top = '50vh';
      cursor.style.opacity = '0';
      document.body.appendChild(cursor);
    }

    if (step.action === 'wait_for_selector' && step.target) {
      let attempts = 0;
      const checkInterval = setInterval(() => {
        const el = document.querySelector(step.target);
        attempts++;
        if (el && el.getBoundingClientRect().width > 0) {
          clearInterval(checkInterval);
          setTimeout(processNextStep, step.delay);
        } else if (attempts > 50) { // 5 seconds timeout
          clearInterval(checkInterval);
          console.warn('[NAV-DEBUG] Timeout waiting for selector:', step.target);
          processNextStep();
        }
      }, 100);
      return;
    }

    if (step.action === 'navigate' && step.path) {
      navigate(step.path);
      setTimeout(processNextStep, step.delay);
      return;
    }

    if (step.action === 'move' && step.target) {
      const targetEl = document.querySelector(step.target) as HTMLElement;
      if (targetEl) {
        // scroll into view
        targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // Wait for scroll to settle
        setTimeout(() => {
          const rect = targetEl.getBoundingClientRect();
          const targetX = rect.left + rect.width / 2;
          const targetY = rect.top + rect.height / 2;
          
          cursor!.style.opacity = '1';
          cursor!.style.transform = 'scale(1)';
          cursor!.style.backgroundColor = 'rgba(238, 124, 43, 0.6)';
          cursor!.style.left = `${targetX - 12}px`;
          cursor!.style.top = `${targetY - 12}px`;
          
          setTimeout(processNextStep, step.delay);
        }, 100); // 100ms scroll buffer
      } else {
        console.warn('[NAV-DEBUG] Move target not found:', step.target);
        processNextStep();
      }
      return;
    }

    if (step.action === 'click' && step.target) {
      const targetEl = document.querySelector(step.target) as HTMLElement;
      if (targetEl) {
        cursor.style.transform = 'scale(0.5)';
        cursor.style.backgroundColor = 'rgba(238, 124, 43, 0.9)';
        targetEl.click();
        
        setTimeout(() => {
          cursor!.style.transform = 'scale(1)';
          cursor!.style.backgroundColor = 'rgba(238, 124, 43, 0.6)';
          setTimeout(processNextStep, step.delay);
        }, 150);
      } else {
        console.warn('[NAV-DEBUG] Click target not found:', step.target);
        processNextStep();
      }
      return;
    }

    if (step.action === 'type' && step.target && step.text) {
      const targetEl = document.querySelector(step.target) as HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;
      console.log(`[FORM-FILL-EXEC] Action: TYPE. Target: "${step.target}". ElementFound: ${!!targetEl}. ValueToSet: "${step.text}"`);
      if (targetEl) {
         console.log('[FORM-FILL-EXEC] Dispatching input event with value:', step.text);
         
         // In React 18, input value setters are defined on the instance proto
         let nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
         if (targetEl.tagName.toLowerCase() === 'textarea') {
             nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')?.set;
         } else if (targetEl.tagName.toLowerCase() === 'select') {
             nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value')?.set;
         }

         if (nativeInputValueSetter) {
             nativeInputValueSetter.call(targetEl, step.text);
             console.log('[FORM-FILL-EXEC] Used nativeInputValueSetter');
         } else {
             targetEl.value = step.text;
             console.log('[FORM-FILL-EXEC] Used direct assignment');
         }
         
         const inputEventSuccess = targetEl.dispatchEvent(new Event('input', { bubbles: true }));
         const changeEventSuccess = targetEl.dispatchEvent(new Event('change', { bubbles: true }));
         console.log(`[FORM-FILL-EXEC] Dispatched events. inputSuccess=${inputEventSuccess}, changeSuccess=${changeEventSuccess}`);
      }
      setTimeout(processNextStep, step.delay);
      return;
    }

    processNextStep();
  }, [navigate]);

  const processNextStepRef = useRef(processNextStep);
  useEffect(() => {
    processNextStepRef.current = processNextStep;
  }, [processNextStep]);

  useEffect(() => {
    console.log(`[Voice] ---> STATE TRANSITION: ${state} <---`);
  }, [state]);

  useEffect(() => {
    console.log('[Voice] Initializing WebSocket...');
    const wsUrl = import.meta.env.VITE_API_BASE_URL.replace('http', 'ws') + '/ws/voice';
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log('[Voice] WebSocket Connected');
      setIsConnected(true);
      ws.send(JSON.stringify({
        type: 'CONNECT',
        payload: { language: 'hi' }
      }));
    };

    ws.onmessage = async (event) => {
        try {
          const msg = JSON.parse(event.data);
          // [DIAGNOSTIC] Log every single message type and AI_RESPONSE payload explicitly
          if (msg.type === 'AI_RESPONSE') {
             console.log('[DIAGNOSTIC] FULL RAW AI_RESPONSE PAYLOAD:', JSON.stringify(msg.payload));
          }
          if (!msg.type) return;
          console.log(`[Voice] Received message type: ${msg.type}`);

          // ----------- TRANSCRIPT handling -----------------------------------
          if (msg.type === 'TRANSCRIPT') {
            const { text, is_final } = msg.payload as { text: string; is_final: boolean };
            console.log('[Voice] TRANSCRIPT', is_final ? 'final' : 'partial', text);
            setDialogueText(text);
            if (is_final) {
              setSaarthiState('idle'); // Wait for AI_RESPONSE
              // Auto-minimize on first command
              console.log('[WIDGET] Shrink condition check (TRANSCRIPT): is_final=true, _hasMinimizedOnce=', (window as any)._hasMinimizedOnce);
              if (!(window as any)._hasMinimizedOnce) {
                  console.log('[WIDGET] Triggering shrink-to-corner animation now (via TRANSCRIPT)');
                  forceMinimize();
                  (window as any)._hasMinimizedOnce = true;
              }
            }
            return;
          }

          // ----------- CONNECTED handling -----------------------------------
          if (msg.type === 'CONNECTED') {
            console.log('[Voice] CONNECTED received');
            return;
          }

          // ----------- AI_RESPONSE handling -----------------------------------
          if (msg.type === 'AI_RESPONSE') {
            console.log('[Voice] AI_RESPONSE received:', JSON.stringify(msg.payload));
            let contentStr = msg.payload.content || '';
            
            let action = msg.payload.action || null;
            let target = msg.payload.target || null;
            let intent = msg.payload.intent || null;
            let query = msg.payload.query || null;
            
            try {
              const parsed = JSON.parse(contentStr);
              if (!action && parsed.action) action = parsed.action;
              if (!target && parsed.target) target = parsed.target;
              if (!intent && parsed.intent) intent = parsed.intent;
              if (!query && parsed.query) query = parsed.query;
              if (parsed.response_text) contentStr = parsed.response_text;
            } catch (e) {}

            console.log('[Voice] --------------------------------------------------');
            console.log('[Voice] AI_RESPONSE NAVIGATION CHECK:');
            console.log('[Voice] Raw Target:', target);
            console.log('[Voice] Raw Action:', action);
            console.log('[Voice] Intent:', intent);
            console.log('[Voice] Query:', query);
            console.log('[Voice] --------------------------------------------------');

            console.log('[NAV-DEBUG] RAW AI_RESPONSE Received. action=', action, 'target=', JSON.stringify(target));

            if (action === 'NAVIGATE' && target) {
              const cleanTarget = target.trim();
              
              const runSequence = (seq: any[]) => {
                sequenceQueueRef.current = seq;
                if (!isExecutingSequenceRef.current) {
                  processNextStepRef.current();
                }
              };

              console.log(`[NAV-DEBUG] Routing for target: ${cleanTarget}, query: ${query}, currentPath: ${window.location.pathname}`);
              
              const getTargetSelectorForPath = (path: string) => {
                if (path === '/') return '[data-testid="link-home-logo"]';
                if (path.includes('puja')) return '[data-testid="button-nav-services"]';
                if (path.includes('kundali')) return '[data-testid="button-nav-spiritual-tools"]';
                if (path.includes('muhurat')) return '[data-testid="button-nav-spiritual-tools"]';
                if (path.includes('login')) return '[data-testid="button-login"]';
                if (path.includes('signup') || path.includes('sign-up')) return '[data-testid="button-signup"]';
                if (path.includes('dash')) return 'a[href="/dashboard"]';
                return `a[href="${path}"]`;
              };

              const seq = [];
              const finalTarget = getTargetSelectorForPath(cleanTarget);

              if (query && cleanTarget.includes('puja')) {
                // GENERIC QUERY FLOW (e.g., Any specific puja) - GOLDEN PATH
                console.log('[NAV-DEBUG] Preparing to type search query into filter box:', query);
                if (window.location.pathname === '/puja') {
                  seq.push(
                    { action: 'move', target: '[data-testid="input-search-puja"]', delay: 800 },
                    { action: 'click', target: '[data-testid="input-search-puja"]', delay: 200 },
                    { action: 'type', target: '[data-testid="input-search-puja"]', text: query, delay: 800 },
                    { action: 'wait_for_selector', target: '[data-testid^="button-book-now-"]', delay: 400 },
                    { action: 'move', target: '[data-testid^="button-book-now-"]', delay: 800 },
                    { action: 'click', target: '[data-testid^="button-book-now-"]', delay: 0 }
                  );
                } else {
                  seq.push({ action: 'move', target: '[data-testid="button-nav-services"]', delay: 800 });
                  seq.push({ action: 'click', target: '[data-testid="button-nav-services"]', delay: 400 });
                  seq.push({ action: 'move', target: '[data-testid="link-nav-service-book-puja"]', delay: 800 });
                  seq.push({ action: 'click', target: '[data-testid="link-nav-service-book-puja"]', delay: 800 });
                  seq.push({ action: 'wait_for_selector', target: '[data-testid="input-search-puja"]', delay: 400 });
                  seq.push({ action: 'move', target: '[data-testid="input-search-puja"]', delay: 800 });
                  seq.push({ action: 'click', target: '[data-testid="input-search-puja"]', delay: 200 });
                  seq.push({ action: 'type', target: '[data-testid="input-search-puja"]', text: query, delay: 800 });
                  seq.push({ action: 'wait_for_selector', target: '[data-testid^="button-book-now-"]', delay: 400 });
                  seq.push({ action: 'move', target: '[data-testid^="button-book-now-"]', delay: 800 });
                  seq.push({ action: 'click', target: '[data-testid^="button-book-now-"]', delay: 0 });
                }
              } else {
                // GENERIC PAGE-LEVEL NAV FLOW
                seq.push({ action: 'move', target: finalTarget, delay: 800 });
                // We just point at the top level link and navigate directly
                seq.push({ action: 'navigate', path: cleanTarget, delay: 400 });
                
                // Fix for Pandit role switching
                if (cleanTarget.includes('role=pandit')) {
                  seq.push({ action: 'wait_for_selector', target: '[data-testid="tab-usertype-pandit"]', delay: 400 });
                  seq.push({ action: 'click', target: '[data-testid="tab-usertype-pandit"]', delay: 200 });
                  console.log('[NAV-DEBUG] Clicked Pandit tab explicitly after navigating');
                }
              }

              runSequence(seq);
              // Fallback handled by generic page level flow
            } else if (action === 'FILL_FORM' && (msg.payload.fields || (target && query))) {
              console.log('[FORM-FILL] Raw AI_RESPONSE for FILL_FORM:', msg.payload);
              console.log('[FORM-FILL] Received fields array:', JSON.stringify(msg.payload.fields));
              
              const fieldsToFill = msg.payload.fields || [{ target, query }];
              console.log('[FORM-FILL] Number of fields to process:', fieldsToFill.length);
              console.log('[FORM-FILL] Fields to fill:', fieldsToFill);

              const seq: any[] = [];
              let hasNavigatedToPandit = false;

              for (const field of fieldsToFill) {
                const fTarget = field.target;
                const fQuery = field.query;
                
                let isPanditField = fTarget.startsWith('pandit-');
                
                // Smart tab detection: If we are on signup page and pandit tab is active, treat all generic fields as pandit fields
                if (!isPanditField && window.location.pathname.includes('signup') && document.querySelector('[data-testid="tab-usertype-pandit"][aria-pressed="true"]')) {
                   isPanditField = true;
                }

                let selector = '';
                if (fTarget.includes('name')) selector = isPanditField ? '[data-testid="input-pandit-name"]' : 'input[name="name"], [data-testid="input-name"], #devotee-name';
                else if (fTarget.includes('phone') || fTarget.includes('mobile')) selector = isPanditField ? '[data-testid="input-pandit-phone"]' : 'input[name="phone"], input[type="tel"], [data-testid="input-phone"], #devotee-phone';
                else if (fTarget.includes('city') || fTarget.includes('location')) selector = isPanditField ? '[data-testid="input-pandit-city"]' : 'input[name="city"], [data-testid="input-city"], select#booking-city, #booking-city';
                else if (fTarget.includes('state')) selector = isPanditField ? '[data-testid="input-pandit-state"]' : 'input[name="state"], [data-testid="input-state"]';
                else if (fTarget.includes('email')) selector = isPanditField ? '[data-testid="input-pandit-email"]' : 'input[name="email"], input[type="email"], [data-testid="input-email"]';
                else if (fTarget.includes('date')) selector = 'input[name="date"], input[type="date"], [data-testid="input-date"], #booking-date';
                else if (fTarget.includes('time')) selector = 'input[name="time"], input[type="time"], [data-testid="input-time"], select#booking-time, #booking-time';
                else selector = `input[name="${fTarget}"], #${fTarget}`;
                
                console.log(`[FORM-FILL] Processing field ${fTarget} -> selector: ${selector}`);

                if (isPanditField && !hasNavigatedToPandit) {
                  hasNavigatedToPandit = true;
                  if (window.location.pathname !== '/signup') {
                     seq.push({ action: 'navigate', path: '/signup?role=pandit', delay: 400 });
                  } else {
                     seq.push({ action: 'click', target: '[data-testid="tab-usertype-pandit"]', delay: 200 });
                  }
                  seq.push({ action: 'wait_for_selector', target: selector, delay: 200 });
                }

                if (isPanditField) {
                  seq.push({ action: 'move', target: selector, delay: 400 });
                  seq.push({ action: 'type', target: selector, text: fQuery, delay: 800 });
                } else {
                  const element = document.querySelector(selector);
                  console.log(`[FORM-FILL] Attempting to queue fill: field="${fTarget}", value="${fQuery}", selector="${selector}", foundElement=${!!element}`);
                  if (element || hasNavigatedToPandit) {
                    seq.push({ action: 'move', target: selector, delay: 800 });
                    seq.push({ action: 'type', target: selector, text: fQuery, delay: 800 });
                  } else {
                    console.warn(`[FORM-FILL] Could not find element for target: ${fTarget}`);
                  }
                }
              }

              if (seq.length > 0) {
                sequenceQueueRef.current = seq;
                if (!isExecutingSequenceRef.current) {
                  processNextStepRef.current();
                }
              }
            }
            
            setDialogueText(contentStr);
            console.log('[STATE]', 'idle -> speaking');
            setSaarthiState('speaking');
            isFinalChunkReceived.current = false;
            
            // Fallback: if no audio arrives or queue gets stuck, go back to listening after 7 seconds
            if (fallbackTimeoutRef.current) clearTimeout(fallbackTimeoutRef.current);
            fallbackTimeoutRef.current = setTimeout(() => {
               if (audioQueueRef.current.length === 0 && !isPlayingRef.current) {
                  console.log('[STATE]', 'fallback timeout fired after 7s');
                  console.log('[STATE]', 'speaking -> listening');
                  setSaarthiState('listening');
               }
            }, 7000);
            
            return;
          }

          // ----------- AUDIO_CHUNK handling -----------------------------------
          if (msg.type === 'AUDIO_CHUNK') {
            const dataLength = msg.payload.data_length || 0;
            const isFinal = msg.payload.is_final || false;
            console.log('[STATE]', 'AUDIO_CHUNK is_final:', isFinal);
            
            if (isFinal) {
                isFinalChunkReceived.current = true;
            }
            if (!audioContextRef.current) {
              audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
            }
            if (audioContextRef.current.state === 'suspended') {
              console.log(`[Voice] AudioContext is suspended. Attempting resume()...`);
              try {
                await audioContextRef.current.resume();
                console.log(`[Voice] AudioContext resume() succeeded. State is now: ${audioContextRef.current.state}`);
              } catch (e) {
                console.warn('[Voice] Could not resume AudioContext (autoplay blocked):', e);
                console.log(`[Voice] AudioContext state after failed resume: ${audioContextRef.current.state}`);
                
                // Add global listener to resume on next interaction
                if (!(window as any)._audioPlayClickListenerAdded) {
                  (window as any)._audioPlayClickListenerAdded = true;
                  console.log('[Voice] Added global user interaction listener to resume audio.');
                  const resumeAudio = async () => {
                    console.log('[Voice] User interaction detected, attempting to resume AudioContext...');
                    if (audioContextRef.current?.state === 'suspended') {
                      try {
                        await audioContextRef.current.resume();
                        console.log('[Voice] AudioContext resumed successfully via user interaction.');
                      } catch (err) {
                        console.error('[Voice] Failed to resume on user interaction:', err);
                      }
                    }
                    window.removeEventListener('click', resumeAudio);
                    window.removeEventListener('keydown', resumeAudio);
                    window.removeEventListener('touchstart', resumeAudio);
                    (window as any)._audioPlayClickListenerAdded = false;
                  };
                  window.addEventListener('click', resumeAudio);
                  window.addEventListener('keydown', resumeAudio);
                  window.addEventListener('touchstart', resumeAudio);
                }
              }
            }
            const audioData = msg.payload.data || msg.payload.audio_b64;
            if (audioData) {
              const binaryString = atob(audioData);
              const bytes = new Uint8Array(binaryString.length);
              for (let i = 0; i < binaryString.length; i++) bytes[i] = binaryString.charCodeAt(i);
              console.log(`[Voice] Decoded audioData bytes length: ${bytes.length}`);
              try {
                const decoded = await audioContextRef.current.decodeAudioData(bytes.buffer);
                console.log(`[Voice] Successfully decoded via decodeAudioData (duration: ${decoded.duration}s)`);
                audioQueueRef.current.push(decoded);
                playNextAudio();
              } catch (e) {
                console.warn('[Voice] decodeAudioData failed, falling back to PCM16 buffer creation', e);
                const pcm16 = new Int16Array(bytes.buffer);
                const float32 = new Float32Array(pcm16.length);
                for (let i = 0; i < pcm16.length; i++) {
                  float32[i] = pcm16[i] / 0x8000;
                }
                const audioBuf = audioContextRef.current.createBuffer(1, float32.length, 16000);
                audioBuf.copyToChannel(float32, 0);
                audioQueueRef.current.push(audioBuf);
                playNextAudio();
              }
            } else {
              console.warn('[Voice] AUDIO_CHUNK missing audio payload');
            }
            return;
          }
        } catch (err) {
          console.error('[Voice] WebSocket message parsing error', err);
        }
      };

    ws.onclose = () => {
      console.log('[Voice] WebSocket Closed');
      setIsConnected(false);
    };
    ws.onerror = (e) => {
      console.error('[Voice] WebSocket Error', e);
      setError('WebSocket error');
    };

    wsRef.current = ws;

    return () => {
      console.log('[Voice] Cleaning up WebSocket');
      ws.close();
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  const playNextAudio = useCallback(() => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0 || !audioContextRef.current) {
      if (audioQueueRef.current.length === 0 && !isPlayingRef.current && isFinalChunkReceived.current) {
         console.log('[STATE]', 'audio queue drained, transitioning to listening');
         isFinalChunkReceived.current = false;
         if (fallbackTimeoutRef.current) {
             clearTimeout(fallbackTimeoutRef.current);
             fallbackTimeoutRef.current = null;
         }
         console.log('[STATE]', 'speaking -> listening');
         setSaarthiState('listening');
      }
      return;
    }
    
    const tryPlay = async () => {
        console.log(`[Voice] Attempting to play greeting audio before playing chunk. Current AudioContext state: ${audioContextRef.current?.state}`);
        if (audioContextRef.current?.state === 'suspended') {
            try {
                await audioContextRef.current.resume();
            } catch (err: any) {
                console.error('[Voice] Failed to resume AudioContext. FULL error object:', err);
            }
        }
        
        if (audioContextRef.current?.state === 'suspended') {
             console.warn('[Voice] AudioContext is still suspended (autoplay policy block). Holding audio queue for user interaction.');
             if (!(window as any)._audioPlayClickListenerAdded) {
                  (window as any)._audioPlayClickListenerAdded = true;
                  const resumeAudio = async () => {
                    console.log('[Voice] User interaction detected, attempting to resume AudioContext...');
                    if (audioContextRef.current?.state === 'suspended') {
                      try {
                        await audioContextRef.current.resume();
                        console.log('[Voice] AudioContext resumed successfully via user interaction.');
                        playNextAudio();
                      } catch (err) {
                        console.error('[Voice] Failed to resume on user interaction:', err);
                      }
                    } else {
                        playNextAudio();
                    }
                    window.removeEventListener('click', resumeAudio, true);
                    window.removeEventListener('keydown', resumeAudio, true);
                    window.removeEventListener('touchstart', resumeAudio, true);
                    (window as any)._audioPlayClickListenerAdded = false;
                  };
                  window.addEventListener('click', resumeAudio, true);
                  window.addEventListener('keydown', resumeAudio, true);
                  window.addEventListener('touchstart', resumeAudio, true);
             }
             return; // abort playNextAudio for now, wait for click!
        }
        
        console.log('[Voice] Playing next audio chunk from queue');
        isPlayingRef.current = true;
        const buffer = audioQueueRef.current.shift()!;
        const source = audioContextRef.current.createBufferSource();
        source.buffer = buffer;
        source.connect(audioContextRef.current.destination);
        
        source.onended = () => {
          console.log('[Voice] Audio chunk playback ended');
          isPlayingRef.current = false;
          playNextAudio();
        };
        
        try {
            console.log(`[Voice] Calling source.start(). AudioContext state is: ${audioContextRef.current.state}`);
            source.start(0);
        } catch (err: any) {
            console.error('[Voice] source.start(0) threw an error! FULL error object:', err);
            isPlayingRef.current = false;
            playNextAudio();
        }
    };
    
    tryPlay();
  }, [setSaarthiState]);

  useEffect(() => {
    console.log(`[Voice] state changed to: ${state}, isConnected: ${isConnected}`);
    let vadInterval: number;
    let vadAudioCtx: AudioContext;
    let silenceStart = Date.now();
    let isSpeaking = false;
    let recordedBytesSent = 0;
    let vadWarmupTime = Date.now() + 1000; // 1 second warmup where VAD doesn't trigger silence

    if (state === 'listening' && isConnected) {
      console.log('[Voice] Requesting microphone permission...');
      navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
          console.log('[Voice] Microphone permission granted');
          // Start AudioContext with 16000 sampleRate
          if (audioContextRef.current) {
             if (audioContextRef.current.sampleRate !== 16000) {
                 audioContextRef.current.close();
                 audioContextRef.current = null;
             }
          }
          if (!audioContextRef.current) {
            audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
          }
          
          const audioCtx = audioContextRef.current;
          // Ensure AudioContext is resumed if suspended
          if (audioCtx.state === 'suspended') {
             audioCtx.resume().then(() => console.log('[Voice] AudioContext resumed for mic input'));
          }

          const sourceNode = audioCtx.createMediaStreamSource(stream);
          const processor = audioCtx.createScriptProcessor(4096, 1, 1);
          
          let chunkCounter = 0;
          processor.onaudioprocess = (event) => {
            chunkCounter++;
            if (chunkCounter % 10 === 0) {
               console.log(`[DIAGNOSTIC] onaudioprocess fired (chunk ${chunkCounter}). AudioCtx state: ${audioCtx.state}`);
            }
            if (wsRef.current?.readyState === WebSocket.OPEN) {
              const inputData = event.inputBuffer.getChannelData(0);
              const pcm16 = float32ToPCM16(inputData);
              const base64data = uint8ArrayToBase64(pcm16);
              recordedBytesSent += pcm16.byteLength;
              if (chunkCounter % 10 === 0) {
                 console.log(`[DIAGNOSTIC] Recorded bytes this chunk: ${pcm16.byteLength}, Total sent: ${recordedBytesSent}`);
              }
              wsRef.current.send(JSON.stringify({
                type: 'AUDIO_FRAME',
                payload: { data: base64data },
              }));
            }
          };
          
          sourceNode.connect(processor);
          processor.connect(audioCtx.destination); // Required for script processor to run
          
          // Store these in the ref so we can clean them up instead of MediaRecorder
          (mediaRecorderRef as any).current = {
            state: 'recording',
            stop: () => {
              processor.disconnect();
              sourceNode.disconnect();
            },
            stream: stream
          };
          console.log('[Voice] Started ScriptProcessorNode for streaming audio');

          // VAD Setup
          vadAudioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
          const source = vadAudioCtx.createMediaStreamSource(stream);
          const analyser = vadAudioCtx.createAnalyser();
          analyser.fftSize = 512;
          analyser.minDecibels = -70; // More sensitive
          analyser.smoothingTimeConstant = 0.1;
          source.connect(analyser);

          const dataArray = new Uint8Array(analyser.frequencyBinCount);
          silenceStart = Date.now();

          vadInterval = window.setInterval(() => {
            analyser.getByteFrequencyData(dataArray);
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) {
              sum += dataArray[i];
            }
            const average = sum / dataArray.length;
            
            // Console log VAD metrics every 500ms
            if (Date.now() % 500 < 100) {
              console.log(`[Voice] VAD Tick | Volume Avg: ${average.toFixed(2)} | isSpeaking: ${isSpeaking}`);
            }

            if (Date.now() < vadWarmupTime) {
               // Ignore silence logic during warmup
               silenceStart = Date.now();
               return;
            }

            if (average > 10) { // Threshold for speech (lowered to 10 for better detection)
              if (!isSpeaking) {
                console.log(`[Voice] VAD: Speech started (Volume: ${average.toFixed(2)} > 10)`);
                isSpeaking = true;
              }
              silenceStart = Date.now();
            } else {
              if (isSpeaking && (Date.now() - silenceStart > 1800)) { // 1.8 seconds of silence
                console.log(`[Voice] VAD: Silence detected. Triggering AUDIO_END. Volume was: ${average.toFixed(2)}`);
                isSpeaking = false;
                setSaarthiState('idle'); // This will trigger the cleanup and AUDIO_END via the hook dependency change
                
                // Auto-minimize on first real voice command completion
                console.log('[WIDGET] Shrink condition check (VAD): isSpeaking=false, _hasMinimizedOnce=', (window as any)._hasMinimizedOnce);
                if (!(window as any)._hasMinimizedOnce) {
                  console.log('[WIDGET] Triggering shrink-to-corner animation now (via VAD)');
                  forceMinimize();
                  (window as any)._hasMinimizedOnce = true;
                }
              }
            }
          }, 100);

        })
        .catch(err => {
          console.error('[Voice] Microphone error', err);
          setError('Could not access microphone');
          setSaarthiState('idle');
        });
    }
    
    return () => {
      window.clearInterval(vadInterval);
      if (vadAudioCtx && vadAudioCtx.state !== 'closed') {
        vadAudioCtx.close();
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        console.log(`[Voice] Stopping MediaRecorder (cleanup). Total recorded bytes sent: ${recordedBytesSent}`);
        
        // Prevent ghost cleanups by correctly mutating our mocked state
        mediaRecorderRef.current.state = 'inactive';
        
        mediaRecorderRef.current.stop();
        mediaRecorderRef.current.stream.getTracks().forEach((track: MediaStreamTrack) => track.stop());
        
        if (recordedBytesSent > 0) {
            console.log(`[Voice] Sending AUDIO_END frame with total byte size: ${recordedBytesSent}`);
            wsRef.current?.send(JSON.stringify({
              type: 'AUDIO_END',
              payload: {}
            }));
        } else {
            console.log('[Voice] Skipping AUDIO_END frame because 0 bytes were recorded during this session.');
        }
      }
    };
  }, [state, isConnected, setSaarthiState]);

  const stopSpeaking = useCallback(() => {
    console.log('[Voice] Barge-in / Stop requested. Halting speech.');
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close().then(() => {
         audioContextRef.current = null;
      });
    }
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    isFinalChunkReceived.current = false;
    if (fallbackTimeoutRef.current) {
      clearTimeout(fallbackTimeoutRef.current);
      fallbackTimeoutRef.current = null;
    }
    setSaarthiState('listening');
  }, [setSaarthiState]);

  return { isConnected, error, stopSpeaking };
}
