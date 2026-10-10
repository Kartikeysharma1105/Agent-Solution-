const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const TIMEOUT_MS = 15_000;

// Ephemeral in-memory operator token store (never persisted to localStorage or logs)
let inMemoryOperatorToken: string = "";

export function setOperatorToken(token: string): void {
  inMemoryOperatorToken = token.trim();
}

export function getOperatorToken(): string {
  return inMemoryOperatorToken;
}

export function clearOperatorToken(): void {
  inMemoryOperatorToken = "";
}

export function hasOperatorToken(): boolean {
  return Boolean(inMemoryOperatorToken);
}

export class ApiError extends Error {
  status: number;
  code?: string;
  payload: unknown;
  errors?: Array<{ loc: string[]; type: string }>;

  constructor(message: string, status = 0, payload?: unknown, code?: string, errors?: Array<{ loc: string[]; type: string }>) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
    this.code = code;
    this.errors = errors;
  }
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const headers: Record<string, string> = {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(inMemoryOperatorToken ? { "X-Operator-Token": inMemoryOperatorToken } : {}),
      ...(init.headers as Record<string, string> | undefined),
    };

    const response = await fetch(`${API_BASE}${path}`, {
      ...init,
      signal: controller.signal,
      headers,
    });

    const raw = await response.text();
    let body: unknown = undefined;
    if (raw) {
      try {
        body = JSON.parse(raw);
      } catch {
        body = raw;
      }
    }

    if (!response.ok) {
      const record = body && typeof body === "object" ? (body as Record<string, unknown>) : {};
      const code = typeof record.code === "string" ? record.code : undefined;
      const errors = Array.isArray(record.errors) ? (record.errors as Array<{ loc: string[]; type: string }>) : undefined;
      const detailMsg = record.detail ? String(record.detail) : undefined;
      const message =
        detailMsg ||
        (typeof record.message === "string" ? record.message : undefined) ||
        (typeof record.error === "string" ? record.error : undefined) ||
        `Request failed with status ${response.status}`;

      throw new ApiError(message, response.status, body, code, errors);
    }

    return body as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("Request timed out after 15 seconds.", 408);
    }
    throw new ApiError(
      "Cannot reach the SENTINEL-X backend API. Verify the server is running and CORS allows this origin.",
      0,
      error
    );
  } finally {
    window.clearTimeout(timeout);
  }
}

export const apiBaseUrl = API_BASE || "(same origin)";
