/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Brand palette
        brand: {
          purple: '#7C3AED',
          'purple-light': '#9D5BF5',
          'purple-dark': '#5B21B6',
          cyan: '#06B6D4',
          'cyan-light': '#22D3EE',
          'cyan-dark': '#0891B2',
          amber: '#F59E0B',
        },
        // Dark theme surface colors
        surface: {
          base: '#0A0A14',
          elevated: '#0F0F1F',
          card: '#141428',
          border: '#1E1E3A',
          'border-light': '#2A2A4A',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Inter', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'gradient-brand': 'linear-gradient(135deg, #7C3AED 0%, #06B6D4 100%)',
        'gradient-dark': 'linear-gradient(135deg, #0A0A14 0%, #0F0F1F 100%)',
        'gradient-card': 'linear-gradient(135deg, #141428 0%, #0F0F1F 100%)',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'pulse-slow': 'pulse 3s ease-in-out infinite',
        'shimmer': 'shimmer 1.5s ease-in-out infinite',
        'spin-slow': 'spin 3s linear infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      boxShadow: {
        'brand': '0 0 30px rgba(124, 58, 237, 0.3)',
        'brand-sm': '0 0 15px rgba(124, 58, 237, 0.2)',
        'cyan': '0 0 30px rgba(6, 182, 212, 0.3)',
        'card': '0 4px 24px rgba(0, 0, 0, 0.4)',
        'card-hover': '0 8px 40px rgba(0, 0, 0, 0.6)',
      },
    },
  },
  plugins: [],
}
