import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#00C853',
          light: '#5EF5A7',
          dark: '#009624',
        },
        bg: {
          primary: '#0A0E14',
          secondary: '#111820',
          tertiary: '#1A2332',
          elevated: '#212D3B',
        },
        severity: {
          critical: '#FF3B3B',
          high: '#FF8C00',
          medium: '#FFD300',
          low: '#00C853',
        },
        aqi: {
          good: '#00E400',
          moderate: '#FFFF00',
          unhealthySensitive: '#FF7E00',
          unhealthy: '#FF0000',
          veryUnhealthy: '#8F3F97',
          hazardous: '#7E0023',
        },
      },
    },
  },
  plugins: [],
}
export default config
