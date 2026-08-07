import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles, MousePointerClick } from 'lucide-react';
import { useSaarthi } from './SaarthiContext';

export const choicePopupVariants = {
  hidden: {
    opacity: 0,
    scale: 0.95,
    y: 10,
  },
  enter: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: {
      duration: 0.35,
      ease: [0.16, 1, 0.3, 1] as const,
    },
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: 8,
    transition: {
      duration: 0.2,
      ease: 'easeIn' as const,
    },
  },
};

export const ChoicePopup: React.FC = () => {
  const { continueWithSaarthi, continueManually } = useSaarthi();

  return (
    <motion.div
      variants={choicePopupVariants}
      initial="hidden"
      animate="enter"
      exit="exit"
      className="w-full max-w-md bg-[#fffdf9] border border-[#eadbc9] rounded-2xl p-5 shadow-2xl text-center space-y-3 relative z-20"
      style={{
        boxShadow: '0 20px 60px rgba(121, 63, 25, 0.16)',
      }}
      data-testid="saarthi-choice-popup"
    >
      <div className="flex flex-col sm:flex-row gap-3 pt-1">
        <button
          type="button"
          onClick={continueWithSaarthi}
          className="flex-1 inline-flex items-center justify-center gap-2 px-5 py-3.5 rounded-xl bg-[#ee7c2b] hover:bg-[#d96620] text-white font-bold text-sm transition-all duration-200 shadow-md hover:shadow-lg active:scale-98"
          data-testid="button-continue-saarthi"
        >
          <Sparkles size={16} /> Continue with Saarthi
        </button>

        <button
          type="button"
          onClick={continueManually}
          className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-3.5 rounded-xl border border-[#eadbc9] bg-white hover:bg-[#fff7ed] text-[#5c5248] font-bold text-sm transition-all duration-200 active:scale-98"
          data-testid="button-continue-manually"
        >
          <MousePointerClick size={15} /> Continue Manually
        </button>
      </div>
    </motion.div>
  );
};
