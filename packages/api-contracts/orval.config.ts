import { defineConfig } from "orval";

export default defineConfig({
  contracts: {
    input: "./openapi/openapi.json",
    output: {
      target: "./src/index.ts",
      mode: "single",
      client: "fetch",
      prettier: false,
      clean: true,
    },
  },
});
