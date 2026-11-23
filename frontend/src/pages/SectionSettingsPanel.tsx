import { type FormEvent, useEffect, useState } from "react";
import { api, fieldErrors } from "../api";
import { type MessageKey, t } from "../i18n";

type Key =
  | "ai_enabled"
  | "ai_max_mode"
  | "practice_after_close"
  | "late_hours"
  | "chat_enabled";
type Values = Record<Key, boolean | string | number | null>;

interface SettingsPayload {
  course_defaults: Values;
  overrides: Values;
  effective: Values;
}

const MODES = ["off", "guide", "explain", "full"] as const;
const BOOLS: Key[] = ["practice_after_close", "chat_enabled"];

function shown(key: Key, value: Values[Key]): string {
  if (typeof value === "boolean")
    return value ? t("settings.on") : t("settings.off");
  if (key === "ai_max_mode") return t(`ai.${String(value)}` as MessageKey);
  return String(value);
}

/** SET-01..05: kurs qiymati ko'rinadi; "Kurs qiymati" tanlansa override olib tashlanadi (null). */
export default function SectionSettingsPanel({
  sectionId,
}: {
  sectionId: number;
}) {
  const [data, setData] = useState<SettingsPayload | null>(null);
  const [draft, setDraft] = useState<Values | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      const result = await api<SettingsPayload>(
        `/api/sections/${sectionId}/settings`,
      );
      if (!active) return;
      if (result.ok) {
        setData(result.data);
        setDraft(result.data.overrides);
      } else setError(t("common.unexpectedError"));
    })();
    return () => {
      active = false;
    };
  }, [sectionId]);

  async function send(path: string, method: string, body?: unknown) {
    setMessage(null);
    setError(null);
    const result = await api<SettingsPayload>(
      `/api/sections/${sectionId}/${path}`,
      { method, body },
    );
    if (result.ok) {
      setData(result.data);
      setDraft(result.data.overrides);
      return true;
    }
    const found = fieldErrors(result.data);
    setError(Object.values(found)[0] ?? t("common.unexpectedError"));
    return false;
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (draft && (await send("settings", "PATCH", draft)))
      setMessage(t("settings.saved"));
  }

  if (!data || !draft) {
    return error ? (
      <p role="alert" className="error">
        {error}
      </p>
    ) : null;
  }
  const aiOn = Boolean(data.effective.ai_enabled);
  const set = (key: Key, value: Values[Key]) =>
    setDraft({ ...draft, [key]: value });
  const boolSelect = (key: Key) => (
    <select
      id={`set-${key}`}
      value={draft[key] === null ? "" : String(draft[key])}
      onChange={(e) =>
        set(key, e.target.value === "" ? null : e.target.value === "true")
      }
    >
      <option value="">{t("settings.useCourse")}</option>
      <option value="true">{t("settings.on")}</option>
      <option value="false">{t("settings.off")}</option>
    </select>
  );

  return (
    <section aria-labelledby="settings-panel-title">
      <h2 id="settings-panel-title">{t("settings.title")}</h2>
      <p role="status">
        {t("settings.aiNow", {
          state: aiOn ? t("settings.on") : t("settings.off"),
        })}
      </p>
      <p>
        <button
          type="button"
          onClick={() => void send(aiOn ? "ai/disable" : "ai/enable", "POST")}
        >
          {aiOn ? t("settings.aiDisable") : t("settings.aiEnable")}
        </button>
      </p>
      <form onSubmit={save} noValidate>
        <div className="field">
          <label htmlFor="set-ai_max_mode">{t("settings.ai_max_mode")}</label>
          <select
            id="set-ai_max_mode"
            value={draft.ai_max_mode === null ? "" : String(draft.ai_max_mode)}
            onChange={(e) => set("ai_max_mode", e.target.value || null)}
          >
            <option value="">{t("settings.useCourse")}</option>
            {MODES.map((m) => (
              <option key={m} value={m}>
                {t(`ai.${m}`)}
              </option>
            ))}
          </select>
          <small>
            {t("settings.courseValue", {
              value: shown("ai_max_mode", data.course_defaults.ai_max_mode),
            })}
          </small>
        </div>
        {BOOLS.map((key) => (
          <div className="field" key={key}>
            <label htmlFor={`set-${key}`}>
              {t(`settings.${key}` as MessageKey)}
            </label>
            {boolSelect(key)}
            <small>
              {t("settings.courseValue", {
                value: shown(key, data.course_defaults[key]),
              })}
            </small>
          </div>
        ))}
        <div className="field">
          <label htmlFor="set-late_hours">{t("settings.late_hours")}</label>
          <input
            id="set-late_hours"
            type="number"
            min={0}
            max={168}
            placeholder={t("settings.useCourse")}
            value={draft.late_hours === null ? "" : String(draft.late_hours)}
            onChange={(e) =>
              set(
                "late_hours",
                e.target.value === "" ? null : Number(e.target.value),
              )
            }
          />
          <small>
            {t("settings.courseValue", {
              value: shown("late_hours", data.course_defaults.late_hours),
            })}
          </small>
        </div>
        <button type="submit">{t("settings.save")}</button>
      </form>
      {message && <p role="status">{message}</p>}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
    </section>
  );
}
