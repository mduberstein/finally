import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0d1117",
        panel: "#1a1a2e",
        accentYellow: "#ecad0a",
        bluePrimary: "#209dd7",
        purpleSecondary: "#753991",
      },
    },
  },
  plugins: [],
};

export default config;
