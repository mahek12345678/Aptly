import type { Config } from 'tailwindcss'

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    screens: {
      'sm': '640px',
      'md': '768px',
      'lg': '1024px',
      'xl': '1280px',
      '2xl': '1536px',
    },
    extend: {
      fontFamily: {
        inter: ['Inter', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'sans-serif'],
        serif: ['Newsreader', 'Lora', 'Playfair Display', 'Georgia', 'serif'],
        handwriting: ['Caveat', '"Segoe Script"', 'cursive'],
      },
      colors: {
        accent: {
          DEFAULT: '#2563EB',
          light: '#3B82F6',
        },
        background: '#FAFAFA',
        surface: '#FFFFFF',
        border: '#E2E2E2',
        text: {
          DEFAULT: '#1A1A1A',
          primary: '#1A1A1A',
          muted: '#6B6B6B',
        },
        muted: '#6B6B6B',
        primary: {
          DEFAULT: '#1B2A4A',
          hover: '#142038',
          active: '#3D5580',
        },
        active: '#3D5580',
        status: {
          applied: '#9CA3AF',
          oa: '#6B7A99',
          interview: '#3D5580',
          offer: '#1E4D3A',
          rejected: '#7A2E2E',
        },
        'status-applied': '#9CA3AF',
        'status-oa': '#6B7A99',
        'status-interview': '#3D5580',
        'status-offer': '#1E4D3A',
        'status-rejected': '#7A2E2E',
      },
      transitionDuration: {
        '180': '180ms',
        '250': '250ms',
        '300': '300ms',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeOut: {
          '0%': { opacity: '1' },
          '100%': { opacity: '0' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'fade-in': 'fadeIn 200ms cubic-bezier(0.16, 1, 0.3, 1)',
        'fade-out': 'fadeOut 180ms cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-up': 'slideUp 250ms cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-down': 'slideDown 250ms cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  plugins: [],
} satisfies Config
