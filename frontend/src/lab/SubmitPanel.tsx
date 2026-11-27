/**
 * "Topshirish" paneli (I3-09; AGR-02, AGR-04, AGR-05, AGR-06): kod serverga, navbatdagi o'rin va holat real vaqtda,
 * natija qadamlar bo'yicha (yashirin testlar faqat "yashirin test N"), urinishlar tarixi va eng yuqori ball.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { showTime } from "../datetime";
import { t } from "../i18n";
import {
  answerQuestions,
  getSubmission,
  isOpen,
  listSubmissions,
  type Submission,
  submitCode,
  watchSubmission,
} from "./submissions";

function StatusLine({ submission }: { submission: Submission }) {
  switch (submission.status) {
    case "queued":
      return (
        <p role="status">
          {t("lab.submit.queued", { position: submission.position })}
        </p>
      );
    case "running":
      return <p role="status">{t("lab.submit.running")}</p>;
    case "error":
      return (
        <p role="alert" className="error">
          {t("lab.submit.error")}
        </p>
      );
    case "done":
      return (
        <p role="status" className="submit-score">
          {t("lab.submit.score", { score: submission.final_score ?? "0" })}
          {submission.policy === "late" && <> {t("lab.submit.late")}</>}
          {submission.policy === "practice" && <> {t("lab.submit.practice")}</>}
        </p>
      );
  }
}

/** INT-02: topshirgandan keyin 2 ta savol; javob berilmaguncha ball rasmiy emas. */
function Questions({
  submission,
  onAnswered,
}: {
  submission: Submission;
  onAnswered: (s: Submission) => void;
}) {
  const questions = submission.questions ?? [];
  const [chosen, setChosen] = useState<(number | null)[]>(() =>
    questions.map(() => null),
  );
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const ready = chosen.every((c) => c !== null);

  async function send() {
    setSending(true);
    setError(null);
    const res = await answerQuestions(submission.id, chosen as number[]);
    setSending(false);
    if (res.ok) onAnswered({ ...submission, ...res.data, questions: null });
    else setError(t("common.unexpectedError"));
  }

  return (
    <form
      className="understanding"
      aria-label={t("lab.understanding.title")}
      onSubmit={(e) => {
        e.preventDefault();
        void send();
      }}
    >
      <h4>{t("lab.understanding.title")}</h4>
      <p className="muted">{t("lab.understanding.note")}</p>
      {questions.map((q, i) => (
        <fieldset key={i}>
          <legend>{q.text}</legend>
          {q.options.map((option, j) => (
            <label key={j}>
              <input
                type="radio"
                name={`q${submission.id}-${i}`}
                checked={chosen[i] === j}
                onChange={() =>
                  setChosen((c) => c.map((v, k) => (k === i ? j : v)))
                }
              />{" "}
              {option}
            </label>
          ))}
        </fieldset>
      ))}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <button type="submit" disabled={!ready || sending}>
        {t("lab.understanding.send")}
      </button>
    </form>
  );
}

