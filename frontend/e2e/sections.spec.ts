import { expect, test } from "@playwright/test";
import messages from "../src/i18n/uz.json" with { type: "json" };

/**
 * SEC-01, SEC-02, SEC-04: o'qituvchi guruh yaratadi → havola va QR → so'rovni tasdiqlaydi.
 * Holatli soxta API (frontend CI job'ida backend yo'q); backend oqimi `backend/tests/sections` da.
 */
test("SEC-01/02/04: guruh yaratish, havola va QR, so'rovni tasdiqlash", async ({ page }) => {
  const sections: Record<string, unknown>[] = [];
  let pending = [
    { id: 11, status: "pending", student: { id: 1, hemis_id: "111111111111", full_name: "Ali Valiyev" } },
  ];
  let approved: typeof pending = [];

  await page.context().addCookies([{ name: "csrftoken", value: "e2e", url: "http://localhost:4173" }]);
  await page.route("**/api/**", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const json = (status: number, body: unknown) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    const key = `${req.method()} ${url.pathname}`;
    if (key === "GET /api/auth/me")
      return json(200, { hemis_id: "100000000001", full_name: "Ustoz", role: "instructor", direction: null, must_change_password: false });
    if (key === "GET /api/directions") return json(200, [{ id: 1, name: "Dasturiy injiniring" }]);
    if (key === "GET /api/sections") return json(200, { results: sections });
    if (key === "POST /api/sections") {
      const body = req.postDataJSON();
      const created = { id: 5, name: body.name, direction: body.direction, capacity: body.capacity, join_enabled: true, approved_count: 0, has_join_token: false };
      sections.unshift(created);
      return json(201, created);
    }
    if (key === "GET /api/sections/5") return json(200, { ...sections[0], approved_count: approved.length });
    if (key === "POST /api/sections/5/join-token") {
      sections[0] = { ...sections[0], has_join_token: true };
      return json(201, { token: "t", join_path: "/join/e2eTokenAbc1234567890" });
    }
    if (key === "GET /api/sections/5/members")
      return json(200, { results: url.searchParams.get("status") === "approved" ? approved : pending });
    if (key === "POST /api/sections/5/members/decide") {
      const ids: number[] = req.postDataJSON().ids;
      approved = pending.filter((m) => ids.includes(m.id)).map((m) => ({ ...m, status: "approved" }));
      pending = pending.filter((m) => !ids.includes(m.id));
      return json(200, { approved: ids, rejected: [], skipped: [] });
    }
    return json(404, {});
  });

  await page.goto("/sections");
  await expect(page.getByText(messages["sections.empty"])).toBeVisible();
  await page.getByLabel(messages["sections.field.name"]).fill("ML-21");
  await page.getByLabel(messages["field.direction"]).selectOption({ label: "Dasturiy injiniring" });
  await page.getByRole("button", { name: messages["sections.create.submit"] }).click();
  await page.getByRole("link", { name: messages["sections.open"] }).click();
  await expect(page).toHaveURL(/\/sections\/5$/);

  await page.getByRole("button", { name: messages["section.link.rotate"] }).click();
  await expect(page.getByTestId("join-url")).toHaveText("http://localhost:4173/join/e2eTokenAbc1234567890");
  await expect(page.getByRole("img", { name: messages["section.link.qrAlt"] })).toBeVisible();

  await page.getByRole("checkbox", { name: "Ali Valiyev" }).check();
  await page.getByRole("button", { name: messages["section.requests.approve"] }).click();
  await expect(page.getByText("Tasdiqlandi: 1, rad etildi: 0.")).toBeVisible();
  await expect(page.getByText(messages["section.requests.empty"])).toBeVisible();
  await expect(page.getByRole("cell", { name: "Ali Valiyev" })).toBeVisible();
});
