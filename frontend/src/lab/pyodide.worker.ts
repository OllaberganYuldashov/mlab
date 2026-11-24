/**
 * Pyodide Web Worker (I2-13; LAB-02, LAB-03, ADR-0006). Python shu oqimda ishlaydi — sahifa qotmaydi.
 * Fayllar o'z serverdan (`/pyodide/<versiya>/`), paketlar kod importlariga qarab yuklanadi.
 * Worker'ga sessiya yoki token berilmaydi; `document` yo'q — CSRF token o'qilmaydi.
 */
import {
  type FromWorker,
  PYODIDE_BASE,
  SEABORN_WHEEL,
  type ToWorker,
} from "./protocol";

interface PyProxyLike {
  toJs(): unknown;
  toString(): string;
  destroy(): void;
}

interface Pyodide {
  runPython(code: string): unknown;
  runPythonAsync(code: string): Promise<unknown>;
  loadPackage(
    names: string | string[],
    options?: { messageCallback?: (m: string) => void },
  ): Promise<unknown>;
  loadPackagesFromImports(
    code: string,
    options?: { messageCallback?: (m: string) => void },
  ): Promise<unknown>;
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

// LAB-04: `mlab.load("nomi")` — platforma datasetini pandas DataFrame qilib beradi. Sinxron XHR (faqat
// worker'da ruxsat) talabaning o'z sessiyasi bilan `/api/datasets/<nom>/file` ni oladi.
const MLAB_MODULE = `
import io, re, sys, types
_mlab = types.ModuleType("mlab")
_mlab.__doc__ = "MLab platformasi yordamchilari: mlab.load('iris')"
def _load(name):
    """Platformadagi datasetni pandas DataFrame sifatida yuklaydi: df = mlab.load("iris")."""
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9_]{1,64}", name):
        raise ValueError("Dataset nomi kichik harf, raqam va _ dan iborat (masalan, 'iris').")
    import pandas as pd
    from js import XMLHttpRequest
    req = XMLHttpRequest.new()
    req.open("GET", f"/api/datasets/{name}/file", False)
    req.send(None)
    if req.status == 404:
        raise FileNotFoundError(f"'{name}' dataseti topilmadi. Ro'yxat: Datasetlar sahifasi.")
    if req.status != 200:
        raise ConnectionError(f"Datasetni yuklab bo'lmadi (HTTP {req.status}).")
    return pd.read_csv(io.StringIO(req.responseText))
_mlab.load = _load
sys.modules["mlab"] = _mlab
`;

let current = 0;
let booting: Promise<Pyodide> | null = null;

function boot(): Promise<Pyodide> {
  booting ??= (async () => {
    post({ type: "status", status: "loading" });
    const module = (await import(
      /* @vite-ignore */ `${PYODIDE_BASE}pyodide.mjs`
    )) as {
      loadPyodide(options: { indexURL: string }): Promise<Pyodide>;
    };
    const py = await module.loadPyodide({ indexURL: PYODIDE_BASE });
    py.setStdout({
      batched: (text) => post({ type: "stdout", id: current, text }),
    });
    py.setStderr({
      batched: (text) => post({ type: "stderr", id: current, text }),
    });
    py.runPython("import os; os.environ['MPLBACKEND'] = 'AGG'");
    py.runPython(MLAB_MODULE);
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

// `imports` — paketlarni qaysi koddan aniqlash (AGR-01 "Tekshirish": talaba kodi dastur ichida satr bo'lib turadi).
async function run(id: number, code: string, imports = code): Promise<void> {
  current = id;
  try {
    const py = await boot();
    await py.loadPackagesFromImports(imports, quiet);
    if (/\bmlab\b/.test(imports)) await py.loadPackage(["pandas"], quiet);
    if (/^\s*(import|from)\s+seaborn\b/m.test(imports) && SEABORN_WHEEL) {
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
    post({
      type: "error",
      id,
      message: error instanceof Error ? error.message : String(error),
    });
  }
}

let queue: Promise<void> = Promise.resolve();
// NFR-02: laboratoriya ochilganda fonda tayyorlanish — talaba o'qib turganda Python va eng ko'p ishlatiladigan
// paketlar yuklanadi; birinchi katak tezroq ishlaydi. Xato bo'lsa jim — keyingi `run` qayta urinadi.
async function warmup(): Promise<void> {
  try {
    const py = await boot();
    await py.loadPackage(["numpy", "pandas"], quiet);
  } catch {
    booting = null;
  }
}

ctx.onmessage = (event) => {
  const message = event.data;
  if (message.type === "run")
    queue = queue.then(() => run(message.id, message.code, message.imports));
  else if (message.type === "warmup") queue = queue.then(warmup);
};
