import React from 'react';
import { motion } from 'framer-motion';
import FoodCanvas from '../components/FoodCanvas'; // ← 3D Bileşen içe aktarıldı
import { recipes } from '../data/recipes';

export default function RecipeStream({ selectedIngredients, getMatchData }) {
  return (
    <div className="w-full relative">
      {recipes.map((recipe) => {
        const { matchPercentage } = getMatchData(recipe.ingredients);

        return (
          <section
            key={recipe.id}
            className="h-screen w-full sticky top-0 flex items-center justify-between p-6 md:p-16 overflow-hidden border-t border-white/10"
          >
            {/* Arka Plan Videosu */}
            <video
              autoPlay
              loop
              muted
              playsInline
              src={recipe.videoUrl}
              className="absolute inset-0 w-full h-full object-cover z-0 opacity-40"
            />

            <div className="absolute inset-0 bg-gradient-to-t from-black via-black/40 to-transparent z-10" />

            {/* Sol Taraf: Glassmorphic Tarif Bilgi Kartı */}
            <motion.div
              initial={{ opacity: 0, x: -50 }}
              whileInView={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8 }}
              className="relative z-20 max-w-lg p-6 md:p-8 rounded-3xl bg-black/50 backdrop-blur-xl border border-white/15 shadow-2xl"
            >
              <div className="flex justify-between items-center mb-3">
                <span className="text-xs uppercase tracking-widest text-amber-400 font-mono">
                  {recipe.country}
                </span>
                {matchPercentage !== null && (
                  <span className="text-xs font-bold px-3 py-1 bg-amber-500/20 border border-amber-500/40 text-amber-300 rounded-full">
                    %{matchPercentage} Eşleşme
                  </span>
                )}
              </div>

              <h2 className="text-3xl md:text-4xl font-bold">{recipe.title}</h2>
              <p className="text-gray-300 mt-2 text-sm leading-relaxed">{recipe.description}</p>
            </motion.div>

            {/* Sağ Taraf: Etkileşimli 3D Model Canvas */}
            <motion.div 
              initial={{ opacity: 0, scale: 0.8 }}
              whileInView={{ opacity: 1, scale: 1 }}
              transition={{ duration: 1 }}
              className="relative z-20 w-full md:w-1/2 flex flex-col items-center justify-center"
            >
              {/* Eğer tarif özel bir model içermiyorsa varsayılan 3d modeli yükler */}
              <FoodCanvas modelPath={recipe.model3dUrl || '/models/food_bowl.glb'} />
              <span className="text-[10px] tracking-widest font-mono text-gray-400 uppercase mt-2">
                ↔ Döndürmek için sürükleyin
              </span>
            </motion.div>
          </section>
        );
      })}
    </div>
  );
}