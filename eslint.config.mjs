import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      "out/**",
      "build/**",
      "next-env.d.ts",
      "art-gallery/**",
      "hallotickets/**",
      "interactive-demos/**",
      "particle-heart/**",
      "tongpin/**",
      "tongpin-api/**",
      "unibridge/**",
      "xiaojunceping/**",
      "zuoyejing-stitch-rebuild/**",
    ],
  },
];

export default eslintConfig;
