import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App";
import messages from "./i18n/uz.json";

function visibleTexts(root: HTMLElement): string[] {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const texts: string[] = [];
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const text = node.textContent?.trim();
    if (text) texts.push(text);
  }
  return texts;
}

describe("App", () => {
  it("sarlavha o'zbekcha tarjima faylidan", () => {
    render(<App />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(messages["app.title"]);
  });

  it("NFR-14: sahifadagi hamma matn uz.json dan (qattiq yozilgan matn yo'q)", () => {
    const { container } = render(<App />);
    const allowed = new Set(Object.values(messages));
    const texts = visibleTexts(container);
    expect(texts.length).toBeGreaterThan(0);
    for (const text of texts) {
      expect(allowed, `tarjima faylida yo'q: "${text}"`).toContain(text);
    }
  });

  it("asosiy landmark'lar bor (NFR-13)", () => {
    render(<App />);
    expect(screen.getByRole("main")).toBeInTheDocument();
  });
});
