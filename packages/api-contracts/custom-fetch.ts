type ApiErrorPayload = {
  detail?: string;
  message?: string;
};

const rawApiBaseUrl =
  (globalThis as { __CHAT_ANALYZER_API_BASE_URL__?: string }).__CHAT_ANALYZER_API_BASE_URL__ ??
  "http://localhost:8000/api";

const normalizedApiBaseUrl = rawApiBaseUrl.replace(/\/$/, "");

function buildUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }

  let normalizedPath = path.startsWith("/") ? path : `/${path}`;

  // Keep backward compatibility with VITE_API_BASE_URL that already includes /api.
  if (normalizedApiBaseUrl.endsWith("/api") && normalizedPath.startsWith("/api/")) {
    normalizedPath = normalizedPath.slice("/api".length);
  }

  return `${normalizedApiBaseUrl}${normalizedPath}`;
}

export async function customFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(buildUrl(url), init);
  const textBody = [204, 205, 304].includes(response.status) ? "" : await response.text();

  if (!response.ok) {
    let payload: ApiErrorPayload | null = null;
    try {
      payload = textBody ? (JSON.parse(textBody) as ApiErrorPayload) : null;
    } catch {
      payload = null;
    }

    const error = new Error(payload?.detail ?? payload?.message ?? `HTTP ${response.status}`);
    (error as Error & { status?: number; info?: ApiErrorPayload | string }).status = response.status;
    (error as Error & { status?: number; info?: ApiErrorPayload | string }).info = payload ?? textBody;
    throw error;
  }

  if (!textBody) {
    return undefined as T;
  }

  return JSON.parse(textBody) as T;
}
