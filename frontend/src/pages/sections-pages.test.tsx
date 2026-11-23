import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import messages from "../i18n/uz.json";
import { mockApi } from "../test-utils";

const TEACHER = {
  hemis_id: "100000000001",
  full_name: "Ustoz Sinov",
  role: "instructor",
  direction: null,
  must_change_password: false,
};
const SECTION = {
  id: 5,
  name: "ML-21",
  direction: 1,
  capacity: 30,
  join_enabled: true,
  approved_count: 1,
  has_join_token: false,
};
const PENDING = [
  { id: 11, status: "pending", student: { id: 1, hemis_id: "111111111111", full_name: "Ali Valiyev" } },
  { id: 12, status: "pending", student: { id: 2, hemis_id: "222222222222", full_name: "Vali Aliyev" } },
];
const APPROVED = [
  { id: 13, status: "approved", student: { id: 3, hemis_id: "333333333333", full_name: "Hasan Husanov" } },
];

const SETTINGS_VALUES = {
  ai_enabled: true,
  ai_max_mode: "explain",
  practice_after_close: false,
  late_hours: 0,
  chat_enabled: true,
};
const SETTINGS = {
  course_defaults: { ...SETTINGS_VALUES, late_penalty_percent: 0 },
  overrides: { ai_enabled: null, ai_max_mode: null, practice_after_close: null, late_hours: null, chat_enabled: null },
  effective: { ...SETTINGS_VALUES, late_penalty_percent: 0 },
};

function visit(path: string) {
  window.history.replaceState(null, "", path);
}

function sectionApi(extra: Record<string, Parameters<typeof mockApi>[0][string]> = {}) {
  return mockApi({
    "GET /api/auth/me": () => ({ status: 200, body: TEACHER }),
    "GET /api/sections": () => ({ status: 200, body: { results: [SECTION, { ...SECTION, id: 6, name: "ML-22" }] } }),
    "GET /api/sections/5": () => ({ status: 200, body: SECTION }),
    "GET /api/directions": () => ({ status: 200, body: [{ id: 1, name: "Dasturiy injiniring" }] }),
    "GET /api/sections/5/members?status=pending": () => ({ status: 200, body: { results: PENDING } }),
    "GET /api/sections/5/members?status=approved": () => ({ status: 200, body: { results: APPROVED } }),
    "GET /api/sections/5/settings": () => ({ status: 200, body: SETTINGS }),
    "GET /api/sections/5/windows": () => ({ status: 200, body: { server_time: "2026-12-01T05:00:00Z", windows: [] } }),
    "GET /api/sections/5/deadlines": () => ({ status: 200, body: { deadlines: [] } }),
    ...extra,
  });
}

beforeEach(() => {
  document.cookie = "csrftoken=tok";
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("/sections (SEC-01)", () => {
  it("o'qituvchi guruhlarini ko'radi va yangi guruh yaratadi", async () => {
    const calls = sectionApi({
      "POST /api/sections": () => ({ status: 201, body: { ...SECTION, id: 9, name: "ML-23", approved_count: 0 } }),
    });
    visit("/sections");
    render(<App />);
    expect(await screen.findByRole("heading", { name: "ML-21" })).toBeInTheDocument();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(messages["sections.field.name"]), "ML-23");
    await waitFor(() => expect(screen.getByRole("option", { name: "Dasturiy injiniring" })).toBeInTheDocument());
    await user.selectOptions(screen.getByLabelText(messages["field.direction"]), "1");
    await user.click(screen.getByRole("button", { name: messages["sections.create.submit"] }));
    expect(await screen.findByRole("heading", { name: "ML-23" })).toBeInTheDocument();
    const post = calls.find((c) => c.method === "POST" && c.path === "/api/sections");
    expect(post?.body).toEqual({ name: "ML-23", direction: 1, capacity: 30 });
    expect(post?.csrf).toBe("tok");
  });

  it("bo'sh holat va xato xabari", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: TEACHER }),
      "GET /api/sections": () => ({ status: 200, body: { results: [] } }),
      "GET /api/directions": () => ({ status: 200, body: [] }),
    });
    visit("/sections");
    render(<App />);
    expect(await screen.findByText(messages["sections.empty"])).toBeInTheDocument();
  });

  it("maydon xatosi ko'rsatiladi", async () => {
    sectionApi({
      "POST /api/sections": () => ({ status: 400, body: { capacity: ["Sig'im noto'g'ri."] } }),
    });
    visit("/sections");
    render(<App />);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(messages["sections.field.name"]), "X");
    await waitFor(() => expect(screen.getByRole("option", { name: "Dasturiy injiniring" })).toBeInTheDocument());
    await user.selectOptions(screen.getByLabelText(messages["field.direction"]), "1");
    await user.click(screen.getByRole("button", { name: messages["sections.create.submit"] }));
    expect(await screen.findByText("Sig'im noto'g'ri.")).toBeInTheDocument();
  });

  it("talaba /sections ni ko'rmaydi", async () => {
    mockApi({ "GET /api/auth/me": () => ({ status: 200, body: { ...TEACHER, role: "student" } }) });
    visit("/sections");
    render(<App />);
    expect(await screen.findByRole("heading", { name: messages["notFound.title"] })).toBeInTheDocument();
  });
});

