import { expect, test, type Page } from "@playwright/test";
import messages from "../src/i18n/uz.json" with { type: "json" };

/**
 * AUTH-01/02: ro'yxatdan o'tish → chiqish → kirish. Backend'ning o'zi `backend/tests` da real PostgreSQL bilan
 * sinaladi; bu yerda brauzer oqimi (forma, CSRF sarlavhasi, yo'naltirish) holatli soxta API bilan tekshiriladi,
 * chunki frontend CI job'ida backend servislari yo'q.
 */
async function fakeBackend(page: Page) {
  const users = new Map<string, { password: string; full_name: string }>();
  let sessionUser: string | null = null;
  const csrfHeaders: (string | undefined)[] = [];

  await page.context().addCookies([
    { name: "csrftoken", value: "e2e-token", url: "http://localhost:4173" },
  ]);
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const method = request.method();
    const json = (status: number, body: unknown) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    if (method !== "GET") csrfHeaders.push(request.headers()["x-csrftoken"]);
    if (path === "/api/directions") return json(200, [{ id: 1, name: "Dasturiy injiniring" }]);
    if (path === "/api/policy") return json(200, { version: "2026-11-22" });
    if (path === "/api/auth/me") {
      const u = sessionUser && users.get(sessionUser);
      return u && sessionUser
        ? json(200, {
            hemis_id: sessionUser,
            full_name: u.full_name,
            role: "student",
            direction: 1,
            must_change_password: false,
          })
        : json(403, { detail: "x" });
    }
    if (path === "/api/auth/register") {
      const body = request.postDataJSON();
      if (body.consent !== true || body.policy_version !== "2026-11-22") return json(400, {});
      users.set(body.hemis_id, { password: body.password, full_name: body.full_name });
      return json(201, {});
    }
    if (path === "/api/auth/login") {
      const body = request.postDataJSON();
      const u = users.get(body.hemis_id);
      if (!u || u.password !== body.password) return json(400, { detail: "x" });
      sessionUser = body.hemis_id;
      return json(200, {
        hemis_id: body.hemis_id,
        full_name: u.full_name,
        role: "student",
        direction: 1,
        must_change_password: false,
      });
    }
    if (path === "/api/auth/logout") {
      sessionUser = null;
      return route.fulfill({ status: 204 });
    }
    return json(404, {});
  });
  return { csrfHeaders };
}

test("AUTH-01/02: ro'yxatdan o'tish → chiqish → kirish (faqat klaviatura bilan)", async ({ page }) => {
  const { csrfHeaders } = await fakeBackend(page);
  await page.goto("/register");

  // Rozilik belgisisiz tugma faol emas.
  const submit = page.getByRole("button", { name: messages["register.submit"] });
  await expect(submit).toBeDisabled();
  await expect(page.getByRole("link", { name: messages["register.policyLink"] })).toHaveAttribute(
    "href",
    "/policy",
  );

  await page.getByLabel(messages["field.hemisId"]).fill("123456789012");
  await page.getByLabel(messages["field.fullName"]).fill("Sinov Talaba");
  await page.getByLabel(messages["field.direction"]).selectOption({ label: "Dasturiy injiniring" });
  await page.getByLabel(messages["field.password"]).fill("uzun-maxfiy-parol-9");
  await page.getByLabel(messages["register.consentCheckbox"]).focus();
  await page.keyboard.press("Space");
  await expect(submit).toBeEnabled();
  await page.keyboard.press("Tab"); // tugmaga o'tish
  await page.keyboard.press("Enter");

  await expect(page).toHaveURL(/\/login\?registered=1$/);
  await expect(page.getByText(messages["register.success"])).toBeVisible();

  await page.getByLabel(messages["field.hemisId"]).fill("123456789012");
  await page.getByLabel(messages["field.password"]).fill("uzun-maxfiy-parol-9");
  await page.keyboard.press("Enter");
  await expect(page.getByText("Salom, Sinov Talaba!")).toBeVisible();

  await page.getByRole("button", { name: messages["nav.logout"] }).click();
  await expect(page).toHaveURL(/\/login$/);

  // Noto'g'ri parol — xabar; to'g'ri parol — kiradi.
  await page.getByLabel(messages["field.hemisId"]).fill("123456789012");
  await page.getByLabel(messages["field.password"]).fill("noto'g'ri");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("alert")).toHaveText(messages["login.failed"]);
  await page.getByLabel(messages["field.password"]).fill("uzun-maxfiy-parol-9");
  await page.keyboard.press("Enter");
  await expect(page.getByText("Salom, Sinov Talaba!")).toBeVisible();

  // Har bir o'zgartiruvchi so'rov CSRF sarlavhasi bilan ketgan.
  expect(csrfHeaders.length).toBeGreaterThanOrEqual(4);
  expect(csrfHeaders.every((h) => h === "e2e-token")).toBe(true);
});
