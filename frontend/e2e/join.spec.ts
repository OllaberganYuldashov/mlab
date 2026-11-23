import { expect, test } from "@playwright/test";
import messages from "../src/i18n/uz.json" with { type: "json" };

const TOKEN = "e2eJoinToken1234567890";

/** SEC-03/04: havola → kirish → shu havolaga qaytish → so'rov → bosh sahifada "kutilmoqda". Soxta API. */
test("SEC-03: talaba havola orqali kiradi va so'rov yuboradi", async ({ page }) => {
  let loggedIn = false;
  let requested = false;
  await page.context().addCookies([{ name: "csrftoken", value: "e2e", url: "http://localhost:4173" }]);
  await page.route("**/ws/**", (route) => route.abort());
  await page.route("**/api/**", async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    const json = (status: number, body: unknown) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    const me = { hemis_id: "123456789012", full_name: "Sinov Talaba", role: "student", direction: 1, must_change_password: false };
    if (path === "/api/auth/me") return loggedIn ? json(200, me) : json(403, {});
    if (path === "/api/auth/login") {
      loggedIn = true;
      return json(200, me);
    }
    if (path === `/api/join/${TOKEN}` && req.method() === "GET")
      return json(200, { section: "ML-21", instructor: "Ustoz Sinov", join_enabled: true, is_full: false });
    if (path === `/api/join/${TOKEN}`) {
      requested = true;
      return json(201, { status: "pending" });
    }
    if (path === "/api/me/membership")
      return json(200, { membership: requested ? { status: "pending", section: "ML-21", instructor: "Ustoz Sinov" } : null });
    return json(404, {});
  });

  await page.goto(`/join/${TOKEN}`);
  await expect(page.getByText("Guruh: ML-21")).toBeVisible();
  await page.getByRole("link", { name: messages["nav.login"] }).click();
  await page.getByLabel(messages["field.hemisId"]).fill("123456789012");
  await page.getByLabel(messages["field.password"]).fill(`p-${Date.now()}`);
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(new RegExp(`/join/${TOKEN}$`));
  await page.getByRole("button", { name: messages["join.submit"] }).click();
  await expect(page.getByText(messages["join.sent"])).toBeVisible();
  await page.getByRole("link", { name: messages["nav.home"] }).click();
  await expect(page.getByText(/tasdig'ini kutmoqda/)).toBeVisible();
});
