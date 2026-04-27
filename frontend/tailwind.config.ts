import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{vue,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#0053db',
        'primary-dim': '#0048c1',
        surface: '#f7f9fb',
        'surface-container-low': '#f0f4f7',
        'surface-container': '#e8eff3',
        'surface-container-high': '#d9e4ea',
        'surface-container-highest': '#d9e4ea',
        'on-surface': '#2a3439',
        'on-surface-variant': '#566166',
        'outline-variant': '#a9b4b9',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        ambient: '0 12px 40px rgba(42, 52, 57, 0.06)',
      },
      borderRadius: {
        md: '0.75rem',
      },
    },
  },
  plugins: [],
} satisfies Config
