import { expect, test } from "@playwright/test";
import messages from "../src/i18n/uz.json" with { type: "json" };

/** ACC-03/04: haftalik slot bilan rejalashtirish va bitta mavzuni "Hozir ochish". Holatli soxta API. */
test("ACC-04: haftalik jadval va hozir ochish", async ({ page }) => {
  const rows = [1, 2].map((n) => ({
    topic: { code: `M0${n}`, title: `Mavzu ${n}`, order: n },
    mode: "closed",
    proctored: false,
    state: { status: "closed", opens_at: null as string | null, closes_at: null as string | null },
  }));
  const values = { ai_enabled: true, ai_max_mode: "explain", practice_after_close: false, late_hours: 0, chat_enabled: true };
  await page.context().addCookies([{ name: "csrftoken", value: "e2e", url: "http://localhost:4173" }]);
  await page.route("**/api/**", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const json = (status: number, body: unknown) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    const key = `${req.method()} ${url.pathname}`;
    if (key === "GET /api/auth/me") return json(200, { hemis_id: "1", full_name: "Ustoz", role: "instructor", direction: null, must_change_password: false });
    if (key === "GET /api/sections") return json(200, { results: [] });
    if (key === "GET /api/sections/5") return json(200, { id: 5, name: "ML-21", direction: 1, capacity: 30, join_enabled: true, approved_count: 0, has_join_token: false });
    if (key === "GET /api/sections/5/members") return json(200, { results: [] });
    if (key === "GET /api/sections/5/settings") return json(200, { course_defaults: values, overrides: {}, effective: values });
    if (key === "GET /api/sections/5/deadlines") return json(200, { deadlines: [] });
    if (key === "GET /api/sections/5/windows") return json(200, { server_time: new Date().toISOString(), windows: rows });
    if (key === "POST /api/sections/5/windows/plan") {
      const body = req.postDataJSON();
      const plan = rows.map((r, i) => ({ topic: r.topic.code, opens_at: `2026-12-${String(1 + 7 * i).padStart(2, "0")}T05:00:00Z`, closes_at: `2026-12-${String(1 + 7 * i).padStart(2, "0")}T06:20:00Z` }));
      if (!body.preview) plan.forEach((p, i) => Object.assign(rows[i] ?? {}, { mode: "scheduled", state: { status: "upcoming", opens_at: p.opens_at, closes_at: p.closes_at } }));
      return json(200, { plan, saved: !body.preview });
    }
    if (key === "POST /api/sections/5/windows/M01/open-now") {
      Object.assign(rows[0] ?? {}, { mode: "open_now", state: { status: "open", opens_at: new Date().toISOString(), closes_at: null } });
      return json(200, rows[0]);
    }
    return json(404, {});
  });

  await page.goto("/sections/5");
  await page.getByLabel(messages["plan.start"]).fill("2026-12-01");
  await page.getByRole("button", { name: messages["plan.preview"] }).click();
  await expect(page.getByText(/M02: /)).toBeVisible();
  await page.getByRole("button", { name: messages["plan.apply"] }).click();
  await expect(page.getByText(messages["plan.saved"])).toBeVisible();
  await expect(page.getByRole("row", { name: /M02 Mavzu 2/ })).toContainText("Ochiladi:");

  await page.getByRole("row", { name: /M01 Mavzu 1/ }).getByRole("button", { name: messages["windows.openNow"] }).click();
  await expect(page.getByRole("row", { name: /M01 Mavzu 1/ })).toContainText(messages["windows.open"]);
});
