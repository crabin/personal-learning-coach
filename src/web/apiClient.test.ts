import { describe, expect, it, vi } from "vitest";

import { ApiError, LearningCoachApi, buildUrl } from "./apiClient";

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    headers: { "content-type": "application/json" },
    ...init,
  });
}

describe("LearningCoachApi", () => {
  it("builds query strings for GET requests", async () => {
    const fetcher = vi.fn().mockResolvedValue(jsonResponse({ status: "ok" }));
    const api = new LearningCoachApi({ baseUrl: "/", fetcher });

    const response = await api.request("/domains/ai_agent/status", {
      query: { user_id: "u1" },
    });

    expect(fetcher).toHaveBeenCalledWith("/domains/ai_agent/status?user_id=u1", {
      method: "GET",
      headers: expect.any(Headers),
      body: undefined,
    });
    expect(response.data).toEqual({ status: "ok" });
  });

  it("sends JSON bodies for POST requests", async () => {
    const fetcher = vi.fn().mockResolvedValue(jsonResponse({ delivered: true }));
    const api = new LearningCoachApi({ baseUrl: "/", fetcher });

    await api.request("/schedules/trigger", {
      method: "POST",
      body: { user_id: "u1", domain: "ai_agent" },
    });

    const [, request] = fetcher.mock.calls[0];
    expect(request.method).toBe("POST");
    expect(request.body).toBe(JSON.stringify({ user_id: "u1", domain: "ai_agent" }));
    expect(request.headers.get("content-type")).toBe("application/json");
  });

  it("adds the admin API key only for admin requests", async () => {
    const fetcher = vi.fn().mockResolvedValue(jsonResponse([]));
    const api = new LearningCoachApi({
      baseUrl: "/",
      adminApiKey: "read-token",
      fetcher,
    });

    await api.request("/admin/runtime-events", { admin: true });

    const [, request] = fetcher.mock.calls[0];
    expect(request.headers.get("x-api-key")).toBe("read-token");
  });

  it("formats backend detail errors", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      jsonResponse({ detail: "Domain enrollment not found" }, { status: 404 }),
    );
    const api = new LearningCoachApi({ baseUrl: "/", fetcher });

    await expect(api.request("/domains/missing/status")).rejects.toThrow(
      "HTTP 404: Domain enrollment not found",
    );
    await expect(api.request("/domains/missing/status")).rejects.toBeInstanceOf(ApiError);
  });
});

describe("buildUrl", () => {
  it("keeps absolute API bases configurable", () => {
    expect(buildUrl("http://127.0.0.1:8000", "/health")).toBe(
      "http://127.0.0.1:8000/health",
    );
  });
});
