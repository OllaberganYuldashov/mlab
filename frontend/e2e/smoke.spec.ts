import { expect, test } from "@playwright/test";
import messages from "../src/i18n/uz.json" with { type: "json" };

test("smoke: bosh sahifa ochiladi va o'zbekcha sarlavha ko'rinadi", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("lang", "uz");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(messages["app.title"]);
  await expect(page.getByText(messages["app.tagline"])).toBeVisible();
});
