import { useEffect, useState } from "react";
import { api } from "../api";
import { showTime } from "../datetime";
import { t } from "../i18n";
import Notebook from "../lab/Notebook";
import { type Notebook as NotebookState, emptyNotebook } from "../lab/notebook";
import { Link } from "../Link";
import type { LabState } from "./TopicsPage";

type Policy = "on_time" | "late" | "practice" | "closed";

interface Work {
  version: number;
  notebook: NotebookState | null;
  saved_at: string | null;
  policy: Policy;
}

interface TopicBrief {
  code: string;
  title: string;
  lab: LabState | null;
}

interface Loaded {
  work: Work;
  topic: TopicBrief | undefined;
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
          work.status === 404 ? t("lecture.notFound") : work.status === 403 ? t("topics.noAccess") : t("common.unexpectedError"),
        );
        return;
      }
      setLoaded({ work: work.data, topic: topics.ok ? topics.data.topics.find((x) => x.code === code) : undefined });
    })();
    return () => {
      active = false;
    };
  }, [code]);

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
            {policy !== "on_time" && <p className="badge">{t(`lab.policy.${policy}`)}</p>}
            <p>{t("lab.task.placeholder")}</p>
            <p>
              <Link to={`/topics/${code}`}>{t("lab.task.lecture")}</Link>
            </p>
          </aside>
          <section className="lab-main" aria-label={t("lab.notebook")}>
            <Notebook initial={loaded.work.notebook ?? emptyNotebook()} />
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
