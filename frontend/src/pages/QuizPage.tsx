import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { t } from "../i18n";
import { Link } from "../Link";
import { formatLeft } from "../time";

interface QuizQuestion {
  position: number;
  text: string;
  options: string[];
  chosen?: number | null;
  answer?: number;
  correct?: boolean;
}

interface Attempt {
  id: number;
  number: number;
  deadline: string;
  server_time: string;
  submitted_at: string | null;
  score: number | null;
  max_score: number;
  questions: QuizQuestion[];
}

interface Summary {
  settings: { questions: number; minutes: number; attempts: number };
  available_questions: number;
  used_attempts: number;
  active_attempt: number | null;
  attempts: { id: number; number: number; score: number | null; max_score: number; submitted_at: string | null }[];
}

const LETTERS = "ABCDEF";

function refusal(data: unknown): string {
  const code = (data as { code?: string } | null)?.code;
  if (code === "no_attempts") return t("quiz.noAttempts");
  if (code === "no_questions") return t("quiz.noQuestions");
  if (code === "time_over") return t("quiz.timeOver");
  return t("common.unexpectedError");
}

/** CNT-06: mavzu testi — boshlash, taymer (server vaqti bilan), topshirish, natija. */
export default function QuizPage({ code }: { code: string }) {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [now, setNow] = useState(() => Date.now());
  const submitting = useRef(false);

  const showAttempt = useCallback((data: Attempt) => {
    // Yangi ochiq urinish — yana topshirish mumkin; topshirilgan bo'lsa qayta yuborilmaydi.
    submitting.current = data.submitted_at !== null;
    setAttempt(data);
    setOffset(new Date(data.server_time).getTime() - Date.now());
    const chosen: Record<number, number> = {};
    for (const q of data.questions) if (q.chosen != null) chosen[q.position] = q.chosen;
    setAnswers(chosen);
  }, []);

  const loadSummary = useCallback(async () => {
    const result = await api<Summary>(`/api/course/topics/${code}/quiz`);
    if (!result.ok) {
      setError(result.status === 403 ? t("topics.noAccess") : t("common.unexpectedError"));
      return null;
    }
    setSummary(result.data);
    return result.data;
  }, [code]);

  useEffect(() => {
    let active = true;
    void (async () => {
      const data = await loadSummary();
      if (!active || !data?.active_attempt) return;
      const open = await api<Attempt>(`/api/course/quiz/attempts/${data.active_attempt}`);
      if (active && open.ok) showAttempt(open.data);
    })();
    return () => {
      active = false;
    };
  }, [loadSummary, showAttempt]);

  async function start() {
    setError(null);
    const result = await api<Attempt>(`/api/course/topics/${code}/quiz/attempts`, { method: "POST" });
    if (result.ok) showAttempt(result.data);
    else setError(refusal(result.data));
  }

  const submit = useCallback(async () => {
    if (!attempt || submitting.current) return;
    submitting.current = true;
    setError(null);
    const result = await api<Attempt>(`/api/course/quiz/attempts/${attempt.id}/submit`, {
      method: "POST",
      body: { answers },
    });
    if (result.ok) showAttempt(result.data);
    else {
      setError(refusal(result.data));
      setAttempt(null);
      submitting.current = false;
    }
    await loadSummary();
  }, [attempt, answers, showAttempt, loadSummary]);

  const open = attempt !== null && attempt.submitted_at === null;
  const left = open ? new Date(attempt.deadline).getTime() - (now + offset) : 0;

  // Har soniya taymer; vaqt tugasa — avtomatik topshirish (server 30 s imtiyoz beradi).
  const submitRef = useRef(submit);
  const deadlineRef = useRef<number | null>(null);
  const offsetRef = useRef(0);
  useEffect(() => {
    submitRef.current = submit;
    deadlineRef.current = open ? new Date(attempt.deadline).getTime() : null;
    offsetRef.current = offset;
  }, [submit, open, attempt, offset]);
  useEffect(() => {
    if (!open) return;
    const id = setInterval(() => {
      const current = Date.now();
      setNow(current);
      const deadline = deadlineRef.current;
      if (deadline !== null && current + offsetRef.current >= deadline) void submitRef.current();
    }, 1000);
    return () => clearInterval(id);
  }, [open]);

  return (
    <main className="app">
      <p className="links">
        <Link to={`/topics/${code}`}>{t("quiz.backToLecture")}</Link>
        <Link to="/topics">{t("topics.back")}</Link>
      </p>
      <h1>{t("quiz.title", { code })}</h1>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {!summary && !error && <p role="status">{t("common.loading")}</p>}

      {open && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          <p className="timer" aria-live="off">
            {t("quiz.left", { time: formatLeft(left) })}
          </p>
          {attempt.questions.map((q) => (
            <fieldset key={q.position} className="quick-question">
              <legend>
                {q.position}. {q.text}
              </legend>
              {q.options.map((option, i) => (
                <label key={i} className="option">
                  <input
                    type="radio"
                    name={`q-${q.position}`}
                    checked={answers[q.position] === i}
                    onChange={() => setAnswers((prev) => ({ ...prev, [q.position]: i }))}
                  />{" "}
                  {LETTERS[i]}) {option}
                </label>
              ))}
            </fieldset>
          ))}
          <p className="muted">
            {t("quiz.answered", { n: Object.keys(answers).length, total: attempt.questions.length })}
          </p>
          <button type="submit">{t("quiz.submit")}</button>
        </form>
      )}

      {attempt && attempt.submitted_at !== null && (
        <section aria-labelledby="quiz-result">
          <h2 id="quiz-result" role="status">
            {t("quiz.result", { score: attempt.score ?? 0, max: attempt.max_score })}
          </h2>
          <ol>
            {attempt.questions.map((q) => (
              <li key={q.position} className={q.correct ? "ok" : "error"}>
                {q.text} — {q.correct ? t("quiz.right") : t("quiz.wrong")}{" "}
                {!q.correct && q.answer !== undefined && t("quiz.rightAnswer", { answer: q.options[q.answer] ?? "" })}
              </li>
            ))}
          </ol>
        </section>
      )}

      {summary && !open && (
        <section aria-labelledby="quiz-info">
          <h2 id="quiz-info">{t("quiz.info")}</h2>
          <p>
            {t("quiz.settings", {
              questions: Math.min(summary.settings.questions, summary.available_questions),
              minutes: summary.settings.minutes,
            })}
          </p>
          <p>{t("quiz.attempts", { used: summary.used_attempts, total: summary.settings.attempts })}</p>
          {summary.attempts.some((a) => a.score !== null) && (
            <ul>
              {summary.attempts
                .filter((a) => a.score !== null)
                .map((a) => (
                  <li key={a.id}>{t("quiz.past", { n: a.number, score: a.score ?? 0, max: a.max_score })}</li>
                ))}
            </ul>
          )}
          {summary.used_attempts < summary.settings.attempts && summary.available_questions > 0 && (
            <button type="button" onClick={() => void start()}>
              {summary.used_attempts === 0 ? t("quiz.start") : t("quiz.retry")}
            </button>
          )}
        </section>
      )}
    </main>
  );
}
