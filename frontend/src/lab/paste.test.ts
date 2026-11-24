import { afterEach, describe, expect, it, vi } from "vitest";
import { pasteAllowed, pasteSize, reportPaste } from "./paste";

afterEach(() => vi.unstubAllGlobals());

describe("paste qoidalari (INT-01, ACC-09)", () => {
  it("hajm kod nuqtalari bo'yicha", () => {
    expect(pasteSize("abc")).toBe(3);
    expect(pasteSize("oʻgʻil")).toBe(6);
    expect(pasteSize("😀")).toBe(1);
    expect(pasteSize("")).toBe(0);
  });

  it("chegara ichida ruxsat, oshsa yoki nazorat rejimida — rad", () => {
    expect(pasteAllowed(200, { limit: 200, proctored: false })).toBe(true);
    expect(pasteAllowed(201, { limit: 200, proctored: false })).toBe(false);
    expect(pasteAllowed(1, { limit: 200, proctored: true })).toBe(false);
    expect(pasteAllowed(0, { limit: 0, proctored: false })).toBe(true);
  });

  it("qayd: faqat hajm va katak; tarmoq xatosi jim", async () => {
    document.cookie = "csrftoken=t";
    const fetch = vi.fn().mockRejectedValue(new Error("offline"));
    vi.stubGlobal("fetch", fetch);
    reportPaste("M01", "c1", 42);
    await vi.waitFor(() => expect(fetch).toHaveBeenCalled());
    const [url, init] = fetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/labs/M01/events");
    expect(JSON.parse(init.body as string)).toEqual({
      kind: "paste",
      size: 42,
      cell: "c1",
    });
  });
});
