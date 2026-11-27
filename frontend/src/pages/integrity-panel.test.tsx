import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import App from "../App";
import messages from "../i18n/uz.json";
import { mockApi } from "../test-utils";
import type { IntegrityRow } from "./SectionIntegrityPanel";

const TEACHER = { hemis_id: "100000000001", full_name: "Ustoz", role: "instructor", direction: null, must_change_password: false };
const SECTION = { id: 5, name: "ML-21", direction: 1, capacity: 30, join_enabled: true, approved_count: 1, has_join_token: false };
const VALUES = { ai_enabled: true, ai_max_mode: "explain", practice_after_close: false, late_hours: 0, chat_enabled: true, late_penalty_percent: 0 };
const ROWS = [
  { topic: { code: "M01", title: "Kirish", order: 1 }, mode: "closed", proctored: false, state: { status: "closed", opens_at: null, closes_at: null } },
  { topic: { code: "M07", title: "Logistik regressiya", order: 7 }, mode: "open_now", proctored: true, state: { status: "open", opens_at: null, closes_at: null } },
];
const FLAGGED: IntegrityRow = {
  student_id: 42,
  full_name: "Aliyev Vali",
  paste_blocked: 2,
  tab_hidden: 3,
  understanding_failed: 1,
  fast_full_score: true,
  note: null,
};
const NOTE_URL = "/api/sections/5/labs/M07/students/42/integrity-note";

function api(students: () => IntegrityRow[], extra: Parameters<typeof mockApi>[0] = {}) {
  return mockApi({
    "GET /api/auth/me": () => ({ status: 200, body: TEACHER }),
    "GET /api/sections": () => ({ status: 200, body: { results: [SECTION] } }),
    "GET /api/sections/5": () => ({ status: 200, body: SECTION }),
    "GET /api/sections/5/members?status=pending": () => ({ status: 200, body: { results: [] } }),
    "GET /api/sections/5/members?status=approved": () => ({ status: 200, body: { results: [] } }),
    "GET /api/sections/5/settings": () => ({ status: 200, body: { course_defaults: VALUES, overrides: {}, effective: VALUES } }),
    "GET /api/sections/5/windows": () => ({ status: 200, body: { server_time: "2026-12-01T05:10:00Z", windows: ROWS } }),
    "GET /api/sections/5/deadlines": () => ({ status: 200, body: { deadlines: [] } }),
    "GET /api/sections/5/labs/M07/integrity": () => ({ status: 200, body: { students: students() } }),
    "GET /api/sections/5/labs/M01/integrity": () => ({ status: 200, body: { students: [] } }),
    ...extra,
  });
}

beforeEach(() => {
  document.cookie = "csrftoken=tok";
  window.history.replaceState(null, "", "/sections/5");
});
afterEach(() => cleanup());

describe("shubhali holatlar (INT-04, INT-05)", () => {
  it("mavzu tanlanganda belgilar jadvali; jazo yo'qligi aytiladi", async () => {
    api(() => [FLAGGED]);
    render(<App />);
    const user = userEvent.setup();
    const panel = (await screen.findByRole("heading", { name: messages["integrity.title"] })).closest("section");
    expect(panel).not.toBeNull();
    const scope = within(panel as HTMLElement);
    expect(scope.getByText(messages["integrity.hint"])).toBeInTheDocument();
    await user.selectOptions(await scope.findByRole("combobox"), "M07");
    const row = (await scope.findByRole("rowheader", { name: "Aliyev Vali" })).closest("tr") as HTMLElement;
    const cells = within(row).getAllByRole("cell").map((c) => c.textContent);
    expect(cells.slice(0, 4)).toEqual(["2", "3", "1", messages["integrity.yes"]]);
  });

  it("bo'sh ro'yxat xabari", async () => {
    api(() => []);
    render(<App />);
    const user = userEvent.setup();
    const panel = (await screen.findByRole("heading", { name: messages["integrity.title"] })).closest("section") as HTMLElement;
    await user.selectOptions(await within(panel).findByRole("combobox"), "M01");
    expect(await within(panel).findByText(messages["integrity.empty"])).toBeInTheDocument();
  });

  it("izoh saqlanadi va ro'yxat yangilanadi; xato ko'rsatiladi", async () => {
    let note: IntegrityRow["note"] = null;
    let fail = true;
    const calls = api(() => [{ ...FLAGGED, note }], {
      [`PUT ${NOTE_URL}`]: (c) => {
        if (fail) {
          fail = false;
          return { status: 400, body: { text: ["Juda uzun."] } };
        }
        note = { text: (c.body as { text: string }).text, author: "Ustoz", updated_at: "2026-12-01T05:20:00Z" };
        return { status: 200, body: note };
      },
    });
    render(<App />);
    const user = userEvent.setup();
    const panel = (await screen.findByRole("heading", { name: messages["integrity.title"] })).closest("section") as HTMLElement;
    const scope = within(panel);
    await user.selectOptions(await scope.findByRole("combobox"), "M07");
    const box = await scope.findByRole("textbox", { name: messages["integrity.note"] });
    const save = scope.getByRole("button", { name: messages["integrity.saveNote"] });
    expect(save).toBeDisabled();
    await user.type(box, "Sinfda so'rayman");
    await user.click(save);
    expect(await scope.findByRole("alert")).toHaveTextContent("Juda uzun.");
    await user.click(save);
    expect(await scope.findByText(/^Ustoz, /)).toBeInTheDocument();
    const put = calls.filter((c) => c.path === NOTE_URL);
    expect(put.at(-1)?.body).toEqual({ text: "Sinfda so'rayman" });
    expect(put.at(-1)?.csrf).toBe("tok");
  });
});
