import { type FormEvent, useCallback, useEffect, useState } from "react";
import { api, fieldErrors } from "../api";
import { localToIso, showTime } from "../datetime";
import { type MessageKey, t } from "../i18n";

interface Row {
  topic: { code: string; title: string; order: number };
  mode: string;
  proctored: boolean;
  state: { status: string; opens_at: string | null; closes_at: string | null };
}

interface Deadline {
  assignment: string;
  due_at: string;
}

function errorText(data: unknown): string {
  // `detail` (409 javoblari) avval; aks holda birinchi maydon xatosi (DRF 400).
  const detail = (data as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  const first = Object.values(fieldErrors(data))[0];
  return first ?? t("common.unexpectedError");
}

function stateText(row: Row): string {
  const s = row.state;
  if (s.status === "open")
    return s.closes_at
      ? `${t("windows.open")} · ${t("windows.until", { time: showTime(s.closes_at) })}`
      : t("windows.open");
  if (s.status === "upcoming")
    return t("windows.upcoming", { time: showTime(s.opens_at) });
  return t("windows.closed");
}

function WindowRow({
  sectionId,
  row,
  onChanged,
  onError,
}: {
  sectionId: number;
  row: Row;
  onChanged: () => void;
  onError: (m: string) => void;
}) {
  const [minutes, setMinutes] = useState("");
  const [opens, setOpens] = useState("");
  const [closes, setCloses] = useState("");
  const [proctored, setProctored] = useState(row.proctored);
  const base = `/api/sections/${sectionId}/windows/${row.topic.code}`;
  const code = row.topic.code;

  async function call(path: string, method: string, body?: unknown) {
    const result = await api(base + path, { method, body });
    if (result.ok) onChanged();
    else onError(errorText(result.data));
  }

  return (
    <tr>
      <th scope="row">
        {code} {row.topic.title}
      </th>
      <td>{stateText(row)}</td>
      <td>
        <div className="links">
          <input
            aria-label={`${t("windows.minutes")}: ${code}`}
            type="number"
            min={1}
            className="narrow"
            value={minutes}
            onChange={(e) => setMinutes(e.target.value)}
          />
          <button
            type="button"
            onClick={() =>
              void call(
                "/open-now",
                "POST",
                minutes ? { minutes: Number(minutes) } : {},
              )
            }
          >
            {t("windows.openNow")}
          </button>
          <button type="button" onClick={() => void call("/close", "POST")}>
            {t("windows.close")}
          </button>
        </div>
        <div className="links">
          <input
            aria-label={`${t("windows.opensAt")}: ${code}`}
            type="datetime-local"
            value={opens}
            onChange={(e) => setOpens(e.target.value)}
          />
          <input
            aria-label={`${t("windows.closesAt")}: ${code}`}
            type="datetime-local"
            value={closes}
            onChange={(e) => setCloses(e.target.value)}
          />
          <label>
            <input
              type="checkbox"
              checked={proctored}
              onChange={(e) => setProctored(e.target.checked)}
            />{" "}
            {t("windows.proctored")}
          </label>
          <button
            type="button"
            onClick={() =>
              void call("", "PUT", {
                mode: "scheduled",
                opens_at: localToIso(opens),
                closes_at: localToIso(closes),
                proctored,
              })
            }
          >
            {t("windows.schedule")}
          </button>
        </div>
      </td>
    </tr>
  );
}

function WeeklyPlan({
  sectionId,
  onSaved,
}: {
  sectionId: number;
  onSaved: () => void;
}) {
  const [weekday, setWeekday] = useState("1");
  const [time, setTime] = useState("10:00");
  const [minutes, setMinutes] = useState("80");
  const [start, setStart] = useState("");
  const [overwrite, setOverwrite] = useState(false);
  const [plan, setPlan] = useState<
    { topic: string; opens_at: string; closes_at: string }[] | null
  >(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(preview: boolean) {
    setMessage(null);
    setError(null);
    const result = await api<{
      plan: { topic: string; opens_at: string; closes_at: string }[];
    }>(`/api/sections/${sectionId}/windows/plan`, {
      method: "POST",
      body: {
        slots: [{ weekday: Number(weekday), time, minutes: Number(minutes) }],
        start_date: start,
        preview,
        overwrite,
      },
    });
    if (result.ok) {
      setPlan(result.data.plan);
      if (!preview) {
        setMessage(t("plan.saved"));
        onSaved();
      }
    } else setError(errorText(result.data));
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void submit(true);
  };

  return (
    <form onSubmit={onSubmit} aria-labelledby="plan-title" noValidate>
      <h3 id="plan-title">{t("plan.title")}</h3>
      <div className="links">
        <label>
          {t("plan.weekday")}{" "}
          <select value={weekday} onChange={(e) => setWeekday(e.target.value)}>
            {[0, 1, 2, 3, 4, 5, 6].map((d) => (
              <option key={d} value={d}>
                {t(`day.${d}` as MessageKey)}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("plan.time")}{" "}
          <input
            type="time"
            value={time}
            onChange={(e) => setTime(e.target.value)}
          />
        </label>
        <label>
          {t("plan.minutes")}{" "}
          <input
            type="number"
            className="narrow"
            min={1}
            max={600}
            value={minutes}
            onChange={(e) => setMinutes(e.target.value)}
          />
        </label>
        <label>
          {t("plan.start")}{" "}
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
        </label>
      </div>
      <label>
        <input
          type="checkbox"
          checked={overwrite}
          onChange={(e) => setOverwrite(e.target.checked)}
        />{" "}
        {t("plan.overwrite")}
      </label>
      <p className="links">
        <button type="submit">{t("plan.preview")}</button>
        <button
          type="button"
          disabled={!plan}
          onClick={() => void submit(false)}
        >
          {t("plan.apply")}
        </button>
      </p>
      {plan && (
        <ol aria-label={t("plan.preview")}>
          {plan.map((p) => (
            <li key={p.topic}>
              {p.topic}: {showTime(p.opens_at)} – {showTime(p.closes_at)}
            </li>
          ))}
        </ol>
      )}
      {message && <p role="status">{message}</p>}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
    </form>
  );
}

function Deadlines({ sectionId }: { sectionId: number }) {
  const [rows, setRows] = useState<Deadline[]>([]);
  const [code, setCode] = useState("");
  const [due, setDue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    void (async () => {
      const result = await api<{ deadlines: Deadline[] }>(
        `/api/sections/${sectionId}/deadlines`,
      );
      if (active && result.ok) setRows(result.data.deadlines);
    })();
    return () => {
      active = false;
    };
  }, [sectionId, version]);

  async function call(target: string, method: string, body?: unknown) {
    setError(null);
    const result = await api(
      `/api/sections/${sectionId}/deadlines/${encodeURIComponent(target)}`,
      { method, body },
    );
    if (result.ok) setVersion((v) => v + 1);
    else
      setError(
        result.status === 404
          ? t("common.unexpectedError")
          : errorText(result.data),
      );
  }

  return (
    <section aria-labelledby="deadlines-title">
      <h3 id="deadlines-title">{t("deadlines.title")}</h3>
      {rows.length === 0 ? (
        <p>{t("deadlines.empty")}</p>
      ) : (
        <ul>
          {rows.map((d) => (
            <li key={d.assignment}>
              {d.assignment}: {showTime(d.due_at)}{" "}
              <button
                type="button"
                onClick={() => void call(d.assignment, "DELETE")}
              >
                {t("deadlines.remove")}
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="links">
        <label>
          {t("deadlines.code")}{" "}
          <input
            className="narrow"
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
          />
        </label>
        <label>
          {t("deadlines.due")}{" "}
          <input
            type="datetime-local"
            value={due}
            onChange={(e) => setDue(e.target.value)}
          />
        </label>
        <button
          type="button"
          disabled={!code || !due}
          onClick={() => void call(code, "PUT", { due_at: localToIso(due) })}
        >
          {t("deadlines.save")}
        </button>
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
    </section>
  );
}

/** ACC-03, ACC-04, ACC-09, ACC-10: mavzular bo'yicha oynalar, haftalik jadval va mustaqil muddatlar. */
export default function SectionWindowsPanel({
  sectionId,
}: {
  sectionId: number;
}) {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const reload = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    let active = true;
    void (async () => {
      const result = await api<{ windows: Row[] }>(
        `/api/sections/${sectionId}/windows`,
      );
      if (!active) return;
      if (result.ok) setRows(result.data.windows);
      else setError(t("common.unexpectedError"));
    })();
    return () => {
      active = false;
    };
  }, [sectionId, version]);

  return (
    <section aria-labelledby="windows-title">
      <h2 id="windows-title">{t("windows.title")}</h2>
      {rows && rows.length === 0 && <p>{t("windows.empty")}</p>}
      {rows && rows.length > 0 && (
        <div className="scroll-x">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">{t("windows.col.topic")}</th>
                <th scope="col">{t("windows.col.state")}</th>
                <th scope="col">{t("windows.col.actions")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <WindowRow
                  key={row.topic.code}
                  sectionId={sectionId}
                  row={row}
                  onChanged={() => {
                    setError(null);
                    reload();
                  }}
                  onError={setError}
                />
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
      <WeeklyPlan sectionId={sectionId} onSaved={reload} />
      <Deadlines sectionId={sectionId} />
    </section>
  );
}
