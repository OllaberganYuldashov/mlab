import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import messages from "../i18n/uz.json";
import { safeNext } from "../nav";
import { mockApi } from "../test-utils";
import { formatLeft } from "../time";

const TOKEN = "abcDEF1234567890xyz";
const STUDENT = {
  hemis_id: "123456789012",
  full_name: "Test Talaba",
  role: "student",
  direction: 1,
  must_change_password: false,
};
const PREVIEW = { section: "ML-21", instructor: "Ustoz Sinov", join_enabled: true, is_full: false };

function visit(path: string) {
  window.history.replaceState(null, "", path);
}

class FakeSocket {
  static last: FakeSocket | null = null;
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  url: string;
  closed = false;
  constructor(url: string) {
    this.url = url;
    FakeSocket.last = this;
  }
  close() {
    this.closed = true;
  }
}

beforeEach(() => {
  document.cookie = "csrftoken=tok";
  FakeSocket.last = null;
  vi.stubGlobal("WebSocket", FakeSocket);
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("safeNext (open redirect'ga qarshi)", () => {
  it.each([
    [`/join/${TOKEN}`, `/join/${TOKEN}`],
    ["https://evil.example/join/x", null],
    ["//evil.example", null],
    ["/\\evil", null],
    ["/admin/", null],
    ["/join/short", null],
    [null, null],
  ])("%s -> %s", (raw, expected) => {
    expect(safeNext(raw)).toBe(expected);
  });
});

describe("formatLeft", () => {
  it("kun/soat/daqiqa va soat:daqiqa:soniya", () => {
    expect(formatLeft((2 * 86400 + 3 * 3600 + 4 * 60) * 1000)).toBe("2 kun 3 soat 4 daqiqa");
    expect(formatLeft((1 * 3600 + 2 * 60 + 3) * 1000)).toBe("01:02:03");
    expect(formatLeft(-5000)).toBe("00:00:00");
  });
});

describe("/join/<token> (SEC-03)", () => {
  it("kirmagan foydalanuvchi guruhni va kirish havolalarini (qaytish manzili bilan) ko'radi", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 403, body: {} }),
      [`GET /api/join/${TOKEN}`]: () => ({ status: 200, body: PREVIEW }),
    });
    visit(`/join/${TOKEN}`);
    render(<App />);
    expect(await screen.findByText("Guruh: ML-21")).toBeInTheDocument();
    expect(screen.getByText("O'qituvchi: Ustoz Sinov")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: messages["nav.login"] })).toHaveAttribute(
      "href",
      `/login?next=${encodeURIComponent(`/join/${TOKEN}`)}`,
    );
    expect(screen.getByRole("link", { name: messages["nav.register"] })).toHaveAttribute(
      "href",
      `/register?next=${encodeURIComponent(`/join/${TOKEN}`)}`,
    );
  });

  it("noto'g'ri havola", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 403, body: {} }),
      [`GET /api/join/${TOKEN}`]: () => ({ status: 404, body: {} }),
    });
    visit(`/join/${TOKEN}`);
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent(messages["join.invalid"]);
  });

  it("talaba so'rov yuboradi (CSRF bilan)", async () => {
    const calls = mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      [`GET /api/join/${TOKEN}`]: () => ({ status: 200, body: PREVIEW }),
      [`POST /api/join/${TOKEN}`]: () => ({ status: 201, body: { status: "pending" } }),
    });
    visit(`/join/${TOKEN}`);
    render(<App />);
    await userEvent.setup().click(await screen.findByRole("button", { name: messages["join.submit"] }));
    expect(await screen.findByRole("status")).toHaveTextContent(messages["join.sent"]);
    expect(calls.find((c) => c.method === "POST")?.csrf).toBe("tok");
  });

  it("server rad etsa (409) aniq xabar; bekor token (404)", async () => {
    let answer = 409;
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      [`GET /api/join/${TOKEN}`]: () => ({ status: 200, body: PREVIEW }),
      [`POST /api/join/${TOKEN}`]: () =>
        answer === 409
          ? { status: 409, body: { code: "other_section", detail: "Siz boshqa guruhga a'zosiz." } }
          : { status: 404, body: {} },
    });
    visit(`/join/${TOKEN}`);
    render(<App />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: messages["join.submit"] }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Siz boshqa guruhga a'zosiz.");
    answer = 404;
    await user.click(screen.getByRole("button", { name: messages["join.submit"] }));
    expect(await screen.findByText(messages["join.invalid"])).toBeInTheDocument();
  });

  it("to'lgan yoki o'chirilgan guruhda tugma faol emas; o'qituvchiga izoh", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      [`GET /api/join/${TOKEN}`]: () => ({ status: 200, body: { ...PREVIEW, is_full: true, join_enabled: false } }),
    });
    visit(`/join/${TOKEN}`);
    render(<App />);
    expect(await screen.findByText(messages["join.full"])).toBeInTheDocument();
    expect(screen.getByText(messages["join.disabled"])).toBeInTheDocument();
    expect(screen.getByRole("button", { name: messages["join.submit"] })).toBeDisabled();
    cleanup();
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: { ...STUDENT, role: "instructor" } }),
      [`GET /api/join/${TOKEN}`]: () => ({ status: 200, body: PREVIEW }),
    });
    render(<App />);
    expect(await screen.findByText(messages["join.onlyStudents"])).toBeInTheDocument();
  });

  it("tarmoq xatosi", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string) => {
        if (input === "/api/auth/me") return new Response(null, { status: 403 });
        throw new TypeError("network");
      }),
    );
    visit(`/join/${TOKEN}`);
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent(messages["common.networkError"]);
  });

  it("kirgandan keyin havola sahifasiga qaytadi", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 403, body: {} }),
      "POST /api/auth/login": () => ({ status: 200, body: STUDENT }),
      [`GET /api/join/${TOKEN}`]: () => ({ status: 200, body: PREVIEW }),
    });
    visit(`/login?next=${encodeURIComponent(`/join/${TOKEN}`)}`);
    render(<App />);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(messages["field.hemisId"]), "123456789012");
    await user.type(screen.getByLabelText(messages["field.password"]), "x");
    await user.click(screen.getByRole("button", { name: messages["login.submit"] }));
    await waitFor(() => expect(window.location.pathname).toBe(`/join/${TOKEN}`));
  });

  it("begona `next` e'tiborsiz — bosh sahifa", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 403, body: {} }),
      "POST /api/auth/login": () => ({ status: 200, body: { ...STUDENT, role: "instructor" } }),
    });
    visit("/login?next=https://evil.example");
    render(<App />);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(messages["field.hemisId"]), "1");
    await user.type(screen.getByLabelText(messages["field.password"]), "x");
    await user.click(screen.getByRole("button", { name: messages["login.submit"] }));
    await waitFor(() => expect(window.location.pathname).toBe("/"));
  });
});

