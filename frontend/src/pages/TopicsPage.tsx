import { useEffect, useState } from "react";
import { api } from "../api";
import { showTime } from "../datetime";
import { t } from "../i18n";
import { Link } from "../Link";

export interface LabState {
  status: "closed" | "open" | "upcoming";
  opens_at: string | null;
  closes_at: string | null;
}

interface TopicBrief {
  code: string;
  title: string;
  order: number;
  steps: number;
  questions: number;
  lab: LabState | null;
}

interface CourseTopics {
  course: { slug: string; title: string };
  topics: TopicBrief[];
}

function labText(lab: LabState): string {
  if (lab.status === "open") return t("topics.lab.open");
  if (lab.status === "upcoming" && lab.opens_at) return t("topics.lab.upcoming", { time: showTime(lab.opens_at) });
  return t("topics.lab.closed");
}

/** CNT-02, ACC-01: mavzular ro'yxati — ma'ruzalar doim ochiq, laboratoriya holati talabaga ko'rinadi. */
export default function TopicsPage() {
  const [data, setData] = useState<CourseTopics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      const result = await api<CourseTopics>("/api/course/topics");
      if (!active) return;
      if (result.ok) setData(result.data);
      else setError(result.status === 403 ? t("topics.noAccess") : t("common.unexpectedError"));
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="app">
      <h1>{data ? data.course.title : t("topics.title")}</h1>
      <p className="links">
        <Link to="/">{t("nav.home")}</Link>
        <Link to="/datasets">{t("datasets.title")}</Link>
      </p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {!data && !error && <p role="status">{t("common.loading")}</p>}
      {data && (
        <ol className="topic-list">
          {data.topics.map((topic) => (
            <li key={topic.code}>
              <Link to={`/topics/${topic.code}`}>
                {topic.code}. {topic.title}
              </Link>{" "}
              <span className="muted">{t("topics.steps", { n: topic.steps })}</span>
              {topic.lab && <span className={`badge badge-${topic.lab.status}`}>{labText(topic.lab)}</span>}
              {topic.lab && topic.questions > 0 && (
                <>
                  {" "}
                  <Link to={`/topics/${topic.code}/quiz`}>{t("topics.quiz")}</Link>
                </>
              )}
            </li>
          ))}
        </ol>
      )}
    </main>
  );
}
