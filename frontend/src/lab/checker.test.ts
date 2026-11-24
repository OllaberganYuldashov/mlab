import { afterEach, describe, expect, it, vi } from "vitest";
import { checkProgram, notebookCode, runCheck } from "./checker";
import type { PythonRuntime, RunResult } from "./runtime";

function fakeRuntime(
  results: (code: string, imports?: string) => Promise<RunResult>,
) {
  const calls: { code: string; imports?: string }[] = [];
  const restart = vi.fn();
  const runtime = {
    run: (code: string, _e: unknown, imports?: string) => {
      calls.push({ code, imports });
      return results(code, imports);
    },
    restart,
  } as unknown as PythonRuntime;
  return { runtime, calls, restart };
}

const ok = (result: string | null): RunResult => ({
  ok: true,
  result,
  error: null,
});

afterEach(() => vi.useRealTimers());

describe("checker (AGR-01)", () => {
  it("notebookCode: faqat kod kataklari, tartib bilan", () => {
    expect(
      notebookCode({
        format: 1,
        cells: [
          { id: "a", type: "code", source: "x = 1" },
          { id: "b", type: "markdown", source: "# matn" },
          { id: "c", type: "code", source: "y = x" },
        ],
      }),
    ).toBe("x = 1\n\ny = x");
  });

  it("checkProgram: kod va testlar bitta JSON satr literali ichida (tuzilma buzilmaydi)", () => {
    const tricky = `s = """'\\"\n"""\nprint("\\\\", '\u2028')`;
    const program = checkProgram(
      tricky,
      [{ step: "a", source: "def test_x(ns, params): pass" }],
      {
        n: 3,
      },
    );
    const literal = program.trim().split("\n").at(-1) ?? "";
    expect(literal.startsWith("_mlab_check(")).toBe(true);
    const payload = JSON.parse(
      JSON.parse(literal.slice("_mlab_check(".length, -1)) as string,
    );
    expect(payload).toEqual({
      code: tricky,
      tests: [{ step: "a", source: "def test_x(ns, params): pass" }],
      params: { n: 3 },
    });
  });

  it("avval paketlar (talaba kodi importlari), keyin dastur; natija JSON'dan", async () => {
    const outcome = {
      status: "ok",
      error: null,
      stdout: "",
      tests: [{ step: "a", name: "test_x", passed: true, message: "", ms: 1 }],
    };
    const { runtime, calls } = fakeRuntime(async (code) =>
      ok(code === "None" ? null : JSON.stringify(outcome)),
    );
    const result = await runCheck(runtime, "import pandas", [], {});
    expect(result).toEqual(outcome);
    expect(calls[0]).toEqual({ code: "None", imports: "import pandas" });
    expect(calls[1]?.imports).toBe("");
    expect(calls[1]?.code).toContain("def _mlab_check");
  });

  it("vaqt chegarasi: worker qayta ochiladi va timeout qaytadi", async () => {
    vi.useFakeTimers();
    let release: (r: RunResult) => void = () => undefined;
    const { runtime, restart } = fakeRuntime((code) =>
      code === "None"
        ? Promise.resolve(ok(null))
        : new Promise<RunResult>((resolve) => {
            release = resolve;
          }),
    );
    restart.mockImplementation(() =>
      release({ ok: false, result: null, error: null, interrupted: true }),
    );
    const pending = runCheck(runtime, "while True: pass", [], {}, 1000);
    await vi.advanceTimersByTimeAsync(1000);
    expect(await pending).toEqual({
      status: "timeout",
      error: null,
      stdout: "",
      tests: [],
    });
    expect(restart).toHaveBeenCalledOnce();
  });

  it("muhit xatosi va noto'g'ri natija — failed", async () => {
    const broken = fakeRuntime(async (code) =>
      code === "None" ? ok(null) : { ok: false, result: null, error: "boom" },
    );
    expect((await runCheck(broken.runtime, "", [], {})).status).toBe("failed");
    const garbage = fakeRuntime(async (code) =>
      ok(code === "None" ? null : "not json"),
    );
    expect((await runCheck(garbage.runtime, "", [], {})).status).toBe("failed");
    const stopped = fakeRuntime(async () => ({
      ok: false,
      result: null,
      error: null,
      interrupted: true,
    }));
    expect((await runCheck(stopped.runtime, "", [], {})).status).toBe("failed");
  });
});
