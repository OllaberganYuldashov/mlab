/** Sahifa ↔ Pyodide worker xabarlari (I2-13; LAB-02). Kod faqat worker'da bajariladi (AGR-03 — serverda emas). */
import lock from "../../pyodide.lock.json";

export const PYODIDE_VERSION: string = lock.version;
export const PYODIDE_BASE = `/pyodide/${PYODIDE_VERSION}/`;
export const SEABORN_WHEEL =
  lock.files.find((f) => f.file.startsWith("seaborn-"))?.file ?? "";

export type ToWorker =
  | { type: "run"; id: number; code: string }
  | { type: "warmup" };

export type FromWorker =
  | { type: "status"; status: "loading" | "ready" }
  | { type: "stdout"; id: number; text: string }
  | { type: "stderr"; id: number; text: string }
  | { type: "figure"; id: number; png: string }
  | { type: "done"; id: number; result: string | null }
  | { type: "error"; id: number; message: string };
