import { expect, test } from "@playwright/test";
import messages from "../src/i18n/uz.json" with { type: "json" };

/** LAB-05: ishga tushirishda saqlanadi; tarmoq uzilsa — "oflayn", qaytganda yuboriladi; sahifa yangilansa ish joyida. */
test("LAB-05: avtosaqlash va oflayn navbat", async ({ page, context }) => {
  test.setTimeout(180_000);
  let server = { version: 0, notebook: null as unknown };
  const puts: unknown[] = [];
  let down = false;
  await context.addCookies([{ name: "csrftoken", value: "e2e", url: "http://localhost:4173" }]);
  await page.route("**/ws/**", (route) => route.abort());
  await page.route("**/api/**", async (route) => {
    const req = route.request();
    const key = `${req.method()} ${new URL(req.url()).pathname}`;
    const json = (status: number, body: unknown) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    if (key === "GET /api/auth/me")
      return json(200, { hemis_id: "123456789012", full_name: "Sinov Talaba", role: "student", direction: 1, must_change_password: false });
    if (key === "GET /api/course/topics")
      return json(200, { course: { slug: "ml", title: "ML" }, topics: [{ code: "M01", title: "ML", order: 1, steps: 1, questions: 0, lab: { status: "open", opens_at: null, closes_at: null } }] });
    if (key === "GET /api/labs/M01/work")
      return json(200, { ...server, saved_at: server.version ? new Date().toISOString() : null, policy: "on_time" });
    if (key === "PUT /api/labs/M01/work") {
      if (down) return route.abort("internetdisconnected");
      const body = req.postDataJSON();
      puts.push(body);
      if (body.version !== server.version) return json(409, { code: "version_conflict", current_version: server.version, notebook: server.notebook });
      server = { version: server.version + 1, notebook: body.notebook };
      return json(200, { version: server.version, saved_at: new Date().toISOString(), policy: "on_time" });
    }
    return json(404, {});
  });

  await page.goto("/labs/M01");
  await page.getByRole("textbox", { name: "Kod katagi 1" }).click();
  await page.keyboard.type("print('birinchi')");
  await page.keyboard.press("Shift+Enter");
  await expect(page.getByText(/Saqlandi:/)).toBeVisible();
  expect(server.version).toBe(1);

  down = true;
  await page.getByRole("textbox", { name: "Kod katagi 1" }).click();
  await page.keyboard.press("End");
  await page.keyboard.type("  # oflayn");
  await page.keyboard.press("Shift+Enter");
  await expect(page.getByText(messages["save.offline"])).toBeVisible();

  down = false;
  await page.evaluate("window.dispatchEvent(new Event('online'))");
  await expect(page.getByText(/Saqlandi:/)).toBeVisible();
  expect(JSON.stringify(server.notebook)).toContain("# oflayn");

  await page.reload();
  await expect(page.getByRole("textbox", { name: "Kod katagi 1" })).toContainText("# oflayn");
});
