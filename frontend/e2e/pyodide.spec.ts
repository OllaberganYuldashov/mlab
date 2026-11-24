import { expect, test } from "@playwright/test";
import messages from "../src/i18n/uz.json" with { type: "json" };

/**
 * LAB-02, LAB-03, ADR-0006: haqiqiy Pyodide (o'z serverdan, `/pyodide/<versiya>/`) prod CSP ostida — chiqish,
 * Python xatosi (traceback) va matplotlib grafigi. Tashqi domenga so'rov ketmasligi ham tekshiriladi.
 */
test("LAB-02: brauzerda Python — print, xato, grafik", async ({ page }) => {
  test.setTimeout(180_000);
  const external: string[] = [];
  page.on("request", (req) => {
    const url = new URL(req.url());
    if (url.hostname !== "localhost") external.push(req.url());
  });
  await page.route("**/ws/**", (route) => route.abort());
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const json = (status: number, body: unknown) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    if (path === "/api/auth/me")
      return json(200, { hemis_id: "123456789012", full_name: "Sinov Talaba", role: "student", direction: 1, must_change_password: false });
    if (path === "/api/course/topics/M01/lecture")
      return json(200, {
        topic: { code: "M01", title: "ML" },
        title: "ML",
        prev: null,
        next: null,
        steps: [
          {
            order: 1,
            title: "Sinab ko'r",
            body: [
              "```python try\nx = 2 + 2\nprint('natija', x)\nx * 10\n```",
              "```python try\n1 / 0\n```",
              "```python try\nimport matplotlib.pyplot as plt\nplt.plot([1, 2, 3], [1, 4, 9])\nprint(x)\n```",
            ].join("\n\n"),
            question: null,
          },
        ],
      });
    return json(404, {});
  });

  await page.goto("/topics/M01");
  const blocks = page.locator(".runnable");
  await blocks.nth(0).getByRole("button", { name: messages["lab.run"] }).click();
  const first = blocks.nth(0).getByTestId("run-output");
  await expect(first).toContainText("natija 4", { timeout: 90_000 });
  await expect(first.locator(".result")).toHaveText("40");

  await blocks.nth(1).getByRole("button", { name: messages["lab.run"] }).click();
  await expect(blocks.nth(1).getByRole("alert")).toContainText("ZeroDivisionError");

  await blocks.nth(2).getByRole("button", { name: messages["lab.run"] }).click();
  await expect(blocks.nth(2).getByRole("img", { name: "Grafik 1" })).toBeVisible({ timeout: 90_000 });
  await expect(blocks.nth(2).getByTestId("run-output")).toContainText("4"); // o'zgaruvchi saqlanadi

  expect(external).toEqual([]);
});
