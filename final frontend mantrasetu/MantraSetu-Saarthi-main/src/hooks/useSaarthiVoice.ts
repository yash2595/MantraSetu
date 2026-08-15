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

    const avatarInput = document.querySelector<HTMLInputElement>('#pandit-avatar, [data-testid="input-pandit-avatar"]');
    const avatarPreviewImg = document.querySelector<HTMLImageElement>('[alt="Preview"]');
    const hasAvatarFile = (avatarInput && avatarInput.files && avatarInput.files.length > 0) ||
                          (avatarPreviewImg && avatarPreviewImg.getAttribute('src')?.startsWith('data:image'));
    data['avatar_attached'] = hasAvatarFile ? 'true' : 'false';

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
  const { state, setDialogueText, setSaarthiState, minimizeSaarthi, forceMinimize, announceMessage } = useSaarthi();
  const [isConnected, setIsConnected] = useState(false);
  const [isSessionReady, setIsSessionReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const wsRef = useRef<WebSocket | null>(null);
  const isSessionReadyRef = useRef(false);
  const isConnectingRef = useRef(false);
  const reconnectTimerRef = useRef<any>(null);
  const connectionTimeoutRef = useRef<any>(null);
  const reconnectAttemptsRef = useRef(0);
  const MAX_RECONNECT_ATTEMPTS = 10;

  const updateSessionReady = useCallback((ready: boolean) => {
    console.log(`[Voice] Session ready state updated: ${ready}`);
    isSessionReadyRef.current = ready;
    setIsSessionReady(ready);
    if (ready) {
      userRecordedBytesRef.current = 0;
      userHasSpokenRef.current = false;
    }
  }, []);

  const sendWsMessage = useCallback((payload: any): boolean => {
    const currentWs = wsRef.current;
    if (currentWs && currentWs.readyState === WebSocket.OPEN) {
      currentWs.send(JSON.stringify(payload));
      return true;
    }
    console.warn(
      `[Voice] Cannot send WebSocket message (type: ${payload?.type}). ` +
      `Socket state is ${currentWs ? currentWs.readyState : 'NULL'} (expected WebSocket.OPEN=${WebSocket.OPEN}).`
    );
    return false;
  }, []);

  useEffect(() => {
    (window as any).simulateUserSpeech = (text: string) => {
      console.log(`[DEBUG-SIMULATION] Simulating user speech: "${text}"`);
      sendWsMessage({
        type: 'TEXT',
        payload: {
          text: text,
          language: 'hi'
        }
      });
    };
    return () => {
      delete (window as any).simulateUserSpeech;
    };
  }, [sendWsMessage]);

  const playNextAudioRef = useRef<(() => void) | undefined>(undefined);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const currentAudioSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const audioQueueRef = useRef<AudioBuffer[]>([]);
  const isPlayingRef = useRef(false);
  const isFinalChunkReceived = useRef(false);
  const streamIntervalRef = useRef<number | any | null>(null);
  const fallbackTimeoutRef = useRef<number | any | null>(null);
  const sequenceQueueRef = useRef<any[]>([]);
  const isExecutingSequenceRef = useRef(false);
  const lastTargetRef = useRef<string | null>(null);
  const activeFieldRef = useRef<string | null>(null);

  // Sync activeFieldRef on page change: reset to null on non-signup pages
  useEffect(() => {
    const isSignupPage = window.location.pathname.includes('/signup');
    if (!isSignupPage) {
      activeFieldRef.current = null;
    }
  }, [navigate]);

  const stateRef = useRef(state);
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  const stopAudioPlayback = useCallback(() => {
    console.log('[BARGE-IN] Executing stopAudioPlayback(). Halting active audio source & flushing audio queue.');
    if (streamIntervalRef.current) {
      clearInterval(streamIntervalRef.current as any);
      streamIntervalRef.current = null;
    }
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

         // For select elements: set value instantly (no char-by-char)
         if (targetEl.tagName.toLowerCase() === 'select') {
           if (nativeInputValueSetter) {
             nativeInputValueSetter.call(targetEl, step.text);
           } else {
             (targetEl as HTMLSelectElement).value = step.text;
           }
           targetEl.dispatchEvent(new Event('input', { bubbles: true }));
           targetEl.dispatchEvent(new Event('change', { bubbles: true }));
           setTimeout(() => {
             targetEl.classList.remove('saarthi-highlight');
             targetEl.classList.add('saarthi-filled');
             processNextStep();
           }, 400);
           return;
         }

         // ── CHARACTER-BY-CHARACTER TYPING ANIMATION ──
         // Clear field first, then type character by character with React-compatible events
         const fullText = step.text as string;
         const charDelay = Math.min(60, Math.max(30, 1200 / fullText.length)); // 30-60ms per char, total ~1-2s
         let charIndex = 0;

         // Focus the field so cursor blink is visible
         (targetEl as HTMLInputElement).focus();

         const typeNextChar = () => {
            if (charIndex > fullText.length) {
              // Typing complete: swap highlight → filled glow and advance sequence
              targetEl.classList.remove('saarthi-highlight');
              targetEl.classList.add('saarthi-filled');
              const tracker = (targetEl as any)._valueTracker;
              if (tracker) tracker.setValue('');
              targetEl.dispatchEvent(new Event('input', { bubbles: true }));
              targetEl.dispatchEvent(new Event('change', { bubbles: true }));
              console.log(`[FORM-FILL-PROOF] Final Char-by-char typing complete for target="${step.target}" | Final DOM Value="${(targetEl as HTMLInputElement).value}"`);
              setTimeout(processNextStep, step.delay || 400);
              return;
            }

            const currentVal = fullText.slice(0, charIndex);

            const tracker = (targetEl as any)._valueTracker;
            if (tracker) tracker.setValue('');

            if (nativeInputValueSetter) {
              nativeInputValueSetter.call(targetEl, currentVal);
            } else {
              (targetEl as HTMLInputElement).value = currentVal;
            }

            // Fire input & change events so React's onChange / controlled input updates
            targetEl.dispatchEvent(new Event('input', { bubbles: true }));
            targetEl.dispatchEvent(new Event('change', { bubbles: true }));

            console.log(`[FORM-FILL-PROOF] Typing target="${step.target}" | Char ${charIndex}/${fullText.length} | Val="${currentVal}" | DOM Val="${(targetEl as HTMLInputElement).value}"`);

            charIndex++;
            setTimeout(typeNextChar, charDelay);
          };

          typeNextChar();
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

  const runSequence = useCallback((seq: any[]) => {
    if (seq && seq.length > 0) {
      console.log('[NAV-SEQUENCE] Queuing navigation action sequence with', seq.length, 'steps:', seq);
      sequenceQueueRef.current = seq;
      if (!isExecutingSequenceRef.current) {
        processNextStepRef.current();
      }
    }
  }, []);

  const connectWebSocket = useCallback(() => {
    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const wsUrl = apiBase.replace('http', 'ws') + '/ws/voice';

    // Prevent duplicate in-flight reconnection attempts
    if (isConnectingRef.current) {
      console.log('[Voice] Reconnect/Connect already in progress. Debouncing duplicate attempt.');
      return;
    }

    if (wsRef.current && (wsRef.current.readyState === WebSocket.CONNECTING || wsRef.current.readyState === WebSocket.OPEN)) {
      console.log('[Voice] WebSocket is already CONNECTING or OPEN. Skipping connect.');
      return;
    }

    isConnectingRef.current = true;
    
    if (connectionTimeoutRef.current) {
      clearTimeout(connectionTimeoutRef.current);
    }
    connectionTimeoutRef.current = setTimeout(() => {
      if (isConnectingRef.current && wsRef.current && wsRef.current.readyState === WebSocket.CONNECTING) {
        console.warn('[Voice] Connection attempt timed out. Resetting connection state and forcing retry.');
        isConnectingRef.current = false;
        wsRef.current.onclose = null;
        wsRef.current.onerror = null;
        wsRef.current.close();
        wsRef.current = null;
        
        // Trigger a fresh reconnect attempt
        const delay = 1000;
        console.log(`[Voice] Scheduling WebSocket auto-reconnect after timeout in ${delay} ms`);
        if (reconnectTimerRef.current) {
          clearTimeout(reconnectTimerRef.current);
        }
        reconnectTimerRef.current = setTimeout(() => {
          connectWebSocket();
        }, delay);
      }
    }, 5000);

    console.log('[Voice] Opening WebSocket connection to:', wsUrl);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[Voice] WebSocket Connected successfully.');
      isConnectingRef.current = false;
      if (connectionTimeoutRef.current) {
        clearTimeout(connectionTimeoutRef.current);
        connectionTimeoutRef.current = null;
      }
      reconnectAttemptsRef.current = 0;
      setIsConnected(true);
      updateSessionReady(false);

      let persistentSessionId = sessionStorage.getItem('saarthi_session_id');
      if (!persistentSessionId) {
        persistentSessionId = 'vsession_f' + Math.random().toString(36).substring(2, 14);
        sessionStorage.setItem('saarthi_session_id', persistentSessionId);
      }
      console.log('[Voice] Sending CONNECT with session_id:', persistentSessionId, 'current_page:', window.location.pathname);

      // Always read fresh wsRef.current at send time!
      const sent = sendWsMessage({
        type: 'CONNECT',
        payload: {
          language: 'hi',
          session_id: persistentSessionId,
          current_page: window.location.pathname,
        },
      });

      if (!sent) {
        console.warn('[Voice] CONNECT frame could not be sent on ws.onopen!');
      }
    };

    ws.onmessage = async (event: MessageEvent) => {
        try {
          const msg = JSON.parse(event.data);
          // [DIAGNOSTIC] Log every single message type and AI_RESPONSE payload explicitly
          if (msg.type === 'AI_RESPONSE') {
             console.log('[DIAGNOSTIC] FULL RAW AI_RESPONSE PAYLOAD:', JSON.stringify(msg.payload));
          }
          if (!msg.type) return;
          console.log(`[Voice] Received message type: ${msg.type}`);
          if (msg.type === 'ERROR') {
             console.error('[Voice] [ERROR-PAYLOAD] Received ERROR envelope from backend:', JSON.stringify(msg.payload || msg));
          }

          // ----------- TRANSCRIPT handling -----------------------------------
          if (msg.type === 'TRANSCRIPT') {
            const { text, is_final } = msg.payload as { text: string; is_final: boolean };
            console.log('[Voice] TRANSCRIPT', is_final ? 'final' : 'partial', text);
            // Bug 2 Fix: Do not render live user transcript in dialogue bubble
            // setDialogueText(text);
            
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
            console.log('[Voice] CONNECTED received from backend. Session handshake READY.');
            updateSessionReady(true);
            return;
          }

          // ----------- AI_RESPONSE handling -----------------------------------
          if (msg.type === 'AI_RESPONSE') {
            if (!isSessionReadyRef.current) {
              updateSessionReady(true);
            }
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
              activeFieldRef.current = activeField;
              // ── STEP MAPPING & UI STEP SYNCHRONIZATION ──
              const step1Fields = ['pandit-first-name', 'pandit-last-name', 'pandit-email', 'pandit-phone', 'pandit-gender', 'pandit-availability', 'pandit-city', 'pandit-state', 'pandit-service-areas', 'pandit-name'];
              const step2Fields = ['pandit-exp', 'pandit-gurukul', 'pandit-education', 'pandit-languages', 'pandit-spec', 'pandit-achievements', 'pandit-bio'];
              const step3Fields = ['pandit-certFile', 'pandit-aadhaarFile', 'pandit-galleryFiles', 'pandit-password', 'pandit-confirm'];

              let targetStep: 1 | 2 | 3 = 1;
              if (step2Fields.includes(activeField)) targetStep = 2;
              else if (step3Fields.includes(activeField)) targetStep = 3;

              console.log(`[NAV-SYNC-TRACE] Active field received: "${activeField}" -> Computed Step: ${targetStep}. Dispatching saarthi-set-step event.`);
              window.dispatchEvent(new CustomEvent('saarthi-set-step', { detail: { step: targetStep, activeField } }));


              document.querySelectorAll('.saarthi-highlight').forEach((el) => {
                el.classList.remove('saarthi-highlight');
              });
              document.querySelectorAll('.saarthi-options-list').forEach((el) => {
                el.remove();
              });

              let highlightSelector = '';
              const isPanditField = activeField.startsWith('pandit-') || !!document.querySelector('[data-testid="tab-usertype-pandit"][aria-pressed="true"]');

              
              if (activeField === 'pandit-avatar') {
                highlightSelector = '[data-testid="input-pandit-avatar"], #pandit-avatar';
              } else if (activeField === 'pandit-first-name') {
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
            if (activeField) {
              activeFieldRef.current = activeField;
              const step2Fields = ['exp', 'gurukul', 'education', 'spec', 'lang', 'achievements', 'bio'];
              const step3Fields = ['certfile', 'aadhaarfile', 'galleryfiles', 'password', 'confirm', 'codeofconduct'];
              
              let targetStep: 1 | 2 | 3 = 1;
              const fieldLower = activeField.toLowerCase();
              if (step2Fields.some(f => fieldLower.includes(f))) targetStep = 2;
              if (step3Fields.some(f => fieldLower.includes(f))) targetStep = 3;

              console.log(`[PANDIT-STEP-TRACE] Dispatching saarthi-set-step event for activeField: "${activeField}" -> step: ${targetStep}`);
              window.dispatchEvent(new CustomEvent('saarthi-set-step', { detail: { step: targetStep, activeField } }));

              // Visually highlight active field in DOM
              setTimeout(() => {
                document.querySelectorAll('.saarthi-highlight').forEach(el => el.classList.remove('saarthi-highlight'));
                const sel = `[data-testid="input-${activeField}"], #${activeField}, [data-testid="input-${activeField.replace('pandit-', '')}"]`;
                const el = document.querySelector<HTMLElement>(sel);
                if (el) {
                  el.classList.add('saarthi-highlight');
                  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                  el.focus();
                }
              }, 100);
            }

            console.log('[NAV-DEBUG] RAW AI_RESPONSE Received. action=', action, 'target=', JSON.stringify(target));

            if (action === 'NAVIGATE' && target) {
              const cleanTarget = target.trim();
              const intentName = msg.payload?.intent || '';
              console.log(`[NAV-DEBUG] Routing for target: ${cleanTarget}, query: ${query}, intent: ${intentName}, currentPath: ${window.location.pathname}`);
              
              // 1. Reset voice highlighting/focus state cleanly
              document.querySelectorAll('.saarthi-highlight').forEach((el) => {
                el.classList.remove('saarthi-highlight');
              });
              document.querySelectorAll('.saarthi-options-list').forEach((el) => {
                el.remove();
              });
              
              // Also ensure we hide the synthetic cursor immediately
              const cursor = document.getElementById('saarthi-cursor');
              if (cursor) cursor.style.opacity = '0';
              
              // 🚨 GENERIC AUTO-BOOKING SEQUENCE FOR ALL PUJAS
              // If navigating to /puja or /services AND (a specific query exists OR intent is BOOK_PUJA)
              if ((cleanTarget.startsWith('/puja') || cleanTarget.startsWith('/services')) && (query || intentName === 'BOOK_PUJA')) {
                 console.log(`[PUJA-AUTOBOOK] Auto-booking sequence triggered for query: ${query || 'general'}`);
                 const seq: any[] = [];
                 const qParam = query ? `?q=${encodeURIComponent(query)}` : '';
                 seq.push({ action: 'navigate', path: `/puja${qParam}`, delay: 400 });
                 seq.push({ action: 'wait_for_selector', target: '[data-testid^="card-puja-"], .service-card', delay: 400 });
                 seq.push({ action: 'scroll', target: '[data-testid^="card-puja-"], .service-card', delay: 400 });
                 seq.push({ action: 'move', target: '[data-testid^="button-book-now-"], .service-card button', delay: 800 });
                 seq.push({ action: 'click', target: '[data-testid^="button-book-now-"], .service-card button', delay: 400 });
                 runSequence(seq);
                 return;
              }

              // 2. Perform soft in-app routing using React Router's useNavigate
              navigate(cleanTarget);
              
              // Allow any cleanup or state resets to happen
              return;
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
                const fTarget = field.target || '';
                const fQuery = field.query || '';
                
                let isPanditField = fTarget.startsWith('pandit-') || 
                                    (activeField && activeField.startsWith('pandit-')) || 
                                    !!document.querySelector('[data-testid="tab-usertype-pandit"][aria-pressed="true"]');

                if (window.location.pathname.includes('signup') && document.querySelector('[data-testid="tab-usertype-pandit"][aria-pressed="true"]')) {
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
                else if (fTarget.includes('bio')) selector = '#pandit-bio, [data-testid="textarea-pandit-bio"]';
                else if (fTarget.includes('achieve')) selector = '#pandit-achievements, [data-testid^="input-pandit-achievements-"]';
                else if (fTarget.includes('date')) selector = 'input[name="date"], input[type="date"], [data-testid="input-date"], #booking-date';
                else if (fTarget.includes('time')) selector = 'input[name="time"], input[type="time"], [data-testid="input-time"], select#booking-time, #booking-time';
                else selector = `input[name="${fTarget}"], #${fTarget}`;
                
                console.log(`[FORM-FILL] Processing field ${fTarget} -> selector: ${selector}`);

                if (isPanditField && !hasNavigatedToPandit) {
                  hasNavigatedToPandit = true;
                  if (window.location.pathname !== '/signup') {
                     seq.push({ action: 'navigate', path: '/signup?role=pandit', delay: 200 });
                     seq.push({ action: 'wait_for_selector', target: selector, delay: 150 });
                  } else {
                     const isPanditTabActive = !!document.querySelector('[data-testid="tab-usertype-pandit"][aria-pressed="true"]');
                     if (!isPanditTabActive) {
                        seq.push({ action: 'click', target: '[data-testid="tab-usertype-pandit"]', delay: 150 });
                        seq.push({ action: 'wait_for_selector', target: selector, delay: 150 });
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
                      seq.push({ action: 'click', target: '[data-testid="button-pandit-next-1"]', delay: 150 });
                  }
                  if (targetStep >= 3) {
                      seq.push({ action: 'click', target: '[data-testid="button-pandit-next-2"]', delay: 150 });
                  }
                  
                  // Add a small delay to allow DOM to render new step
                  if (targetStep > 1) {
                      seq.push({ action: 'wait_for_selector', target: selector, delay: 150 });
                  }

                  const isSelectDropdown = fTarget.includes('exp') || fTarget.includes('spec');
                  const isLangToggle = fTarget.includes('lang');
                  const isButtonGroup = fTarget.includes('gender') || fTarget.includes('availability') || fTarget.includes('service') || fTarget.includes('mode');

                  if (isButtonGroup) {
                    const btnGroupSel = `[data-field="${fTarget}"] button, [data-testid="pill-group-${fTarget}"] button, [data-testid^="pill-${fTarget}"]`;
                    const queryLower = (fQuery || '').toLowerCase();
                    const buttons = Array.from(document.querySelectorAll<HTMLElement>(btnGroupSel));
                    const matchedBtn = buttons.find(b => (b.textContent || '').toLowerCase().includes(queryLower));
                    
                    if (matchedBtn) {
                      const btnIndex = buttons.indexOf(matchedBtn);
                      const targetBtnSel = `[data-field="${fTarget}"] button:nth-of-type(${btnIndex + 1}), [data-testid="pill-group-${fTarget}"] button:nth-of-type(${btnIndex + 1})`;
                      seq.push({ action: 'move', target: targetBtnSel, delay: 150 });
                      seq.push({ action: 'click', target: targetBtnSel, delay: 150 });
                    } else {
                      const fallbackSel = `[data-testid="pill-${fTarget}-${queryLower}"]`;
                      seq.push({ action: 'move', target: fallbackSel, delay: 150 });
                      seq.push({ action: 'click', target: fallbackSel, delay: 150 });
                    }
                  } else if (isSelectDropdown) {
                    seq.push({ action: 'move', target: selector, delay: 200 });
                    seq.push({ action: 'open_dropdown', target: selector, delay: 200 });
                    seq.push({ action: 'select_option', target: selector, text: fQuery, delay: 300 });
                  } else if (isLangToggle) {
                    const queryLower = (fQuery || '').toLowerCase();
                    const allPossibleLangs = ['hindi', 'sanskrit', 'english', 'gujarati', 'marathi', 'bengali', 'tamil', 'telugu'];
                    
                    for (const lang of allPossibleLangs) {
                      const btnSelector = `[data-testid="toggle-lang-${lang}"]`;
                      const isSpoken = queryLower.includes(lang) || (lang === 'english' && (queryLower.includes('angrezi') || queryLower.includes('english')));
                      
                      const btnEl = document.querySelector<HTMLElement>(btnSelector);
                      const isActive = btnEl ? (btnEl.textContent || '').includes('✓') : false;
                      
                      if (isSpoken && !isActive) {
                        seq.push({ action: 'move', target: btnSelector, delay: 150 });
                        seq.push({ action: 'click', target: btnSelector, delay: 150 });
                      }
                    }
                  } else {
                    seq.push({ action: 'move', target: selector, delay: 200 });
                    seq.push({ action: 'type', target: selector, text: fQuery, delay: 300 });
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
            
            // 🚨 REAL-TIME WORD-BY-WORD PROGRESSIVE STREAMING FOR ASSISTANT RESPONSE
            if (streamIntervalRef.current) clearInterval(streamIntervalRef.current as any);

            const fullText = contentStr;
            const words = fullText.split(' ');
            if (words.length > 1) {
               let wordIdx = 0;
               setDialogueText(words[0]);
               streamIntervalRef.current = setInterval(() => {
                  wordIdx++;
                  if (wordIdx < words.length) {
                     setDialogueText(words.slice(0, wordIdx + 1).join(' '));
                  } else {
                     if (streamIntervalRef.current) {
                        clearInterval(streamIntervalRef.current as any);
                        streamIntervalRef.current = null;
                     }
                  }
               }, 110);
            } else {
               setDialogueText(fullText);
            }

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
              audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
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
                // Slice buffer copy to prevent detaching original bytes.buffer
                const decoded = await audioContextRef.current.decodeAudioData(bytes.buffer.slice(0));
                console.log(`[Voice] Successfully decoded via decodeAudioData (duration: ${decoded.duration}s)`);
                audioQueueRef.current.push(decoded);
                playNextAudioRef.current?.();
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
                playNextAudioRef.current?.();
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

    ws.onclose = (event: CloseEvent) => {
      console.log(`[Voice] WebSocket Closed (code: ${event.code}, clean: ${event.wasClean})`);
      setIsConnected(false);
      updateSessionReady(false);

      const isClean = event.code === 1000 || event.code === 1001;
      if (!isClean && reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttemptsRef.current += 1;
        const delay = Math.min(30000, 1000 * Math.pow(2, reconnectAttemptsRef.current - 1));
        console.log(`[Voice] WebSocket auto-reconnect attempt ${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS} in ${delay} ms`);
        
        if (reconnectTimerRef.current) {
          clearTimeout(reconnectTimerRef.current);
        }
        reconnectTimerRef.current = setTimeout(() => {
          if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
            console.log(`[Voice] Executing auto-reconnect attempt ${reconnectAttemptsRef.current}...`);
            connectWebSocket();
          }
        }, delay);
      }
    };

    ws.onerror = (e) => {
      console.error('[Voice] WebSocket Error', e);
      isConnectingRef.current = false;
      if (connectionTimeoutRef.current) {
        clearTimeout(connectionTimeoutRef.current);
        connectionTimeoutRef.current = null;
      }
      setError('WebSocket error');
      updateSessionReady(false);
    };

    wsRef.current = ws;
  }, [updateSessionReady, sendWsMessage, setDialogueText, setSaarthiState, forceMinimize, announceMessage, stopAudioPlayback, runSequence, navigate]);

  const connectWebSocketRef = useRef(connectWebSocket);
  useEffect(() => {
    connectWebSocketRef.current = connectWebSocket;
  }, [connectWebSocket]);

  useEffect(() => {
    console.log('[Voice] Mounting: Initializing WebSocket connection...');
    connectWebSocketRef.current();

    return () => {
      console.log('[Voice] Unmounting: Cleaning up WebSocket...');
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (connectionTimeoutRef.current) {
        clearTimeout(connectionTimeoutRef.current);
      }
      if (wsRef.current) {
        console.log('[Voice] Silencing event handlers and closing socket during unmount.');
        wsRef.current.onclose = null;
        wsRef.current.onerror = null;
        wsRef.current.close();
        wsRef.current = null;
      }
      isConnectingRef.current = false;
    };
  }, []);

  const playNextAudio = useCallback(() => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0 || !audioContextRef.current) {
      if (audioQueueRef.current.length === 0 && !isPlayingRef.current) {
         console.log('[VERIFY-DIAGNOSTIC] (a) Audio playback complete (verification readout finished).');
         console.log('[VERIFY-DIAGNOSTIC] (b) Mic re-armed. Transitioning state: speaking -> listening.');
         isFinalChunkReceived.current = false;
         if (fallbackTimeoutRef.current) {
             clearTimeout(fallbackTimeoutRef.current);
             fallbackTimeoutRef.current = null;
         }
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
    playNextAudioRef.current = playNextAudio;
  }, [playNextAudio]);

  // ── PERSISTENT MICROPHONE & VAD EFFECT (Lifetime tied to WS Connection) ──
  const micStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const vadAudioCtxRef = useRef<AudioContext | null>(null);
  const vadIntervalRef = useRef<any>(null);
  const userRecordedBytesRef = useRef<number>(0);
  const userHasSpokenRef = useRef<boolean>(false);

  // Reset speech counters whenever entering 'listening' mode (User turn starts)
  useEffect(() => {
    if (state === 'listening') {
      console.log('[Voice] Entered LISTENING state. Resetting user speech byte counters.');
      userRecordedBytesRef.current = 0;
      userHasSpokenRef.current = false;
    }
  }, [state]);

  useEffect(() => {
    console.log('[Voice] mic useEffect triggered | isConnected:', isConnected, '| micStreamActive:', !!(micStreamRef.current && micStreamRef.current.active));
    if (!isConnected) return;

    if (micStreamRef.current && micStreamRef.current.active && processorRef.current) {
      console.log('[Voice] Persistent microphone stream is ALREADY active. Preserving active stream.');
      return;
    }

    console.log('[Voice] Initializing PERSISTENT microphone stream for WebSocket session...');
    let silenceStart = Date.now();
    let vadWarmupTime = Date.now() + 1000;

    navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } })
      .then(stream => {
        micStreamRef.current = stream;
        console.log('[Voice] Persistent Microphone permission granted & stream active');

        if (!audioContextRef.current) {
          audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
        }
        const audioCtx = audioContextRef.current;
        if (audioCtx.state === 'suspended') {
          audioCtx.resume().then(() => console.log('[Voice] AudioContext resumed for persistent mic input'));
        }

        // ── AUTOPLAY UNBLOCKER: Attach global user interaction listeners ──
        const resumeAllAudioContexts = () => {
          if (audioContextRef.current && audioContextRef.current.state === 'suspended') {
            audioContextRef.current.resume().then(() => {
              console.log('[Voice] Main audioContextRef resumed via user interaction! State:', audioContextRef.current?.state);
            }).catch(e => console.warn('[Voice] Main AudioContext resume error:', e));
          }
          if (vadAudioCtxRef.current && vadAudioCtxRef.current.state === 'suspended') {
            vadAudioCtxRef.current.resume().then(() => {
              console.log('[Voice] vadAudioCtxRef resumed via user interaction! State:', vadAudioCtxRef.current?.state);
            }).catch(e => console.warn('[Voice] VAD AudioContext resume error:', e));
          }
        };

        window.addEventListener('click', resumeAllAudioContexts, true);
        window.addEventListener('pointerdown', resumeAllAudioContexts, true);
        window.addEventListener('touchstart', resumeAllAudioContexts, true);
        window.addEventListener('keydown', resumeAllAudioContexts, true);

        const sourceNode = audioCtx.createMediaStreamSource(stream);
        const processor = audioCtx.createScriptProcessor(4096, 1, 1);
        processorRef.current = processor;

        let chunkCounter = 0;

        processor.onaudioprocess = (event) => {
          // Stream AUDIO_FRAMEs ONLY when backend handshake is CONFIRMED READY and Saarthi is not speaking
          if ((stateRef.current as string) !== 'speaking' && wsRef.current?.readyState === WebSocket.OPEN && isSessionReadyRef.current) {
            chunkCounter++;
            const inputData = event.inputBuffer.getChannelData(0);
            const pcm16 = float32ToPCM16(inputData);
            const base64data = uint8ArrayToBase64(pcm16);

            userRecordedBytesRef.current += pcm16.byteLength;
            if (chunkCounter % 10 === 0) {
              console.log(`[VAD-DIAGNOSTIC] Streaming AUDIO_FRAME (chunk ${chunkCounter}). Total user bytes: ${userRecordedBytesRef.current}`);
            }
            sendWsMessage({
              type: 'AUDIO_FRAME',
              payload: { data: base64data },
            });
          } else if (!isSessionReadyRef.current) {
            // Discard audio captured during connection/handshake gap so stale audio does not garble future utterances
            userRecordedBytesRef.current = 0;
            userHasSpokenRef.current = false;
          }
        };

        sourceNode.connect(processor);
        processor.connect(audioCtx.destination);

        // VAD Setup
        const vadAudioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
        vadAudioCtxRef.current = vadAudioCtx;
        if (vadAudioCtx.state === 'suspended') {
          vadAudioCtx.resume().catch(() => {});
        }

        const vadSource = vadAudioCtx.createMediaStreamSource(stream);
        const analyser = vadAudioCtx.createAnalyser();
        analyser.fftSize = 512;
        analyser.minDecibels = -80;
        analyser.smoothingTimeConstant = 0.1;
        vadSource.connect(analyser);

        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        silenceStart = Date.now();
        const VAD_THRESHOLD = 3.0;

        vadIntervalRef.current = window.setInterval(() => {
          // Periodically attempt resume if suspended
          if (vadAudioCtxRef.current?.state === 'suspended') {
            vadAudioCtxRef.current.resume().catch(() => {});
          }
          if (audioContextRef.current?.state === 'suspended') {
            audioContextRef.current.resume().catch(() => {});
          }

          analyser.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
          const average = sum / dataArray.length;

          if (Date.now() % 500 < 100) {
            console.log(`[VAD-DIAGNOSTIC] VAD Tick | State: ${stateRef.current} | Vol: ${average.toFixed(2)} | Thresh: ${VAD_THRESHOLD} | Vol>Thresh: ${average > VAD_THRESHOLD} | UserSpoken: ${userHasSpokenRef.current}`);
          }

          if (Date.now() < vadWarmupTime) {
            silenceStart = Date.now();
            return;
          }

          // Ignore VAD during Saarthi's own TTS playback ('speaking')
          if ((stateRef.current as string) === 'speaking') {
            silenceStart = Date.now();
            return;
          }

          // VAD Logic whenever Saarthi is not speaking (during 'listening' or 'idle' state)
          if ((stateRef.current as string) !== 'speaking') {
            if (average > VAD_THRESHOLD) {
              if (!userHasSpokenRef.current) {
                console.log(`[VAD-DIAGNOSTIC] 🎯 User speech CONFIRMED started! (Vol: ${average.toFixed(2)} > ${VAD_THRESHOLD})`);
                userHasSpokenRef.current = true;
                userRecordedBytesRef.current = 0; // Clear noise bytes accumulated during silence!
                if (stateRef.current !== 'listening') {
                  setSaarthiState('listening');
                }
              }
              silenceStart = Date.now();
            } else {
              if (userHasSpokenRef.current && (Date.now() - silenceStart > 1800)) {
                console.log(`[VAD-DIAGNOSTIC] 🤫 Silence detected after 1.8s. User speech complete. Total bytes: ${userRecordedBytesRef.current}`);
                userHasSpokenRef.current = false;
                
                // Send AUDIO_END only for genuine user speech when session handshake is READY
                if (wsRef.current?.readyState === WebSocket.OPEN && isSessionReadyRef.current && userRecordedBytesRef.current > 0) {
                  const domData = getFormStateData();
                  console.log(`[VAD-DIAGNOSTIC] ✅ Sending AUDIO_END frame with activeField: "${activeFieldRef.current}", DOM data:`, domData);
                  sendWsMessage({
                    type: 'AUDIO_END',
                    payload: {
                      current_page: window.location.pathname,
                      active_field: activeFieldRef.current,
                      dom_form_data: domData,
                    }
                  });
                }
                userRecordedBytesRef.current = 0;
                setSaarthiState('idle');

                if (!(window as any)._hasMinimizedOnce) {
                  console.log('[WIDGET] Triggering shrink-to-corner animation now (via VAD)');
                  forceMinimize();
                  (window as any)._hasMinimizedOnce = true;
                }
              }
            }
          }
        }, 100);
      })
      .catch(err => {
        console.error('[Voice] Persistent Microphone error', err);
        setError('Could not access microphone');
        setSaarthiState('idle');
      });

    return () => {
      // Only destroy microphone stream tracks if the WebSocket connection is explicitly closed
      if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
        console.log('[Voice] WebSocket closed. Tearing down persistent microphone stream...');
        if (vadIntervalRef.current) window.clearInterval(vadIntervalRef.current);
        if (vadAudioCtxRef.current && vadAudioCtxRef.current.state !== 'closed') {
          vadAudioCtxRef.current.close().catch(() => {});
        }
        if (processorRef.current) {
          try { processorRef.current.disconnect(); } catch (e) {}
        }
        if (micStreamRef.current) {
          micStreamRef.current.getTracks().forEach(track => track.stop());
          micStreamRef.current = null;
        }
      } else {
        console.log('[Voice] Component re-render/remount detected. Preserving active microphone stream & VAD context.');
      }
    };
  }, [isConnected]);

  const stopSpeaking = useCallback(() => {
    console.log('[Voice] Barge-in / Stop requested. Halting speech.');
    if (currentAudioSourceRef.current) {
      try {
        currentAudioSourceRef.current.stop();
        currentAudioSourceRef.current.disconnect();
      } catch (e) {}
      currentAudioSourceRef.current = null;
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

  return { isConnected, isSessionReady, error, stopSpeaking };
}
