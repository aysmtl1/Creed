import React from 'react';
import SmoothScroll from './components/SmoothScroll';
import CustomCursor from './components/CustomCursor';
import Navbar from './components/Navbar';
import HeroSection from './sections/HeroSection';
import RecipeStream from './sections/RecipeStream';
import { useIngredientMatcher } from './hooks/useIngredientMatcher';

export default function App() {
  const {
    selectedIngredients,
    inputVal,
    setInputVal,
    addIngredient,
    removeIngredient,
    getMatchData,
  } = useIngredientMatcher();

  return (
    <SmoothScroll>
      <CustomCursor />
      <Navbar
        inputVal={inputVal}
        setInputVal={setInputVal}
        addIngredient={addIngredient}
        selectedIngredients={selectedIngredients}
        removeIngredient={removeIngredient}
      />
      <main className="bg-slate-50 text-slate-900 relative">
        <HeroSection />
        <RecipeStream
          selectedIngredients={selectedIngredients}
          getMatchData={getMatchData}
        />
      </main>
    </SmoothScroll>
  );
}