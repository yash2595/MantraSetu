import React, { useState, useEffect, useCallback } from 'react';
import {
  SaarthiContext,
  type SaarthiState,
  type OnboardingPhase,
} from './SaarthiContext';
import { SaarthiController } from './SaarthiController';

interface SaarthiProviderProps {
  children: React.ReactNode;
}

export const SaarthiProvider: React.FC<SaarthiProviderProps> = ({ children }) => {
  // State declarations (production mode)
  const [state, setState] = useState<SaarthiState>('idle');
  const [onboardingPhase, setOnboardingPhase] = useState<OnboardingPhase>('saarthi_listening');
  const [dialogueText, setDialogueText] = useState<string>('');
  const [isMinimized, setIsMinimized] = useState<boolean>(false);
  const [showChoicePopup, setShowChoicePopup] = useState<boolean>(true);
  const [showSpeechBubble, setShowSpeechBubble] = useState<boolean>(true);

  // Log state transitions for debugging
  React.useEffect(() => {
    console.log('[Provider] state changed to', state);
  }, [state]);

  React.useEffect(() => {
    console.log('[Provider] onboardingPhase changed to', onboardingPhase);
  }, [onboardingPhase]);

  // ── FULL PAGE REFRESH (F5) ALWAYS REPLAYS ONBOARDING ───────────────────
  // Because SaarthiProvider is mounted at top level of App, React Router navigation
  // maintains state, while F5 full page refresh re-initializes this state completely.
  useEffect(() => {
  // Onboarding disabled in production; backend will handle greeting and AI_RESPONSE.
}, []);

  // ── USER CHOICE 1: Continue Manually ────────────────────────
  const continueManually = useCallback(() => {
    console.log('[Provider] continueManually invoked');
    // 180ms fade out popup & bubble -> 100ms pause -> bow -> minimize to bottom-right
    setShowChoicePopup(false);
    setShowSpeechBubble(false);

    setTimeout(() => {
      setState('greeting'); // 8-10° gentle bow
      setTimeout(() => {
        setIsMinimized(true);
        setState('idle');
        setOnboardingPhase('minimized');
        setDialogueText('');
      }, 500);
    }, 280); // 180ms fade + 100ms pause
  }, []);

  // ── USER CHOICE 2: Continue with Saarthi ────────────────────
  const continueWithSaarthi = useCallback(() => {
    console.log('[Provider] continueWithSaarathi invoked, switching to listening');
    setShowChoicePopup(false);
    setIsMinimized(false); // REMAINS in center
    setShowSpeechBubble(true);
    setDialogueText('जी बताइए,\nआज मैं आपकी क्या सहायता कर सकता हूँ?');
    setState('listening');
    setOnboardingPhase('saarthi_listening');
  }, []);

  // ── MINIMIZE / STEP-ASIDE CONTROL (Sequence Refined) ─────────
  const minimizeSaarthi = useCallback(() => {
    console.trace('[Provider] minimizeSaarthi invoked');
    // 1. Speech bubble & popup fade out (180ms)
    setShowChoicePopup(false);
    setShowSpeechBubble(false);

    // 2. 100ms pause -> 3. Gentle 8-10° bow gesture -> 4. Move to bottom-right
    setTimeout(() => {
      setState('greeting'); // Gentle bow
      setTimeout(() => {
        setIsMinimized(true);
        setState('idle');
        setOnboardingPhase('minimized');
        setDialogueText('');
      }, 500);
    }, 280); // 180ms fade + 100ms pause
  }, []);

  // ── FORCE MINIMIZE (Instant, for AI Interactions) ─────────
  const forceMinimize = useCallback(() => {
    console.log('[WIDGET] forceMinimize executing. setting isMinimized to true');
    console.trace('[Provider] forceMinimize invoked');
    setShowChoicePopup(false);
    setShowSpeechBubble(true); // Keep speech bubble visible!
    setIsMinimized(true);
    setOnboardingPhase('minimized');
  }, []);

  // ── REOPEN CONTROL (When floating avatar is clicked later) ───
  const reopenSaarthi = useCallback(() => {
    console.log('[Provider] reopenSaarthi invoked');
    // Return to center, skip onboarding, skip "Jai Bholenath", simply say "जी बताइए।"
    setIsMinimized(false);
    setShowChoicePopup(false);
    setShowSpeechBubble(true);
    setDialogueText('जी बताइए।');
    setState('listening');
    setOnboardingPhase('saarthi_listening');
  }, []);

  const toggleMinimized = useCallback(() => {
    if (isMinimized) {
      reopenSaarthi();
    } else {
      minimizeSaarthi();
    }
  }, [isMinimized, reopenSaarthi, minimizeSaarthi]);

  const setSaarthiState = useCallback((newState: SaarthiState) => {
    setState(newState);
  }, []);

  const announceMessage = useCallback((text: string, isSuccess: boolean = true) => {
    console.log('[Saarthi] Announce message:', text, 'isSuccess:', isSuccess);
    setDialogueText(text);
    setShowSpeechBubble(true);
    
    if (isSuccess) {
      setState('namaste');
      setTimeout(() => {
        setState('speaking');
      }, 1500);
    } else {
      setState('speaking');
    }

    setTimeout(() => {
      setState('idle');
    }, 8000);
  }, []);

  return (
    <SaarthiContext.Provider
      value={{
        state,
        onboardingPhase,
        dialogueText,
        isMinimized,
        showChoicePopup,
        showSpeechBubble,

        continueWithSaarthi,
        continueManually,
        minimizeSaarthi,
        forceMinimize,
        reopenSaarthi,
        setSaarthiState,
        setDialogueText,
        toggleMinimized,
        announceMessage,
      }}
    >
      {children}
      <SaarthiController />
    </SaarthiContext.Provider>
  );
};
