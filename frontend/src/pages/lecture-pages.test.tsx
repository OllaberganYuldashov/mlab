import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import messages from "../i18n/uz.json";
import { mockApi } from "../test-utils";

const STUDENT = { hemis_id: "123456789012", full_name: "Test Talaba", role: "student", direction: 1, must_change_password: false };

const TOPICS = {
  course: { slug: "machine-learning", title: "Machine Learning" },
  topics: [
    { code: "M01", title: "ML asoslari", order: 1, steps: 3, questions: 4, lab: { status: "open", opens_at: null, closes_at: null } },
    { code: "M02", title: "Ma'lumotlar", order: 2, steps: 5, questions: 0, lab: { status: "closed", opens_at: null, closes_at: null } },
  ],
};

const LECTURE = {
  topic: { code: "M01", title: "ML asoslari" },
  title: "ML asoslari",
  prev: null,
  next: "M02",
  steps: [
    { order: 1, title: "Kirish", body: "**ML** — ma'lumotdan o'rganish.\n\n![Chiziq](/api/course/images/abc)", question: null },
    { order: 2, title: "Sinab ko'r", body: "```python try\nprint(2 + 2)\n```", question: null },
    {
      order: 3,
      title: "Savol",
      body: "",
      question: { question: "Spam filtri qaysi tur?", options: ["Nazoratli", "Nazoratsiz"], answer: 0, explain: "Belgilar bor." },
    },
  ],
};

function visit(path: string) {
  window.history.replaceState(null, "", path);
}

beforeEach(() => {
  vi.stubGlobal("WebSocket", undefined);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("ma'ruzalar (CNT-02)", () => {
  it("mavzular ro'yxati: qadamlar soni va laboratoriya holati", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      "GET /api/course/topics": () => ({ status: 200, body: TOPICS }),
    });
    visit("/topics");
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Machine Learning" })).toBeInTheDocument();
    const items = screen.getAllByRole("listitem");
    expect(within(items[0] as HTMLElement).getByRole("link", { name: "M01. ML asoslari" })).toHaveAttribute("href", "/topics/M01");
    expect(items[0]).toHaveTextContent("3 qadam");
    expect(items[0]).toHaveTextContent(messages["topics.lab.open"]);
    expect(items[1]).toHaveTextContent(messages["topics.lab.closed"]);
  });

  it("a'zo bo'lmagan — tushunarli xabar", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      "GET /api/course/topics": () => ({ status: 403, body: { detail: "x" } }),
    });
    visit("/topics");
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent(messages["topics.noAccess"]);
  });

  it("qadamlar bo'yicha yurish, sinab ko'r bloki va tezkor savol", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      "GET /api/course/topics/M01/lecture": () => ({ status: 200, body: LECTURE }),
    });
    const user = userEvent.setup();
    visit("/topics/M01");
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Kirish" })).toBeInTheDocument();
    expect(screen.getByText("Qadam 1 / 3")).toBeInTheDocument();
    expect(screen.getByText("ML").tagName).toBe("STRONG");
    expect(screen.getByRole("img", { name: "Chiziq" })).toHaveAttribute("src", "/api/course/images/abc");
    expect(screen.getByRole("button", { name: messages["lecture.prev"] })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: messages["lecture.next"] }));
    expect(screen.getByRole("heading", { name: "Sinab ko'r" })).toHaveFocus();
    expect(screen.getByText(messages["lecture.try"])).toBeInTheDocument();
    expect(screen.getByText("print(2 + 2)")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: messages["lecture.next"] }));
    const check = screen.getByRole("button", { name: messages["lecture.check"] });
    expect(check).toBeDisabled();
    await user.click(screen.getByRole("radio", { name: "B) Nazoratsiz" }));
    await user.click(check);
    expect(screen.getByRole("status")).toHaveTextContent("Noto'g'ri. To'g'ri javob: A) Nazoratli. Belgilar bor.");
    await user.click(screen.getByRole("radio", { name: "A) Nazoratli" }));
    expect(screen.queryByRole("status")).toBeNull();
    await user.click(check);
    expect(screen.getByRole("status")).toHaveTextContent(messages["lecture.correct"]);

    expect(screen.getByRole("link", { name: "Keyingi mavzu: M02 →" })).toHaveAttribute("href", "/topics/M02");
    await user.click(screen.getByRole("button", { name: messages["lecture.prev"] }));
    expect(screen.getByRole("heading", { name: "Sinab ko'r" })).toBeInTheDocument();
  });

  it("noma'lum mavzu — 404 xabari", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      "GET /api/course/topics/M09/lecture": () => ({ status: 404, body: {} }),
    });
    visit("/topics/M09");
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent(messages["lecture.notFound"]);
  });

  it("kirmagan foydalanuvchiga mavzular sahifasi yo'q", async () => {
    mockApi({ "GET /api/auth/me": () => ({ status: 403, body: {} }) });
    visit("/topics");
    render(<App />);
    expect(await screen.findByRole("heading", { name: messages["notFound.title"] })).toBeInTheDocument();
  });

  it("bosh sahifada ma'ruzalar havolasi", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      "GET /api/me/membership": () => ({ status: 200, body: { membership: null } }),
    });
    visit("/");
    render(<App />);
    expect(await screen.findByRole("link", { name: messages["nav.topics"] })).toHaveAttribute("href", "/topics");
  });
});
