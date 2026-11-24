/**
 * Pyodide Web Worker (I2-13; LAB-02, LAB-03, ADR-0006). Python shu oqimda ishlaydi — sahifa qotmaydi.
 * Fayllar o'z serverdan (`/pyodide/<versiya>/`), paketlar kod importlariga qarab yuklanadi.
 * Worker'ga sessiya yoki token berilmaydi; `document` yo'q — CSRF token o'qilmaydi.
 */
import { type FromWorker, PYODIDE_BASE, SEABORN_WHEEL, type ToWorker } from "./protocol";

interface PyProxyLike {
  toJs(): unknown;
  toString(): string;
  destroy(): void;
}

interface Pyodide {
  runPython(code: string): unknown;
  runPythonAsync(code: string): Promise<unknown>;
  loadPackage(names: string | string[], options?: { messageCallback?: (m: string) => void }): Promise<unknown>;
  loadPackagesFromImports(code: string, options?: { messageCallback?: (m: string) => void }): Promise<unknown>;
  setStdout(options: { batched: (line: string) => void }): void;
  setStderr(options: { batched: (line: string) => void }): void;
}

const ctx = self as unknown as {
  postMessage(message: FromWorker, transfer?: Transferable[]): void;
  onmessage: ((event: MessageEvent<ToWorker>) => void) | null;
};
const post = (message: FromWorker) => ctx.postMessage(message);
const quiet = { messageCallback: () => undefined };

// matplotlib grafiklarini PNG (base64) qilib oladi va yopadi: DOM'da SVG to'planmaydi (NFR-02 xotira).
const FIGURES = `
import sys
def _mlab_figures():
    if "matplotlib.pyplot" not in sys.modules:
        return []
    import base64, io
    import matplotlib.pyplot as plt
    out = []
    for num in plt.get_fignums():
        buf = io.BytesIO()
        plt.figure(num).savefig(buf, format="png", bbox_inches="tight", dpi=90)
        out.append(base64.b64encode(buf.getvalue()).decode())
    plt.close("all")
    return out
_mlab_figures()
`;

let current = 0;
let booting: Promise<Pyodide> | null = null;

function boot(): Promise<Pyodide> {
  booting ??= (async () => {
    post({ type: "status", status: "loading" });
    const module = (await import(/* @vite-ignore */ `${PYODIDE_BASE}pyodide.mjs`)) as {
      loadPyodide(options: { indexURL: string }): Promise<Pyodide>;
    };
    const py = await module.loadPyodide({ indexURL: PYODIDE_BASE });
    py.setStdout({ batched: (text) => post({ type: "stdout", id: current, text }) });
    py.setStderr({ batched: (text) => post({ type: "stderr", id: current, text }) });
    py.runPython("import os; os.environ['MPLBACKEND'] = 'AGG'");
    post({ type: "status", status: "ready" });
    return py;
  })();
  return booting;
}

function show(value: unknown): string | null {
  if (value === undefined || value === null) return null;
  if (typeof value === "object" && "toString" in value && "destroy" in value) {
    const proxy = value as PyProxyLike;
    const text = proxy.toString();
    proxy.destroy();
    return text;
  }
  return String(value);
}

async function run(id: number, code: string): Promise<void> {
  current = id;
  try {
    const py = await boot();
    await py.loadPackagesFromImports(code, quiet);
    if (/^\s*(import|from)\s+seaborn\b/m.test(code) && SEABORN_WHEEL) {
      await py.loadPackage(["numpy", "pandas", "matplotlib", "scipy"], quiet);
      await py.loadPackage(`${PYODIDE_BASE}${SEABORN_WHEEL}`, quiet);
    }
    const result = show(await py.runPythonAsync(code));
    const figures = py.runPython(FIGURES) as PyProxyLike;
    const pngs = figures.toJs() as string[];
    figures.destroy();
    for (const png of pngs) post({ type: "figure", id, png });
    post({ type: "done", id, result });
  } catch (error) {
    post({ type: "error", id, message: error instanceof Error ? error.message : String(error) });
  }
}

let queue: Promise<void> = Promise.resolve();
ctx.onmessage = (event) => {
  const message = event.data;
  if (message.type === "run") queue = queue.then(() => run(message.id, message.code));
};
