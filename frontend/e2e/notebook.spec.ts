import { expect, test } from "@playwright/test";
import messages from "../src/i18n/uz.json" with { type: "json" };

/** LAB-01: haqiqiy CodeMirror va Pyodide — yozish, Shift+Enter, o'zgaruvchi kataklar orasida, grafik, matn katagi. */
test("LAB-01: notebook", async ({ page }) => {
  test.setTimeout(180_000);
  await page.route("**/ws/**", (route) => route.abort());
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const json = (status: number, body: unknown) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    if (path === "/api/auth/me")
      return json(200, { hemis_id: "123456789012", full_name: "Sinov Talaba", role: "student", direction: 1, must_change_password: false });
    return json(404, {});
  });
  await page.goto("/labs/M01");
  const first = page.getByRole("textbox", { name: "Kod katagi 1" });
  await first.click();
  await page.keyboard.type("a = 21\nprint(a * 2)");
  await page.keyboard.press("Shift+Enter");
  await expect(page.getByTestId("cell-output").first()).toContainText("42", { timeout: 90_000 });
  await expect(page.getByText("[1]")).toBeVisible();

  await page.getByRole("button", { name: messages["lab.cell.addCode"] }).first().click();
  await page.getByRole("textbox", { name: "Kod katagi 2" }).click();
  await page.keyboard.type("import matplotlib.pyplot as plt\nplt.bar(['a', 'b'], [a, 1])");
  await page.getByRole("button", { name: "2-katakni ishga tushirish" }).click();
  await expect(page.getByRole("img", { name: "Grafik 1" })).toBeVisible({ timeout: 90_000 });

  await page.getByRole("button", { name: messages["lab.cell.addMarkdown"] }).nth(1).click();
  await page.getByRole("textbox", { name: "Matn katagi 3" }).click();
  await page.keyboard.type("**Xulosa:** ishladi");
  await page.keyboard.press("Shift+Enter");
  await expect(page.getByRole("region", { name: "Matn katagi 3" }).locator("strong")).toHaveText("Xulosa:");
});