describe("talaba bosh sahifasi (SEC-04, ACC-05)", () => {
  const home = (membership: unknown, next: unknown = { server_time: new Date().toISOString(), open: [], next: null }) =>
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      "GET /api/me/membership": () => ({ status: 200, body: { membership } }),
      "GET /api/me/next-window": () => ({ status: 200, body: next }),
    });

  it("a'zolik yo'q", async () => {
    home(null);
    visit("/");
    render(<App />);
    expect(await screen.findByText(messages["membership.none"])).toBeInTheDocument();
    expect(FakeSocket.last).toBeNull();
  });

  it("kutilmoqda", async () => {
    home({ status: "pending", section: "ML-21", instructor: "Ustoz" });
    visit("/");
    render(<App />);
    expect(await screen.findByText(/tasdig'ini kutmoqda/)).toBeInTheDocument();
  });

  it("tasdiqlangan: ochiq laboratoriya va keyingi mavzu vaqti, WebSocket xabarida yangilanadi", async () => {
    const now = Date.now();
    let opened = false;
    const calls = mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      "GET /api/me/membership": () => ({
        status: 200,
        body: { membership: { status: "approved", section: "ML-21", instructor: "Ustoz" } },
      }),
      "GET /api/me/next-window": () => ({
        status: 200,
        body: {
          server_time: new Date(now).toISOString(),
          open: opened
            ? [{ topic: { code: "M02", title: "Regressiya" }, state: { opens_at: new Date(now).toISOString(), closes_at: new Date(now + 3600_000).toISOString() } }]
            : [],
          next: opened
            ? null
            : { topic: { code: "M02", title: "Regressiya" }, state: { opens_at: new Date(now + 2 * 86400_000 + 3600_000).toISOString(), closes_at: null } },
        },
      }),
    });
    visit("/");
    render(<App />);
    expect(await screen.findByText(/a'zosisiz/)).toBeInTheDocument();
    expect(await screen.findByText(/Keyingi: M02 Regressiya — ochilishiga 2 kun 1 soat/)).toBeInTheDocument();
    await waitFor(() => expect(FakeSocket.last?.url).toMatch(/\/ws\/student$/));
    opened = true;
    act(() => FakeSocket.last?.onmessage?.({ data: "{}" }));
    expect(await screen.findByText(/Hozir ochiq: M02 Regressiya/)).toBeInTheDocument();
    expect(screen.getByText(/yopilishiga/)).toBeInTheDocument();
    expect(calls.filter((c) => c.path === "/api/me/next-window").length).toBeGreaterThanOrEqual(2);
  });

  it("ulanish uzilsa qayta ulanadi; laboratoriya yo'q", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    home({ status: "approved", section: "ML-21", instructor: "Ustoz" });
    visit("/");
    render(<App />);
    expect(await screen.findByText(messages["lab.none"])).toBeInTheDocument();
    await waitFor(() => expect(FakeSocket.last).not.toBeNull());
    const first = FakeSocket.last;
    act(() => first?.onopen?.());
    act(() => first?.onclose?.());
    await act(async () => {
      vi.advanceTimersByTime(1100);
    });
    expect(FakeSocket.last).not.toBe(first);
  });

  it("rejalashtirilgan ochilish lahzasida holat qayta so'raladi", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const now = Date.now();
    const calls = home(
      { status: "approved", section: "ML-21", instructor: "Ustoz" },
      {
        server_time: new Date(now).toISOString(),
        open: [],
        next: { topic: { code: "M03", title: "T" }, state: { opens_at: new Date(now + 1500).toISOString(), closes_at: null } },
      },
    );
    visit("/");
    render(<App />);
    expect(await screen.findByText(/Keyingi: M03/)).toBeInTheDocument();
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });
    await waitFor(() =>
      expect(calls.filter((c) => c.path === "/api/me/next-window").length).toBeGreaterThanOrEqual(2),
    );
  });
});