function ResultView({ submission }: { submission: Submission }) {
  const result = submission.result;
  if (!result) return null;
  return (
    <div className="submit-result">
      {result.code_error && (
        <p role="alert" className="error">
          {t("lab.check.codeError", { error: result.code_error })}
        </p>
      )}
      <ol className="result-steps">
        {result.steps.map((step) => (
          <li key={step.key}>
            <strong>{step.title}</strong> —{" "}
            {t("lab.submit.stepScore", {
              score: step.score,
              points: step.points,
              passed: step.passed,
              total: step.total,
            })}
            <ul className="check-tests">
              {step.tests.map((test, i) => (
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
          </li>
        ))}
      </ol>
    </div>
  );
}

export default function SubmitPanel({
  code,
  getCode,
  onGraded,
}: {
  code: string;
  getCode: () => string;
  /** Urinish baholandi (masalan, challenge ochilgan bo'lishi mumkin — ADP-03). */
  onGraded?: () => void;
}) {
  const [history, setHistory] = useState<Submission[]>([]);
  const [best, setBest] = useState<string | null>(null);
  const [current, setCurrent] = useState<Submission | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const stopWatch = useRef<(() => void) | null>(null);
  const graded = useRef(onGraded);
  useEffect(() => {
    graded.current = onGraded;
  }, [onGraded]);

  const reload = useCallback(async () => {
    const res = await listSubmissions(code);
    if (!res.ok) return;
    setHistory(res.data.submissions);
    setBest(res.data.best_final_score);
  }, [code]);

  const watch = useCallback(
    (id: number) => {
      stopWatch.current?.();
      stopWatch.current = watchSubmission(id, (s) => {
        setCurrent(s);
        if (!isOpen(s)) void reload();
        if (s.status === "done") graded.current?.();
      });
    },
    [reload],
  );

  // Sahifa ochilganda (yoki qayta ulanishda): tarix va ochiq urinish bo'lsa — kuzatish (AGR-04).
  useEffect(() => {
    let active = true;
    void listSubmissions(code).then((res) => {
      if (!active || !res.ok) return;
      setHistory(res.data.submissions);
      setBest(res.data.best_final_score);
      const open = res.data.submissions.find(isOpen);
      if (open) {
        setCurrent(open);
        watch(open.id);
        return;
      }
      // INT-02: javob berilmagan urinish — savollar bilan qaytariladi (sahifa yangilansa ham).
      const unanswered = res.data.submissions.find(
        (s) => s.understanding === "pending",
      );
      if (unanswered)
        void getSubmission(unanswered.id).then((detail) => {
          if (active && detail.ok) setCurrent(detail.data);
        });
    });
    return () => {
      active = false;
      stopWatch.current?.();
    };
  }, [code, watch]);

  async function submit() {
    const source = getCode();
    if (!source.trim()) {
      setMessage(t("lab.submit.empty"));
      return;
    }
    setSending(true);
    setMessage(null);
    try {
      const res = await submitCode(code, source);
      if (res.ok) {
        setCurrent(res.data);
        setHistory((h) => [res.data, ...h]);
        watch(res.data.id);
        return;
      }
      const reason = (res.data as { code?: string } | null)?.code;
      setMessage(
        reason === "submission_pending"
          ? t("lab.submit.pending")
          : reason === "lab_closed"
            ? t("save.closed")
            : res.status === 429
              ? t("lab.submit.tooMany")
              : t("common.unexpectedError"),
      );
    } finally {
      setSending(false);
    }
  }

  const busy = sending || (current !== null && isOpen(current));
  return (
    <section className="submit-panel" aria-label={t("lab.submit.title")}>
      <button type="button" disabled={busy} onClick={() => void submit()}>
        {t("lab.submit.button")}
      </button>
      <p className="muted">{t("lab.submit.note")}</p>
      {message && (
        <p role="alert" className="error">
          {message}
        </p>
      )}
      {current && <StatusLine submission={current} />}
      {current && <ResultView submission={current} />}
      {current?.status === "done" &&
        current.understanding === "pending" &&
        current.questions && (
          <Questions
            key={current.id}
            submission={current}
            onAnswered={(s) => {
              setCurrent(s);
              void reload();
              graded.current?.();
            }}
          />
        )}
      {current?.understanding === "passed" && (
        <p role="status">{t("lab.understanding.passed")}</p>
      )}
      {current?.understanding === "failed" && (
        <p role="alert" className="error">
          {t("lab.understanding.failed")}
        </p>
      )}
      {best !== null && (
        <p className="badge">{t("lab.submit.best", { score: best })}</p>
      )}
      {history.length > 0 && (
        <details className="submit-history">
          <summary>
            {t("lab.submit.history", { count: history.length })}
          </summary>
          <ul>
            {history.map((s) => (
              <li key={s.id}>
                {showTime(s.created_at)} —{" "}
                {s.status === "done"
                  ? t("lab.submit.historyScore", {
                      score: s.final_score ?? "0",
                    })
                  : t(`lab.submit.state.${s.status}`)}
                {s.policy === "practice" && <> {t("lab.submit.practice")}</>}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
