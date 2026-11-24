import { useEffect, useState } from "react";
import { api } from "../api";
import { t } from "../i18n";
import { Link } from "../Link";

interface DatasetInfo {
  name: string;
  title: string;
  description: string;
  source_url: string;
  license: string;
  license_url: string;
  rows: number;
  columns: string[];
  size: number;
}

/** DAT-02: datasetlar — tavsif, ustunlar, rasmiy manba va litsenziya; `mlab.load()` namunasi. */
export default function DatasetsPage() {
  const [items, setItems] = useState<DatasetInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      const result = await api<DatasetInfo[]>("/api/datasets");
      if (!active) return;
      if (result.ok) setItems(result.data);
      else setError(result.status === 403 ? t("topics.noAccess") : t("common.unexpectedError"));
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="app">
      <p className="links">
        <Link to="/topics">{t("topics.back")}</Link>
      </p>
      <h1>{t("datasets.title")}</h1>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {!items && !error && <p role="status">{t("common.loading")}</p>}
      {items?.length === 0 && <p>{t("datasets.empty")}</p>}
      {items?.map((d) => (
        <article key={d.name} className="card" aria-labelledby={`ds-${d.name}`}>
          <h2 id={`ds-${d.name}`}>{d.title}</h2>
          <p>{d.description}</p>
          <p>
            <code>{`df = mlab.load("${d.name}")`}</code>
          </p>
          <p className="muted">
            {t("datasets.shape", { rows: d.rows, columns: d.columns.length })}: {d.columns.join(", ")}
          </p>
          <p>
            {t("datasets.source")}:{" "}
            <a href={d.source_url} target="_blank" rel="noopener noreferrer">
              {d.source_url}
            </a>
            {" · "}
            {t("datasets.license")}:{" "}
            <a href={d.license_url} target="_blank" rel="noopener noreferrer">
              {d.license}
            </a>
          </p>
        </article>
      ))}
    </main>
  );
}
