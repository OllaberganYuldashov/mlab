import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import messages from "../i18n/uz.json";
import { mockApi } from "../test-utils";

// SRS 7-bo'lim "Siyosat tarkibi" jadvalidagi bo'limlar (mas'ul shaxs ... foydalanish qoidalari).
const SRS_SECTIONS = [
  "Mas'ul shaxs",
  "Yig'iladigan ma'lumotlar",
  "Maqsad",
  "Kim ko'radi",
  "Uchinchi tomon",
  "Saqlash muddati",
  "Talaba huquqlari",
  "Xavfsizlik",
  "Foydalanish qoidalari",
];

const NO_SESSION = { "GET /api/auth/me": () => ({ status: 403, body: {} }) };

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("/policy (SRS 7)", () => {
  it("autentifikatsiyasiz ochiladi va SRS jadvalidagi barcha bo'limlar bor", async () => {
    mockApi({ ...NO_SESSION, "GET /api/policy": () => ({ status: 200, body: { version: "2026-11-22" } }) });
    window.history.replaceState(null, "", "/policy");
    render(<App />);
    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent(messages["policy.title"]);
    const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(headings).toEqual(SRS_SECTIONS);
    expect(await screen.findByText("Siyosat versiyasi: 2026-11-22")).toBeInTheDocument();
  });

  it("versiya yuklanmasa ham matn o'qiladi", async () => {
    mockApi({ ...NO_SESSION, "GET /api/policy": () => ({ status: 500 }) });
    window.history.replaceState(null, "", "/policy");
    render(<App />);
    expect(await screen.findByRole("heading", { level: 1 })).toBeInTheDocument();
    expect(screen.queryByText(/Siyosat versiyasi/)).not.toBeInTheDocument();
    expect(screen.getAllByRole("region")).toHaveLength(9);
  });

  it("NFR-14: hamma matn uz.json dan", async () => {
    mockApi({ ...NO_SESSION, "GET /api/policy": () => ({ status: 200, body: { version: "2026-11-22" } }) });
    window.history.replaceState(null, "", "/policy");
    const { container } = render(<App />);
    await screen.findByText(/Siyosat versiyasi/);
    const allowed = Object.values(messages).map((m) => m.replace("{version}", "2026-11-22"));
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const text = node.textContent?.trim();
      if (text) expect(allowed, `tarjima faylida yo'q: "${text}"`).toContain(text);
    }
  });

  it("ro'yxatdan o'tish formasidagi havola siyosat sahifasiga olib boradi", async () => {
    mockApi({
      ...NO_SESSION,
      "GET /api/directions": () => ({ status: 200, body: [] }),
      "GET /api/policy": () => ({ status: 200, body: { version: "2026-11-22" } }),
    });
    window.history.replaceState(null, "", "/register");
    render(<App />);
    await userEvent.setup().click(await screen.findByRole("link", { name: messages["register.policyLink"] }));
    await waitFor(() => expect(window.location.pathname).toBe("/policy"));
    const main = await screen.findByRole("main");
    expect(within(main).getByRole("heading", { level: 1 })).toHaveTextContent(messages["policy.title"]);
  });
});