describe("/sections/:id (SEC-02, SEC-04, SEC-07)", () => {
  it("yangi havola: URL va QR ko'rinadi, CSRF bilan", async () => {
    const calls = sectionApi({
      "POST /api/sections/5/join-token": () => ({ status: 201, body: { token: "abc", join_path: "/join/abcDEF1234567890xyz" } }),
    });
    visit("/sections/5");
    render(<App />);
    expect(await screen.findByText(messages["section.link.none"])).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: messages["section.link.rotate"] }));
    expect(await screen.findByTestId("join-url")).toHaveTextContent(`${window.location.origin}/join/abcDEF1234567890xyz`);
    const img = screen.getByRole("img", { name: messages["section.link.qrAlt"] });
    expect(img.getAttribute("src")).toMatch(/^data:image\/svg\+xml/);
    expect(calls.find((c) => c.path === "/api/sections/5/join-token")?.csrf).toBe("tok");
  });

  it("havola bor, lekin token ko'rsatilmaydi; o'chirish", async () => {
    const calls = sectionApi({
      "GET /api/sections/5": () => ({ status: 200, body: { ...SECTION, has_join_token: true } }),
      "DELETE /api/sections/5/join-token": () => ({ status: 204 }),
    });
    visit("/sections/5");
    render(<App />);
    expect(await screen.findByText(messages["section.link.hidden"])).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: messages["section.link.disable"] }));
    await waitFor(() => expect(calls.some((c) => c.method === "DELETE")).toBe(true));
  });

  it("so'rovlarni ommaviy tasdiqlash", async () => {
    const calls = sectionApi({
      "POST /api/sections/5/members/decide": () => ({ status: 200, body: { approved: [11, 12], rejected: [], skipped: [] } }),
    });
    visit("/sections/5");
    render(<App />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("checkbox", { name: messages["section.requests.selectAll"] }));
    await user.click(screen.getByRole("button", { name: messages["section.requests.approve"] }));
    expect(await screen.findByText("Tasdiqlandi: 2, rad etildi: 0.")).toBeInTheDocument();
    const post = calls.find((c) => c.path === "/api/sections/5/members/decide");
    expect(post?.body).toEqual({ ids: [11, 12], decision: "approve" });
  });

  it("bitta so'rovni rad etish; sig'im xatosi ko'rsatiladi", async () => {
    const calls = sectionApi({
      "POST /api/sections/5/members/decide": (call) =>
        (call.body as { decision: string }).decision === "approve"
          ? { status: 409, body: { code: "section_full", detail: "Guruh sig'imi yetmaydi." } }
          : { status: 200, body: { approved: [], rejected: [12], skipped: [] } },
    });
    visit("/sections/5");
    render(<App />);
    const user = userEvent.setup();
    await user.click(await screen.findByLabelText("Vali Aliyev"));
    await user.click(screen.getByRole("button", { name: messages["section.requests.approve"] }));
    expect(await screen.findByText("Guruh sig'imi yetmaydi.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: messages["section.requests.reject"] }));
    await waitFor(() =>
      expect(calls.filter((c) => c.path === "/api/sections/5/members/decide").at(-1)?.body).toEqual({
        ids: [12],
        decision: "reject",
      }),
    );
  });

  it("a'zoni boshqa guruhga o'tkazish va chiqarish", async () => {
    const calls = sectionApi({
      "POST /api/sections/5/members/13/move": () => ({ status: 200, body: {} }),
      "POST /api/sections/5/members/13/remove": () => ({ status: 204 }),
    });
    visit("/sections/5");
    render(<App />);
    const user = userEvent.setup();
    const tables = await screen.findAllByRole("table");
    const table = tables[tables.length - 1];
    if (!table) throw new Error("a'zolar jadvali yo'q");
    await within(table).findByText("Hasan Husanov");
    await user.selectOptions(
      screen.getByLabelText(`${messages["section.members.moveTo"]}: Hasan Husanov`),
      "6",
    );
    await waitFor(() =>
      expect(calls.find((c) => c.path.endsWith("/move"))?.body).toEqual({ target_section: 6 }),
    );
    await user.click(screen.getByRole("button", { name: messages["section.members.remove"] }));
    await waitFor(() => expect(calls.some((c) => c.path.endsWith("/remove"))).toBe(true));
  });

  it("sig'im va qo'shilishni saqlash", async () => {
    const calls = sectionApi({
      "PATCH /api/sections/5": () => ({ status: 200, body: { ...SECTION, capacity: 40, join_enabled: false } }),
    });
    visit("/sections/5");
    render(<App />);
    const user = userEvent.setup();
    const capacity = await screen.findByLabelText(messages["sections.field.capacity"]);
    await user.clear(capacity);
    await user.type(capacity, "40");
    await user.click(screen.getByLabelText(messages["section.joinEnabled"]));
    await user.click(screen.getByRole("button", { name: messages["section.save"] }));
    expect(await screen.findByText(messages["section.saved"])).toBeInTheDocument();
    expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ capacity: 40, join_enabled: false });
  });

  it("begona yoki yo'q guruh — 'topilmadi'", async () => {
    sectionApi({ "GET /api/sections/5": () => ({ status: 404, body: {} }) });
    visit("/sections/5");
    render(<App />);
    expect(await screen.findByRole("heading", { name: messages["section.notFound"] })).toBeInTheDocument();
  });
});

