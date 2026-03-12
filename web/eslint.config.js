import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import nextPlugin from "@next/eslint-plugin-next";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", ".next/**/*", "node_modules/**/*", "output/**/*"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
      "@next/next": nextPlugin,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      ...nextPlugin.configs.recommended.rules,
      ...nextPlugin.configs["core-web-vitals"].rules,
      "@typescript-eslint/no-explicit-any": 0,
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { args: "none", argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true, allowExportNames: ["metadata"] },
      ],
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["@radix-ui/*"],
              message:
                "统一从 src/components/ui 封装组件导入，禁止在页面/业务层直接使用 Radix primitives",
            },
          ],
        },
      ],
    },
  },
  {
    files: ["src/components/ui/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": 0,
      "react-refresh/only-export-components": 0,
    },
  },
  {
    files: [
      "src/providers/**/*.{ts,tsx}",
      "src/components/chat/artifact.tsx",
      "src/components/chat/messages/tool-calls.tsx",
      "src/components/todo/TodoListCard.tsx",
    ],
    rules: {
      "react-refresh/only-export-components": 0,
    },
  },
);
