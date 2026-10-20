import React from 'react';
import { motion } from 'framer-motion';

export default function HeroSection() {
  return (
    <section className="h-screen w-full flex flex-col justify-center items-center relative overflow-hidden px-6 text-center">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1 }}
        className="z-10"
      >
        <span className="text-amber-500 tracking-widest text-sm uppercase mb-4 block font-mono">
          Interactive Culinary Experience
        </span>
        <h1 className="text-5xl md:text-8xl font-black tracking-tighter uppercase leading-none">
          DÜNYA MUTFAĞI <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-amber-600">
            PARMAKLARINIZDA
          </span>
        </h1>
        <p className="text-gray-400 mt-6 max-w-lg mx-auto text-sm md:text-base">
          Evdeki malzemelerinizi girin, dinamik ve sinematik video akışıyla dünya mutfaklarını keşfedin.
        </p>
      </motion.div>

      {/* Arka Plan Izgarası & Efekt */}
      <div className="absolute inset-0 bg-[radial-gradient(#ffffff_1px,transparent_1px)] [background-size:32px_32px] opacity-10 pointer-events-none" />
      <div className="absolute bottom-10 animate-bounce text-xs font-mono tracking-widest text-gray-500 uppercase">
        ↓ AŞAĞI KAYDIRIN
      </div>
    </section>
  );
}