/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["DM Sans", "system-ui", "sans-serif"],
        display: ["Instrument Sans", "system-ui", "sans-serif"],
      },
      colors: {
        ink: {
          50: "#f7f8fa",
          100: "#eceef2",
          200: "#d5dae3",
          300: "#b0b9c9",
          400: "#8592ab",
          500: "#667892",
          600: "#526079",
          700: "#434e63",
          800: "#3a4354",
          900: "#323946",
          950: "#1e222b",
        },
        accent: {
          DEFAULT: "#0d9488",
          muted: "#5eead4",
          fg: "#042f2e",
        },
      },
      boxShadow: {
        card: "0 1px 2px rgb(0 0 0 / 0.04), 0 8px 24px rgb(0 0 0 / 0.06)",
      },
    },
  },
  plugins: [],
};
