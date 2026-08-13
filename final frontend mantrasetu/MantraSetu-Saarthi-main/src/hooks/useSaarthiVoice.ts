import { useState, useEffect, useRef, useCallback } from 'react';
import { useSaarthi } from '../components/saarthi/SaarthiContext';
import { useNavigate } from 'react-router-dom';
import { getPersistableData } from '../utils/formSecurity';

/** Shared sanitization helper to guarantee no passwords/credentials enter sessionStorage */
export function persistVoiceState(data: Record<string, any>) {
  try {
    const safeData = getPersistableData(data);
    sessionStorage.setItem('ms_saarthi_form_state', JSON.stringify(safeData));
  } catch (e) {}
}

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

export function getFormStateData(): Record<string, string> {
  const data: Record<string, string> = {};

  try {
    const isPanditForm = !!document.querySelector('#pandit-onboarding-form, [data-testid="card-signup"]');
    if (!isPanditForm) return data;

    const firstNameEl = document.querySelector<HTMLInputElement>('#pandit-first-name, [data-testid="input-pandit-first-name"]');
    const lastNameEl = document.querySelector<HTMLInputElement>('#pandit-last-name, [data-testid="input-pandit-last-name"]');
    const phoneEl = document.querySelector<HTMLInputElement>('#pandit-phone, [data-testid="input-pandit-phone"]');
    const emailEl = document.querySelector<HTMLInputElement>('#pandit-email, [data-testid="input-pandit-email"]');
    const genderEl = document.querySelector<HTMLSelectElement>('#pandit-gender, [data-testid="select-pandit-gender"]');
    const cityEl = document.querySelector<HTMLInputElement>('#pandit-city, [data-testid="input-pandit-city"]');
    const stateEl = document.querySelector<HTMLInputElement>('#pandit-state, [data-testid="input-pandit-state"]');
    const expEl = document.querySelector<HTMLSelectElement>('#pandit-exp, [data-testid="select-pandit-exp"]');
    const eduEl = document.querySelector<HTMLInputElement>('#pandit-education, [data-testid="input-pandit-education"]');
    const specEl = document.querySelector<HTMLSelectElement>('#pandit-spec, [data-testid="select-pandit-spec"]');
    const bioEl = document.querySelector<HTMLTextAreaElement>('#pandit-bio, [data-testid="textarea-pandit-bio"]');

    const pwdEl = document.querySelector<HTMLInputElement>('#pandit-password, [data-testid="input-pandit-password"]');
    const cpwdEl = document.querySelector<HTMLInputElement>('#pandit-confirm, [data-testid="input-pandit-confirm"]');
    const aadhaarInput = document.querySelector<HTMLInputElement>('#pandit-aadhaar-input, [data-testid="input-aadhaar-file"]');
    const certInput = document.querySelector<HTMLInputElement>('#pandit-cert-input, [data-testid="input-cert-file"]');
    const termsEl = document.querySelector<HTMLInputElement>('#pandit-terms-accepted, [data-testid="checkbox-pandit-terms"]');

    const stepEl = document.querySelector('[data-testid="pandit-wizard-step"]');
    if (stepEl) {
      data['pandit-step'] = stepEl.getAttribute('data-step') || '1';
    }

    if (firstNameEl?.value) data['pandit-first-name'] = firstNameEl.value.trim();
    if (lastNameEl?.value) data['pandit-last-name'] = lastNameEl.value.trim();

    const fn = firstNameEl?.value?.trim() || '';
    const ln = lastNameEl?.value?.trim() || '';
    if (fn || ln) {
      data['pandit-name'] = `${fn} ${ln}`.trim();
      data['name'] = `${fn} ${ln}`.trim();
    }

    if (phoneEl?.value) {
      data['pandit-phone'] = phoneEl.value.trim();
      data['phone'] = phoneEl.value.trim();
    }
    if (emailEl?.value) {
      data['pandit-email'] = emailEl.value.trim();
      data['email'] = emailEl.value.trim();
    }
    if (genderEl?.value) data['pandit-gender'] = genderEl.value.trim();
    if (cityEl?.value) {
      data['pandit-city'] = cityEl.value.trim();
      data['city'] = cityEl.value.trim();
    }
    if (stateEl?.value) {
      data['pandit-state'] = stateEl.value.trim();
      data['state'] = stateEl.value.trim();
    }
    if (expEl?.value) {
      data['pandit-exp'] = expEl.value.trim();
      data['experience'] = expEl.value.trim();
    }
    if (eduEl?.value) data['pandit-education'] = eduEl.value.trim();
    if (specEl?.value) {
      data['pandit-spec'] = specEl.value.trim();
      data['specialization'] = specEl.value.trim();
    }
    if (bioEl?.value) data['pandit-bio'] = bioEl.value.trim();

    // Password security: send flags only, never raw string
    data['pandit-password_filled'] = (pwdEl && pwdEl.value && pwdEl.value.trim().length > 0) ? 'true' : 'false';
    data['password_filled'] = data['pandit-password_filled'];

    data['pandit-confirm_filled'] = (cpwdEl && cpwdEl.value && cpwdEl.value.trim().length > 0) ? 'true' : 'false';
    data['confirm_filled'] = data['pandit-confirm_filled'];

    data['aadhaar_attached'] = (aadhaarInput && aadhaarInput.files && aadhaarInput.files.length > 0) ? 'true' : 'false';
    data['cert_attached'] = (certInput && certInput.files && certInput.files.length > 0) ? 'true' : 'false';
    data['terms_accepted'] = (termsEl && termsEl.checked) ? 'true' : 'false';

    if ((window as any)._lastSubmissionError) {
      data['submission_error'] = (window as any)._lastSubmissionError;
    }
    if ((window as any)._lastConflictField) {
      data['conflict_field'] = (window as any)._lastConflictField;
    }
  } catch (e) {
    console.warn('[FORM-STATE] Error building form state data:', e);
  }

  return data;
}

