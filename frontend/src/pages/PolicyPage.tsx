import { useEffect, useState } from "react";
import { api } from "../api";
import { Link } from "../Link";
import { t } from "../i18n";

const SECTIONS = [1, 2, 3, 4, 5, 6, 7, 8, 9] as const;

/** SRS 7-bo'lim siyosat tarkibi. Matn faqat `uz.json` da; versiya backend'dan (`Consent` bilan bir manba). */
export default function PolicyPage() {
  const [version, setVersion] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const result = await api<{ version: string }>("/api/policy");
        if (active && result.ok) setVersion(result.data.version);
      } catch {
        // Versiya ko'rinmasa ham siyosat matni o'qiladi.
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="app">
      <h1>{t("policy.title")}</h1>
      {version && <p className="status">{t("policy.version", { version })}</p>}
      {SECTIONS.map((n) => (
        <section key={n} aria-labelledby={`policy-s${n}`}>
          <h2 id={`policy-s${n}`}>{t(`policy.s${n}.title`)}</h2>
          <p>{t(`policy.s${n}.body`)}</p>
        </section>
      ))}
      <p>
        <Link to="/register">{t("policy.back")}</Link>
      </p>
    </main>
  );
}
