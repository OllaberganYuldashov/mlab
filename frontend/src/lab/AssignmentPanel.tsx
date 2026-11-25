/**
 * Topshiriq paneli (I3-04; AGR-01, LAB-07): shart (talaba varianti bilan), qadamlar va "Tekshirish".
 * Tekshirish ko'rinadigan testlarni brauzerda ishga tushiradi; yakuniy ball — "Topshirish" (I3-07..09).
 */
import { useEffect, useState } from "react";
import { api } from "../api";
import { t } from "../i18n";
import { Markdown } from "../Markdown.view";
import {
  CHECK_TIMEOUT_MS,
  type CheckResult,
  notebookCode,
  runCheck,
  type VisibleTest,
} from "./checker";
import type { Notebook } from "./notebook";
import { getRuntime } from "./runtime";
import SubmitPanel from "./SubmitPanel";

type Level = "basic" | "medium" | "advanced";

export interface Assignment {
  code: string;
  title: string;
  level: Level;
  statement: string;
  params: Record<string, unknown>;
  steps: {
    key: string;
    title: string;
    points: number;
    visible_test: string | null;
  }[];
}

type State =
  | { kind: "loading" }
  | { kind: "none" }
  | { kind: "error" }
  | { kind: "ready"; assignment: Assignment };

function CheckOutput({ result }: { result: CheckResult }) {
  if (result.status === "timeout")
    return (
      <p role="alert" className="error">
        {t("lab.check.timeout", { seconds: CHECK_TIMEOUT_MS / 1000 })}
      </p>
    );
  if (result.status === "failed")
    return (
      <p role="alert" className="error">
        {t("lab.check.failed")}
      </p>
    );
  const passed = result.tests.filter((x) => x.passed).length;
  return (
    <div className="check-result">
      {result.error && (
        <p role="alert" className="error">
          {t("lab.check.codeError", { error: result.error })}
        </p>
      )}
      <p role="status">
        {t("lab.check.summary", { passed, total: result.tests.length })}
      </p>
      <ul className="check-tests">
        {result.tests.map((test, i) => (
          <li key={i} className={test.passed ? "ok" : "error"}>
            <span
              aria-label={t(
                test.passed ? "lab.check.passed" : "lab.check.notPassed",
              )}
            >
              {test.passed ? "✓" : "✗"}
            </span>{" "}
            <code>{test.name}</code>
            {test.message && <> — {test.message}</>}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function AssignmentPanel({
  code,
  getNotebook,
}: {
  code: string;
  getNotebook: () => Notebook;
}) {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<CheckResult | null>(null);

  useEffect(() => {
    let active = true;
    void api<Assignment>(`/api/labs/${code}/assignment`).then((res) => {
      if (!active) return;
      if (res.ok) setState({ kind: "ready", assignment: res.data });
      else setState({ kind: res.status === 404 ? "none" : "error" });
    });
    return () => {
      active = false;
    };
  }, [code]);

  if (state.kind === "loading")
    return <p role="status">{t("common.loading")}</p>;
  if (state.kind === "none") return <p>{t("lab.task.placeholder")}</p>;
  if (state.kind === "error")
    return (
      <p role="alert" className="error">
        {t("common.unexpectedError")}
      </p>
    );

  const { assignment } = state;
  const tests: VisibleTest[] = assignment.steps.flatMap((s) =>
    s.visible_test === null ? [] : [{ step: s.key, source: s.visible_test }],
  );

  async function check() {
    setChecking(true);
    setResult(null);
    try {
      setResult(
        await runCheck(
          getRuntime(),
          notebookCode(getNotebook()),
          tests,
          assignment.params,
        ),
      );
    } finally {
      setChecking(false);
    }
  }

  return (
    <>
      <h3>
        {assignment.code}. {assignment.title}
      </h3>
      <p className="badge">
        {t("lab.task.level", { level: t(`lab.level.${assignment.level}`) })}
      </p>
      <Markdown text={assignment.statement} />
      {Object.keys(assignment.params).length > 0 && (
        <details className="task-params">
          <summary>{t("lab.task.params")}</summary>
          <dl>
            {Object.entries(assignment.params).map(([name, value]) => (
              <div key={name}>
                <dt>
                  <code>{name}</code>
                </dt>
                <dd>
                  {typeof value === "string" ? value : JSON.stringify(value)}
                </dd>
              </div>
            ))}
          </dl>
        </details>
      )}
      <ol className="task-steps">
        {assignment.steps.map((s) => (
          <li key={s.key}>
            {s.title} — {t("lab.task.points", { points: s.points })}
          </li>
        ))}
      </ol>
      {tests.length === 0 ? (
        <p className="muted">{t("lab.check.none")}</p>
      ) : (
        <>
          <button
            type="button"
            disabled={checking}
            onClick={() => void check()}
          >
            {t("lab.check.button")}
          </button>
          <p className="muted">{t("lab.check.note")}</p>
          {checking && <p role="status">{t("lab.check.running")}</p>}
          {result && <CheckOutput result={result} />}
        </>
      )}
      <SubmitPanel code={code} getCode={() => notebookCode(getNotebook())} />
    </>
  );
}
