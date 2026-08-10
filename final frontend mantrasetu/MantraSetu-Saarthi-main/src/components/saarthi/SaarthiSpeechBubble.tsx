import React from 'react';
import { motion } from 'framer-motion';

export interface SaarthiSpeechBubbleProps {
  text: string;
}

export const speechBubbleVariants = {
  hidden: {
    opacity: 0,
    y: 12,
    scale: 0.96,
  },
  enter: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: 0.4,
      ease: [0.16, 1, 0.3, 1] as const,
    },
  },
  exit: {
    opacity: 0,
    y: -8,
    transition: {
      duration: 0.18,
      ease: 'easeIn' as const,
    },
  },
};

export const SaarthiSpeechBubble: React.FC<SaarthiSpeechBubbleProps> = ({ text }) => {
  if (!text) return null;

  return (
    <motion.div
      variants={speechBubbleVariants}
      initial="hidden"
      animate="enter"
      exit="exit"
      className="relative w-full max-w-sm sm:max-w-md bg-[#fffdf9]/95 backdrop-blur-md border border-[#eadbc9] rounded-2xl p-3 sm:p-4 shadow-xl text-center max-h-[140px] overflow-y-auto overflow-x-hidden custom-scrollbar"
      data-testid="saarthi-speech-bubble"
    >
      <p className="text-sm sm:text-base font-serif text-[#24272d] leading-snug whitespace-pre-line font-medium">
        {text}
      </p>
    </motion.div>
  );
};
