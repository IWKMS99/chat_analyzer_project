import { defineConfig } from "orval";

export default defineConfig({
  contracts: {
    input: "./openapi/openapi.json",
    output: {
      target: "./src/index.ts",
      mode: "single",
      client: "react-query",
      httpClient: "fetch",
      prettier: false,
      clean: true,
      override: {
        operationName: (operation) => operation.operationId?.split("_api_")[0] ?? "unnamed_operation",
        mutator: {
          path: "./custom-fetch.ts",
          name: "customFetch",
        },
        query: {
          version: 5,
        },
        fetch: {
          includeHttpResponseReturnType: false,
          forceSuccessResponse: false,
        },
      },
    },
  },
});
