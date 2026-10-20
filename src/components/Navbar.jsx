import React from 'react';

export default function Navbar({
  inputVal,
  setInputVal,
  addIngredient,
  selectedIngredients,
  removeIngredient,
}) {
  return (
    <nav className="fixed top-0 left-0 w-full z-40 p-6 bg-gradient-to-b from-black/90 via-black/40 to-transparent backdrop-blur-md border-b border-white/10 flex flex-col md:flex-row justify-between items-center gap-4">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold tracking-widest text-amber-500">FLAVORPULSE</h1>
        <span className="text-xs border border-amber-500/30 bg-amber-500/10 text-amber-400 px-3 py-1 rounded-full uppercase tracking-wider">
          HCI UX Studio
        </span>
      </div>

      <div className="flex flex-col items-center gap-2 w-full md:w-auto">
        <form onSubmit={addIngredient} className="flex gap-2 w-full md:w-80">
          <input
            type="text"
            placeholder="Elinizdeki malzemeyi yazın..."
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            className="w-full px-4 py-2 rounded-full bg-white/10 border border-white/20 text-sm text-white placeholder-gray-400 focus:outline-none focus:border-amber-500 transition-all"
          />
          <button
            type="submit"
            className="px-5 py-2 bg-amber-500 hover:bg-amber-600 text-black text-sm font-semibold rounded-full transition-all cursor-pointer"
          >
            Ekle
          </button>
        </form>

        {selectedIngredients.length > 0 && (
          <div className="flex gap-2 flex-wrap justify-center">
            {selectedIngredients.map((ing) => (
              <span
                key={ing}
                onClick={() => removeIngredient(ing)}
                className="cursor-pointer text-xs bg-amber-500/20 text-amber-300 border border-amber-500/40 px-3 py-1 rounded-full flex items-center gap-1 hover:bg-amber-500/30 transition-all"
              >
                #{ing} ✕
              </span>
            ))}
          </div>
        )}
      </div>
    </nav>
  );
}