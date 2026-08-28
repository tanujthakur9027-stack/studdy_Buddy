import type { Config } from "tailwindcss";
import typography from "@tailwindcss/typography";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#f0f4ff",
          100: "#dde8ff",
          200: "#c3d4ff",
          300: "#9ab5ff",
          400: "#6b8dfc",
          500: "#4361f5",
          600: "#2d43ea",
          700: "#2433cf",
          800: "#242ba7",
          900: "#232c84",
          950: "#161a52",
        },
        accent: {
          400: "#fb923c",
          500: "#f97316",
          600: "#ea580c",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "bounce-slow": "bounce 2s infinite",
      },
      typography: {
        DEFAULT: {
          css: {
            maxWidth: "none",
            color: "#e5e7eb",
            "h1,h2,h3,h4,h5,h6": { color: "#f9fafb" },
            strong: { color: "#f9fafb" },
            a: { color: "#6b8dfc" },
            code: { color: "#a5b4fc", background: "rgba(99,102,241,0.1)", padding: "0.1em 0.3em", borderRadius: "4px" },
            "pre code": { background: "transparent", padding: 0 },
            pre: { background: "#111827", color: "#e5e7eb" },
            blockquote: { color: "#9ca3af", borderLeftColor: "#4361f5" },
          },
        },
      },
    },
  },
  plugins: [typography],
};

export default config;
