import { describe, expect, it } from "vitest";
import lock from "../../pyodide.lock.json";
import { PYODIDE_BASE, SEABORN_WHEEL, type FromWorker, type ToWorker } from "./protocol";
import { PythonRuntime } from "./runtime";

class FakeWorker {
  sent: ToWorker[] = [];
  terminated = false;
  onmessage: ((event: MessageEvent<FromWorker>) => void) | null = null;
  postMessage(message: ToWorker) {
    this.sent.push(message);
  }
  terminate() {
    this.terminated = true;
  }
  emit(message: FromWorker) {
    this.onmessage?.({ data: message } as MessageEvent<FromWorker>);
  }
}

function setup() {
  const workers: FakeWorker[] = [];
  const runtime = new PythonRuntime(() => {
    const worker = new FakeWorker();
    workers.push(worker);
    return worker;
  });
  return { runtime, workers };
}

describe("PythonRuntime (LAB-02)", () => {
  it("lock fayl: versiya, o'z server yo'li va xeshlar", () => {
    expect(PYODIDE_BASE).toBe(`/pyodide/${lock.version}/`);
    expect(SEABORN_WHEEL).toMatch(/^seaborn-.*\.whl$/);
    for (const file of lock.files) expect(file.sha256).toMatch(/^[0-9a-f]{64}$/);
    expect(lock.files.map((f) => f.file)).toEqual(expect.arrayContaining(["pyodide.mjs", "pyodide.asm.wasm"]));
  });

  it("run: hodisalar va natija, status", async () => {
    const { runtime, workers } = setup();
    const statuses: string[] = [];
    runtime.onStatus((s) => statuses.push(s));
    const events: unknown[] = [];
    const done = runtime.run("print(1)", (e) => events.push(e));
    const worker = workers[0] as FakeWorker;
    expect(worker.sent).toEqual([{ type: "run", id: 1, code: "print(1)" }]);
    worker.emit({ type: "status", status: "loading" });
    worker.emit({ type: "stdout", id: 1, text: "1" });
    worker.emit({ type: "stderr", id: 1, text: "ogoh" });
    worker.emit({ type: "figure", id: 1, png: "AAA" });
    worker.emit({ type: "stdout", id: 99, text: "begona" });
    worker.emit({ type: "status", status: "ready" });
    worker.emit({ type: "done", id: 1, result: "42" });
    expect(await done).toEqual({ ok: true, result: "42", error: null });
    expect(events).toEqual([
      { kind: "stdout", text: "1" },
      { kind: "stderr", text: "ogoh" },
      { kind: "figure", png: "AAA" },
    ]);
    expect(statuses).toEqual(["loading", "ready"]);
    expect(runtime.status).toBe("ready");
  });

  it("xato va bitta worker qayta ishlatiladi", async () => {
    const { runtime, workers } = setup();
    const first = runtime.run("1/0");
    workers[0]?.emit({ type: "error", id: 1, message: "ZeroDivisionError" });
    expect(await first).toEqual({ ok: false, result: null, error: "ZeroDivisionError" });
    const second = runtime.run("2");
    expect(workers).toHaveLength(1);
    workers[0]?.emit({ type: "done", id: 2, result: null });
    expect((await second).ok).toBe(true);
  });

  it("restart (LAB-06): kutilayotgan ishlar to'xtatildi, yangi worker", async () => {
    const { runtime, workers } = setup();
    const pending = runtime.run("while True: pass");
    runtime.restart();
    expect(workers[0]?.terminated).toBe(true);
    expect(await pending).toEqual({ ok: false, result: null, error: null, interrupted: true });
    expect(runtime.status).toBe("idle");
    void runtime.run("1");
    expect(workers).toHaveLength(2);
  });
});
