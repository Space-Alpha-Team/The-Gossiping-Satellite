/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'space-black': '#050505',
        'space-panel': '#0F1115',
        'neon-green': '#00FF41',
        'neon-blue': '#00F3FF',
      },
      animation: {
        'typewriter': 'typewriter 0.1s steps(1) forwards',
      },
      keyframes: {
        typewriter: {
          'from': { opacity: 0 },
          'to': { opacity: 1 }
        }
      }
    },
  },
  plugins: [],
}