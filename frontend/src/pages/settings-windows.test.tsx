import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { localToIso, showTime } from "../datetime";
import messages from "../i18n/uz.json";
import { mockApi } from "../test-utils";

const TEACHER = { hemis_id: "100000000001", full_name: "Ustoz", role: "instructor", direction: null, must_change_password: false };
const SECTION = { id: 5, name: "ML-21", direction: 1, capacity: 30, join_enabled: true, approved_count: 0, has_join_token: false };
const VALUES = { ai_enabled: true, ai_max_mode: "explain", practice_after_close: false, late_hours: 0, chat_enabled: true };
type Overrides = Record<keyof typeof VALUES, boolean | string | number | null>;
const NULLS: Overrides = { ai_enabled: null, ai_max_mode: null, practice_after_close: null, late_hours: null, chat_enabled: null };
const settings = (overrides: Overrides = NULLS, effective: Record<string, unknown> = VALUES) => ({
  course_defaults: { ...VALUES, late_penalty_percent: 0 },
  overrides,
  effective: { ...effective, late_penalty_percent: 0 },
});
const ROWS = [
  { topic: { code: "M01", title: "Kirish", order: 1 }, mode: "closed", proctored: false, state: { status: "closed", opens_at: null, closes_at: null } },
  { topic: { code: "M02", title: "Regressiya", order: 2 }, mode: "open_now", proctored: false, state: { status: "open", opens_at: "2026-12-01T05:00:00Z", closes_at: "2026-12-01T06:20:00Z" } },
  { topic: { code: "M03", title: "Tasniflash", order: 3 }, mode: "scheduled", proctored: true, state: { status: "upcoming", opens_at: "2026-12-08T05:00:00Z", closes_at: "2026-12-08T06:20:00Z" } },
];

type Handlers = Parameters<typeof mockApi>[0];

function api(extra: Handlers = {}) {
  return mockApi({
    "GET /api/auth/me": () => ({ status: 200, body: TEACHER }),
    "GET /api/sections": () => ({ status: 200, body: { results: [SECTION] } }),
    "GET /api/sections/5": () => ({ status: 200, body: SECTION }),
    "GET /api/sections/5/members?status=pending": () => ({ status: 200, body: { results: [] } }),
    "GET /api/sections/5/members?status=approved": () => ({ status: 200, body: { results: [] } }),
    "GET /api/sections/5/settings": () => ({ status: 200, body: settings() }),
    "GET /api/sections/5/windows": () => ({ status: 200, body: { server_time: "2026-12-01T05:10:00Z", windows: ROWS } }),
    "GET /api/sections/5/deadlines": () => ({ status: 200, body: { deadlines: [] } }),
    ...extra,
  });
}

beforeEach(() => {
  document.cookie = "csrftoken=tok";
  window.history.replaceState(null, "", "/sections/5");
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("datetime yordamchilari", () => {
  it("Asia/Tashkent'da ko'rsatadi; bo'sh qiymat", () => {
    expect(showTime("2026-12-01T05:00:00Z")).toContain("10:00");
    expect(showTime(null)).toBe("—");
    expect(localToIso("")).toBeNull();
    expect(localToIso("emas")).toBeNull();
    expect(localToIso("2026-12-01T10:00")).toMatch(/^2026-12-01T/);
  });
});

describe("guruh sozlamalari (SET-01..05)", () => {
  it("AI tutorni bir tugmada o'chiradi (SET-02)", async () => {
    const calls = api({
      "POST /api/sections/5/ai/disable": () => ({ status: 200, body: settings({ ...NULLS, ai_enabled: false }, { ...VALUES, ai_enabled: false }) }),
    });
    render(<App />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: messages["settings.aiDisable"] }));
    expect(await screen.findByText("AI tutor hozir: O'chirilgan")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: messages["settings.aiEnable"] })).toBeInTheDocument();
    expect(calls.find((c) => c.path.endsWith("/ai/disable"))?.csrf).toBe("tok");
  });

  it("override saqlanadi; kurs qiymatiga qaytarish null yuboradi", async () => {
    const calls = api({
      "PATCH /api/sections/5/settings": (c) => ({ status: 200, body: settings(c.body as typeof NULLS) }),
    });
    render(<App />);
    const user = userEvent.setup();
    await user.selectOptions(await screen.findByLabelText(messages["settings.ai_max_mode"]), "guide");
    await user.selectOptions(screen.getByLabelText(messages["settings.chat_enabled"]), "false");
    await user.type(screen.getByLabelText(messages["settings.late_hours"]), "24");
    await user.click(screen.getByRole("button", { name: messages["settings.save"] }));
    expect(await screen.findByText(messages["settings.saved"])).toBeInTheDocument();
    expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({
      ai_enabled: null,
      ai_max_mode: "guide",
      practice_after_close: null,
      late_hours: 24,
      chat_enabled: false,
    });
    await user.selectOptions(screen.getByLabelText(messages["settings.ai_max_mode"]), "");
    await user.clear(screen.getByLabelText(messages["settings.late_hours"]));
    await user.click(screen.getByRole("button", { name: messages["settings.save"] }));
    await waitFor(() =>
      expect(calls.filter((c) => c.method === "PATCH").at(-1)?.body).toMatchObject({ ai_max_mode: null, late_hours: null }),
    );
  });

  it("saqlash xatosi va yuklash xatosi", async () => {
    api({ "PATCH /api/sections/5/settings": () => ({ status: 400, body: { late_hours: ["Juda katta."] } }) });
    render(<App />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: messages["settings.save"] }));
    expect(await screen.findByText("Juda katta.")).toBeInTheDocument();
    cleanup();
    api({ "GET /api/sections/5/settings": () => ({ status: 500 }) });
    render(<App />);
    await waitFor(() => expect(screen.getAllByRole("alert").length).toBeGreaterThan(0));
  });
});

