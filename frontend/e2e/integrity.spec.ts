import { expect, test } from "@playwright/test";
import messages from "../src/i18n/uz.json" with { type: "json" };

/**
 * INT-04, INT-05 (I3-14): o'qituvchi mavzu bo'yicha shubhali holatlarni ko'radi va izoh qoldiradi.
 * Holatli soxta API: saqlangan izoh qayta yuklangan ro'yxatda ko'rinadi.
 */
test("INT-04: shubhali holatlar ro'yxati va o'qituvchi izohi", async ({ page }) => {
  const values = { ai_enabled: true, ai_max_mode: "explain", practice_after_close: false, late_hours: 0, chat_enabled: true };
  const windows = [
    { topic: { code: "M07", title: "Logistik regressiya", order: 7 }, mode: "open_now", proctored: true, state: { status: "open", opens_at: null, closes_at: null } },
  ];
  let note: { text: string; author: string; updated_at: string } | null = null;
  const student = () => ({
    student_id: 42,
    full_name: "Aliyev Vali",
    paste_blocked: 2,
    tab_hidden: 3,
    understanding_failed: 0,
    fast_full_score: false,
    note,
  });
  await page.context().addCookies([{ name: "csrftoken", value: "e2e", url: "http://localhost:4173" }]);
  await page.route("**/api/**", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const json = (status: number, body: unknown) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    const key = `${req.method()} ${url.pathname}`;
    if (key === "GET /api/auth/me") return json(200, { hemis_id: "1", full_name: "Ustoz", role: "instructor", direction: null, must_change_password: false });
    if (key === "GET /api/sections") return json(200, { results: [] });
    if (key === "GET /api/sections/5") return json(200, { id: 5, name: "ML-21", direction: 1, capacity: 30, join_enabled: true, approved_count: 1, has_join_token: false });
    if (key === "GET /api/sections/5/members") return json(200, { results: [] });
    if (key === "GET /api/sections/5/settings") return json(200, { course_defaults: values, overrides: {}, effective: values });
    if (key === "GET /api/sections/5/deadlines") return json(200, { deadlines: [] });
    if (key === "GET /api/sections/5/windows") return json(200, { server_time: new Date().toISOString(), windows });
    if (key === "GET /api/sections/5/labs/M07/integrity") return json(200, { students: [student()] });
    if (key === "PUT /api/sections/5/labs/M07/students/42/integrity-note") {
      note = { text: req.postDataJSON().text, author: "Ustoz", updated_at: new Date().toISOString() };
      return json(200, note);
    }
    return json(404, {});
  });

  await page.goto("/sections/5");
  const panel = page.getByRole("region", { name: messages["integrity.title"] });
  await expect(panel.getByText(messages["integrity.hint"])).toBeVisible();
  await panel.getByRole("combobox").selectOption("M07");
  const row = panel.getByRole("row", { name: /Aliyev Vali/ });
  await expect(row).toContainText("2");
  await expect(row).toContainText("3");
  await row.getByRole("textbox", { name: messages["integrity.note"] }).fill("Sinfda so'rab ko'raman");
  await row.getByRole("button", { name: messages["integrity.saveNote"] }).click();
  await expect(row.getByText(/^Ustoz, /)).toBeVisible();
  await expect(row.getByRole("textbox", { name: messages["integrity.note"] })).toHaveValue("Sinfda so'rab ko'raman");
});
