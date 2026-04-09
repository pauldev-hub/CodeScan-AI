/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        bg2: "var(--bg2)",
        bg3: "var(--bg3)",
        border: "var(--border)",
        text: "var(--text)",
        text2: "var(--text2)",
        accent: "var(--accent)",
        green: "var(--green)",
        red: "var(--red)",
        yellow: "var(--yellow)",
        purple: "var(--purple)",
      },
      fontFamily: {
        syne: ["Syne", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "Courier New", "monospace"],
        body: ["-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
      },
      screens: {
        xs: "320px",
      },
      keyframes: {
        pulseDot: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: ".45" },
        },
      },
      animation: {
        pulseDot: "pulseDot 2s cubic-bezier(0.4,0,0.2,1) infinite",
      },
    },
  },
  plugins: [],
};
