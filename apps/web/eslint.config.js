import js from "@eslint/js";
import tsParser from "@typescript-eslint/parser";
import tsPlugin from "@typescript-eslint/eslint-plugin";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";

export default [
  { ignores: ["dist", "node_modules", "coverage"] },
  js.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      parser: tsParser,
      // Browser globals (fetch, document, FormData, RequestInit) and the
      // vitest globals used by the test suite. Without these, core-eslint's
      // no-undef rejects every DOM API the SPA depends on.
      globals: { ...globals.browser, ...globals.es2022, React: "readonly" },
      parserOptions: {
        ecmaVersion: 2022,
        sourceType: "module",
        ecmaFeatures: { jsx: true },
      },
    },
    plugins: {
      "@typescript-eslint": tsPlugin,
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...tsPlugin.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      // TypeScript already checks these and does it better.
      "no-undef": "off",
      "no-redeclare": "off",
    },
  },
  {
    files: ["**/*.test.{ts,tsx}", "src/test-setup.ts"],
    languageOptions: { globals: { ...globals.browser, ...globals.vitest } },
  },
  {
    files: ["*.config.{js,ts}"],
    languageOptions: { globals: { ...globals.node } },
  },
];
