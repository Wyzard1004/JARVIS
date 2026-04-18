/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        'jarvis-dark': '#0F172A',
        'jarvis-red': '#DC2626',
      }
    },
  },
  plugins: [],
}
