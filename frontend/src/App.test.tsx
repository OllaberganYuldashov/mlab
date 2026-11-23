import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import messages from "./i18n/uz.json";
import { mockApi } from "./test-utils";

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
  beforeEach(() => {
    window.history.replaceState(null, "", "/");
    mockApi({ "GET /api/auth/me": () => ({ status: 403, body: {} }) });
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("sarlavha o'zbekcha tarjima faylidan", async () => {
    render(<App />);
    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent(messages["app.title"]);
  });

  it("NFR-14: sahifadagi hamma matn uz.json dan (qattiq yozilgan matn yo'q)", async () => {
    const { container } = render(<App />);
    await screen.findByRole("heading", { level: 1 });
    const allowed = new Set(Object.values(messages));
    const texts = visibleTexts(container);
    expect(texts.length).toBeGreaterThan(0);
    for (const text of texts) {
      expect(allowed, `tarjima faylida yo'q: "${text}"`).toContain(text);
    }
  });

  it("asosiy landmark'lar bor (NFR-13)", async () => {
    render(<App />);
    await screen.findByRole("heading", { level: 1 });
    expect(screen.getByRole("main")).toBeInTheDocument();
  });
});