describe("kirish oynalari (ACC-03, ACC-04, ACC-09)", () => {
  it("har mavzu holati ko'rinadi", async () => {
    api();
    render(<App />);
    const table = await screen.findByRole("table");
    expect(within(table).getByText("M01 Kirish").closest("tr")).toHaveTextContent(messages["windows.closed"]);
    expect(within(table).getByText("M02 Regressiya").closest("tr")).toHaveTextContent(/Ochiq · .*11:20 gacha/);
    expect(within(table).getByText("M03 Tasniflash").closest("tr")).toHaveTextContent(/Ochiladi: .*10:00/);
  });

  it("hozir ochish (N daqiqa), yopish va jadvalga qo'yish", async () => {
    const calls = api({
      "POST /api/sections/5/windows/M01/open-now": () => ({ status: 200, body: ROWS[1] }),
      "POST /api/sections/5/windows/M02/close": () => ({ status: 200, body: ROWS[0] }),
      "PUT /api/sections/5/windows/M01": () => ({ status: 200, body: ROWS[2] }),
    });
    render(<App />);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(`${messages["windows.minutes"]}: M01`), "80");
    const m01 = screen.getByText("M01 Kirish").closest("tr") as HTMLElement;
    await user.click(within(m01).getByRole("button", { name: messages["windows.openNow"] }));
    const m02 = screen.getByText("M02 Regressiya").closest("tr") as HTMLElement;
    await user.click(within(m02).getByRole("button", { name: messages["windows.close"] }));
    await user.type(screen.getByLabelText(`${messages["windows.opensAt"]}: M01`), "2026-12-01T10:00");
    await user.type(screen.getByLabelText(`${messages["windows.closesAt"]}: M01`), "2026-12-01T11:20");
    await user.click(within(m01).getByLabelText(messages["windows.proctored"]));
    await user.click(within(m01).getByRole("button", { name: messages["windows.schedule"] }));
    await waitFor(() => expect(calls.some((c) => c.method === "PUT")).toBe(true));
    expect(calls.find((c) => c.path.endsWith("/M01/open-now"))?.body).toEqual({ minutes: 80 });
    expect(calls.some((c) => c.path.endsWith("/M02/close"))).toBe(true);
    expect(calls.find((c) => c.method === "PUT")?.body).toMatchObject({ mode: "scheduled", proctored: true });
  });

  it("server xatosi ko'rsatiladi (masalan, noto'g'ri vaqt)", async () => {
    api({
      "PUT /api/sections/5/windows/M01": () => ({ status: 400, body: { non_field_errors: ["Yopilish vaqti ochilishdan keyin bo'lishi kerak."] } }),
      "POST /api/sections/5/windows/M01/open-now": () => ({ status: 500 }),
    });
    render(<App />);
    const user = userEvent.setup();
    const m01 = (await screen.findByText("M01 Kirish")).closest("tr") as HTMLElement;
    await user.click(within(m01).getByRole("button", { name: messages["windows.schedule"] }));
    expect(await screen.findByText("Yopilish vaqti ochilishdan keyin bo'lishi kerak.")).toBeInTheDocument();
    await user.click(within(m01).getByRole("button", { name: messages["windows.openNow"] }));
    expect(await screen.findByText(messages["common.unexpectedError"])).toBeInTheDocument();
  });

  it("mavzu yo'q va yuklash xatosi", async () => {
    api({ "GET /api/sections/5/windows": () => ({ status: 200, body: { server_time: "x", windows: [] } }) });
    render(<App />);
    expect(await screen.findByText(messages["windows.empty"])).toBeInTheDocument();
  });

  it("haftalik jadval: oldindan ko'rish, keyin saqlash; mavjud oynalar xatosi", async () => {
    let attempt = 0;
    const calls = api({
      "POST /api/sections/5/windows/plan": (c) => {
        const body = c.body as { preview: boolean; overwrite: boolean };
        if (!body.preview && !body.overwrite && attempt++ === 0)
          return { status: 409, body: { code: "windows_exist", detail: "Bu mavzularda oyna bor.", topics: ["M02"] } };
        return { status: 200, body: { plan: [{ topic: "M01", opens_at: "2026-12-01T05:00:00Z", closes_at: "2026-12-01T06:20:00Z" }], saved: !body.preview } };
      },
    });
    render(<App />);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(messages["plan.start"]), "2026-12-01");
    expect(screen.getByRole("button", { name: messages["plan.apply"] })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: messages["plan.preview"] }));
    expect(await screen.findByText(/M01: .*10:00/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: messages["plan.apply"] }));
    expect(await screen.findByText("Bu mavzularda oyna bor.")).toBeInTheDocument();
    await user.click(screen.getByLabelText(messages["plan.overwrite"]));
    await user.click(screen.getByRole("button", { name: messages["plan.apply"] }));
    expect(await screen.findByText(messages["plan.saved"])).toBeInTheDocument();
    const posts = calls.filter((c) => c.path.endsWith("/windows/plan"));
    expect(posts[0]?.body).toEqual({
      slots: [{ weekday: 1, time: "10:00", minutes: 80 }],
      start_date: "2026-12-01",
      preview: true,
      overwrite: false,
    });
    expect(posts.at(-1)?.body).toMatchObject({ preview: false, overwrite: true });
  });
});

