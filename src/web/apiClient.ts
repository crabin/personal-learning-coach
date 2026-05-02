export type HttpMethod = "GET" | "POST" | "PATCH" | "DELETE";

export interface ApiClientOptions {
  baseUrl: string;
  adminApiKey?: string;
  authToken?: string;
  fetcher?: typeof fetch;
}

export interface RequestOptions {
  method?: HttpMethod;
  query?: Record<string, string | number | boolean | undefined>;
  body?: unknown;
  admin?: boolean;
  responseType?: "json" | "text";
}

export interface ApiResponse<T> {
  request: {
    method: HttpMethod;
    url: string;
    body?: unknown;
  };
  data: T;
}

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, detail: unknown) {
    super(formatApiError(status, detail));
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export class LearningCoachApi {
  private baseUrl: string;
  private readonly fetcher: typeof fetch;
  private adminApiKey: string;
  private authToken: string;

  constructor(options: ApiClientOptions) {
    this.baseUrl = normalizeBaseUrl(options.baseUrl);
    this.fetcher = options.fetcher ?? ((input, init) => globalThis.fetch(input, init));
    this.adminApiKey = options.adminApiKey ?? "";
    this.authToken = options.authToken ?? "";
  }

  setBaseUrl(baseUrl: string): void {
    this.baseUrl = normalizeBaseUrl(baseUrl);
  }

  setAdminApiKey(adminApiKey: string): void {
    this.adminApiKey = adminApiKey;
  }

  setAuthToken(authToken: string): void {
    this.authToken = authToken;
  }

  async request<T>(path: string, options: RequestOptions = {}): Promise<ApiResponse<T>> {
    const method = options.method ?? "GET";
    const url = buildUrl(this.baseUrl, path, options.query);
    const headers = new Headers();
    if (options.body !== undefined) {
      headers.set("content-type", "application/json");
    }
    if (options.admin && this.adminApiKey.trim()) {
      headers.set("x-api-key", this.adminApiKey.trim());
    }
    if (this.authToken.trim()) {
      headers.set("authorization", `Bearer ${this.authToken.trim()}`);
    }

    const response = await this.fetcher(url, {
      method,
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });

    if (!response.ok) {
      throw new ApiError(response.status, await readErrorDetail(response));
    }

    const data =
      options.responseType === "text"
        ? ((await response.text()) as T)
        : ((await response.json()) as T);

    return {
      request: {
        method,
        url,
        body: options.body,
      },
      data,
    };
  }
}

export function buildUrl(
  baseUrl: string,
  path: string,
  query: Record<string, string | number | boolean | undefined> = {},
): string {
  const normalizedBase = normalizeBaseUrl(baseUrl);
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const fallbackOrigin = "http://localhost";
  const url = new URL(`${normalizedBase}${normalizedPath}`, fallbackOrigin);
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });
  if (isAbsoluteUrl(normalizedBase)) {
    return url.toString();
  }
  return url.pathname + url.search + url.hash;
}

function normalizeBaseUrl(baseUrl: string): string {
  const value = baseUrl.trim() || "";
  if (!value || value === "/") {
    return "";
  }
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

function isAbsoluteUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}

async function readErrorDetail(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    try {
      return await response.json();
    } catch {
      return response.statusText;
    }
  }
  return response.text();
}

function formatApiError(status: number, detail: unknown): string {
  if (typeof detail === "object" && detail !== null && "detail" in detail) {
    const value = (detail as { detail: unknown }).detail;
    return `HTTP ${status}: ${String(value)}`;
  }
  return `HTTP ${status}: ${String(detail || "Request failed")}`;
}
