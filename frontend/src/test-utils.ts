/** Testlar uchun soxta backend: `fetch` ni almashtiradi va so'rovlarni yozib boradi. */
import { vi } from "vitest";

export interface Call {
  path: string;
  method: string;
  body: unknown;
  csrf: string | null;
}

type Handler = (call: Call) => { status: number; body?: unknown };

export function mockApi(handlers: Record<string, Handler>): Call[] {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string, init: RequestInit = {}) => {
      const method = init.method ?? "GET";
      const headers = (init.headers ?? {}) as Record<string, string>;
      const call: Call = {
        path: input,
        method,
        body: init.body ? JSON.parse(String(init.body)) : undefined,
        csrf: headers["X-CSRFToken"] ?? null,
      };
      calls.push(call);
      const handler = handlers[`${method} ${input}`];
      if (!handler) return new Response(null, { status: 404 });
      const { status, body } = handler(call);
      return new Response(body === undefined ? null : JSON.stringify(body), { status });
    }),
  );
  return calls;
}
