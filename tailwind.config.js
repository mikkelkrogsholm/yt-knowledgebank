/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/**/*.js",
    "./static/**/*.css"
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Knowledge Bank Brand Colors
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554'
        },
        secondary: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
          950: '#052e16'
        },
        accent: {
          50: '#fef7ff',
          100: '#fceeff',
          200: '#f8d4fe',
          300: '#f3abfc',
          400: '#ec72f7',
          500: '#e140f0',
          600: '#c916d3',
          700: '#a40bb0',
          800: '#86108f',
          900: '#701474',
          950: '#4a044e'
        },
        // Semantic Colors
        success: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d'
        },
        warning: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f'
        },
        error: {
          50: '#fef2f2',
          100: '#fee2e2',
          200: '#fecaca',
          300: '#fca5a5',
          400: '#f87171',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
          800: '#991b1b',
          900: '#7f1d1d'
        },
        // Content Type Colors
        video: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a'
        },
        entity: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d'
        },
        topic: {
          50: '#fef7ff',
          100: '#fceeff',
          200: '#f8d4fe',
          300: '#f3abfc',
          400: '#ec72f7',
          500: '#e140f0',
          600: '#c916d3',
          700: '#a40bb0',
          800: '#86108f',
          900: '#701474'
        },
        search: {
          50: '#fff7ed',
          100: '#ffedd5',
          200: '#fed7aa',
          300: '#fdba74',
          400: '#fb923c',
          500: '#f97316',
          600: '#ea580c',
          700: '#c2410c',
          800: '#9a3412',
          900: '#7c2d12'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['Fira Code', 'Consolas', 'Monaco', 'monospace']
      },
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1rem' }],
        'sm': ['0.875rem', { lineHeight: '1.25rem' }],
        'base': ['1rem', { lineHeight: '1.5rem' }],
        'lg': ['1.125rem', { lineHeight: '1.75rem' }],
        'xl': ['1.25rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }],
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
        '5xl': ['3rem', { lineHeight: '1' }],
        '6xl': ['3.75rem', { lineHeight: '1' }],
        '7xl': ['4.5rem', { lineHeight: '1' }],
        '8xl': ['6rem', { lineHeight: '1' }],
        '9xl': ['8rem', { lineHeight: '1' }]
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem'
      },
      borderRadius: {
        'xl': '0.75rem',
        '2xl': '1rem',
        '3xl': '1.5rem'
      },
      boxShadow: {
        'sm': '0 1px 2px 0 rgb(0 0 0 / 0.05)',
        'DEFAULT': '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
        'md': '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
        'lg': '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
        'xl': '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
        '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
        'inner': 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
        'glow': '0 0 0 1px rgb(59 130 246 / 0.15), 0 0 0 4px rgb(59 130 246 / 0.1)',
        'glow-sm': '0 0 0 1px rgb(59 130 246 / 0.1), 0 0 0 2px rgb(59 130 246 / 0.05)'
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'fade-out': 'fadeOut 0.5s ease-in-out',
        'slide-in': 'slideIn 0.3s ease-out',
        'slide-out': 'slideOut 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'scale-out': 'scaleOut 0.2s ease-out',
        'bounce-soft': 'bounceSoft 2s infinite',
        'pulse-slow': 'pulse 3s infinite',
        'float': 'float 3s ease-in-out infinite'
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' }
        },
        fadeOut: {
          '0%': { opacity: '1' },
          '100%': { opacity: '0' }
        },
        slideIn: {
          '0%': { transform: 'translateX(-100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' }
        },
        slideOut: {
          '0%': { transform: 'translateX(0)', opacity: '1' },
          '100%': { transform: 'translateX(-100%)', opacity: '0' }
        },
        scaleIn: {
          '0%': { transform: 'scale(0.9)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' }
        },
        scaleOut: {
          '0%': { transform: 'scale(1)', opacity: '1' },
          '100%': { transform: 'scale(0.9)', opacity: '0' }
        },
        bounceSoft: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-5px)' }
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' }
        }
      },
      backdropBlur: {
        'xs': '2px'
      },
      transitionProperty: {
        'width': 'width',
        'height': 'height',
        'spacing': 'margin, padding'
      }
    }
  },
  plugins: [
    // Custom component classes
    function({ addComponents, theme }) {
      addComponents({
        // Button Components
        '.btn': {
          '@apply inline-flex items-center justify-center px-4 py-2 rounded-lg font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2': {},
        },
        '.btn-primary': {
          '@apply btn bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-500 active:bg-primary-800': {},
        },
        '.btn-secondary': {
          '@apply btn bg-gray-100 text-gray-900 hover:bg-gray-200 focus:ring-gray-500 dark:bg-gray-800 dark:text-gray-100 dark:hover:bg-gray-700': {},
        },
        '.btn-success': {
          '@apply btn bg-success-600 text-white hover:bg-success-700 focus:ring-success-500': {},
        },
        '.btn-warning': {
          '@apply btn bg-warning-600 text-white hover:bg-warning-700 focus:ring-warning-500': {},
        },
        '.btn-error': {
          '@apply btn bg-error-600 text-white hover:bg-error-700 focus:ring-error-500': {},
        },
        '.btn-ghost': {
          '@apply btn bg-transparent text-gray-700 hover:bg-gray-100 focus:ring-gray-500 dark:text-gray-300 dark:hover:bg-gray-800': {},
        },
        '.btn-sm': {
          '@apply px-3 py-1.5 text-sm': {},
        },
        '.btn-lg': {
          '@apply px-6 py-3 text-lg': {},
        },
        
        // Card Components
        '.card': {
          '@apply bg-white rounded-lg shadow-sm border border-gray-200 dark:bg-gray-800 dark:border-gray-700': {},
        },
        '.card-hover': {
          '@apply card hover:shadow-md transition-shadow duration-200': {},
        },
        '.card-interactive': {
          '@apply card-hover cursor-pointer hover:border-primary-300 dark:hover:border-primary-600': {},
        },
        
        // Input Components
        '.input': {
          '@apply block w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100': {},
        },
        '.input-error': {
          '@apply input border-error-300 focus:ring-error-500 focus:border-error-500': {},
        },
        
        // Badge Components
        '.badge': {
          '@apply inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium': {},
        },
        '.badge-primary': {
          '@apply badge bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200': {},
        },
        '.badge-secondary': {
          '@apply badge bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200': {},
        },
        '.badge-success': {
          '@apply badge bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-200': {},
        },
        '.badge-warning': {
          '@apply badge bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-200': {},
        },
        '.badge-error': {
          '@apply badge bg-error-100 text-error-800 dark:bg-error-900 dark:text-error-200': {},
        },
        '.badge-video': {
          '@apply badge bg-video-100 text-video-800 dark:bg-video-900 dark:text-video-200': {},
        },
        '.badge-entity': {
          '@apply badge bg-entity-100 text-entity-800 dark:bg-entity-900 dark:text-entity-200': {},
        },
        '.badge-topic': {
          '@apply badge bg-topic-100 text-topic-800 dark:bg-topic-900 dark:text-topic-200': {},
        },
        '.badge-search': {
          '@apply badge bg-search-100 text-search-800 dark:bg-search-900 dark:text-search-200': {},
        },
        
        // Loading States
        '.loading-overlay': {
          '@apply absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center dark:bg-gray-900 dark:bg-opacity-75': {},
        },
        '.loading-skeleton': {
          '@apply animate-pulse bg-gray-200 dark:bg-gray-700': {},
        },
        
        // Modal Components
        '.modal-backdrop': {
          '@apply fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm z-40': {},
        },
        '.modal-container': {
          '@apply fixed inset-0 z-50 overflow-y-auto': {},
        },
        '.modal-content': {
          '@apply relative bg-white rounded-lg shadow-xl dark:bg-gray-800': {},
        },
        
        // Search Components
        '.search-highlight': {
          '@apply bg-yellow-200 text-yellow-900 px-1 rounded dark:bg-yellow-800 dark:text-yellow-100': {},
        },
        
        // Notification Components
        '.notification': {
          '@apply fixed top-4 right-4 max-w-sm w-full bg-white rounded-lg shadow-lg border border-gray-200 dark:bg-gray-800 dark:border-gray-700 z-50': {},
        },
        '.notification-success': {
          '@apply notification border-l-4 border-l-success-500': {},
        },
        '.notification-warning': {
          '@apply notification border-l-4 border-l-warning-500': {},
        },
        '.notification-error': {
          '@apply notification border-l-4 border-l-error-500': {},
        },
        '.notification-info': {
          '@apply notification border-l-4 border-l-primary-500': {},
        }
      })
    }
  ]
}