import { afterEach, describe, expect, it } from "vitest";
import { Autosave, type SaveOutcome, type SaveStatus, readLocal } from "./autosave";
import type { Notebook } from "./notebook";

const nb = (source: string): Notebook => ({ format: 1, cells: [{ id: "a", type: "code", source }] });

function harness(outcomes: SaveOutcome[], start = { version: 1, notebook: nb("v1"), dirty: false }) {
  const statuses: SaveStatus[] = [];
  const sent: { version: number; source: string }[] = [];
  const timers: { fn: () => void; ms: number }[] = [];
  const saver = new Autosave("M01", start, (s) => statuses.push(s), {
    save: async (version, notebook) => {
      sent.push({ version, source: notebook.cells[0]?.source ?? "" });
      return outcomes.shift() ?? { kind: "error" };
    },
    schedule: (fn, ms) => {
      timers.push({ fn, ms });
      return () => undefined;
    },
  });
  return { saver, statuses, sent, timers };
}

afterEach(() => window.localStorage.clear());

describe("Autosave (LAB-05)", () => {
  it("o'zgarishsiz tick saqlamaydi; o'zgarish — versiya bilan saqlaydi va lokal nusxani tozalaydi", async () => {
    const { saver, statuses, sent } = harness([{ kind: "saved", version: 2, savedAt: "2026-11-24T05:00:00Z" }]);
    saver.tick();
    expect(sent).toEqual([]);
    saver.change(nb("v2"));
    expect(readLocal("M01")).toEqual({ base: 1, notebook: nb("v2") });
    await saver.flush();
    expect(sent).toEqual([{ version: 1, source: "v2" }]);
    expect(statuses.map((s) => s.kind)).toEqual(["saving", "saved"]);
    expect(readLocal("M01")).toBeNull();
    saver.tick();
    expect(sent).toHaveLength(1);
  });

  it("saqlash paytidagi o'zgarish keyin yana yuboriladi (yangi versiya bilan)", async () => {
    const h = harness([
      { kind: "saved", version: 2, savedAt: "t" },
      { kind: "saved", version: 3, savedAt: "t" },
    ]);
    h.saver.change(nb("a"));
    const first = h.saver.flush();
    h.saver.change(nb("b"));
    void h.saver.flush();
    await first;
    await new Promise((r) => setTimeout(r, 0));
    expect(h.sent).toEqual([
      { version: 1, source: "a" },
      { version: 2, source: "b" },
    ]);
  });

  it("oflayn: lokal nusxa qoladi, eksponensial qayta urinish", async () => {
    const h = harness([{ kind: "offline" }, { kind: "offline" }, { kind: "saved", version: 2, savedAt: "t" }]);
    h.saver.change(nb("oflayn ish"));
    await h.saver.flush();
    expect(h.statuses.at(-1)).toEqual({ kind: "offline", retryInMs: 2000 });
    expect(readLocal("M01")?.notebook).toEqual(nb("oflayn ish"));
    h.timers[0]?.fn();
    await new Promise((r) => setTimeout(r, 0));
    expect(h.timers[1]?.ms).toBe(4000);
    h.timers[1]?.fn();
    await new Promise((r) => setTimeout(r, 0));
    expect(h.statuses.at(-1)?.kind).toBe("saved");
    expect(readLocal("M01")).toBeNull();
  });

  it("409: to'xtaydi; o'zimnikini saqlash serverdagi versiya ustidan", async () => {
    const h = harness([
      { kind: "conflict", version: 5, notebook: nb("server") },
      { kind: "saved", version: 6, savedAt: "t" },
    ]);
    h.saver.change(nb("mine"));
    await h.saver.flush();
    expect(h.statuses.at(-1)).toEqual({ kind: "conflict", serverVersion: 5, serverNotebook: nb("server") });
    await h.saver.flush();
    expect(h.sent).toHaveLength(1); // to'xtagan
    expect(h.saver.resolve(true, 5, nb("server"))).toEqual(nb("mine"));
    await new Promise((r) => setTimeout(r, 0));
    expect(h.sent.at(-1)).toEqual({ version: 5, source: "mine" });
  });

  it("409: serverdagisini olish lokal nusxani tozalaydi", async () => {
    const h = harness([{ kind: "conflict", version: 5, notebook: nb("server") }]);
    h.saver.change(nb("mine"));
    await h.saver.flush();
    expect(h.saver.resolve(false, 5, nb("server"))).toEqual(nb("server"));
    expect(readLocal("M01")).toBeNull();
    expect(h.statuses.at(-1)).toEqual({ kind: "idle" });
  });

  it("oyna yopildi — saqlash to'xtaydi; boshqa xato", async () => {
    const h = harness([{ kind: "closed" }]);
    h.saver.change(nb("x"));
    await h.saver.flush();
    expect(h.statuses.at(-1)).toEqual({ kind: "closed" });
    const e = harness([{ kind: "error" }]);
    e.saver.change(nb("x"));
    await e.saver.flush();
    expect(e.statuses.at(-1)).toEqual({ kind: "error" });
  });

  it("initial: yuborilmagan lokal nusxa tiklanadi, aks holda serverdagi", () => {
    const fallback = nb("");
    expect(Autosave.initial("M01", { version: 3, notebook: nb("srv") }, fallback)).toEqual({
      version: 3,
      notebook: nb("srv"),
      dirty: false,
    });
    window.localStorage.setItem("mlab:lab:M01", JSON.stringify({ base: 2, notebook: nb("local") }));
    expect(Autosave.initial("M01", { version: 3, notebook: nb("srv") }, fallback)).toEqual({
      version: 2,
      notebook: nb("local"),
      dirty: true,
    });
    window.localStorage.setItem("mlab:lab:M01", "{buzuq");
    expect(Autosave.initial("M01", { version: 0, notebook: null }, fallback).notebook).toEqual(fallback);
  });
});

describe("putWork (server javoblari)", () => {
  it("saved / conflict / closed / offline / error", async () => {
    const { mockApi } = await import("../test-utils");
    const { putWork } = await import("./autosave");
    const { vi } = await import("vitest");
    document.cookie = "csrftoken=t";
    const reply = { status: 200, body: { version: 4, saved_at: "t" } as unknown };
    const calls = mockApi({ "PUT /api/labs/M01/work": () => reply });
    expect(await putWork("M01", 3, nb("x"))).toEqual({ kind: "saved", version: 4, savedAt: "t" });
    expect(calls[0]?.body).toEqual({ version: 3, notebook: nb("x") });
    Object.assign(reply, { status: 409, body: { code: "version_conflict", current_version: 7, notebook: nb("s") } });
    expect(await putWork("M01", 3, nb("x"))).toEqual({ kind: "conflict", version: 7, notebook: nb("s") });
    Object.assign(reply, { status: 403, body: { code: "lab_closed" } });
    expect((await putWork("M01", 3, nb("x"))).kind).toBe("closed");
    Object.assign(reply, { status: 503, body: null });
    expect((await putWork("M01", 3, nb("x"))).kind).toBe("offline");
    Object.assign(reply, { status: 400, body: { notebook: ["x"] } });
    expect((await putWork("M01", 3, nb("x"))).kind).toBe("error");
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("Failed to fetch"))));
    expect((await putWork("M01", 3, nb("x"))).kind).toBe("offline");
    vi.unstubAllGlobals();
  });
});
