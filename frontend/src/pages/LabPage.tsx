import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { showTime } from "../datetime";
import { t } from "../i18n";
import { Autosave, SAVE_INTERVAL_MS, type SaveStatus } from "../lab/autosave";
import Notebook from "../lab/Notebook";
import { pasteAllowed, reportPaste } from "../lab/paste";
import { getRuntime } from "../lab/runtime";
import { type Notebook as NotebookState, emptyNotebook } from "../lab/notebook";
import { Link } from "../Link";
import type { LabState } from "./TopicsPage";

type Policy = "on_time" | "late" | "practice" | "closed";

interface Work {
  version: number;
  notebook: NotebookState | null;
  saved_at: string | null;
  policy: Policy;
  paste_limit: number;
  proctored: boolean;
}

interface TopicBrief {
  code: string;
  title: string;
  lab: LabState | null;
}

interface Loaded {
  work: Work;
  topic: TopicBrief | undefined;
  notebook: NotebookState;
  version: number;
  dirty: boolean;
}

function SaveIndicator({
  status,
  onResolve,
}: {
  status: SaveStatus;
  onResolve: (keepMine: boolean) => void;
}) {
  switch (status.kind) {
    case "idle":
      return null;
    case "saving":
      return <span className="muted">{t("save.saving")}</span>;
    case "saved":
      return (
        <span className="muted">
          {t("save.saved", { time: showTime(status.at) })}
        </span>
      );
    case "offline":
      return (
        <span role="status" className="error">
          {t("save.offline")}
        </span>
      );
    case "closed":
      return (
        <span role="alert" className="error">
          {t("save.closed")}
        </span>
      );
    case "error":
      return (
        <span role="alert" className="error">
          {t("save.error")}
        </span>
      );
    case "conflict":
      return (
        <span role="alert" className="error">
          {t("save.conflict")}{" "}
          <button type="button" onClick={() => onResolve(true)}>
            {t("save.keepMine")}
          </button>{" "}
          <button type="button" onClick={() => onResolve(false)}>
            {t("save.useServer")}
          </button>
        </span>
      );
  }
}

/**
 * LAB-07: laboratoriya sahifasi — chapda topshiriq sharti va qadamlar, o'rtada notebook, o'ngda AI tutor joyi (I4).
 * Oyna yopiq bo'lsa (ACC-02/05) — notebook emas, keyingi ochilish vaqti. Topshiriq formati (assignment.yaml) — I3.
 */
