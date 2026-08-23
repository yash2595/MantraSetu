import { createContext, useContext } from 'react';

export type SaarthiState =
  | 'hidden'
  | 'enter'
  | 'greeting'
  | 'namaste'
  | 'idle'
  | 'listening'
  | 'thinking'
  | 'speaking'
  | 'minimized';

export type OnboardingPhase =
  | 'loading'
  | 'avatar_enter'
  | 'avatar_bow'
  | 'center_greeting'
  | 'user_choice'
  | 'saarthi_listening'
  | 'minimized';

export interface SaarthiContextType {
  // Avatar Body State
  state: SaarthiState;
  onboardingPhase: OnboardingPhase;
  dialogueText: string;
  isMinimized: boolean;
  showChoicePopup: boolean;
  showSpeechBubble: boolean;

  // Flow Actions
  continueWithSaarthi: () => void;
  continueManually: () => void;
  minimizeSaarthi: () => void;
  forceMinimize: () => void;
  reopenSaarthi: () => void;
  setSaarthiState: (state: SaarthiState) => void;
  setDialogueText: (text: string) => void;
  toggleMinimized: () => void;
  announceMessage: (text: string, isSuccess?: boolean) => void;
  disableVoice: () => void;
  enableVoice: () => void;
}

export const SaarthiContext = createContext<SaarthiContextType | undefined>(undefined);

export const useSaarthi = () => {
  const context = useContext(SaarthiContext);
  if (!context) {
    throw new Error('useSaarthi must be used within a SaarthiProvider');
  }
  return context;
};
