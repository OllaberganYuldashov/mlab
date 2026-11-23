import { type FormEvent, useEffect, useState } from "react";
import { api, fieldErrors } from "../api";
import { t } from "../i18n";
import { Link } from "../Link";

export interface Section {
  id: number;
  name: string;
  direction: number;
  capacity: number;
  join_enabled: boolean;
  approved_count: number;
  has_join_token: boolean;
}

interface Direction {
  id: number;
  name: string;
}

export default function SectionsPage() {
  const [sections, setSections] = useState<Section[] | null>(null);
  const [directions, setDirections] = useState<Direction[]>([]);
  const [loadError, setLoadError] = useState(false);
  const [name, setName] = useState("");
  const [direction, setDirection] = useState("");
  const [capacity, setCapacity] = useState("30");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [list, dirs] = await Promise.all([
          api<{ results: Section[] }>("/api/sections"),
          api<Direction[]>("/api/directions"),
        ]);
        if (!active) return;
        if (list.ok) setSections(list.data.results);
        else setLoadError(true);
        if (dirs.ok) setDirections(dirs.data);
      } catch {
        if (active) setLoadError(true);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setErrors({});
    try {
      const result = await api<Section>("/api/sections", {
        method: "POST",
        body: { name, direction: Number(direction), capacity: Number(capacity) },
      });
      if (result.ok) {
        setSections((prev) => [result.data, ...(prev ?? [])]);
        setName("");
      } else {
        const found = fieldErrors(result.data);
        setErrors(Object.keys(found).length ? found : { form: t("common.unexpectedError") });
      }
    } catch {
      setErrors({ form: t("common.networkError") });
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="app">
      <h1>{t("sections.title")}</h1>
      {loadError && (
        <p role="alert" className="error">
          {t("sections.loadError")}
        </p>
      )}
      {sections && sections.length === 0 && <p>{t("sections.empty")}</p>}
      {sections && sections.length > 0 && (
        <ul className="cards">
          {sections.map((s) => (
            <li key={s.id} className="card">
              <h2>{s.name}</h2>
              <p className="status">
                {t("sections.members", { approved: s.approved_count, capacity: s.capacity })}
              </p>
              <Link to={`/sections/${s.id}`}>{t("sections.open")}</Link>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={create} noValidate aria-labelledby="create-title">
        <h2 id="create-title">{t("sections.create.title")}</h2>
        <div className="field">
          <label htmlFor="section-name">{t("sections.field.name")}</label>
          <input id="section-name" value={name} onChange={(e) => setName(e.target.value)} required />
          {errors.name && <p className="error">{errors.name}</p>}
        </div>
        <div className="field">
          <label htmlFor="section-direction">{t("field.direction")}</label>
          <select
            id="section-direction"
            value={direction}
            onChange={(e) => setDirection(e.target.value)}
            required
          >
            <option value="">{t("field.direction.choose")}</option>
            {directions.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
          {errors.direction && <p className="error">{errors.direction}</p>}
        </div>
        <div className="field">
          <label htmlFor="section-capacity">{t("sections.field.capacity")}</label>
          <input
            id="section-capacity"
            type="number"
            min={1}
            max={500}
            value={capacity}
            onChange={(e) => setCapacity(e.target.value)}
          />
          {errors.capacity && <p className="error">{errors.capacity}</p>}
        </div>
        {(errors.form || errors.course) && (
          <p role="alert" className="error">
            {errors.form || errors.course}
          </p>
        )}
        <button type="submit" disabled={busy || !name.trim() || !direction}>
          {t("sections.create.submit")}
        </button>
      </form>
    </main>
  );
}
