import { useCallback, useEffect, useRef, useState } from "react";
import { t } from "../i18n";
import { Markdown } from "../Markdown.view";
import CodeEditor from "./CodeEditor";
import {
  type Cell,
  type CellType,
  MAX_CELLS,
  type Notebook as NotebookState,
  addCell,
  moveCell,
  removeCell,
  setSource,
} from "./notebook";
import { type RunEvent, getRuntime } from "./runtime";

interface CellOutput {
  count: number | null; // bajarilish tartibi; null — navbatda/bajarilmoqda
  events: RunEvent[];
  result: string | null;
  error: string | null;
}

/** Chiqish 1 MB dan oshsa qisqartiriladi (ADR-0006: xotira byudjeti). */
const MAX_OUTPUT_CHARS = 1_000_000;

function OutputView({ output }: { output: CellOutput }) {
  let text = output.events
    .filter((e): e is { kind: "stdout" | "stderr"; text: string } => e.kind !== "figure")
    .map((e) => e.text)
    .join("\n");
  if (text.length > MAX_OUTPUT_CHARS) text = `${text.slice(0, MAX_OUTPUT_CHARS)}\n${t("lab.truncated")}`;
  return (
    <div className="output" aria-live="polite" data-testid="cell-output">
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
  );
}

/** Bajarilish tartib raqami (Jupyter'dagi [n]). */
function nextCount(ref: { current: number }): number {
  ref.current += 1;
  return ref.current;
}

interface Props {
  initial: NotebookState;
  onChange?: (notebook: NotebookState) => void;
  /** Katak ishga tushirilganda (LAB-05: har ishga tushirishda saqlash). */
  onRun?: (notebook: NotebookState) => void;
}

/** LAB-01: notebook — kod va matn kataklari, ▶ va Shift+Enter, chiqish va grafiklar. */
export default function Notebook({ initial, onChange, onRun }: Props) {
  const runtime = getRuntime();
  const [notebook, setNotebook] = useState(initial);
  const [outputs, setOutputs] = useState<Record<string, CellOutput>>({});
  const [editing, setEditing] = useState<Record<string, boolean>>({});
  const [running, setRunning] = useState(0);
  const counter = useRef(0);
  const current = useRef(notebook);

  const update = useCallback(
    (next: NotebookState) => {
      current.current = next;
      setNotebook(next);
      onChange?.(next);
    },
    [onChange],
  );

  useEffect(() => {
    current.current = notebook;
  }, [notebook]);

  async function runCell(id: string) {
    const cell = current.current.cells.find((c) => c.id === id);
    if (!cell) return;
    if (cell.type === "markdown") {
      setEditing((e) => ({ ...e, [id]: false }));
      return;
    }
    onRun?.(current.current);
    setRunning((n) => n + 1);
    const events: RunEvent[] = [];
    setOutputs((o) => ({ ...o, [id]: { count: null, events: [], result: null, error: null } }));
    const result = await runtime.run(cell.source, (event) => {
      events.push(event);
      setOutputs((o) => ({ ...o, [id]: { count: null, events: [...events], result: null, error: null } }));
    });
    const count = nextCount(counter);
    setOutputs((o) => ({
      ...o,
      [id]: {
        count,
        events: [...events],
        result: result.result,
        error: result.interrupted ? t("lab.interrupted") : result.error,
      },
    }));
    setRunning((n) => n - 1);
  }

  function add(index: number, type: CellType) {
    const next = addCell(current.current, index, type);
    const added = next.cells[index + 1];
    if (added && type === "markdown") setEditing((e) => ({ ...e, [added.id]: true }));
    update(next);
  }

  const renderCell = (cell: Cell, index: number) => {
    const output = outputs[cell.id];
    const isMarkdownView = cell.type === "markdown" && !editing[cell.id] && cell.source.trim() !== "";
    const label = t(cell.type === "code" ? "lab.cell.code" : "lab.cell.markdown", { n: index + 1 });
    return (
      <section key={cell.id} className={`cell cell-${cell.type}`} aria-label={label}>
        <div className="cell-toolbar">
          <span className="cell-count" aria-hidden="true">
            {cell.type === "code" ? `[${output ? (output.count ?? "*") : " "}]` : "¶"}
          </span>
          {cell.type === "code" && (
            <button type="button" onClick={() => void runCell(cell.id)} aria-label={t("lab.cell.run", { n: index + 1 })}>
              ▶
            </button>
          )}
          {isMarkdownView && (
            <button type="button" onClick={() => setEditing((e) => ({ ...e, [cell.id]: true }))}>
              {t("lab.cell.edit")}
            </button>
          )}
          <button
            type="button"
            onClick={() => update(moveCell(current.current, index, -1))}
            disabled={index === 0}
            aria-label={t("lab.cell.up", { n: index + 1 })}
          >
            ↑
          </button>
          <button
            type="button"
            onClick={() => update(moveCell(current.current, index, 1))}
            disabled={index === notebook.cells.length - 1}
            aria-label={t("lab.cell.down", { n: index + 1 })}
          >
            ↓
          </button>
          <button
            type="button"
            onClick={() => update(removeCell(current.current, index))}
            disabled={notebook.cells.length <= 1}
            aria-label={t("lab.cell.delete", { n: index + 1 })}
          >
            ✕
          </button>
        </div>
        {isMarkdownView ? (
          <div className="markdown-view">
            <Markdown text={cell.source} />
          </div>
        ) : (
          <CodeEditor
            value={cell.source}
            language={cell.type === "code" ? "python" : "markdown"}
            label={label}
            onChange={(source) => update(setSource(current.current, cell.id, source))}
            onRun={() => void runCell(cell.id)}
          />
        )}
        {output && <OutputView output={output} />}
        <div className="cell-add">
          <button type="button" onClick={() => add(index, "code")} disabled={notebook.cells.length >= MAX_CELLS}>
            {t("lab.cell.addCode")}
          </button>
          <button type="button" onClick={() => add(index, "markdown")} disabled={notebook.cells.length >= MAX_CELLS}>
            {t("lab.cell.addMarkdown")}
          </button>
        </div>
      </section>
    );
  };

  return (
    <div className="notebook">
      <div className="notebook-bar">
        {running > 0 && (
          <button type="button" className="secondary" onClick={() => runtime.restart()}>
            {t("lab.stop")}
          </button>
        )}
        <span className="muted">{t("lab.hint")}</span>
      </div>
      {notebook.cells.map(renderCell)}
    </div>
  );
}