describe("ro'yxatdan o'tish `next` bilan", () => {
  it("muvaffaqiyatdan keyin login sahifasiga `next` uzatiladi", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 403, body: {} }),
      "GET /api/auth/csrf": () => ({ status: 204 }),
      "GET /api/directions": () => ({ status: 200, body: [{ id: 7, name: "DI" }] }),
      "GET /api/policy": () => ({ status: 200, body: { version: "2026-11-22" } }),
      "POST /api/auth/register": () => ({ status: 201, body: {} }),
    });
    visit(`/register?next=${encodeURIComponent(`/join/${TOKEN}`)}`);
    render(<App />);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(messages["field.hemisId"]), "123456789012");
    await user.type(screen.getByLabelText(messages["field.fullName"]), "Test");
    await waitFor(() => expect(screen.getByRole("option", { name: "DI" })).toBeInTheDocument());
    await user.selectOptions(screen.getByLabelText(messages["field.direction"]), "7");
    await user.type(screen.getByLabelText(messages["field.password"]), `p-${crypto.randomUUID()}`);
    await user.click(screen.getByLabelText(messages["register.consentCheckbox"]));
    await user.click(screen.getByRole("button", { name: messages["register.submit"] }));
    await waitFor(() => expect(window.location.search).toContain(`next=${encodeURIComponent(`/join/${TOKEN}`)}`));
  });
});
