import React from 'react';
import { motion } from 'framer-motion';
import { EarOff } from 'lucide-react';

export interface SaarthiSpeechBubbleProps {
  text: string;
  needsRepeat?: boolean;
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

export const SaarthiSpeechBubble: React.FC<SaarthiSpeechBubbleProps> = React.memo(({ text, needsRepeat = false }) => {
  if (!text) return null;

  const bubbleClass = needsRepeat
    ? 'relative w-full max-w-sm sm:max-w-md bg-[#fff8ec]/95 backdrop-blur-md border border-[#f0c473] rounded-2xl p-3 sm:p-4 shadow-xl text-center max-h-[160px] overflow-y-auto overflow-x-hidden custom-scrollbar ring-1 ring-[#f0c473]/60'
    : 'relative w-full max-w-sm sm:max-w-md bg-[#fffdf9]/95 backdrop-blur-md border border-[#eadbc9] rounded-2xl p-3 sm:p-4 shadow-xl text-center max-h-[140px] overflow-y-auto overflow-x-hidden custom-scrollbar';

  return (
    <motion.div
      variants={speechBubbleVariants}
      initial="hidden"
      animate="enter"
      exit="exit"
      className={bubbleClass}
      data-testid="saarthi-speech-bubble"
    >
      {needsRepeat && (
        <div
          className="flex items-center justify-center gap-1.5 mb-1.5 text-[#b45309]"
          data-testid="saarthi-repeat-cue"
        >
          <EarOff size={14} className="shrink-0" />
          <span className="text-xs font-semibold tracking-wide">Main sun nahi paya — dobara boliye</span>
        </div>
      )}
      <p className="text-sm sm:text-base font-serif text-[#24272d] leading-snug whitespace-pre-line font-medium transition-all duration-100 ease-out">
        {text}
      </p>
    </motion.div>
  );
});

