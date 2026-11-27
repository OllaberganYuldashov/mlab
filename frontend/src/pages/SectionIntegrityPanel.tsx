import { useEffect, useState } from "react";
import { api, fieldErrors } from "../api";
import { showTime } from "../datetime";
import { t } from "../i18n";

interface Note {
  text: string;
  author: string;
  updated_at: string;
}

export interface IntegrityRow {
  student_id: number;
  full_name: string;
  paste_blocked: number;
  tab_hidden: number;
  understanding_failed: number;
  fast_full_score: boolean;
  note: Note | null;
}

interface Topic {
  code: string;
  title: string;
}

function NoteEditor({
  url,
  note,
  onSaved,
}: {
  url: string;
  note: Note | null;
  onSaved: () => void;
}) {
  const [text, setText] = useState(note?.text ?? "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    setError(null);
    try {
      const result = await api(url, { method: "PUT", body: { text } });
      if (result.ok) onSaved();
      else
        setError(
          Object.values(fieldErrors(result.data))[0] ??
            t("common.unexpectedError"),
        );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="integrity-note">
      <textarea
        aria-label={t("integrity.note")}
        maxLength={1000}
        rows={2}
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <button
        type="button"
        disabled={busy || text.trim() === (note?.text ?? "")}
        onClick={() => void save()}
      >
        {t("integrity.saveNote")}
      </button>
      {note && (
        <p className="muted">
          {t("integrity.noteBy", {
            author: note.author,
            time: showTime(note.updated_at),
          })}
        </p>
      )}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
    </div>
  );
}

/** INT-04, INT-05: guruh x mavzu bo'yicha shubhali holatlar. Avtomatik jazo yo'q — qaror o'qituvchida. */
export default function SectionIntegrityPanel({
  sectionId,
}: {
  sectionId: number;
}) {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [code, setCode] = useState("");
  const [rows, setRows] = useState<IntegrityRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    void (async () => {
      const result = await api<{ windows: { topic: Topic }[] }>(
        `/api/sections/${sectionId}/windows`,
      );
      if (active && result.ok)
        setTopics(result.data.windows.map((w) => w.topic));
    })();
    return () => {
      active = false;
    };
  }, [sectionId]);

  useEffect(() => {
    if (!code) return;
    let active = true;
    void (async () => {
      const result = await api<{ students: IntegrityRow[] }>(
        `/api/sections/${sectionId}/labs/${code}/integrity`,
      );
      if (!active) return;
      if (result.ok) {
        setRows(result.data.students);
        setError(null);
      } else setError(t("common.unexpectedError"));
    })();
    return () => {
      active = false;
    };
  }, [sectionId, code, version]);

  return (
    <section aria-labelledby="integrity-title">
      <h2 id="integrity-title">{t("integrity.title")}</h2>
      <p className="muted">{t("integrity.hint")}</p>
      <label>
        {t("integrity.topic")}{" "}
        <select
          value={code}
          onChange={(e) => {
            setRows(null);
            setCode(e.target.value);
          }}
        >
          <option value="">{t("integrity.chooseTopic")}</option>
          {topics.map((topic) => (
            <option key={topic.code} value={topic.code}>
              {topic.code}. {topic.title}
            </option>
          ))}
        </select>
      </label>
      {rows && rows.length === 0 && <p>{t("integrity.empty")}</p>}
      {rows && rows.length > 0 && (
        <div className="scroll-x">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">{t("integrity.col.student")}</th>
                <th scope="col">{t("integrity.col.paste")}</th>
                <th scope="col">{t("integrity.col.tab")}</th>
                <th scope="col">{t("integrity.col.understanding")}</th>
                <th scope="col">{t("integrity.col.fast")}</th>
                <th scope="col">{t("integrity.col.note")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.student_id}>
                  <th scope="row">{row.full_name}</th>
                  <td>{row.paste_blocked}</td>
                  <td>{row.tab_hidden}</td>
                  <td>{row.understanding_failed}</td>
                  <td>{row.fast_full_score ? t("integrity.yes") : "—"}</td>
                  <td>
                    <NoteEditor
                      key={`${row.student_id}-${row.note?.updated_at ?? ""}`}
                      url={`/api/sections/${sectionId}/labs/${code}/students/${row.student_id}/integrity-note`}
                      note={row.note}
                      onSaved={() => setVersion((v) => v + 1)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
    </section>
  );
}
