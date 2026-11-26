import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ApiResult } from "../api";
import { type Submission, watchSubmission } from "./submissions";

const base: Submission = {
  id: 7,
  status: "queued",
  position: 2,
  policy: "on_time",
  score: null,
  final_score: null,
  created_at: "2026-11-26T00:00:00Z",
  finished_at: null,
  understanding: "none",
};

function fakeSocket() {
  const sockets: {
    onmessage: ((e: { data: string }) => void) | null;
    onclose: (() => void) | null;
    close: () => void;
    closed: boolean;
  }[] = [];
  const factory = () => {
    const s = {
      onmessage: null as ((e: { data: string }) => void) | null,
      onclose: null as (() => void) | null,
      closed: false,
      close() {
        s.closed = true;
      },
    };
    sockets.push(s);
    return s;
  };
  return { sockets, factory };
}

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("watchSubmission (AGR-04)", () => {
  it("WebSocket xabari — darhol so'rov; tugaganda to'xtaydi va ulanish yopiladi", async () => {
    const replies: Submission[] = [
      { ...base, status: "running", position: 0 },
      { ...base, status: "done", position: 0, score: 80, final_score: "80.00" },
    ];
    const fetch = vi.fn(
      async (): Promise<ApiResult<Submission>> => ({
        ok: true,
        status: 200,
        data: replies.shift() ?? base,
      }),
    );
    const { sockets, factory } = fakeSocket();
    const seen: string[] = [];
    watchSubmission(7, (s) => seen.push(s.status), { fetch, socket: factory });
    const ws = sockets[0];
    ws?.onmessage?.({
      data: JSON.stringify({ type: "submission.status", id: 99 }),
    });
    ws?.onmessage?.({ data: "buzuq" });
    expect(fetch).not.toHaveBeenCalled(); // boshqa urinish va buzuq xabar — e'tiborsiz
    ws?.onmessage?.({
      data: JSON.stringify({ type: "submission.status", id: 7 }),
    });
    await vi.advanceTimersByTimeAsync(0);
    ws?.onmessage?.({
      data: JSON.stringify({ type: "submission.status", id: 7 }),
    });
    await vi.advanceTimersByTimeAsync(0);
    expect(seen).toEqual(["running", "done"]);
    expect(ws?.closed).toBe(true);
    await vi.advanceTimersByTimeAsync(20_000);
    expect(fetch).toHaveBeenCalledTimes(2); // tugagach so'rov yo'q
  });

  it("xabar kelmasa — zaxira so'rov; uzilsa qayta ulanadi; stop() hammasini to'xtatadi", async () => {
    const fetch = vi.fn(
      async (): Promise<ApiResult<Submission>> => ({
        ok: true,
        status: 200,
        data: base,
      }),
    );
    const { sockets, factory } = fakeSocket();
    const stop = watchSubmission(7, () => undefined, {
      fetch,
      socket: factory,
      pollMs: 1000,
    });
    sockets[0]?.onclose?.();
    await vi.advanceTimersByTimeAsync(1000);
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(sockets).toHaveLength(2);
    stop();
    expect(sockets[1]?.closed).toBe(true);
    await vi.advanceTimersByTimeAsync(5000);
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("ketma-ket xabarlar bitta navbatdagi so'rovga birlashadi; xato javob — e'tiborsiz", async () => {
    let release: () => void = () => undefined;
    const fetch = vi.fn(
      () =>
        new Promise<ApiResult<Submission>>((resolve) => {
          release = () => resolve({ ok: false, status: 500, data: null });
        }),
    );
    const { sockets, factory } = fakeSocket();
    const onUpdate = vi.fn();
    watchSubmission(7, onUpdate, { fetch, socket: factory });
    const msg = { data: JSON.stringify({ type: "submission.status", id: 7 }) };
    sockets[0]?.onmessage?.(msg);
    sockets[0]?.onmessage?.(msg);
    sockets[0]?.onmessage?.(msg);
    expect(fetch).toHaveBeenCalledTimes(1);
    release();
    await vi.advanceTimersByTimeAsync(0);
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(onUpdate).not.toHaveBeenCalled();
  });

  it("WebSocket yo'q muhitda faqat so'rov bilan ishlaydi", async () => {
    const fetch = vi.fn(
      async (): Promise<ApiResult<Submission>> => ({
        ok: true,
        status: 200,
        data: { ...base, status: "error" },
      }),
    );
    const onUpdate = vi.fn();
    watchSubmission(7, onUpdate, { fetch, socket: () => null, pollMs: 500 });
    await vi.advanceTimersByTimeAsync(500);
    expect(onUpdate).toHaveBeenCalledOnce();
    await vi.advanceTimersByTimeAsync(5000);
    expect(fetch).toHaveBeenCalledOnce();
  });
});
