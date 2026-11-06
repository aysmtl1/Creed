/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: { roast: "#3b2314", mocha: "#6f4528", crema: "#e8d3b5", latte: "#c89b6a" },
    },
  },
  plugins: [],
};
