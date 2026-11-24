import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { t } from "../i18n";
import RunnableCode from "../lab/RunnableCode";
import { Link } from "../Link";
import VisualBlock from "../visual/VisualBlock";
import type { CodeBlockInfo } from "../markdown";
import { Markdown } from "../Markdown.view";

interface QuickQuestion {
  question: string;
  options: string[];
  answer: number;
  explain: string;
}

interface Step {
  order: number;
  title: string;
  body: string;
  question: QuickQuestion | null;
}

interface Lecture {
  topic: { code: string; title: string };
  title: string;
  prev: string | null;
  next: string | null;
  steps: Step[];
}

const LETTERS = "ABCDEF";

function TryBlock({ info }: { info: CodeBlockInfo }) {
  if (info.language === "visual") return <VisualBlock source={info.code} />;
  if (!info.tryable) {
    return (
      <pre>
        <code>{info.code}</code>
      </pre>
    );
  }
  return (
    <figure className="try-block">
      <figcaption>{t("lecture.try")}</figcaption>
      <RunnableCode code={info.code} />
    </figure>
  );
}

/** CNT-02 tezkor savol: baholanmaydi, javob darhol tekshiriladi. */
function QuickQuestionBox({ question, name }: { question: QuickQuestion; name: string }) {
  const [chosen, setChosen] = useState<number | null>(null);
  const [checked, setChecked] = useState(false);
  const correct = chosen === question.answer;
  return (
    <fieldset className="quick-question">
      <legend>{question.question}</legend>
      {question.options.map((option, i) => (
        <label key={option} className="option">
          <input
            type="radio"
            name={name}
            checked={chosen === i}
            onChange={() => {
              setChosen(i);
              setChecked(false);
            }}
          />{" "}
          {LETTERS[i]}) {option}
        </label>
      ))}
      <button type="button" disabled={chosen === null} onClick={() => setChecked(true)}>
        {t("lecture.check")}
      </button>
      {checked && (
        <p role="status" className={correct ? "ok" : "error"}>
          {correct
            ? t("lecture.correct")
            : t("lecture.wrong", { answer: `${LETTERS[question.answer]}) ${question.options[question.answer]}` })}
          {question.explain && ` ${question.explain}`}
        </p>
      )}
    </fieldset>
  );
}

/** CNT-02: ma'ruza qadamlari — oldingi/keyingi qadam, rasm, "O'zing sinab ko'r", tezkor savol. */
export default function LecturePage({ code }: { code: string }) {
  const [lecture, setLecture] = useState<Lecture | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [index, setIndex] = useState(0);
  const heading = useRef<HTMLHeadingElement>(null);
  const moved = useRef(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      const result = await api<Lecture>(`/api/course/topics/${encodeURIComponent(code)}/lecture`);
      if (!active) return;
      setIndex(0);
      if (result.ok) {
        setLecture(result.data);
        setError(null);
      } else {
        setLecture(null);
        setError(
          result.status === 404
            ? t("lecture.notFound")
            : result.status === 403
              ? t("topics.noAccess")
              : t("common.unexpectedError"),
        );
      }
    })();
    return () => {
      active = false;
    };
  }, [code]);

  // Qadam almashganda fokus sarlavhaga — ekran o'quvchi yangi qadamni o'qiydi (NFR-13).
  useEffect(() => {
    if (moved.current) heading.current?.focus();
  }, [index]);

  if (error) {
    return (
      <main className="app">
        <p role="alert" className="error">
          {error}
        </p>
        <p className="links">
          <Link to="/topics">{t("topics.back")}</Link>
        </p>
      </main>
    );
  }
  if (!lecture) {
    return (
      <main className="app">
        <p role="status">{t("common.loading")}</p>
      </main>
    );
  }
  const step = lecture.steps[index];
  const total = lecture.steps.length;
  const go = (next: number) => {
    moved.current = true;
    setIndex(next);
  };

  return (
    <main className="app lecture">
      <p className="links">
        <Link to="/topics">{t("topics.back")}</Link>
      </p>
      <h1>
        {lecture.topic.code}. {lecture.title}
      </h1>
      <p className="muted" aria-live="polite">
        {t("lecture.progress", { n: index + 1, total })}
      </p>
      {step && (
        <article aria-labelledby="step-title">
          <h2 id="step-title" tabIndex={-1} ref={heading}>
            {step.title}
          </h2>
          <Markdown text={step.body} renderCode={(info) => <TryBlock info={info} />} />
          {step.question && (
            <QuickQuestionBox key={step.order} question={step.question} name={`q-${step.order}`} />
          )}
        </article>
      )}
      <nav className="step-nav" aria-label={t("lecture.nav")}>
        <button type="button" disabled={index === 0} onClick={() => go(index - 1)}>
          {t("lecture.prev")}
        </button>
        {index < total - 1 ? (
          <button type="button" onClick={() => go(index + 1)}>
            {t("lecture.next")}
          </button>
        ) : lecture.next ? (
          <Link to={`/topics/${lecture.next}`}>{t("lecture.nextTopic", { code: lecture.next })}</Link>
        ) : (
          <span className="muted">{t("lecture.end")}</span>
        )}
      </nav>
    </main>
  );
}
