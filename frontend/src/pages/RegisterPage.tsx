import { type FormEvent, useEffect, useState } from "react";
import { api, fieldErrors } from "../api";
import { t } from "../i18n";
import { Link } from "../Link";
import { nextParam } from "../nav";
import { navigate } from "../router";

interface Direction {
  id: number;
  name: string;
}

export default function RegisterPage() {
  const [directions, setDirections] = useState<Direction[]>([]);
  const [policyVersion, setPolicyVersion] = useState<string | null>(null);
  const [hemisId, setHemisId] = useState("");
  const [fullName, setFullName] = useState("");
  const [direction, setDirection] = useState("");
  const [password, setPassword] = useState("");
  const [consent, setConsent] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [dirs, policy] = await Promise.all([
          api<Direction[]>("/api/directions"),
          api<{ version: string }>("/api/policy"),
        ]);
        if (!active) return;
        if (dirs.ok) setDirections(dirs.data);
        if (policy.ok) setPolicyVersion(policy.data.version);
        else setFormError(t("register.policyUnavailable"));
      } catch {
        if (active) setFormError(t("common.networkError"));
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!consent || !policyVersion) return;
    setBusy(true);
    setErrors({});
    setFormError(null);
    try {
      const result = await api("/api/auth/register", {
        method: "POST",
        body: {
          hemis_id: hemisId,
          full_name: fullName,
          direction: Number(direction),
          password,
          consent: true,
          policy_version: policyVersion,
        },
      });
      if (result.ok) {
        const next = nextParam();
        navigate(next ? `/login?registered=1&next=${encodeURIComponent(next)}` : "/login?registered=1");
      } else if (result.status === 400) {
        const found = fieldErrors(result.data);
        setErrors(found);
        if (Object.keys(found).length === 0) setFormError(t("common.unexpectedError"));
      } else {
        setFormError(t("common.unexpectedError"));
      }
    } catch {
      setFormError(t("common.networkError"));
    } finally {
      setBusy(false);
    }
  }

  const field = (name: string) => ({
    "aria-invalid": errors[name] ? true : undefined,
    "aria-describedby": errors[name] ? `${name}-error` : undefined,
  });
  const fieldError = (name: string) =>
    errors[name] ? (
      <p id={`${name}-error`} className="error">
        {errors[name]}
      </p>
    ) : null;

  return (
    <main className="app">
      <h1>{t("register.title")}</h1>
      <form onSubmit={submit} noValidate>
        <div className="field">
          <label htmlFor="hemis_id">{t("field.hemisId")}</label>
          <input
            id="hemis_id"
            name="hemis_id"
            inputMode="numeric"
            autoComplete="username"
            required
            value={hemisId}
            onChange={(e) => setHemisId(e.target.value)}
            {...field("hemis_id")}
          />
          <small>{t("field.hemisId.hint")}</small>
          {fieldError("hemis_id")}
        </div>
        <div className="field">
          <label htmlFor="full_name">{t("field.fullName")}</label>
          <input
            id="full_name"
            name="full_name"
            autoComplete="name"
            required
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            {...field("full_name")}
          />
          {fieldError("full_name")}
        </div>
        <div className="field">
          <label htmlFor="direction">{t("field.direction")}</label>
          <select
            id="direction"
            name="direction"
            required
            value={direction}
            onChange={(e) => setDirection(e.target.value)}
            {...field("direction")}
          >
            <option value="">{t("field.direction.choose")}</option>
            {directions.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
          {fieldError("direction")}
        </div>
        <div className="field">
          <label htmlFor="password">{t("field.password")}</label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            {...field("password")}
          />
          {fieldError("password")}
        </div>
        <fieldset className="consent">
          <legend>{t("register.consentIntro")}</legend>
          <ul>
            <li>{t("register.consent1")}</li>
            <li>{t("register.consent2")}</li>
            <li>{t("register.consent3")}</li>
          </ul>
          <p>
            <Link to="/policy">{t("register.policyLink")}</Link>
          </p>
          <label>
            <input
              type="checkbox"
              name="consent"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              {...field("consent")}
            />{" "}
            {t("register.consentCheckbox")}
          </label>
          {fieldError("consent")}
          {fieldError("policy_version")}
        </fieldset>
        {formError && (
          <p role="alert" className="error">
            {formError}
          </p>
        )}
        <button type="submit" disabled={!consent || !policyVersion || busy}>
          {t("register.submit")}
        </button>
      </form>
      <p>
        <Link to="/login">{t("register.toLogin")}</Link>
      </p>
    </main>
  );
}
