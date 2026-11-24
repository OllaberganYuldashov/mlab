/**
 * "Tekshirish" (I3-04; AGR-01, LAB-07): ko'rinadigan testlar brauzerdagi Python'da (Pyodide worker).
 * Server sandbox runner'i (`sandbox/runner.py`) bilan bir xil shartnoma: talaba kodi yangi nomlar fazosida
 * bajariladi, keyin har `test_*(ns, params)` funksiyasi. Natija — taxminiy: yakuniy ball yashirin testlar
 * bilan serverda (AGR-05). Yashirin testlar bu yerga hech qachon kelmaydi.
 */
import type { Notebook } from "./notebook";
import type { PythonRuntime } from "./runtime";

export interface VisibleTest {
  step: string;
  source: string;
}

export interface TestOutcome {
  step: string;
  name: string;
  passed: boolean;
  message: string;
  ms: number;
}

export interface CheckResult {
  status: "ok" | "code_error" | "timeout" | "failed";
  error: string | null;
  stdout: string;
  tests: TestOutcome[];
}

/** Talaba kodi + testlar bajarilishiga chegara (paketlar yuklanishi bunga kirmaydi). */
export const CHECK_TIMEOUT_MS = 30_000;

/** Notebook'dagi kod kataklari tartib bilan (Markdown kataklari tashlanadi). */
export function notebookCode(nb: Notebook): string {
  return nb.cells
    .filter((c) => c.type === "code")
    .map((c) => c.source)
    .join("\n\n");
}

// `sandbox/runner.py` ning brauzer nusxasi (signal yo'q — vaqt chegarasi JS tomonida, worker qayta ochiladi).
const RUNNER = `
def _mlab_check(payload):
    import contextlib, io, json, time, traceback
    data = json.loads(payload)
    buf = io.StringIO()
    ns = {"__name__": "__main__"}
    res = {"status": "ok", "error": None, "stdout": "", "tests": []}
    def short(exc):
        return f"{type(exc).__name__}: {exc}".strip()[:500]
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            exec(compile(data["code"], "<talaba>", "exec"), ns)
        except BaseException as exc:
            frames = [f for f in traceback.extract_tb(exc.__traceback__) if f.filename == "<talaba>"]
            where = f" ({frames[-1].lineno}-qator)" if frames else ""
            res["status"] = "code_error"
            res["error"] = (short(exc) + where)[:500]
        for spec in data["tests"]:
            module = {"__name__": "mlab_test_" + spec["step"]}
            try:
                exec(compile(spec["source"], "<test:" + spec["step"] + ">", "exec"), module)
            except BaseException:
                res["tests"].append({"step": spec["step"], "name": "test fayli", "passed": False,
                    "message": "Test faylida xato (o'qituvchiga xabar bering)", "ms": 0})
                continue
            for name, func in list(module.items()):
                if not (name.startswith("test_") and callable(func)):
                    continue
                started = time.monotonic()
                passed, message = True, ""
                try:
                    if res["status"] == "code_error":
                        raise RuntimeError("kod xato bilan tugagan")
                    func(ns, data["params"])
                except AssertionError as exc:
                    passed, message = False, (str(exc) or "Natija kutilganidek emas")[:500]
                except BaseException as exc:
                    passed, message = False, short(exc)
                res["tests"].append({"step": spec["step"], "name": name, "passed": passed,
                    "message": message, "ms": int((time.monotonic() - started) * 1000)})
    res["stdout"] = buf.getvalue()[:64000]
    return json.dumps(res, ensure_ascii=False)
`;

/**
 * Python dasturi: ma'lumot JSON satr literali sifatida (JSON satr escape'lari Python satrida ham to'g'ri),
 * shuning uchun talaba kodi yoki test matni dastur tuzilishini buzolmaydi.
 */
export function checkProgram(
  code: string,
  tests: VisibleTest[],
  params: Record<string, unknown>,
): string {
  const payload = JSON.stringify({ code, tests, params });
  return `${RUNNER}\n_mlab_check(${JSON.stringify(payload)})\n`;
}

function failed(error: string): CheckResult {
  return { status: "failed", error, stdout: "", tests: [] };
}

export async function runCheck(
  runtime: PythonRuntime,
  code: string,
  tests: VisibleTest[],
  params: Record<string, unknown>,
  timeoutMs: number = CHECK_TIMEOUT_MS,
): Promise<CheckResult> {
  // 1) Python va kod import qilgan paketlar — vaqt chegarasisiz (birinchi marta uzoq bo'lishi mumkin).
  const prepared = await runtime.run("None", undefined, code);
  if (prepared.interrupted) return failed("interrupted");
  // 2) Talaba kodi va testlar — chegara bilan; oshsa worker qayta ochiladi (cheksiz sikl to'xtaydi).
  let timer: ReturnType<typeof setTimeout> | undefined;
  let timedOut = false;
  const run = runtime.run(checkProgram(code, tests, params), undefined, "");
  const guard = new Promise<void>((resolve) => {
    timer = setTimeout(() => {
      timedOut = true;
      runtime.restart();
      resolve();
    }, timeoutMs);
  });
  const result = await Promise.race([run, guard.then(() => run)]);
  clearTimeout(timer);
  if (timedOut)
    return { status: "timeout", error: null, stdout: "", tests: [] };
  if (!result.ok || result.result === null)
    return failed(result.error ?? "no result");
  try {
    return JSON.parse(result.result) as CheckResult;
  } catch {
    return failed("bad result");
  }
}
