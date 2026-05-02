import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        parchment: "#f3eedd",
        ink: "#3a2f22",
        moss: "#5b8c3e",
        pine: "#3f7a3a",
        bark: "#6b3e1f",
      },
    },
  },
  plugins: [],
} satisfies Config;
