import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import App from "./App";
import "./styles.css";

const runtimeApiBaseUrl = (globalThis as { __CHAT_ANALYZER_API_BASE_URL__?: string }).__CHAT_ANALYZER_API_BASE_URL__;
if (!runtimeApiBaseUrl || runtimeApiBaseUrl === "__CHAT_ANALYZER_API_BASE_URL__") {
  (globalThis as { __CHAT_ANALYZER_API_BASE_URL__?: string }).__CHAT_ANALYZER_API_BASE_URL__ = import.meta.env.VITE_API_BASE_URL;
}

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
);