export function useSaarthiVoice() {
  const { state, setDialogueText, setSaarthiState, minimizeSaarthi, forceMinimize } = useSaarthi();
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const currentAudioSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const audioQueueRef = useRef<AudioBuffer[]>([]);
  const isPlayingRef = useRef(false);
  const isFinalChunkReceived = useRef(false);
  const fallbackTimeoutRef = useRef<number | NodeJS.Timeout | null>(null);
  const sequenceQueueRef = useRef<any[]>([]);
  const isExecutingSequenceRef = useRef(false);
  const lastTargetRef = useRef<string | null>(null);

  const stateRef = useRef(state);
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  const stopAudioPlayback = useCallback(() => {
    console.log('[BARGE-IN] Executing stopAudioPlayback(). Halting active audio source & flushing audio queue.');
    if (currentAudioSourceRef.current) {
      try {
        currentAudioSourceRef.current.stop();
        currentAudioSourceRef.current.disconnect();
      } catch (e) {
        console.warn('[BARGE-IN] Error stopping audio source:', e);
      }
      currentAudioSourceRef.current = null;
    }
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    isFinalChunkReceived.current = false;

    if (fallbackTimeoutRef.current) {
      clearTimeout(fallbackTimeoutRef.current);
      fallbackTimeoutRef.current = null;
    }

    if (sequenceQueueRef.current.length > 0) {
      console.log('[BARGE-IN] Flushing active UI animation sequence queue due to interruption.');
      sequenceQueueRef.current = [];
      isExecutingSequenceRef.current = false;
    }
  }, []);

  const processNextStep = useCallback(() => {
    if (sequenceQueueRef.current.length === 0) {
      isExecutingSequenceRef.current = false;
      const cursor = document.getElementById('saarthi-cursor');
      if (cursor) {
          // Keep cursor visible between questions. Only hide when the entire sequence is complete
          // (meaning the final specialization field was filled) or if Saarthi is minimized.
          const isComplete = lastTargetRef.current?.includes('pandit-spec');
          if (isComplete) {
              setTimeout(() => {
                 cursor.style.opacity = '0';
              }, 1200);
          }
      }
      return;
    }

    isExecutingSequenceRef.current = true;
    const step = sequenceQueueRef.current.shift()!;
    console.log('[NAV-DEBUG] Executing step:', step);
    if (step.target) {
      lastTargetRef.current = step.target;
    }

    let cursor = document.getElementById('saarthi-cursor');
    if (!cursor) {
      cursor = document.createElement('div');
      cursor.id = 'saarthi-cursor';
      cursor.style.position = 'fixed'; // Use fixed so it tracks viewport coordinates
      cursor.style.width = '24px';
      cursor.style.height = '24px';
      cursor.style.borderRadius = '50%';
      cursor.style.backgroundColor = 'rgba(238, 124, 43, 0.6)';
      cursor.style.border = '2px solid #ee7c2b';
      cursor.style.boxShadow = '0 0 10px rgba(238, 124, 43, 0.5)';
      cursor.style.zIndex = '99999';
      cursor.style.pointerEvents = 'none';
      cursor.style.transition = 'all 0.8s ease-in-out';
      cursor.style.left = `${window.innerWidth / 2 - 12}px`;
      cursor.style.top = `${window.innerHeight / 2 - 12}px`;
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
      // Hide cursor on page navigation to prevent floating cursor during load
      cursor.style.opacity = '0';
      navigate(step.path);
      setTimeout(processNextStep, step.delay);
      return;
    }

    if (step.action === 'REFRESH_PAGE') {
      console.log('[NAV-DEBUG] Triggering browser reload for REFRESH_PAGE action');
      window.location.reload();
      return;
    }

    if (step.action === 'scroll' && step.target) {
      const targetEl = document.querySelector(step.target) as HTMLElement;
      if (targetEl) {
        targetEl.scrollIntoView({ behavior: 'auto', block: 'center' });
        setTimeout(processNextStep, step.delay || 400);
      } else {
        console.warn('[NAV-DEBUG] Scroll target not found, gracefully staying at top:', step.target);
        processNextStep();
      }
      return;
    }

    if (step.action === 'move' && step.target) {
      const targetEl = document.querySelector(step.target) as HTMLElement;
      if (targetEl) {
        targetEl.scrollIntoView({ behavior: 'auto', block: 'center' });
        
        // 300ms scroll buffer to ensure final coordinates are accurate
        setTimeout(() => {
          const rect = targetEl.getBoundingClientRect();
          // Coordinates targeting the center of the element relative to viewport
          const targetX = rect.left + rect.width / 2;
          const targetY = rect.top + rect.height / 2;
          
          cursor!.style.opacity = '1';
          cursor!.style.transform = 'scale(1)';
          cursor!.style.backgroundColor = 'rgba(238, 124, 43, 0.6)';
          cursor!.style.left = `${targetX - 12}px`;
          cursor!.style.top = `${targetY - 12}px`;
          
          setTimeout(processNextStep, step.delay);
        }, 300);
      } else {
        console.warn('[NAV-DEBUG] Move target not found:', step.target);
        processNextStep();
      }
      return;
    }

    if (step.action === 'click' && step.target) {
      let targetEl = document.querySelector(step.target) as HTMLElement;
      if (!targetEl && step.target.includes('submit')) {
        targetEl = document.querySelector('[data-testid="button-submit-pandit-signup"], [data-testid="button-submit-signup"], form button[type="submit"], button[type="submit"]') as HTMLElement;
      }
      if (targetEl) {
        const rect = targetEl.getBoundingClientRect();
        const targetX = rect.left + rect.width / 2;
        const targetY = rect.top + rect.height / 2;
        
        cursor.style.left = `${targetX - 12}px`;
        cursor.style.top = `${targetY - 12}px`;
        cursor.style.transform = 'scale(0.5)';
        cursor.style.backgroundColor = 'rgba(238, 124, 43, 0.9)';
        
        targetEl.click();
        targetEl.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
        const formEl = targetEl.closest('form');
        if (formEl && (targetEl.getAttribute('type') === 'submit' || step.target.includes('submit'))) {
          console.log('[FORM-SUBMIT] Triggering form.requestSubmit() explicitly');
          if (typeof formEl.requestSubmit === 'function') {
            formEl.requestSubmit();
          } else {
            formEl.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
          }
        }
        
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

    if (step.action === 'open_dropdown' && step.target) {
      const targetEl = document.querySelector(step.target) as HTMLSelectElement;
      if (targetEl && targetEl.tagName.toLowerCase() === 'select') {
        targetEl.scrollIntoView({ behavior: 'auto', block: 'center' });
        setTimeout(() => {
          // Open dropdown visually by setting size to options length
          targetEl.size = targetEl.options.length || 4;
          targetEl.focus();
          setTimeout(processNextStep, step.delay);
        }, 300);
      } else {
        console.warn('[NAV-DEBUG] open_dropdown target not found or not select:', step.target);
        processNextStep();
      }
      return;
    }

    if (step.action === 'select_option' && step.target && step.text) {
      const targetEl = document.querySelector(step.target) as HTMLSelectElement;
      if (targetEl && targetEl.tagName.toLowerCase() === 'select') {
        const options = Array.from(targetEl.options);
        const matchVal = step.text.toLowerCase();
        
        let matchedIdx = options.findIndex(o => o.value.toLowerCase() === matchVal || o.text.toLowerCase() === matchVal);
        if (matchedIdx === -1) {
          // Fuzzy lookup
          matchedIdx = options.findIndex(o => o.value.toLowerCase().includes(matchVal) || o.text.toLowerCase().includes(matchVal));
        }
        if (matchedIdx === -1) matchedIdx = 0;

        const matchedOption = options[matchedIdx];
        const selectRect = targetEl.getBoundingClientRect();
        
        let optX = selectRect.left + selectRect.width / 2;
        let optY = selectRect.top + selectRect.height;

        try {
          const optRect = matchedOption.getBoundingClientRect();
          if (optRect && optRect.height > 0) {
            optX = optRect.left + optRect.width / 2;
            optY = optRect.top + optRect.height / 2;
          } else {
            const optionHeight = 24; // fallback item height
            optY = selectRect.top + selectRect.height + matchedIdx * optionHeight + optionHeight / 2;
          }
        } catch (e) {
          const optionHeight = 24;
          optY = selectRect.top + selectRect.height + matchedIdx * optionHeight + optionHeight / 2;
        }

        // Move cursor to option visual center
        cursor.style.opacity = '1';
        cursor.style.transform = 'scale(1)';
        cursor.style.backgroundColor = 'rgba(238, 124, 43, 0.6)';
        cursor.style.left = `${optX - 12}px`;
        cursor.style.top = `${optY - 12}px`;

        // Hover delay to simulate choosing
        setTimeout(() => {
          cursor.style.transform = 'scale(0.5)';
          cursor.style.backgroundColor = 'rgba(238, 124, 43, 0.9)';
          
          targetEl.selectedIndex = matchedIdx;
          targetEl.dispatchEvent(new Event('input', { bubbles: true }));
          targetEl.dispatchEvent(new Event('change', { bubbles: true }));

          setTimeout(() => {
            cursor.style.transform = 'scale(1)';
            cursor.style.backgroundColor = 'rgba(238, 124, 43, 0.6)';
            
            // Collapse dropdown back to normal select
            targetEl.size = 1;
            targetEl.classList.add('saarthi-highlight');
            
            setTimeout(() => {
              targetEl.classList.remove('saarthi-highlight');
              setTimeout(processNextStep, step.delay);
            }, 600);
          }, 150);
        }, 600);
      } else {
        console.warn('[NAV-DEBUG] select_option target not found or not select:', step.target);
        processNextStep();
      }
      return;
    }

    if (step.action === 'type' && step.target && step.text) {
      const targetEl = document.querySelector(step.target) as HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;
      console.log(`[FORM-FILL-EXEC] Action: TYPE. Target: "${step.target}". ElementFound: ${!!targetEl}. ValueToSet: "${step.text}"`);
      if (targetEl) {
         const rect = targetEl.getBoundingClientRect();
         const targetX = rect.left + rect.width / 2;
         const targetY = rect.top + rect.height / 2;
         
         cursor.style.left = `${targetX - 12}px`;
         cursor.style.top = `${targetY - 12}px`;
         
         // In React 18, input value setters are defined on the instance proto
         let nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
         if (targetEl.tagName.toLowerCase() === 'textarea') {
             nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')?.set;
         } else if (targetEl.tagName.toLowerCase() === 'select') {
             nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value')?.set;
         }

         // Clear previous highlights before typing new field value
         document.querySelectorAll('.saarthi-highlight').forEach((el) => {
           el.classList.remove('saarthi-highlight');
         });
         targetEl.classList.add('saarthi-highlight');
         console.log('[FORM-FILL-EXEC] Applied saarthi-highlight class to target:', step.target);

         // Set value instantly instead of char-by-char to avoid React race conditions
         if (nativeInputValueSetter) {
           nativeInputValueSetter.call(targetEl, step.text);
         } else {
           (targetEl as HTMLInputElement).value = step.text;
         }

         targetEl.dispatchEvent(new Event('input', { bubbles: true }));
         targetEl.dispatchEvent(new Event('change', { bubbles: true }));

         setTimeout(() => {
           targetEl.classList.remove('saarthi-highlight');
           processNextStep();
         }, 400);
      } else {
         console.warn('[NAV-DEBUG] Type target not found:', step.target);
         processNextStep();
      }
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
      
      let persistentSessionId = sessionStorage.getItem('saarthi_session_id');
      if (!persistentSessionId) {
        persistentSessionId = 'vsession_f' + Math.random().toString(36).substring(2, 14);
        sessionStorage.setItem('saarthi_session_id', persistentSessionId);
      }
      console.log('[Voice] Sending CONNECT with session_id:', persistentSessionId, 'current_page:', window.location.pathname);
      
      ws.send(JSON.stringify({
        type: 'CONNECT',
        payload: {
          language: 'hi',
          session_id: persistentSessionId,
          current_page: window.location.pathname
        }
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
            
            // BARGE-IN / INTERRUPTION: Flush any active tour or sequence when user speaks
            if (sequenceQueueRef.current.length > 0) {
              console.log('[BARGE-IN] Interrupted active sequence queue due to new user speech.');
              sequenceQueueRef.current = [];
              isExecutingSequenceRef.current = false;
            }

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
            console.log('[Voice] [CONNECT-DIAGNOSTIC] RAW AI_RESPONSE Received:', JSON.stringify(msg.payload));
            let contentStr = msg.payload.content || '';
            
            let action = msg.payload.action || (msg.payload.navigation_directive && msg.payload.navigation_directive.action) || null;
            let target = msg.payload.target || (msg.payload.navigation_directive && msg.payload.navigation_directive.target) || null;
            let intent = msg.payload.intent || (msg.payload.navigation_directive && msg.payload.navigation_directive.intent) || null;
            let query = msg.payload.query || (msg.payload.navigation_directive && msg.payload.navigation_directive.query) || null;
            let activeField = msg.payload.active_field || (msg.payload.navigation_directive && msg.payload.navigation_directive.active_field) || null;
            
            try {
              const parsed = JSON.parse(contentStr);
              if (!action && parsed.action) action = parsed.action;
              if (!target && parsed.target) target = parsed.target;
              if (!intent && parsed.intent) intent = parsed.intent;
              if (!query && parsed.query) query = parsed.query;
              if (!activeField && parsed.active_field) activeField = parsed.active_field;
              if (parsed.response_text) contentStr = parsed.response_text;
            } catch (e) {}

            console.log('[DEBUG-PAYLOAD-EXTRACT] Extracted action:', action, 'target:', target, 'activeField:', activeField, 'intent:', intent);

            // ── HIGHLIGHT TRIGGER & GENERALIZED DROPDOWN AUTO-EXPAND ON BOT QUESTION ASK ──
            if (activeField) {
              document.querySelectorAll('.saarthi-highlight').forEach((el) => {
                el.classList.remove('saarthi-highlight');
              });
              document.querySelectorAll('.saarthi-options-list').forEach((el) => {
                el.remove();
              });

              let highlightSelector = '';
              const isPanditField = activeField.startsWith('pandit-') || !!document.querySelector('[data-testid="tab-usertype-pandit"][aria-pressed="true"]');
              
              if (activeField === 'pandit-first-name') {
                highlightSelector = '[data-testid="input-pandit-first-name"]';
              } else if (activeField === 'pandit-last-name') {
                highlightSelector = '[data-testid="input-pandit-last-name"]';
              } else if (activeField === 'pandit-gender') {
                highlightSelector = '[data-testid="pill-group-pandit-gender"]';
              } else if (activeField === 'pandit-availability') {
                highlightSelector = '[data-testid="pill-group-pandit-availability"]';
              } else if (activeField === 'pandit-service-areas') {
                highlightSelector = '[data-testid="pill-group-pandit-service-areas"]';
              } else if (activeField === 'pandit-languages') {
                highlightSelector = '[data-testid="pill-group-pandit-languages"]';
              } else if (activeField === 'pandit-spec') {
                highlightSelector = '[data-testid="pill-group-pandit-spec"]';
              } else if (activeField === 'pandit-certFile') {
                highlightSelector = '[data-testid="upload-pandit-certFile"]';
              } else if (activeField === 'pandit-aadhaarFile') {
                highlightSelector = '[data-testid="upload-pandit-aadhaarFile"]';
              } else if (activeField === 'pandit-galleryFiles') {
                highlightSelector = '[data-testid="upload-pandit-galleryFiles"]';
              } else if (activeField === 'pandit-password') {
                highlightSelector = '[data-testid="input-pandit-password"]';
              } else if (activeField === 'pandit-confirm') {
                highlightSelector = '[data-testid="input-pandit-confirm"]';
              } else if (activeField.includes('name')) {
                highlightSelector = isPanditField ? '[data-testid="input-pandit-name"]' : '#devotee-name, [data-testid="input-name"]';
              } else if (activeField.includes('phone') || activeField.includes('mobile')) {
                highlightSelector = isPanditField ? '[data-testid="input-pandit-phone"]' : 'input[type="tel"], [data-testid="input-phone"]';
              } else if (activeField.includes('email')) {
                highlightSelector = isPanditField ? '[data-testid="input-pandit-email"]' : 'input[type="email"], [data-testid="input-email"]';
              } else if (activeField.includes('city')) {
                highlightSelector = isPanditField ? '[data-testid="input-pandit-city"]' : '[data-testid="input-city"]';
              } else if (activeField.includes('state')) {
                highlightSelector = isPanditField ? '[data-testid="input-pandit-state"]' : '[data-testid="input-state"]';
              } else if (activeField.includes('exp')) {
                highlightSelector = '[data-testid="select-pandit-exp"]';
              } else {
                highlightSelector = `#${activeField}, [data-testid="input-${activeField}"], [data-testid="select-${activeField}"]`;
              }

              const targetHighlightEl = document.querySelector(highlightSelector) as HTMLElement | null;
              console.log('[DEBUG-HIGHLIGHT-TARGET] activeField:', activeField, 'selector:', highlightSelector, 'found:', !!targetHighlightEl, 'tagName:', targetHighlightEl?.tagName);

              if (targetHighlightEl) {
                targetHighlightEl.classList.add('saarthi-highlight');
                targetHighlightEl.scrollIntoView({ behavior: 'auto', block: 'center' });
                const count = document.querySelectorAll('.saarthi-highlight').length;
                console.log('[PROOF-FEATURE-A] activeFieldId:', activeField, '| Highlighted Element:', targetHighlightEl.id || targetHighlightEl.getAttribute('data-testid') || targetHighlightEl.tagName, '| Total .saarthi-highlight count in DOM:', count);

                // ── GENERALIZED DROPDOWN DETECTION & INLINE OPTIONS RENDERING ──
                const selectEl = (targetHighlightEl.tagName === 'SELECT' ? targetHighlightEl : targetHighlightEl.querySelector('select')) as HTMLSelectElement | null;
                console.log('[DEBUG-DROPDOWN-CHECK] activeField:', activeField, 'selectEl:', selectEl?.tagName, 'optionsCount:', selectEl?.options?.length);

                if (selectEl && selectEl.options && selectEl.options.length > 0) {
                  const parentContainer = selectEl.closest('.field') || selectEl.parentElement || targetHighlightEl;
                  if (parentContainer && !parentContainer.querySelector('.saarthi-options-list')) {
                    const optionsContainer = document.createElement('div');
                    optionsContainer.className = 'saarthi-options-list';
                    optionsContainer.setAttribute('data-testid', `options-container-${activeField}`);
                    optionsContainer.style.cssText = 'display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem; padding: 0.5rem; background: #fff8f0; border: 1.5px solid #ee7c2b; border-radius: 0.5rem; box-shadow: 0 4px 12px rgba(238,124,43,0.15); transition: all 0.2s ease;';

                    Array.from(selectEl.options).forEach((opt) => {
                      if (!opt.value && opt.disabled) return;
                      const pillBtn = document.createElement('button');
                      pillBtn.type = 'button';
                      pillBtn.className = 'saarthi-option-pill';
                      pillBtn.setAttribute('data-testid', `option-pill-${opt.value}`);
                      pillBtn.innerText = opt.text || opt.value;
                      const isSelected = selectEl.value === opt.value;
                      pillBtn.style.cssText = `padding: 0.45rem 0.85rem; border-radius: 0.4rem; font-size: 0.82rem; font-weight: 700; cursor: pointer; border: 1px solid ${isSelected ? '#ee7c2b' : '#e0d5c5'}; background: ${isSelected ? '#ee7c2b' : '#ffffff'}; color: ${isSelected ? '#ffffff' : '#4a3b32'}; box-shadow: ${isSelected ? '0 2px 6px rgba(238,124,43,0.3)' : '0 1px 3px rgba(0,0,0,0.05)'}; transition: all 150ms ease;`;

                      pillBtn.onclick = () => {
                        const nativeSelectSetter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value')?.set;
                        if (nativeSelectSetter) {
                          nativeSelectSetter.call(selectEl, opt.value);
                        } else {
                          selectEl.value = opt.value;
                        }
                        selectEl.dispatchEvent(new Event('change', { bubbles: true }));
                        selectEl.dispatchEvent(new Event('input', { bubbles: true }));
                        console.log('[DROPDOWN-TAP] Selected option:', opt.value, 'for activeField:', activeField);
                        optionsContainer.querySelectorAll('.saarthi-option-pill').forEach((btn) => {
                          const b = btn as HTMLElement;
                          b.style.background = '#ffffff';
                          b.style.color = '#4a3b32';
                          b.style.borderColor = '#e0d5c5';
                        });
                        pillBtn.style.background = '#ee7c2b';
                        pillBtn.style.color = '#ffffff';
                        pillBtn.style.borderColor = '#ee7c2b';
                      };

                      optionsContainer.appendChild(pillBtn);
                    });

                    parentContainer.appendChild(optionsContainer);
                    console.log('[PROOF-FEATURE-B] Dropdown options rendered visibly in DOM for activeField:', activeField, '| Total option pills rendered:', optionsContainer.children.length);
                  }
                }
              }
            } else if (action === 'SUBMIT_FORM' || contentStr.toLowerCase().includes('confirm kar lete hain')) {
              document.querySelectorAll('.saarthi-highlight').forEach((el) => {
                el.classList.remove('saarthi-highlight');
              });
              document.querySelectorAll('.saarthi-options-list').forEach((el) => {
                el.remove();
              });
            }

            // ── REFRESH_PAGE ACTION HANDLER ──
            if (action === 'REFRESH_PAGE') {
              console.log('[PROOF-FEATURE-C] Executing REFRESH_PAGE action directive -> window.location.reload() called!');
              setTimeout(() => {
                window.location.reload();
              }, 1000);
            }

            // ── GREETING GUARD: Initial connect greeting MUST NEVER navigate automatically ──
            if (intent === 'GREETING' || msg.payload.intent === 'GREETING') {
              console.log('[Voice] [CONNECT-DIAGNOSTIC] Initial Greeting response received. Forcing action & target to null. User remains on current page.');
              action = null;
              target = null;
            }

            // ── COMPLETION VISUAL MOMENT: Trigger 'namaste' avatar bow on onboarding handoff ──
            if (contentStr.toLowerCase().includes('password') && contentStr.toLowerCase().includes('documents')) {
              console.log('[Voice] [VISUAL-MOMENT] Onboarding completion handoff detected. Triggering Namaste bow animation on avatar!');
              setSaarthiState('namaste' as any);
              setTimeout(() => {
                setSaarthiState('speaking');
              }, 1500);
            }

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
                if (path === '/') return '[data-testid="link-home-logo"], [data-testid="link-nav-home"]';
                if (path.includes('puja')) return '[data-testid="button-nav-services"], [data-testid="link-nav-service-book-puja"]';
                if (path.includes('kundali')) return '[data-testid="button-nav-spiritual-tools"], [data-testid="link-nav-tool-kundali"]';
                if (path.includes('muhurat')) return '[data-testid="button-nav-spiritual-tools"], [data-testid="link-nav-tool-muhurat-finder"]';
                if (path.includes('login')) return '[data-testid="button-login"]';
                if (path.includes('signup') || path.includes('sign-up')) return '[data-testid="button-signup"]';
                if (path.includes('dash')) return 'a[href="/dashboard"]';
                return `a[href="${path}"]`;
              };

              const getTargetSectionForPath = (path: string) => {
                if (path.includes('role=pandit')) return '#pandit-onboarding-form, [data-testid="form-signup"], [data-testid="card-signup"]';
                if (path.includes('signup') || path.includes('sign-up')) return '#signup-form, [data-testid="form-signup"], [data-testid="card-signup"]';
                if (path.includes('login')) return '#login-form, [data-testid="form-login"], [data-testid="card-login"]';
                if (path.includes('kundali')) return '#kundali-form-section, [data-testid="section-kundali-form"]';
                if (path.includes('muhurat')) return '#muhurat-finder-section, [data-testid="section-muhurat-finder"]';
                if (path.includes('puja')) return '#puja-catalog-section, [data-testid="section-puja-catalog"]';
                if (path === '/') return '#hero-section, [data-testid="section-hero"]';
                return 'main, section, body';
              };

              const seq = [];
              const finalTarget = getTargetSelectorForPath(cleanTarget);
              const sectionTarget = getTargetSectionForPath(cleanTarget);

              if (query && cleanTarget.includes('puja')) {
                // QUERY SEARCH FLOW (Specific puja catalog search)
                console.log('[NAV-DEBUG] Preparing query search flow:', query);
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
                // UNIVERSAL WHITE-BOX CURSOR NAVIGATION FOR ALL PAGES
                console.log(`[NAV-DEBUG] Executing Universal Nav Journey -> Target Nav: ${finalTarget}, Section: ${sectionTarget}`);
                seq.push({ action: 'move', target: finalTarget, delay: 600 });
                seq.push({ action: 'click', target: finalTarget, delay: 300 });
                seq.push({ action: 'navigate', path: cleanTarget, delay: 400 });
                seq.push({ action: 'wait_for_selector', target: sectionTarget, delay: 300 });
                seq.push({ action: 'scroll', target: sectionTarget, delay: 400 });
                seq.push({ action: 'move', target: sectionTarget, delay: 600 });
                
                // Fix for Pandit role switching
                const isPanditSignupJourney = cleanTarget.includes('role=pandit') || (cleanTarget.includes('signup') && (msg.payload.content || '').toLowerCase().includes('pandit'));
                if (isPanditSignupJourney) {
                  seq.push({ action: 'wait_for_selector', target: '[data-testid="tab-usertype-pandit"]', delay: 300 });
                  seq.push({ action: 'click', target: '[data-testid="tab-usertype-pandit"]', delay: 200 });
                  console.log('[NAV-DEBUG] Clicked Pandit tab explicitly after navigating');
                }
              }

              runSequence(seq);
              // Fallback handled by generic page level flow
            } else if (action === 'START_TOUR') {
              console.log('[SITE-TOUR] Preparing site tour sequence for target:', target);
              const seq: any[] = [];
              if (target === 'pandit_tour') {
                // PANDIT TOUR: 3 Stops
                // Stop 1: Home page CTA
                seq.push({ action: 'navigate', path: '/', delay: 400 });
                seq.push({ action: 'move', target: '[data-testid="button-become-pandit-cta"], a[href="/sign-up?role=pandit"]', delay: 800 });
                seq.push({ action: 'scroll', target: '[data-testid="button-become-pandit-cta"], a[href="/sign-up?role=pandit"]', delay: 2000 });
                // Stop 2: Pandit Registration Form & Tab
                seq.push({ action: 'navigate', path: '/signup?role=pandit', delay: 400 });
                seq.push({ action: 'wait_for_selector', target: '[data-testid="tab-usertype-pandit"]', delay: 300 });
                seq.push({ action: 'click', target: '[data-testid="tab-usertype-pandit"]', delay: 400 });
                seq.push({ action: 'move', target: '[data-testid="input-pandit-name"]', delay: 2500 });
                // Stop 3: Document Upload Section
                seq.push({ action: 'scroll', target: '[data-testid="button-signup-submit"]', delay: 400 });
                seq.push({ action: 'move', target: '[data-testid="button-signup-submit"]', delay: 2000 });
              } else {
                // DEVOTEE TOUR: 4 Stops
                // Stop 1: Home Hero
                seq.push({ action: 'navigate', path: '/', delay: 400 });
                seq.push({ action: 'move', target: '#hero-section, [data-testid="section-hero"]', delay: 800 });
                seq.push({ action: 'scroll', target: '#hero-section, [data-testid="section-hero"]', delay: 2000 });
                // Stop 2: Puja Booking Catalog
                seq.push({ action: 'navigate', path: '/puja', delay: 400 });
                seq.push({ action: 'wait_for_selector', target: '#puja-catalog-section, [data-testid="section-puja-catalog"]', delay: 300 });
                seq.push({ action: 'scroll', target: '#puja-catalog-section, [data-testid="section-puja-catalog"]', delay: 400 });
                seq.push({ action: 'move', target: '[data-testid="input-search-puja"]', delay: 2500 });
                // Stop 3: Kundali Creation
                seq.push({ action: 'navigate', path: '/kundali-creation', delay: 400 });
                seq.push({ action: 'wait_for_selector', target: '#kundali-form-section, [data-testid="section-kundali-form"]', delay: 300 });
                seq.push({ action: 'scroll', target: '#kundali-form-section, [data-testid="section-kundali-form"]', delay: 400 });
                seq.push({ action: 'move', target: '#kundali-form-section, [data-testid="section-kundali-form"]', delay: 2500 });
                // Stop 4: Muhurat Finder
                seq.push({ action: 'navigate', path: '/muhurat-finder', delay: 400 });
                seq.push({ action: 'wait_for_selector', target: '#muhurat-finder-section, [data-testid="section-muhurat-finder"]', delay: 300 });
                seq.push({ action: 'scroll', target: '#muhurat-finder-section, [data-testid="section-muhurat-finder"]', delay: 400 });
                seq.push({ action: 'move', target: '#muhurat-finder-section, [data-testid="section-muhurat-finder"]', delay: 2000 });
              }
              runSequence(seq);
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
                if (fTarget === 'pandit-first-name') selector = '[data-testid="input-pandit-first-name"], #pandit-first-name';
                else if (fTarget === 'pandit-last-name') selector = '[data-testid="input-pandit-last-name"], #pandit-last-name';
                else if (fTarget.includes('name')) selector = isPanditField ? '[data-testid="input-pandit-first-name"]' : 'input[name="name"], [data-testid="input-name"], #devotee-name';
                else if (fTarget.includes('phone') || fTarget.includes('mobile')) selector = isPanditField ? '[data-testid="input-pandit-phone"]' : 'input[name="phone"], input[type="tel"], [data-testid="input-phone"], #devotee-phone';
                else if (fTarget.includes('city') || fTarget.includes('location')) selector = isPanditField ? '[data-testid="input-pandit-city"]' : 'input[name="city"], [data-testid="input-city"], select#booking-city, #booking-city';
                else if (fTarget.includes('state')) selector = isPanditField ? '[data-testid="input-pandit-state"]' : 'input[name="state"], [data-testid="input-state"]';
                else if (fTarget.includes('email')) selector = isPanditField ? '[data-testid="input-pandit-email"]' : 'input[name="email"], input[type="email"], [data-testid="input-email"]';
                else if (fTarget.includes('lang')) selector = '[data-testid^="toggle-lang-"]';
                else if (fTarget.includes('exp')) selector = '[data-testid="select-pandit-exp"]';
                else if (fTarget.includes('spec')) selector = '[data-testid="select-pandit-spec"]';
                else if (fTarget.includes('date')) selector = 'input[name="date"], input[type="date"], [data-testid="input-date"], #booking-date';
                else if (fTarget.includes('time')) selector = 'input[name="time"], input[type="time"], [data-testid="input-time"], select#booking-time, #booking-time';
                else selector = `input[name="${fTarget}"], #${fTarget}`;
                
                console.log(`[FORM-FILL] Processing field ${fTarget} -> selector: ${selector}`);

                if (isPanditField && !hasNavigatedToPandit) {
                  hasNavigatedToPandit = true;
                  if (window.location.pathname !== '/signup') {
                     seq.push({ action: 'navigate', path: '/signup?role=pandit', delay: 400 });
                     seq.push({ action: 'wait_for_selector', target: selector, delay: 200 });
                  } else {
                     const isPanditTabActive = !!document.querySelector('[data-testid="tab-usertype-pandit"][aria-pressed="true"]');
                     if (!isPanditTabActive) {
                        seq.push({ action: 'click', target: '[data-testid="tab-usertype-pandit"]', delay: 200 });
                        seq.push({ action: 'wait_for_selector', target: selector, delay: 200 });
                     }
                  }
                }

                if (isPanditField) {
                  const step2Fields = ['exp', 'gurukul', 'education', 'spec', 'lang', 'achievements', 'bio'];
                  const step3Fields = ['certfile', 'aadhaarfile', 'galleryfiles', 'password', 'confirm', 'codeofconduct'];
                  
                  let targetStep = 1;
                  const fTargetLower = fTarget.toLowerCase();
                  if (step2Fields.some(f => fTargetLower.includes(f))) targetStep = 2;
                  if (step3Fields.some(f => fTargetLower.includes(f))) targetStep = 3;
                  
                  // Auto-advance wizard steps if needed
                  if (targetStep >= 2) {
                      seq.push({ action: 'click', target: '[data-testid="button-pandit-next-1"]', delay: 200 });
                  }
                  if (targetStep === 3) {
                      seq.push({ action: 'click', target: '[data-testid="button-pandit-next-2"]', delay: 200 });
                  }
                  
                  // Add a small delay to allow DOM to render new step
                  if (targetStep > 1) {
                      seq.push({ action: 'wait_for_selector', target: selector, delay: 300 });
                  }

                  const isSelectDropdown = fTarget.includes('exp') || fTarget.includes('spec');
                  const isLangToggle = fTarget.includes('lang');
                  if (isSelectDropdown) {
                    seq.push({ action: 'move', target: selector, delay: 400 });
                    seq.push({ action: 'open_dropdown', target: selector, delay: 500 });
                    seq.push({ action: 'select_option', target: selector, text: fQuery, delay: 800 });
                  } else if (isLangToggle) {
                    const targetLangs = (fQuery || "Hindi, Sanskrit").split(',').map((l: string) => l.trim().toLowerCase());
                    const allPossibleLangs = ['hindi', 'sanskrit', 'english', 'gujarati', 'marathi', 'bengali', 'tamil', 'telugu'];
                    
                    for (const lang of allPossibleLangs) {
                      const btnSelector = `[data-testid="toggle-lang-${lang}"]`;
                      const shouldBeActive = targetLangs.includes(lang);
                      
                      const btnEl = document.querySelector(btnSelector);
                      const isActive = btnEl ? (btnEl.textContent || '').includes('✓') : (lang === 'hindi' || lang === 'sanskrit');
                      
                      if ((shouldBeActive && !isActive) || (!shouldBeActive && isActive)) {
                        seq.push({ action: 'move', target: btnSelector, delay: 300 });
                        seq.push({ action: 'click', target: btnSelector, delay: 200 });
                      }
                    }
                  } else {
                    seq.push({ action: 'move', target: selector, delay: 400 });
                    seq.push({ action: 'type', target: selector, text: fQuery, delay: 800 });
                  }
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
            } else if (action === 'SUBMIT_FORM') {
              console.log('[FORM-SUBMIT] SUBMIT_FORM action received. Target button:', target);

              const isPanditForm = !!document.querySelector('#pandit-onboarding-form, [data-testid="card-signup"]');
              if (isPanditForm) {
                const stepEl = document.querySelector('[data-testid="pandit-wizard-step"]');
                const currentStep = stepEl ? (stepEl.getAttribute('data-step') || '1') : '1';
                console.log(`[FORM-SUBMIT] Current wizard step: ${currentStep}`);

                if (currentStep === '1') {
                  const next1Btn = '[data-testid="button-pandit-next-1"]';
                  const seq: any[] = [
                    { action: 'wait_for_selector', target: next1Btn, delay: 300 },
                    { action: 'scroll', target: next1Btn, delay: 400 },
                    { action: 'move', target: next1Btn, delay: 800 },
                    { action: 'click', target: next1Btn, delay: 200 },
                  ];
                  sequenceQueueRef.current = seq;
                  if (!isExecutingSequenceRef.current) {
                    processNextStepRef.current();
                  }
                  return;
                } else if (currentStep === '2') {
                  const next2Btn = '[data-testid="button-pandit-next-2"]';
                  const seq: any[] = [
                    { action: 'wait_for_selector', target: next2Btn, delay: 300 },
                    { action: 'scroll', target: next2Btn, delay: 400 },
                    { action: 'move', target: next2Btn, delay: 800 },
                    { action: 'click', target: next2Btn, delay: 200 },
                  ];
                  sequenceQueueRef.current = seq;
                  if (!isExecutingSequenceRef.current) {
                    processNextStepRef.current();
                  }
                  return;
                } else if (currentStep === '3') {
                  // Perform 5 Step 3 Checks
                  const pwdEl = document.querySelector<HTMLInputElement>('#pandit-password, [data-testid="input-pandit-password"]');
                  const cpwdEl = document.querySelector<HTMLInputElement>('#pandit-confirm, [data-testid="input-pandit-confirm"]');
                  const aadhaarInput = document.querySelector<HTMLInputElement>('#pandit-aadhaar-input, [data-testid="input-aadhaar-file"]');
                  const certInput = document.querySelector<HTMLInputElement>('#pandit-cert-input, [data-testid="input-cert-file"]');
                  const termsEl = document.querySelector<HTMLInputElement>('#pandit-terms-accepted, [data-testid="checkbox-pandit-terms"]');

                  const pwdVal = pwdEl?.value?.trim() || '';
                  const cpwdVal = cpwdEl?.value?.trim() || '';
                  const hasPwd = pwdVal.length >= 8;
                  const pwdMatches = pwdVal === cpwdVal;
                  const hasAadhaar = aadhaarInput && aadhaarInput.files && aadhaarInput.files.length > 0;
                  const hasCert = certInput && certInput.files && certInput.files.length > 0;
                  const hasTerms = termsEl && termsEl.checked;

                  if (!hasPwd) {
                    announceMessage("Panditji, aapne abhi tak Password set nahi kiya hai. Kripya screen par Password set karke dobara 'maine kar diya' boliye.", false);
                    return;
                  } else if (!pwdMatches) {
                    announceMessage("Panditji, aapka password aur confirm password match nahi kar rahe. Kripya dono ek jaisa dobara set kijiye.", false);
                    return;
                  } else if (!hasAadhaar && !hasCert) {
                    announceMessage("Panditji, aapne Aadhaar Identity Proof aur Vedic Certificate dono documents upload nahi kiye hain. Kripya dono upload karke dobara 'maine kar diya' boliye.", false);
                    return;
                  } else if (!hasAadhaar) {
                    announceMessage("Panditji, aapka Aadhaar Identity Proof upload karna baki hai. Kripya Aadhaar upload karke dobara 'maine kar diya' boliye.", false);
                    return;
                  } else if (!hasCert) {
                    announceMessage("Panditji, aapka Vedic Certificate document upload karna baki hai. Kripya Certificate upload karke dobara 'maine kar diya' boliye.", false);
                    return;
                  } else if (!hasTerms) {
                    announceMessage("Panditji, aapne Terms & Conditions aur Code of Conduct accept nahi kiya hai. Kripya checkbox tick karke dobara 'maine kar diya' boliye.", false);
                    return;
                  }

                  const submitSelector = '[data-testid="button-submit-pandit-signup"], [data-testid="button-submit-signup"], form button[type="submit"], button[type="submit"]';
                  const seq: any[] = [
                    { action: 'wait_for_selector', target: submitSelector, delay: 300 },
                    { action: 'scroll', target: submitSelector, delay: 400 },
                    { action: 'move', target: submitSelector, delay: 800 },
                    { action: 'click', target: submitSelector, delay: 200 },
                  ];
                  sequenceQueueRef.current = seq;
                  if (!isExecutingSequenceRef.current) {
                    processNextStepRef.current();
                  }
                }
              } else {
                const submitSelector = '[data-testid="button-submit-pandit-signup"], [data-testid="button-submit-signup"], form button[type="submit"], button[type="submit"]';
                const seq: any[] = [
                  { action: 'wait_for_selector', target: submitSelector, delay: 300 },
                  { action: 'scroll', target: submitSelector, delay: 400 },
                  { action: 'move', target: submitSelector, delay: 800 },
                  { action: 'click', target: submitSelector, delay: 200 },
                ];
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
        currentAudioSourceRef.current = source;
        
        source.onended = () => {
          console.log('[Voice] Audio chunk playback ended');
          currentAudioSourceRef.current = null;
          isPlayingRef.current = false;
          playNextAudio();
        };
        
        try {
            console.log(`[Voice] Calling source.start(). AudioContext state is: ${audioContextRef.current.state}`);
            source.start(0);
        } catch (err: any) {
            console.error('[Voice] source.start(0) threw an error! FULL error object:', err);
            currentAudioSourceRef.current = null;
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

    if ((state === 'listening' || state === 'speaking') && isConnected) {
      console.log('[Voice] Requesting microphone permission with Echo Cancellation & Noise Suppression...');
      navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } })
        .then(stream => {
          console.log('[Voice] Microphone permission granted (Active across listening & speaking states)');
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
            if (wsRef.current?.readyState === WebSocket.OPEN) {
              const inputData = event.inputBuffer.getChannelData(0);
              const pcm16 = float32ToPCM16(inputData);
              const base64data = uint8ArrayToBase64(pcm16);

              recordedBytesSent += pcm16.byteLength;
              if (chunkCounter % 10 === 0) {
                 console.log(`[VAD-DIAGNOSTIC] Streaming AUDIO_FRAME (chunk ${chunkCounter}). Total sent: ${recordedBytesSent} bytes.`);
              }
              wsRef.current.send(JSON.stringify({
                type: 'AUDIO_FRAME',
                payload: { data: base64data },
              }));
            }
          };
          
          sourceNode.connect(processor);
          processor.connect(audioCtx.destination);
          
          (mediaRecorderRef as any).current = {
            state: 'recording',
            stop: () => {
              processor.disconnect();
              sourceNode.disconnect();
            },
            stream: stream
          };
          console.log('[Voice] Started ScriptProcessorNode (Audio streaming active)');

          // VAD Setup
          vadAudioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
          const source = vadAudioCtx.createMediaStreamSource(stream);
          const analyser = vadAudioCtx.createAnalyser();
          analyser.fftSize = 512;
          analyser.minDecibels = -70; // High sensitivity VAD
          analyser.smoothingTimeConstant = 0.1;
          source.connect(analyser);

          const dataArray = new Uint8Array(analyser.frequencyBinCount);
          silenceStart = Date.now();
          let speechStreakDuringSpeaking = 0;

          vadInterval = window.setInterval(() => {
            analyser.getByteFrequencyData(dataArray);
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) {
              sum += dataArray[i];
            }
            const average = sum / dataArray.length;
            
            // Console log VAD metrics every 500ms
            if (Date.now() % 500 < 100) {
              console.log(`[VAD-DIAGNOSTIC] VAD Tick | State: ${stateRef.current} | Vol Avg: ${average.toFixed(2)} | isSpeaking: ${isSpeaking}`);
            }

            if (Date.now() < vadWarmupTime) {
               silenceStart = Date.now();
               return;
            }

            // -------------------------------------------------------------------------
            // BARGE-IN DISABLED FOR DEMO STABILITY: Mic only listens after Saarthi finishes speaking
            // -------------------------------------------------------------------------
            if (stateRef.current === 'speaking') {
              silenceStart = Date.now();
              return;
            }

            // -------------------------------------------------------------------------
            // NORMAL LISTENING VAD LOGIC (during 'listening' state)
            // -------------------------------------------------------------------------
            if (average > 6.0) { // Speech start threshold (6.0 for responsive detection)
              if (!isSpeaking) {
                console.log(`[VAD-DIAGNOSTIC] 🎯 Speech CONFIRMED started! (Vol: ${average.toFixed(2)} > 6.0)`);
                isSpeaking = true;
              }
              silenceStart = Date.now();
            } else {
              if (isSpeaking && (Date.now() - silenceStart > 1200)) { // 1.2 seconds of silence after speech
                console.log(`[VAD-DIAGNOSTIC] 🤫 Silence detected after 1.2s. Triggering state transition to idle. Last Vol: ${average.toFixed(2)}`);
                isSpeaking = false;
                setSaarthiState('idle');
                
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
        console.log(`[VAD-DIAGNOSTIC] Stopping MediaRecorder (cleanup). Total recorded bytes sent: ${recordedBytesSent}`);
        
        mediaRecorderRef.current.state = 'inactive';
        mediaRecorderRef.current.stop();
        mediaRecorderRef.current.stream.getTracks().forEach((track: MediaStreamTrack) => track.stop());
        
        if (recordedBytesSent > 0) {
            console.log(`[VAD-DIAGNOSTIC] ✅ Sending AUDIO_END frame with total byte size: ${recordedBytesSent} bytes. current_page: ${window.location.pathname}`);
            wsRef.current?.send(JSON.stringify({
              type: 'AUDIO_END',
              payload: {
                current_page: window.location.pathname
              }
            }));
        } else {
            console.log('[VAD-DIAGNOSTIC] Skipping AUDIO_END frame because 0 bytes were recorded.');
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
