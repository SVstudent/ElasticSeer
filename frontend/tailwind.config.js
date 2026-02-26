/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        elastic: {
          blue: '#0077CC',
          darkBlue: '#006BB4',
          lightBlue: '#E6F1F7',
          gray: '#69707D',
          darkGray: '#343741',
          lightGray: '#F5F7FA',
          border: '#D3DAE6',
        }
      }
    },
  },
  plugins: [],
}
