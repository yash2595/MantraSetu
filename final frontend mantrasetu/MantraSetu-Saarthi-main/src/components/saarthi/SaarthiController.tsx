import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { useSaarthi } from './SaarthiContext';
import { SaarthiAvatar } from './SaarthiAvatar';
import { SaarthiSpeechBubble } from './SaarthiSpeechBubble';
import { ChoicePopup } from './ChoicePopup';
import { useSaarthiVoice } from '../../hooks/useSaarthiVoice';

export const SaarthiController: React.FC = () => {
  const { } = useSaarthiVoice();

  const {
    state,
    onboardingPhase,
    dialogueText,
    isMinimized,
    showChoicePopup,
    showSpeechBubble,
    minimizeSaarthi,
    toggleMinimized,
  } = useSaarthi();

  const isAvatarVisible = onboardingPhase !== 'loading';

  return (
    <>
      {/* ── CENTER DIGITAL HUMAN OVERLAY ── */}
      <AnimatePresence>
        {!isMinimized && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
            className="fixed inset-0 z-50 flex flex-col items-center justify-center p-4 bg-[#140a05]/45 backdrop-blur-xs overflow-hidden pointer-events-none"
            data-testid="saarthi-center-overlay"
          >
            <div className="flex flex-col items-center max-w-md w-full space-y-6 pointer-events-auto">
              {/* Centered Avatar Wrapper with Attached Upper-Right Minimize Button */}
              {isAvatarVisible && (
                <div className="relative flex items-center justify-center">
                  <SaarthiAvatar
                    state={
                      onboardingPhase === 'avatar_enter' ? 'enter'
                      : onboardingPhase === 'avatar_bow' ? 'greeting'
                      : state
                    }
                    minimized={false}
                  />

                  {/* 32px Circular Glass Minimize (X) Button Attached to Avatar */}
                  <button
                    type="button"
                    onClick={minimizeSaarthi}
                    title="Minimize Saarthi"
                    className="absolute -top-1 -right-2 w-8 h-8 rounded-full bg-white/90 backdrop-blur-md border border-[#eadbc9] text-[#7a3e1e] hover:bg-[#ee7c2b] hover:text-white hover:border-[#ee7c2b] shadow-md flex items-center justify-center transition-all duration-200 cursor-pointer active:scale-95 z-30"
                    data-testid="button-minimize-saarthi"
                  >
                    <X size={14} />
                  </button>
                </div>
              )}



              {/* Spoken Dialogue Text Bubble */}
              <AnimatePresence>
                {showSpeechBubble && dialogueText && (
                  <SaarthiSpeechBubble text={dialogueText} />
                )}
              </AnimatePresence>

              {/* Choice Popup Buttons */}
              <AnimatePresence>
                {showChoicePopup && <ChoicePopup />}
              </AnimatePresence>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── BOTTOM-LEFT MINIMIZED PLACEHOLDER (Docked Floating Companion) ── */}
      {isMinimized && (
        <motion.div
          initial={{ scale: 0.5, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="fixed bottom-6 left-6 z-50 flex items-end justify-start pointer-events-auto"
          data-testid="saarthi-minimized-floating"
        >
          {/* Spoken Dialogue Text Bubble (Floating above avatar) */}
          <AnimatePresence>
            {showSpeechBubble && dialogueText && (
              <div className="absolute bottom-full left-4 mb-4 origin-bottom-left w-[300px] sm:w-[340px] max-w-[calc(100vw-3rem)]">
                <SaarthiSpeechBubble text={dialogueText} />
              </div>
            )}
          </AnimatePresence>
          <SaarthiAvatar
            state={state}
            minimized={true}
            onClick={toggleMinimized}
          />

        </motion.div>
      )}
    </>
  );
};
