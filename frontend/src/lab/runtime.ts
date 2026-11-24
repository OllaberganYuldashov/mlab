/**
 * Sahifa tomonidagi Python muhiti (I2-13). Bitta worker — bitta Python (NFR-02: bir tab, bir interpretator).
 * `restart()` worker'ni o'ldirib yangisini ochadi (LAB-06 "To'xtatish"): o'zgaruvchilar yo'qoladi.
 */
import type { FromWorker, ToWorker } from "./protocol";

export type RunEvent =
  | { kind: "stdout" | "stderr"; text: string }
  | { kind: "figure"; png: string };
export interface RunResult {
  ok: boolean;
  result: string | null;
  error: string | null;
  interrupted?: boolean;
}
export type RuntimeStatus = "idle" | "loading" | "ready";

interface WorkerLike {
  postMessage(message: ToWorker): void;
  terminate(): void;
  onmessage: ((event: MessageEvent<FromWorker>) => void) | null;
}

interface Pending {
  onEvent: (event: RunEvent) => void;
  resolve: (result: RunResult) => void;
}

function defaultWorker(): WorkerLike {
  return new Worker(new URL("./pyodide.worker.ts", import.meta.url), {
    type: "module",
  }) as unknown as WorkerLike;
}

export class PythonRuntime {
  private worker: WorkerLike | null = null;
  private nextId = 1;
  private pending = new Map<number, Pending>();
  private listeners = new Set<(status: RuntimeStatus) => void>();
  status: RuntimeStatus = "idle";

  constructor(private readonly factory: () => WorkerLike = defaultWorker) {}

  onStatus(listener: (status: RuntimeStatus) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private setStatus(status: RuntimeStatus) {
    this.status = status;
    for (const listener of this.listeners) listener(status);
  }

  private ensure(): WorkerLike {
    if (this.worker) return this.worker;
    const worker = this.factory();
    worker.onmessage = (event) => this.handle(event.data);
    this.worker = worker;
    return worker;
  }

  private handle(message: FromWorker) {
    if (message.type === "status") {
      this.setStatus(message.status);
      return;
    }
    const pending = this.pending.get(message.id);
    if (!pending) return;
    switch (message.type) {
      case "stdout":
      case "stderr":
        pending.onEvent({ kind: message.type, text: message.text });
        break;
      case "figure":
        pending.onEvent({ kind: "figure", png: message.png });
        break;
      case "done":
        this.pending.delete(message.id);
        pending.resolve({ ok: true, result: message.result, error: null });
        break;
      case "error":
        this.pending.delete(message.id);
        pending.resolve({ ok: false, result: null, error: message.message });
        break;
    }
  }

  /** `imports` berilsa, paketlar shu koddan aniqlanadi (aks holda `code` dan). */
  run(
    code: string,
    onEvent: (event: RunEvent) => void = () => undefined,
    imports?: string,
  ): Promise<RunResult> {
    const id = this.nextId++;
    const worker = this.ensure();
    return new Promise((resolve) => {
      this.pending.set(id, { onEvent, resolve });
      worker.postMessage(
        imports === undefined
          ? { type: "run", id, code }
          : { type: "run", id, code, imports },
      );
    });
  }

  /** NFR-02: Python va numpy/pandas'ni fonda oldindan yuklash (laboratoriya sahifasi ochilganda). */
  warmup(): void {
    if (this.status !== "idle" || this.worker) return;
    try {
      this.ensure().postMessage({ type: "warmup" });
    } catch {
      // Worker yo'q (eski brauzer yoki test muhiti) — birinchi `run` o'zi yuklaydi.
    }
  }

  /** LAB-06: bajarilayotgan kodni to'xtatadi va muhitni qayta ishga tushiradi. */
  restart(): void {
    this.worker?.terminate();
    this.worker = null;
    for (const pending of this.pending.values()) {
      pending.resolve({
        ok: false,
        result: null,
        error: null,
        interrupted: true,
      });
    }
    this.pending.clear();
    this.setStatus("idle");
  }
}

let shared: PythonRuntime | null = null;

export function getRuntime(): PythonRuntime {
  shared ??= new PythonRuntime();
  return shared;
}
