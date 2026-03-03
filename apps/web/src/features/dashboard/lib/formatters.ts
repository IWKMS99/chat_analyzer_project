export function humanize(value: string): string {
  return value
    .replace(/_ds$/, "")
    .split("_")
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

export function safeString(value: unknown): string {
  if (value === null || value === undefined) {
    return "-";
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      return "-";
    }
    return value.toLocaleString();
  }
  if (typeof value === "string") {
    return value || "-";
  }
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export function formatMaybeDate(value: unknown): string {
  if (typeof value !== "string" || !value.includes("T")) {
    return safeString(value);
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}
