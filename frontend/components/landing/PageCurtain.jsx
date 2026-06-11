"use client";

import React from "react";
import { motion } from "framer-motion";

export default function PageCurtain() {
  return (
    <motion.div
      initial={{ y: "0%" }}
      animate={{ y: "-100%" }}
      transition={{ duration: 1.4, ease: [0.76, 0, 0.24, 1], delay: 0.5 }}
      className="fixed inset-0 z-[100] flex items-center justify-center bg-[#050A15]"
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 1.1 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="font-serif-display text-4xl text-white tracking-tight"
      >
        FundersAI
      </motion.div>
    </motion.div>
  );
}
