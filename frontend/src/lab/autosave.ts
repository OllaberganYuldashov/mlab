/**
 * Laboratoriya avtosaqlashi (I2-17; LAB-05). Server: `PUT /api/labs/{code}/work` (optimistik `version`).
 *
 * - O'zgarish bo'lsa har 10 soniyada va har ishga tushirishda saqlanadi; bir vaqtda bitta so'rov.
 * - Tarmoq uzilsa: oxirgi holat brauzerda (localStorage, try/catch) va qayta urinish eksponensial
 *   (2 → 60 s) yoki `online` hodisasida. Sahifa qayta ochilsa, yuborilmagan nusxa tiklanadi.
 * - 409: ish boshqa oynada o'zgargan — foydalanuvchi tanlaydi (o'zimniki / serverdagi).
 * - 403 `lab_closed`: oyna yopildi — saqlash to'xtaydi, lokal nusxa qoladi.
 */
import { api } from "../api";
import type { Notebook } from "./notebook";

export const SAVE_INTERVAL_MS = 10_000;
const MAX_BACKOFF_MS = 60_000;

export type SaveStatus =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "saved"; at: string }
  | { kind: "offline"; retryInMs: number }
  | { kind: "conflict"; serverVersion: number; serverNotebook: Notebook | null }
  | { kind: "closed" }
  | { kind: "error" };

export type SaveOutcome =
  | { kind: "saved"; version: number; savedAt: string }
  | { kind: "conflict"; version: number; notebook: Notebook | null }
  | { kind: "closed" }
  | { kind: "offline" }
  | { kind: "error" };

interface LocalCopy {
  base: number;
  notebook: Notebook;
}

const key = (code: string) => `mlab:lab:${code}`;

export function readLocal(code: string): LocalCopy | null {
  try {
    const raw = window.localStorage.getItem(key(code));
    if (!raw) return null;
    const value = JSON.parse(raw) as LocalCopy;
    return typeof value.base === "number" && value.notebook?.format === 1 ? value : null;
  } catch {
    return null;
  }
}

function writeLocal(code: string, copy: LocalCopy | null): void {
  try {
    if (copy) window.localStorage.setItem(key(code), JSON.stringify(copy));
    else window.localStorage.removeItem(key(code));
  } catch {
    // Xususiy rejim yoki to'lgan xotira — server saqlashi baribir ishlaydi.
  }
}

export async function putWork(code: string, version: number, notebook: Notebook): Promise<SaveOutcome> {
  try {
    const result = await api<{ version: number; saved_at: string }>(`/api/labs/${code}/work`, {
      method: "PUT",
      body: { version, notebook },
    });
    if (result.ok) return { kind: "saved", version: result.data.version, savedAt: result.data.saved_at };
    const data = (result.data ?? {}) as { code?: string; current_version?: number; notebook?: Notebook | null };
    if (result.status === 409 && data.code === "version_conflict")
      return { kind: "conflict", version: data.current_version ?? 0, notebook: data.notebook ?? null };
    if (result.status === 403 && data.code === "lab_closed") return { kind: "closed" };
    if (result.status >= 500 || result.status === 429) return { kind: "offline" };
    return { kind: "error" };
  } catch {
    return { kind: "offline" };
  }
}

interface Deps {
  save: (version: number, notebook: Notebook) => Promise<SaveOutcome>;
  schedule: (fn: () => void, ms: number) => () => void;
}

export class Autosave {
  private version: number;
  private notebook: Notebook;
  private dirty: boolean;
  private saving = false;
  private again = false;
  private failures = 0;
  private cancelRetry: (() => void) | null = null;
  private stopped = false;

  constructor(
    private readonly code: string,
    start: { version: number; notebook: Notebook; dirty: boolean },
    private readonly onStatus: (status: SaveStatus) => void,
    private readonly deps: Deps = {
      save: (version, notebook) => putWork(code, version, notebook),
      schedule: (fn, ms) => {
        const id = setTimeout(fn, ms);
        return () => clearTimeout(id);
      },
    },
  ) {
    this.version = start.version;
    this.notebook = start.notebook;
    this.dirty = start.dirty;
    if (start.dirty) writeLocal(code, { base: this.version, notebook: this.notebook });
  }

  /** Sahifa ochilganda: yuborilmagan lokal nusxa bo'lsa — o'sha (asosi bilan), aks holda serverdagi. */
  static initial(
    code: string,
    server: { version: number; notebook: Notebook | null },
    fallback: Notebook,
  ): { version: number; notebook: Notebook; dirty: boolean } {
    const local = readLocal(code);
    const serverNotebook = server.notebook ?? fallback;
    if (local && JSON.stringify(local.notebook) !== JSON.stringify(server.notebook))
      return { version: local.base, notebook: local.notebook, dirty: true };
    return { version: server.version, notebook: serverNotebook, dirty: false };
  }

  change(notebook: Notebook): void {
    this.notebook = notebook;
    this.dirty = true;
    writeLocal(this.code, { base: this.version, notebook });
  }

  /** Har 10 soniyada (taymer) — faqat o'zgarish bo'lsa. */
  tick(): void {
    if (this.dirty) void this.flush();
  }

  /** Darhol saqlash (ishga tushirishda, oynadan chiqishda, tarmoq qaytganda). */
  async flush(): Promise<void> {
    if (this.stopped) return;
    if (this.saving) {
      this.again = true;
      return;
    }
    this.cancelRetry?.();
    this.cancelRetry = null;
    this.saving = true;
    this.onStatus({ kind: "saving" });
    const sent = this.notebook;
    const outcome = await this.deps.save(this.version, sent);
    this.saving = false;
    switch (outcome.kind) {
      case "saved":
        this.failures = 0;
        this.version = outcome.version;
        if (this.notebook === sent) {
          this.dirty = false;
          writeLocal(this.code, null);
        } else {
          writeLocal(this.code, { base: this.version, notebook: this.notebook });
        }
        this.onStatus({ kind: "saved", at: outcome.savedAt });
        break;
      case "offline": {
        this.failures += 1;
        const wait = Math.min(MAX_BACKOFF_MS, 2000 * 2 ** (this.failures - 1));
        this.cancelRetry = this.deps.schedule(() => void this.flush(), wait);
        this.onStatus({ kind: "offline", retryInMs: wait });
        return;
      }
      case "conflict":
        this.stopped = true;
        this.onStatus({ kind: "conflict", serverVersion: outcome.version, serverNotebook: outcome.notebook });
        return;
      case "closed":
        this.stopped = true;
        this.onStatus({ kind: "closed" });
        return;
      case "error":
        this.onStatus({ kind: "error" });
        return;
    }
    if (this.again) {
      this.again = false;
      if (this.dirty) await this.flush();
    }
  }

  /** 409 dan keyin: o'zimnikini serverdagi versiya ustidan yozish yoki serverdagini olish. */
  resolve(keepMine: boolean, serverVersion: number, serverNotebook: Notebook | null): Notebook {
    this.stopped = false;
    this.version = serverVersion;
    if (keepMine) {
      void this.flush();
      return this.notebook;
    }
    this.notebook = serverNotebook ?? this.notebook;
    this.dirty = false;
    writeLocal(this.code, null);
    this.onStatus({ kind: "idle" });
    return this.notebook;
  }

  stop(): void {
    this.stopped = true;
    this.cancelRetry?.();
  }
}
