/** Kirish/ro'yxatdan keyin qaytish manzili: faqat ichki yo'l (open redirect'ga qarshi). */
export function safeNext(raw: string | null): string | null {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//") || raw.includes("\\")) return null;
  if (!/^\/join\/[A-Za-z0-9_-]{16,64}$/.test(raw)) return null;
  return raw;
}

export function nextParam(): string | null {
  return safeNext(new URLSearchParams(window.location.search).get("next"));
}
