import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import messages from "../i18n/uz.json";
import { mockApi } from "../test-utils";

const STUDENT = { hemis_id: "123456789012", full_name: "Test Talaba", role: "student", direction: 1, must_change_password: false };

function summary(over: Record<string, unknown> = {}) {
  return {
    settings: { questions: 10, minutes: 15, attempts: 3 },
    available_questions: 2,
    used_attempts: 0,
    active_attempt: null,
    attempts: [],
    ...over,
  };
}

function attempt(over: Record<string, unknown> = {}) {
  const now = new Date();
  return {
    id: 7,
    number: 1,
    deadline: new Date(now.getTime() + 15 * 60 * 1000).toISOString(),
    server_time: now.toISOString(),
    submitted_at: null,
    score: null,
    max_score: 2,
    questions: [
      { position: 1, text: "2 + 2?", options: ["3", "4"] },
      { position: 2, text: "ML nima?", options: ["Ma'lumotdan o'rganish", "Qo'lda qoida"] },
    ],
    ...over,
  };
}

const RESULT = attempt({
  submitted_at: new Date().toISOString(),
  score: 1,
  questions: [
    { position: 1, text: "2 + 2?", options: ["3", "4"], chosen: 1, answer: 1, correct: true },
    { position: 2, text: "ML nima?", options: ["Ma'lumotdan o'rganish", "Qo'lda qoida"], chosen: 1, answer: 0, correct: false },
  ],
});

function visit(path: string) {
  window.history.replaceState(null, "", path);
}

beforeEach(() => vi.stubGlobal("WebSocket", undefined));
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("mavzu testi (CNT-06)", () => {
  it("boshlash → javob berish → topshirish → natija", async () => {
    let used = 0;
    const calls = mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      "GET /api/course/topics/M01/quiz": () => ({ status: 200, body: summary({ used_attempts: used }) }),
      "POST /api/course/topics/M01/quiz/attempts": () => ({ status: 201, body: attempt() }),
      "POST /api/course/quiz/attempts/7/submit": () => {
        used = 1;
        return { status: 200, body: RESULT };
      },
    });
    const user = userEvent.setup();
    visit("/topics/M01/quiz");
    render(<App />);
    expect(await screen.findByText("2 ta savol, 15 daqiqa.")).toBeInTheDocument();
    expect(screen.getByText("Urinishlar: 0 / 3.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: messages["quiz.start"] }));
    expect(await screen.findByText(/Qolgan vaqt: 00:1[45]:/)).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: "B) 4" }));
    await user.click(screen.getByRole("radio", { name: "B) Qo'lda qoida" }));
    expect(screen.getByText("Javob berilgan: 2 / 2")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: messages["quiz.submit"] }));
    expect(await screen.findByRole("status")).toHaveTextContent("Natija: 1 / 2");
    expect(screen.getByText(/To'g'ri javob: Ma'lumotdan o'rganish/)).toBeInTheDocument();
    expect(calls.find((c) => c.path.endsWith("/submit"))?.body).toEqual({ answers: { 1: 1, 2: 1 } });
    expect(await screen.findByText("Urinishlar: 1 / 3.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: messages["quiz.retry"] })).toBeInTheDocument();
  });

  it("sahifa yangilansa ochiq urinish davom etadi", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      "GET /api/course/topics/M01/quiz": () => ({ status: 200, body: summary({ used_attempts: 1, active_attempt: 7 }) }),
      "GET /api/course/quiz/attempts/7": () => ({ status: 200, body: attempt() }),
    });
    visit("/topics/M01/quiz");
    render(<App />);
    expect(await screen.findByText("2 + 2?", { exact: false })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: messages["quiz.start"] })).toBeNull();
  });

  it("vaqt tugasa avtomatik topshiriladi", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const calls = mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      "GET /api/course/topics/M01/quiz": () => ({ status: 200, body: summary({ used_attempts: 1, active_attempt: 7 }) }),
      "GET /api/course/quiz/attempts/7": () => ({
        status: 200,
        body: attempt({ deadline: new Date(Date.now() + 2000).toISOString() }),
      }),
      "POST /api/course/quiz/attempts/7/submit": () => ({ status: 200, body: RESULT }),
    });
    visit("/topics/M01/quiz");
    render(<App />);
    await screen.findByText("2 + 2?", { exact: false });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3500);
    });
    expect(await screen.findByRole("status")).toHaveTextContent("Natija: 1 / 2");
    expect(calls.filter((c) => c.path.endsWith("/submit"))).toHaveLength(1);
  });

  it("urinishlar tugagan va vaqt o'tgan xabarlari", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      "GET /api/course/topics/M01/quiz": () => ({ status: 200, body: summary({ used_attempts: 0 }) }),
      "POST /api/course/topics/M01/quiz/attempts": () => ({ status: 409, body: { code: "no_attempts" } }),
    });
    const user = userEvent.setup();
    visit("/topics/M01/quiz");
    render(<App />);
    await user.click(await screen.findByRole("button", { name: messages["quiz.start"] }));
    expect(await screen.findByRole("alert")).toHaveTextContent(messages["quiz.noAttempts"]);
  });

  it("urinishlar to'lgan — boshlash tugmasi yo'q, o'tgan natijalar ko'rinadi", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      "GET /api/course/topics/M01/quiz": () => ({
        status: 200,
        body: summary({
          used_attempts: 3,
          settings: { questions: 10, minutes: 15, attempts: 3 },
          attempts: [{ id: 1, number: 1, score: 2, max_score: 2, submitted_at: "2026-11-24T05:00:00Z" }],
        }),
      }),
    });
    visit("/topics/M01/quiz");
    render(<App />);
    expect(await screen.findByText("1-urinish: 2 / 2")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: messages["quiz.retry"] })).toBeNull();
  });

  it("vaqt tugab server rad etsa — xabar", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      "GET /api/course/topics/M01/quiz": () => ({ status: 200, body: summary({ used_attempts: 1, active_attempt: 7 }) }),
      "GET /api/course/quiz/attempts/7": () => ({ status: 200, body: attempt() }),
      "POST /api/course/quiz/attempts/7/submit": () => ({ status: 409, body: { code: "time_over" } }),
    });
    const user = userEvent.setup();
    visit("/topics/M01/quiz");
    render(<App />);
    await user.click(await screen.findByRole("button", { name: messages["quiz.submit"] }));
    expect(await screen.findByRole("alert")).toHaveTextContent(messages["quiz.timeOver"]);
  });

  it("mavzular ro'yxatida test havolasi faqat savollar bo'lsa", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      "GET /api/course/topics": () => ({
        status: 200,
        body: {
          course: { slug: "ml", title: "ML" },
          topics: [
            { code: "M01", title: "A", order: 1, steps: 1, questions: 4, lab: { status: "closed", opens_at: null, closes_at: null } },
            { code: "M02", title: "B", order: 2, steps: 1, questions: 0, lab: { status: "closed", opens_at: null, closes_at: null } },
          ],
        },
      }),
    });
    visit("/topics");
    render(<App />);
    const links = await screen.findAllByRole("link", { name: messages["topics.quiz"] });
    expect(links).toHaveLength(1);
    expect(links[0]).toHaveAttribute("href", "/topics/M01/quiz");
  });
});
