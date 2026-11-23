import { type FormEvent, useCallback, useEffect, useState } from "react";
import { api, fieldErrors } from "../api";
import { t } from "../i18n";
import { Link } from "../Link";
import { qrDataUrl } from "../qr";
import SectionSettingsPanel from "./SectionSettingsPanel";
import type { Section } from "./SectionsPage";
import SectionWindowsPanel from "./SectionWindowsPanel";

interface Member {
  id: number;
  status: string;
  student: { id: number; hemis_id: string; full_name: string };
}

function JoinLink({ section, onChange }: { section: Section; onChange: () => void }) {
  const [url, setUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function rotate() {
    setError(null);
    const result = await api<{ join_path: string }>(`/api/sections/${section.id}/join-token`, {
      method: "POST",
    });
    if (result.ok) {
      setUrl(window.location.origin + result.data.join_path);
      setCopied(false);
      onChange();
    } else setError(t("common.unexpectedError"));
  }

  async function disable() {
    setError(null);
    const result = await api(`/api/sections/${section.id}/join-token`, { method: "DELETE" });
    if (result.ok) {
      setUrl(null);
      onChange();
    } else setError(t("common.unexpectedError"));
  }

  async function copy() {
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <section aria-labelledby="link-title">
      <h2 id="link-title">{t("section.link.title")}</h2>
      {url ? (
        <div className="join-link">
          <img src={qrDataUrl(url)} alt={t("section.link.qrAlt")} width={220} height={220} />
          <p>
            <code data-testid="join-url">{url}</code>
          </p>
          <button type="button" onClick={copy}>
            {t("section.link.copy")}
          </button>
          {copied && <span role="status"> {t("section.link.copied")}</span>}
        </div>
      ) : (
        <p>{section.has_join_token ? t("section.link.hidden") : t("section.link.none")}</p>
      )}
      <p className="links">
        <button type="button" onClick={rotate}>
          {t("section.link.rotate")}
        </button>
        {(section.has_join_token || url) && (
          <button type="button" onClick={disable}>
            {t("section.link.disable")}
          </button>
        )}
      </p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
    </section>
  );
}

function Settings({ section, onSaved }: { section: Section; onSaved: (s: Section) => void }) {
  const [capacity, setCapacity] = useState(String(section.capacity));
  const [joinEnabled, setJoinEnabled] = useState(section.join_enabled);
  const [message, setMessage] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  async function save(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    setErrors({});
    const result = await api<Section>(`/api/sections/${section.id}`, {
      method: "PATCH",
      body: { capacity: Number(capacity), join_enabled: joinEnabled },
    });
    if (result.ok) {
      onSaved(result.data);
      setMessage(t("section.saved"));
    } else {
      const found = fieldErrors(result.data);
      setErrors(Object.keys(found).length ? found : { form: t("common.unexpectedError") });
    }
  }

  return (
    <form onSubmit={save} aria-labelledby="settings-title" noValidate>
      <h2 id="settings-title">{t("section.settings")}</h2>
      <div className="field">
        <label htmlFor="capacity">{t("sections.field.capacity")}</label>
        <input
          id="capacity"
          type="number"
          min={1}
          max={500}
          value={capacity}
          onChange={(e) => setCapacity(e.target.value)}
        />
        {errors.capacity && <p className="error">{errors.capacity}</p>}
      </div>
      <label>
        <input
          type="checkbox"
          checked={joinEnabled}
          onChange={(e) => setJoinEnabled(e.target.checked)}
        />{" "}
        {t("section.joinEnabled")}
      </label>
      {errors.form && (
        <p role="alert" className="error">
          {errors.form}
        </p>
      )}
      <p>
        <button type="submit">{t("section.save")}</button>
        {message && <span role="status"> {message}</span>}
      </p>
    </form>
  );
}

function Requests({ sectionId, onDecided }: { sectionId: number; onDecided: () => void }) {
  const [rows, setRows] = useState<Member[] | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const result = await api<{ results: Member[] }>(
      `/api/sections/${sectionId}/members?status=pending`,
    );
    setRows(result.ok ? result.data.results : []);
    setSelected(new Set());
  }, [sectionId]);

  useEffect(() => {
    let active = true;
    void (async () => {
      const result = await api<{ results: Member[] }>(
        `/api/sections/${sectionId}/members?status=pending`,
      );
      if (active) setRows(result.ok ? result.data.results : []);
    })();
    return () => {
      active = false;
    };
  }, [sectionId]);

  async function decide(decision: "approve" | "reject") {
    setMessage(null);
    setError(null);
    const result = await api<{ approved: number[]; rejected: number[]; skipped: number[] }>(
      `/api/sections/${sectionId}/members/decide`,
      { method: "POST", body: { ids: [...selected], decision } },
    );
    if (result.ok) {
      setMessage(
        t("section.requests.done", {
          approved: result.data.approved.length,
          rejected: result.data.rejected.length,
        }),
      );
      await load();
      onDecided();
    } else {
      const detail = (result.data as { detail?: unknown } | null)?.detail;
      setError(typeof detail === "string" ? detail : t("common.unexpectedError"));
    }
  }

  const toggle = (id: number) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <section aria-labelledby="requests-title">
      <h2 id="requests-title">{t("section.requests.title")}</h2>
      {rows && rows.length === 0 && <p>{t("section.requests.empty")}</p>}
      {rows && rows.length > 0 && (
        <>
          <label>
            <input
              type="checkbox"
              checked={selected.size === rows.length}
              onChange={(e) => setSelected(e.target.checked ? new Set(rows.map((r) => r.id)) : new Set())}
            />{" "}
            {t("section.requests.selectAll")}
          </label>
          <table className="table">
            <thead>
              <tr>
                <th scope="col" aria-label={t("section.requests.selectAll")} />
                <th scope="col">{t("section.col.student")}</th>
                <th scope="col">{t("section.col.hemis")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>
                    <input
                      type="checkbox"
                      aria-label={r.student.full_name}
                      checked={selected.has(r.id)}
                      onChange={() => toggle(r.id)}
                    />
                  </td>
                  <td>{r.student.full_name}</td>
                  <td>{r.student.hemis_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="links">
            <button type="button" disabled={!selected.size} onClick={() => decide("approve")}>
              {t("section.requests.approve")}
            </button>
            <button type="button" disabled={!selected.size} onClick={() => decide("reject")}>
              {t("section.requests.reject")}
            </button>
          </p>
        </>
      )}
      {message && <p role="status">{message}</p>}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
    </section>
  );
}