describe("xato yo'llari", () => {
  it("guruhlar yuklanmasa xabar", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: TEACHER }),
      "GET /api/sections": () => ({ status: 500 }),
      "GET /api/directions": () => ({ status: 500 }),
    });
    visit("/sections");
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent(messages["sections.loadError"]);
  });

  it("yaratishda tarmoq xatosi va umumiy xato", async () => {
    let attempt = 0;
    sectionApi({
      "POST /api/sections": () => {
        attempt += 1;
        if (attempt === 1) throw new TypeError("network");
        return { status: 400, body: {} };
      },
    });
    visit("/sections");
    render(<App />);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(messages["sections.field.name"]), "X");
    await waitFor(() => expect(screen.getByRole("option", { name: "Dasturiy injiniring" })).toBeInTheDocument());
    await user.selectOptions(screen.getByLabelText(messages["field.direction"]), "1");
    const submit = screen.getByRole("button", { name: messages["sections.create.submit"] });
    await user.click(submit);
    expect(await screen.findByRole("alert")).toHaveTextContent(messages["common.networkError"]);
    await user.click(submit);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(messages["common.unexpectedError"]));
  });

  it("havola amallari muvaffaqiyatsiz — xabar; nusxa olish", async () => {
    const writeText = vi.fn(async () => undefined);
    let rotateOk = true;
    sectionApi({
      "GET /api/sections/5": () => ({ status: 200, body: { ...SECTION, has_join_token: true } }),
      "POST /api/sections/5/join-token": () =>
        rotateOk
          ? { status: 201, body: { token: "t", join_path: "/join/abcDEF1234567890xyz" } }
          : { status: 500 },
      "DELETE /api/sections/5/join-token": () => ({ status: 500 }),
    });
    visit("/sections/5");
    render(<App />);
    const user = userEvent.setup();
    // userEvent o'z clipboard'ini o'rnatadi — undan keyin almashtiramiz.
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    await user.click(await screen.findByRole("button", { name: messages["section.link.rotate"] }));
    await user.click(await screen.findByRole("button", { name: messages["section.link.copy"] }));
    expect(writeText).toHaveBeenCalled();
    expect(await screen.findByText(messages["section.link.copied"])).toBeInTheDocument();
    rotateOk = false;
    await user.click(screen.getByRole("button", { name: messages["section.link.rotate"] }));
    expect(await screen.findByRole("alert")).toHaveTextContent(messages["common.unexpectedError"]);
    await user.click(screen.getByRole("button", { name: messages["section.link.disable"] }));
    expect(screen.getByRole("alert")).toHaveTextContent(messages["common.unexpectedError"]);
  });

  it("nusxa olish rad etilsa sahifa buzilmaydi", async () => {
    sectionApi({
      "POST /api/sections/5/join-token": () => ({ status: 201, body: { token: "t", join_path: "/join/abcDEF1234567890xyz" } }),
    });
    visit("/sections/5");
    render(<App />);
    const user = userEvent.setup();
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: vi.fn(async () => Promise.reject(new Error("no"))) },
      configurable: true,
    });
    await user.click(await screen.findByRole("button", { name: messages["section.link.rotate"] }));
    await user.click(await screen.findByRole("button", { name: messages["section.link.copy"] }));
    expect(screen.queryByText(messages["section.link.copied"])).not.toBeInTheDocument();
  });

  it("saqlash, qaror va a'zo amalidagi xatolar", async () => {
    sectionApi({
      "PATCH /api/sections/5": () => ({ status: 400, body: { capacity: ["Kam."] } }),
      "POST /api/sections/5/members/decide": () => ({ status: 500 }),
      "POST /api/sections/5/members/13/remove": () => ({ status: 409, body: { detail: "Mumkin emas." } }),
    });
    visit("/sections/5");
    render(<App />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: messages["section.save"] }));
    expect(await screen.findByText("Kam.")).toBeInTheDocument();
    await user.click(await screen.findByLabelText("Ali Valiyev"));
    await user.click(screen.getByLabelText("Ali Valiyev"));
    await user.click(screen.getByLabelText("Ali Valiyev"));
    await user.click(screen.getByRole("button", { name: messages["section.requests.reject"] }));
    expect(await screen.findByText(messages["common.unexpectedError"])).toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: messages["section.members.remove"] }));
    expect(await screen.findByText("Mumkin emas.")).toBeInTheDocument();
  });

  it("saqlashda umumiy xato; bo'sh so'rov va a'zo ro'yxati; tanlovni bekor qilish", async () => {
    sectionApi({
      "PATCH /api/sections/5": () => ({ status: 500 }),
      "GET /api/sections/5/members?status=pending": () => ({ status: 200, body: { results: [] } }),
      "GET /api/sections/5/members?status=approved": () => ({ status: 500 }),
    });
    visit("/sections/5");
    render(<App />);
    const user = userEvent.setup();
    expect(await screen.findByText(messages["section.requests.empty"])).toBeInTheDocument();
    expect(await screen.findByText(messages["section.members.empty"])).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: messages["section.save"] }));
    expect(await screen.findByRole("alert")).toHaveTextContent(messages["common.unexpectedError"]);
  });

  it("hammasini belgilash va bekor qilish", async () => {
    sectionApi();
    visit("/sections/5");
    render(<App />);
    const user = userEvent.setup();
    const all = await screen.findByRole("checkbox", { name: messages["section.requests.selectAll"] });
    await user.click(all);
    expect(screen.getByLabelText("Ali Valiyev")).toBeChecked();
    await user.click(all);
    expect(screen.getByLabelText("Ali Valiyev")).not.toBeChecked();
    expect(screen.getByRole("button", { name: messages["section.requests.approve"] })).toBeDisabled();
  });
});
