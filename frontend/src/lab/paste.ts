import { api } from "../api";

/** INT-01, ACC-09: laboratoriyadagi paste qoidalari (server `GET /api/labs/{code}/work` beradi). */
export interface PasteRules {
  limit: number;
  proctored: boolean;
}

/** Belgilar soni — kod nuqtalari bo'yicha (oʻ, emoji bitta belgi; UTF-16 juftligi emas). */
export function pasteSize(text: string): number {
  return Array.from(text).length;
}

export function pasteAllowed(size: number, rules: PasteRules): boolean {
  return !rules.proctored && size <= rules.limit;
}

/** Har paste qayd qilinadi — matn emas, faqat hajm va katak. Xato bo'lsa jim (qaror mijozda allaqachon). */
export function reportPaste(code: string, cell: string, size: number): void {
  void api(`/api/labs/${encodeURIComponent(code)}/events`, {
    method: "POST",
    body: { kind: "paste", size, cell },
  }).catch(() => undefined);
}

/** INT-05, ACC-09: nazorat rejimida sahifa yashirildi (boshqa tab yoki oyna). Faqat vaqti qayd qilinadi. */
export function reportTabHidden(code: string): void {
  void api(`/api/labs/${encodeURIComponent(code)}/events`, {
    method: "POST",
    body: { kind: "tab_hidden" },
  }).catch(() => undefined);
}