export default function LabPage({ code }: { code: string }) {
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      const [work, topics] = await Promise.all([
        api<Work>(`/api/labs/${code}/work`),
        api<{ topics: TopicBrief[] }>("/api/course/topics"),
      ]);
      if (!active) return;
      if (!work.ok) {
        setError(
          work.status === 404
            ? t("lecture.notFound")
            : work.status === 403
              ? t("topics.noAccess")
              : t("common.unexpectedError"),
        );
        return;
      }
      const start = Autosave.initial(code, work.data, emptyNotebook());
      setLoaded({
        work: work.data,
        topic: topics.ok
          ? topics.data.topics.find((x) => x.code === code)
          : undefined,
        ...start,
      });
    })();
    return () => {
      active = false;
    };
  }, [code]);

  // LAB-05: avtosaqlash — har 10 s (o'zgarish bo'lsa), har ishga tushirishda, tarmoq qaytganda, sahifadan chiqishda.
  const [status, setStatus] = useState<SaveStatus>({ kind: "idle" });
  const [notebookKey, setNotebookKey] = useState(0);
  const [shown, setShown] = useState<NotebookState | null>(null);
  const saver = useRef<Autosave | null>(null);
  const canSave = loaded !== null && loaded.work.policy !== "closed";
  // NFR-02: laboratoriya ochiq bo'lsa Python fonda tayyorlanadi.
  useEffect(() => {
    if (canSave) getRuntime().warmup();
  }, [canSave]);

  useEffect(() => {
    if (!loaded || !canSave) return;
    const autosave = new Autosave(code, loaded, setStatus);
    saver.current = autosave;
    const flush = () => void autosave.flush();
    const hidden = () => {
      if (document.visibilityState === "hidden") flush();
    };
    const timer = setInterval(() => autosave.tick(), SAVE_INTERVAL_MS);
    window.addEventListener("online", flush);
    document.addEventListener("visibilitychange", hidden);
    if (loaded.dirty) flush();
    return () => {
      clearInterval(timer);
      window.removeEventListener("online", flush);
      document.removeEventListener("visibilitychange", hidden);
      autosave.stop();
      saver.current = null;
    };
  }, [code, loaded, canSave]);

  // INT-01, ACC-09: har paste qayd qilinadi; chegaradan katta yoki nazorat rejimida — rad.
  const [pasteBlocked, setPasteBlocked] = useState<string | null>(null);
  const onPaste = useCallback(
    (cell: string, size: number) => {
      if (!loaded) return true;
      reportPaste(code, cell, size);
      const rules = {
        limit: loaded.work.paste_limit,
        proctored: loaded.work.proctored,
      };
      const allowed = pasteAllowed(size, rules);
      setPasteBlocked(
        allowed
          ? null
          : rules.proctored
            ? t("lab.paste.proctored")
            : t("lab.paste.tooLarge", { limit: rules.limit, size }),
      );
      return allowed;
    },
    [code, loaded],
  );

  function resolve(keepMine: boolean) {
    if (status.kind !== "conflict" || !saver.current) return;
    const notebook = saver.current.resolve(
      keepMine,
      status.serverVersion,
      status.serverNotebook,
    );
    if (!keepMine) {
      setShown(notebook);
      setNotebookKey((k) => k + 1);
    }
  }

  const title = loaded?.topic ? `${code}. ${loaded.topic.title}` : code;
  const policy = loaded?.work.policy;
  const lab = loaded?.topic?.lab;
  return (
    <main className="app lab">
      <p className="links">
        <Link to={`/topics/${code}`}>{t("quiz.backToLecture")}</Link>
        <Link to="/topics">{t("topics.back")}</Link>
      </p>
      <h1>{t("lab.title.page", { code: title })}</h1>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {!loaded && !error && <p role="status">{t("common.loading")}</p>}
      {loaded && policy === "closed" && (
        <p role="status" className="lab-closed">
          {lab?.status === "upcoming" && lab.opens_at
            ? t("lab.closed.upcoming", { time: showTime(lab.opens_at) })
            : t("lab.closed.now")}
        </p>
      )}
      {loaded && policy && policy !== "closed" && (
        <div className="lab-layout">
          <aside className="lab-task" aria-labelledby="lab-task-title">
            <h2 id="lab-task-title">{t("lab.task.title")}</h2>
            {policy !== "on_time" && (
              <p className="badge">{t(`lab.policy.${policy}`)}</p>
            )}
            <p>{t("lab.task.placeholder")}</p>
            <p>
              <Link to={`/topics/${code}`}>{t("lab.task.lecture")}</Link>
            </p>
          </aside>
          <section className="lab-main" aria-label={t("lab.notebook")}>
            <p className="save-status" aria-live="polite">
              <SaveIndicator status={status} onResolve={resolve} />
            </p>
            {loaded.work.proctored && (
              <p className="badge">{t("lab.proctored")}</p>
            )}
            {pasteBlocked && (
              <p role="alert" className="error">
                {pasteBlocked}
              </p>
            )}
            <Notebook
              key={notebookKey}
              initial={shown ?? loaded.notebook}
              onChange={(nb) => saver.current?.change(nb)}
              onRun={(nb) => {
                saver.current?.change(nb);
                void saver.current?.flush();
              }}
              onPaste={onPaste}
            />
          </section>
          <aside className="lab-tutor" aria-labelledby="lab-tutor-title">
            <h2 id="lab-tutor-title">{t("lab.tutor.title")}</h2>
            <p className="muted">{t("lab.tutor.soon")}</p>
          </aside>
        </div>
      )}
    </main>
  );
}
