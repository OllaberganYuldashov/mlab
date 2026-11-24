import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { parseBlocks, safeHref } from "./markdown";
import { Markdown } from "./Markdown.view";

afterEach(cleanup);

describe("markdown (CNT-02)", () => {
  it("bloklar: sarlavha, paragraf, ro'yxatlar, kod", () => {
    const blocks = parseBlocks(
      "### Sarlavha\n\nBir\nikki\n\n- a\n- b\n  davomi\n\n1. x\n2. y\n\n```python try\nprint(1)\n## kod ichida\n```",
    );
    expect(blocks).toEqual([
      { kind: "heading", level: 3, text: "Sarlavha" },
      { kind: "paragraph", text: "Bir ikki" },
      { kind: "list", ordered: false, items: ["a", "b davomi"] },
      { kind: "list", ordered: true, items: ["x", "y"] },
      { kind: "code", info: { language: "python", tryable: true, code: "print(1)\n## kod ichida" } },
    ]);
  });

  it("try faqat python bilan", () => {
    const [block] = parseBlocks("```text try\nx\n```");
    expect(block).toEqual({ kind: "code", info: { language: "text", tryable: false, code: "x" } });
  });

  it("inline: qalin, kursiv, kod, havola, rasm", () => {
    render(
      <Markdown text="**qalin** va *kursiv*, `kod`, [sayt](https://scikit-learn.org) ![Chiziq](/api/course/images/abc)" />,
    );
    expect(screen.getByText("qalin").tagName).toBe("STRONG");
    expect(screen.getByText("kursiv").tagName).toBe("EM");
    expect(screen.getByText("kod").tagName).toBe("CODE");
    const link = screen.getByRole("link", { name: "sayt" });
    expect(link).toHaveAttribute("href", "https://scikit-learn.org");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByRole("img", { name: "Chiziq" })).toHaveAttribute("src", "/api/course/images/abc");
  });

  it("XSS: HTML matn bo'lib chiqadi, javascript: havola va tashqi rasm yo'q", () => {
    const { container } = render(
      <Markdown text={'<script>alert(1)</script> <img src=x onerror=alert(1)> [bos](javascript:alert(1)) ![x](https://evil.example/x.png)'} />,
    );
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("a")).toBeNull();
    expect(container.textContent).toContain("<script>alert(1)</script>");
    expect(container.textContent).toContain("bos");
  });

  it("safeHref", () => {
    expect(safeHref("/topics/M01")).toBe("/topics/M01");
    expect(safeHref("//evil.example")).toBeNull();
    expect(safeHref("JAVASCRIPT:alert(1)")).toBeNull();
    expect(safeHref("data:text/html,x")).toBeNull();
    expect(safeHref("#qadam")).toBe("#qadam");
    expect(safeHref("HTTPS://example.com")).toBe("HTTPS://example.com");
  });

  it("kod bloki uchun o'z renderer'i", () => {
    render(<Markdown text={"```python try\nprint(2)\n```"} renderCode={(info) => <output>{info.code}</output>} />);
    expect(screen.getByText("print(2)").tagName).toBe("OUTPUT");
  });
});