describe("mustaqil topshiriq muddatlari (ACC-10)", () => {
  it("muddat qo'yish va olib tashlash; xato", async () => {
    let list: { assignment: string; due_at: string }[] = [];
    const calls = api({
      "GET /api/sections/5/deadlines": () => ({ status: 200, body: { deadlines: list } }),
      "PUT /api/sections/5/deadlines/A01": (c) => {
        list = [{ assignment: "A01", due_at: (c.body as { due_at: string }).due_at }];
        return { status: 200, body: list[0] };
      },
      "DELETE /api/sections/5/deadlines/A01": () => {
        list = [];
        return { status: 204 };
      },
      "PUT /api/sections/5/deadlines/X1": () => ({ status: 404, body: {} }),
    });
    render(<App />);
    const user = userEvent.setup();
    expect(await screen.findByText(messages["deadlines.empty"])).toBeInTheDocument();
    await user.type(screen.getByLabelText(messages["deadlines.code"]), "a01");
    await user.type(screen.getByLabelText(messages["deadlines.due"]), "2026-12-10T23:59");
    await user.click(screen.getByRole("button", { name: messages["deadlines.save"] }));
    expect(await screen.findByText(/A01: /)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: messages["deadlines.remove"] }));
    expect(await screen.findByText(messages["deadlines.empty"])).toBeInTheDocument();
    await user.clear(screen.getByLabelText(messages["deadlines.code"]));
    await user.type(screen.getByLabelText(messages["deadlines.code"]), "x1");
    await user.click(screen.getByRole("button", { name: messages["deadlines.save"] }));
    expect(await screen.findByText(messages["common.unexpectedError"])).toBeInTheDocument();
    expect(calls.find((c) => c.path.endsWith("/A01") && c.method === "PUT")?.csrf).toBe("tok");
  });
});
