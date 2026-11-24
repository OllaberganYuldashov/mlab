import { useEffect, useState } from "react";
import { t } from "../i18n";
import { type RunEvent, type RuntimeStatus, getRuntime } from "./runtime";

interface Output {
  events: RunEvent[];
  result: string | null;
  error: string | null;
}

/** CNT-02 "O'zing sinab ko'r": kod brauzerdagi Pyodide'da bajariladi (LAB-02, AGR-03). */
export default function RunnableCode({ code }: { code: string }) {
  const runtime = getRuntime();
  const [status, setStatus] = useState<RuntimeStatus>(runtime.status);
  const [running, setRunning] = useState(false);
  const [output, setOutput] = useState<Output | null>(null);

  useEffect(() => runtime.onStatus(setStatus), [runtime]);

  async function run() {
    setRunning(true);
    const events: RunEvent[] = [];
    setOutput({ events, result: null, error: null });
    const result = await runtime.run(code, (event) => {
      events.push(event);
      setOutput({ events: [...events], result: null, error: null });
    });
    setOutput({
      events: [...events],
      result: result.result,
      error: result.interrupted ? t("lab.interrupted") : result.error,
    });
    setRunning(false);
  }

  const text = output?.events
    .filter((e) => e.kind !== "figure")
    .map((e) => ("text" in e ? e.text : ""))
    .join("\n");
  return (
    <div className="runnable">
      <pre>
        <code>{code}</code>
      </pre>
      <button type="button" onClick={() => void run()} disabled={running}>
        {t("lab.run")}
      </button>
      {running && status === "loading" && <span role="status"> {t("lab.loading")}</span>}
      {running && status !== "loading" && <span role="status"> {t("lab.running")}</span>}
      {output && (
        <div className="output" aria-live="polite" data-testid="run-output">
          {text && <pre>{text}</pre>}
          {output.events
            .filter((e): e is { kind: "figure"; png: string } => e.kind === "figure")
            .map((e, i) => (
              <img key={i} src={`data:image/png;base64,${e.png}`} alt={t("lab.figure", { n: i + 1 })} />
            ))}
          {output.result !== null && <pre className="result">{output.result}</pre>}
          {output.error && (
            <pre role="alert" className="error">
              {output.error}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
