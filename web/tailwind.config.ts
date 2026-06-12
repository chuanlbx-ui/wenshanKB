import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#1a56db",
        accent: "#059669",
      },
    },
  },
  plugins: [],
};

export default config;
