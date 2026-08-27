import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../src/lib/api";

describe("api helpers", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
    globalThis.fetch = originalFetch;
  });

  it("calls health endpoint", async () => {
    const status = await api.health();
    expect(status).toEqual({ status: "ok" });
    expect(fetch).toHaveBeenCalledWith("/api/health");
  });

  it("throws readable errors when response fails", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response("bad request", {
        status: 400,
        headers: { "Content-Type": "text/plain" },
      }) as Response,
    );

    await expect(api.getWatchlist()).rejects.toThrow("bad request");
  });
});