function Members({
  section,
  others,
  version,
  onChanged,
}: {
  section: Section;
  others: Section[];
  version: number;
  onChanged: () => void;
}) {
  const [rows, setRows] = useState<Member[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      const result = await api<{ results: Member[] }>(
        `/api/sections/${section.id}/members?status=approved`,
      );
      if (active) setRows(result.ok ? result.data.results : []);
    })();
    return () => {
      active = false;
    };
  }, [section.id, version]);

  async function act(member: Member, path: string, body?: unknown) {
    setError(null);
    const result = await api(`/api/sections/${section.id}/members/${member.id}/${path}`, {
      method: "POST",
      body,
    });
    if (result.ok) onChanged();
    else {
      const detail = (result.data as { detail?: unknown } | null)?.detail;
      setError(typeof detail === "string" ? detail : t("common.unexpectedError"));
    }
  }

  return (
    <section aria-labelledby="members-title">
      <h2 id="members-title">{t("section.members.title")}</h2>
      {rows && rows.length === 0 && <p>{t("section.members.empty")}</p>}
      {rows && rows.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th scope="col">{t("section.col.student")}</th>
              <th scope="col">{t("section.col.hemis")}</th>
              <th scope="col">{t("section.members.moveTo")}</th>
              <th scope="col">{t("section.members.remove")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((m) => (
              <tr key={m.id}>
                <td>{m.student.full_name}</td>
                <td>{m.student.hemis_id}</td>
                <td>
                  <select
                    aria-label={`${t("section.members.moveTo")}: ${m.student.full_name}`}
                    value=""
                    onChange={(e) => {
                      if (e.target.value) void act(m, "move", { target_section: Number(e.target.value) });
                    }}
                  >
                    <option value="">{t("section.members.moveChoose")}</option>
                    {others.map((o) => (
                      <option key={o.id} value={o.id}>
                        {o.name}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <button type="button" onClick={() => void act(m, "remove")}>
                    {t("section.members.remove")}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
    </section>
  );
}

export default function SectionPage({ sectionId }: { sectionId: number }) {
  const [section, setSection] = useState<Section | null>(null);
  const [others, setOthers] = useState<Section[]>([]);
  const [missing, setMissing] = useState(false);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    void (async () => {
      const [one, all] = await Promise.all([
        api<Section>(`/api/sections/${sectionId}`),
        api<{ results: Section[] }>("/api/sections"),
      ]);
      if (!active) return;
      if (one.ok) setSection(one.data);
      else setMissing(true);
      if (all.ok) setOthers(all.data.results.filter((s) => s.id !== sectionId));
    })();
    return () => {
      active = false;
    };
  }, [sectionId, version]);

  const refresh = () => setVersion((v) => v + 1);

  if (missing) {
    return (
      <main className="app">
        <h1>{t("section.notFound")}</h1>
        <Link to="/sections">{t("section.back")}</Link>
      </main>
    );
  }
  if (!section) {
    return (
      <main className="app">
        <p role="status">{t("common.loading")}</p>
      </main>
    );
  }
  return (
    <main className="app">
      <p>
        <Link to="/sections">{t("section.back")}</Link>
      </p>
      <h1>{section.name}</h1>
      <p className="status">
        {t("sections.members", { approved: section.approved_count, capacity: section.capacity })}
      </p>
      <JoinLink section={section} onChange={refresh} />
      <Requests sectionId={section.id} onDecided={refresh} />
      <Members section={section} others={others} version={version} onChanged={refresh} />
      <Settings key={`${section.id}-${version}`} section={section} onSaved={setSection} />
      <SectionSettingsPanel sectionId={section.id} />
      <SectionWindowsPanel sectionId={section.id} />
    </main>
  );
}
