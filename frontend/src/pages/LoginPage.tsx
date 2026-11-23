import { type FormEvent, useState } from "react";
import { api, type Me } from "../api";
import { t } from "../i18n";
import { Link } from "../Link";

export default function LoginPage({ onLogin }: { onLogin: (me: Me) => void }) {
  const [hemisId, setHemisId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await api<Me>("/api/auth/login", {
        method: "POST",
        body: { hemis_id: hemisId, password },
      });
      if (result.ok) onLogin(result.data);
      else if (result.status === 429) setError(t("login.locked"));
      else if (result.status === 400) setError(t("login.failed"));
      else setError(t("common.unexpectedError"));
    } catch {
      setError(t("common.networkError"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="app">
      <h1>{t("login.title")}</h1>
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
          />
        </div>
        <div className="field">
          <label htmlFor="password">{t("field.password")}</label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <button type="submit" disabled={busy}>
          {t("login.submit")}
        </button>
      </form>
      <p>
        <Link to="/register">{t("login.toRegister")}</Link>
      </p>
    </main>
  );
}
