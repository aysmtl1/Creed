import { useState } from 'react';

export function useIngredientMatcher() {
  const [selectedIngredients, setSelectedIngredients] = useState([]);
  const [inputVal, setInputVal] = useState('');

  const addIngredient = (e) => {
    e.preventDefault();
    const cleanVal = inputVal.trim().toLowerCase();
    if (cleanVal && !selectedIngredients.includes(cleanVal)) {
      setSelectedIngredients([...selectedIngredients, cleanVal]);
      setInputVal('');
    }
  };

  const removeIngredient = (ing) => {
    setSelectedIngredients(selectedIngredients.filter((item) => item !== ing));
  };

  const getMatchData = (recipeIngredients) => {
    if (selectedIngredients.length === 0) return { matchedCount: 0, matchPercentage: null };
    const matchedCount = recipeIngredients.filter((ing) => selectedIngredients.includes(ing)).length;
    const matchPercentage = Math.round((matchedCount / recipeIngredients.length) * 100);
    return { matchedCount, matchPercentage };
  };

  return {
    selectedIngredients,
    inputVal,
    setInputVal,
    addIngredient,
    removeIngredient,
    getMatchData,
  };
}