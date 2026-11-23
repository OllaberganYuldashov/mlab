import { useEffect, useState } from "react";
import { api, type Me } from "../api";
import { t } from "../i18n";
import { Link } from "../Link";

interface Preview {
  section: string;
  instructor: string;
  join_enabled: boolean;
  is_full: boolean;
}

/** SEC-03: havola yoki QR orqali qo'shilish. Token URL'da; javobda faqat guruh nomi va o'qituvchi. */
export default function JoinPage({ token, me }: { token: string; me: Me | null }) {
  const [preview, setPreview] = useState<Preview | null>(null);
  const [invalid, setInvalid] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const result = await api<Preview>(`/api/join/${encodeURIComponent(token)}`);
        if (!active) return;
        if (result.ok) setPreview(result.data);
        else setInvalid(true);
      } catch {
        if (active) setError(t("common.networkError"));
      }
    })();
    return () => {
      active = false;
    };
  }, [token]);

  async function request() {
    setBusy(true);
    setError(null);
    try {
      const result = await api(`/api/join/${encodeURIComponent(token)}`, { method: "POST" });
      if (result.ok) setMessage(t("join.sent"));
      else if (result.status === 404) setInvalid(true);
      else {
        const detail = (result.data as { detail?: unknown } | null)?.detail;
        setError(typeof detail === "string" ? detail : t("common.unexpectedError"));
      }
    } catch {
      setError(t("common.networkError"));
    } finally {
      setBusy(false);
    }
  }

  const back = encodeURIComponent(`/join/${token}`);
  return (
    <main className="app">
      <h1>{t("join.title")}</h1>
      {invalid && (
        <p role="alert" className="error">
          {t("join.invalid")}
        </p>
      )}
      {preview && !invalid && (
        <>
          <p>{t("join.section", { name: preview.section })}</p>
          <p>{t("join.instructor", { name: preview.instructor })}</p>
          {preview.is_full && <p className="error">{t("join.full")}</p>}
          {!preview.join_enabled && <p className="error">{t("join.disabled")}</p>}
          {!me && (
            <>
              <p>{t("join.loginFirst")}</p>
              <p className="links">
                <a href={`/login?next=${back}`}>{t("nav.login")}</a>
                <a href={`/register?next=${back}`}>{t("nav.register")}</a>
              </p>
            </>
          )}
          {me && me.role !== "student" && <p>{t("join.onlyStudents")}</p>}
          {me && me.role === "student" && !message && (
            <button
              type="button"
              onClick={request}
              disabled={busy || preview.is_full || !preview.join_enabled}
            >
              {t("join.submit")}
            </button>
          )}
        </>
      )}
      {message && <p role="status">{message}</p>}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <p>
        <Link to="/">{t("nav.home")}</Link>
      </p>
    </main>
  );
}
