/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: '#F6F7F9',
        surface: '#FFFFFF',
        ink: '#16212B',
        line: '#E1E5EA',
        teal: '#0B6E6E',
        slate: '#5A6472',
        success: '#1E7B4D',
        warning: '#B9770E',
        danger: '#B3261E',
      },
      fontFamily: {
        sans: ['IBM Plex Sans', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
      spacing: {
        'unit': '4px',
        'gutter': '24px',
        'margin-desktop': '40px',
        'margin-mobile': '16px',
        'container-max': '1440px',
      },
    },
  },
  plugins: [],
}
