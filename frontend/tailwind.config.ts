import type { Config } from "tailwindcss";
import typography from "@tailwindcss/typography";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#070b12",
        panel: "#0d1420",
        raised: "#111827",
        line: "#243244",
        gold: "#c8a96a",
      },
      boxShadow: {
        panel: "0 20px 70px rgba(0, 0, 0, 0.25)",
      },
      fontFamily: {
        sans: ["Inter", "Avenir Next", "ui-sans-serif", "system-ui"],
        serif: ["Iowan Old Style", "Palatino Linotype", "Georgia", "serif"],
      },
    },
  },
  plugins: [typography],
};

export default config;
