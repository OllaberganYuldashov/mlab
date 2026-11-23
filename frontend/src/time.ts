import { t } from "./i18n";

/** Qolgan vaqt matni (uz.json formatlari). Manfiy — 0. */
export function formatLeft(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const d = Math.floor(total / 86400);
  const h = Math.floor((total % 86400) / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (d > 0) return t("time.dhm", { d, h, m });
  const pad = (n: number) => String(n).padStart(2, "0");
  return t("time.hms", { h: pad(h), m: pad(m), s: pad(s) });
}
