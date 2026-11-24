/**
 * Ma'ruza matni uchun kichik Markdown renderer (CNT-02). Natija — React elementlari, `innerHTML` yo'q:
 * matndagi har qanday HTML oddiy matn bo'lib chiqadi (XSS tuzilishi bo'yicha mumkin emas).
 *
 * Qo'llab-quvvatlanadi: `###`/`####` sarlavhalar, paragraflar, `-`/`*` va `1.` ro'yxatlar, ```` ``` ```` kod bloklari
 * (```` ```python try ```` — "O'zing sinab ko'r"), `**qalin**`, `*kursiv*`, `` `kod` ``, havola `[matn](url)`
 * (faqat `https:`, `http:`, `/` va `#`), rasm `![alt](/api/...)` (faqat shu sayt). Jadval va HTML — yo'q.
 */
import type { ReactNode } from "react";

export interface CodeBlockInfo {
  language: string;
  tryable: boolean;
  code: string;
}

type Block =
  | { kind: "heading"; level: 3 | 4; text: string }
  | { kind: "paragraph"; text: string }
  | { kind: "list"; ordered: boolean; items: string[] }
  | { kind: "code"; info: CodeBlockInfo };

const FENCE = /^(```|~~~)\s*(.*)$/;
const BULLET = /^\s*[-*]\s+(.*)$/;
const NUMBERED = /^\s*\d+[.)]\s+(.*)$/;
const HEADING = /^(#{1,6})\s+(.*)$/;

export function parseBlocks(text: string): Block[] {
  const lines = text.replace(/\r\n?/g, "\n").split("\n");
  const blocks: Block[] = [];
  let paragraph: string[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;
  const flush = () => {
    if (paragraph.length) blocks.push({ kind: "paragraph", text: paragraph.join(" ") });
    if (list) blocks.push({ kind: "list", ...list });
    paragraph = [];
    list = null;
  };
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i] ?? "";
    const fence = FENCE.exec(line.trim());
    if (fence) {
      flush();
      const marker = fence[1] ?? "```";
      const words = (fence[2] ?? "").split(/\s+/).filter(Boolean);
      const body: string[] = [];
      i++;
      while (i < lines.length && !(lines[i] ?? "").trim().startsWith(marker)) {
        body.push(lines[i] ?? "");
        i++;
      }
      const language = words[0] ?? "";
      blocks.push({
        kind: "code",
        info: { language, tryable: language === "python" && words.includes("try"), code: body.join("\n") },
      });
      continue;
    }
    if (!line.trim()) {
      flush();
      continue;
    }
    const heading = HEADING.exec(line);
    if (heading) {
      flush();
      blocks.push({ kind: "heading", level: (heading[1] ?? "").length <= 3 ? 3 : 4, text: heading[2] ?? "" });
      continue;
    }
    const bullet = BULLET.exec(line);
    const numbered = bullet ? null : NUMBERED.exec(line);
    if (bullet || numbered) {
      const ordered = Boolean(numbered);
      if (paragraph.length || (list && list.ordered !== ordered)) flush();
      list ??= { ordered, items: [] };
      list.items.push((bullet ?? numbered)?.[1] ?? "");
      continue;
    }
    if (list && /^\s{2,}\S/.test(line)) {
      // ro'yxat bandining davomi
      list.items[list.items.length - 1] += ` ${line.trim()}`;
      continue;
    }
    if (list) flush();
    paragraph.push(line.trim());
  }
  flush();
  return blocks;
}

const INLINE = /(!?\[[^\]]*\]\([^)\s]*\))|(\*\*[^*]+\*\*)|(`[^`]+`)|(\*[^*\s][^*]*\*)/g;

export function safeHref(url: string): string | null {
  if (url.startsWith("/") && !url.startsWith("//")) return url;
  if (url.startsWith("#")) return url;
  return /^https?:\/\//i.test(url) ? url : null;
}

function safeImage(url: string): string | null {
  return url.startsWith("/api/") ? url : null;
}

export function renderInline(text: string, keyPrefix = "i"): ReactNode[] {
  const nodes: ReactNode[] = [];
  let last = 0;
  let n = 0;
  for (const match of text.matchAll(INLINE)) {
    const token = match[0];
    const at = match.index ?? 0;
    if (at > last) nodes.push(text.slice(last, at));
    const key = `${keyPrefix}-${n++}`;
    const link = /^(!?)\[([^\]]*)\]\(([^)\s]*)\)$/.exec(token);
    if (link) {
      const [, bang, label = "", url = ""] = link;
      if (bang) {
        const src = safeImage(url);
        nodes.push(src ? <img key={key} src={src} alt={label} className="lecture-img" /> : `[${label}]`);
      } else {
        const href = safeHref(url);
        nodes.push(
          href ? (
            <a key={key} href={href} rel="noopener noreferrer" target={href.startsWith("http") ? "_blank" : undefined}>
              {label}
            </a>
          ) : (
            label
          ),
        );
      }
    } else if (token.startsWith("**")) {
      nodes.push(<strong key={key}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("`")) {
      nodes.push(<code key={key}>{token.slice(1, -1)}</code>);
    } else {
      nodes.push(<em key={key}>{token.slice(1, -1)}</em>);
    }
    last = at + token.length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

