import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import messages from "../i18n/uz.json";
import { mockApi } from "../test-utils";

vi.mock("../lab/CodeEditor", () => ({
  default: ({
    value,
    label,
    onPaste,
  }: {
    value: string;
    label: string;
    onPaste?: (size: number) => boolean;
  }) => (
    <textarea
      aria-label={label}
      defaultValue={value}
      onPaste={(e) => {
        if (onPaste && !onPaste(e.clipboardData.getData("text/plain").length))
          e.preventDefault();
      }}
    />
  ),
}));

const STUDENT = {
  hemis_id: "123456789012",
  full_name: "Test Talaba",
  role: "student",
  direction: 1,
  must_change_password: false,
};
const topics = (lab: Record<string, unknown>) => ({
  status: 200,
  body: {
    course: { slug: "ml", title: "ML" },
    topics: [
      {
        code: "M01",
        title: "ML asoslari",
        order: 1,
        steps: 1,
        questions: 0,
        lab,
      },
    ],
  },
});

function visit(path: string) {
  window.history.replaceState(null, "", path);
}

beforeEach(() => vi.stubGlobal("WebSocket", undefined));
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("laboratoriya sahifasi (LAB-07)", () => {
  it("ochiq: topshiriq paneli, saqlangan notebook, AI joyi", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      "GET /api/labs/M01/work": () => ({
        status: 200,
        body: {
          version: 3,
          notebook: {
            format: 1,
            cells: [{ id: "a", type: "code", source: "print('saqlangan')" }],
          },
          saved_at: "2026-11-24T05:00:00Z",
          policy: "on_time",
        },
      }),
      "GET /api/course/topics": () =>
        topics({ status: "open", opens_at: null, closes_at: null }),
    });
    visit("/labs/M01");
    render(<App />);
    expect(
      await screen.findByRole("heading", {
        name: "M01. ML asoslari — laboratoriya",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("complementary", { name: messages["lab.task.title"] }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("complementary", { name: messages["lab.tutor.title"] }),
    ).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Kod katagi 1" })).toHaveValue(
      "print('saqlangan')",
    );
  });

  it("yopiq: keyingi ochilish vaqti, notebook yo'q", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      "GET /api/labs/M01/work": () => ({
        status: 200,
        body: { version: 0, notebook: null, saved_at: null, policy: "closed" },
      }),
      "GET /api/course/topics": () =>
        topics({
          status: "upcoming",
          opens_at: "2026-12-01T05:00:00Z",
          closes_at: "2026-12-01T06:20:00Z",
        }),
    });
    visit("/labs/M01");
    render(<App />);
    expect(
      await screen.findByText(/Laboratoriya hozir yopiq. Ochiladi:/),
    ).toHaveTextContent("10:00");
    expect(
      screen.queryByRole("region", { name: messages["lab.notebook"] }),
    ).toBeNull();
  });

  it("mashq rejimi belgisi va yopiq (vaqtsiz)", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      "GET /api/labs/M01/work": () => ({
        status: 200,
        body: {
          version: 0,
          notebook: null,
          saved_at: null,
          policy: "practice",
        },
      }),
      "GET /api/course/topics": () => ({ status: 500, body: {} }),
    });
    visit("/labs/M01");
    render(<App />);
    expect(
      await screen.findByText(messages["lab.policy.practice"]),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "M01 — laboratoriya" }),
    ).toBeInTheDocument();
  });

  it("a'zo emas va noma'lum mavzu", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      "GET /api/labs/M01/work": () => ({ status: 403, body: {} }),
      "GET /api/course/topics": () => ({ status: 403, body: {} }),
    });
    visit("/labs/M01");
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      messages["topics.noAccess"],
    );
  });

  it("INT-01: chegaradan katta paste rad etiladi va qayd qilinadi; nazorat rejimi", async () => {
    const events: unknown[] = [];
    const work = (proctored: boolean) => ({
      status: 200,
      body: {
        version: 0,
        notebook: null,
        saved_at: null,
        policy: "on_time",
        paste_limit: 5,
        proctored,
      },
    });
    let proctored = false;
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      "GET /api/labs/M01/work": () => work(proctored),
      "GET /api/course/topics": () =>
        topics({ status: "open", opens_at: null, closes_at: null }),
      "POST /api/labs/M01/events": (call) => {
        events.push(call.body);
        return { status: 201, body: { blocked: false } };
      },
    });
    visit("/labs/M01");
    render(<App />);
    const cell = await screen.findByRole("textbox", { name: "Kod katagi 1" });
    fireEvent.paste(cell, { clipboardData: { getData: () => "abc" } });
    expect(screen.queryByRole("alert")).toBeNull();
    fireEvent.paste(cell, { clipboardData: { getData: () => "abcdef" } });
    expect(screen.getByRole("alert")).toHaveTextContent("ko'pi bilan 5 belgi");
    await waitFor(() => expect(events).toHaveLength(2));
    expect(events[1]).toMatchObject({ kind: "paste", size: 6 });

    cleanup();
    proctored = true;
    render(<App />);
    const again = await screen.findByRole("textbox", { name: "Kod katagi 1" });
    expect(screen.getByText(messages["lab.proctored"])).toBeInTheDocument();
    fireEvent.paste(again, { clipboardData: { getData: () => "a" } });
    expect(screen.getByRole("alert")).toHaveTextContent(
      messages["lab.paste.proctored"],
    );
  });
});
