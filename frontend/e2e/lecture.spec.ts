import { expect, test } from "@playwright/test";
import messages from "../src/i18n/uz.json" with { type: "json" };

/** CNT-02: talaba mavzular ro'yxatidan ma'ruzani ochadi, klaviatura bilan qadamlarni o'tadi va tezkor savolga javob beradi. */
test("CNT-02: ma'ruza qadamlari va tezkor savol", async ({ page }) => {
  await page.route("**/ws/**", (route) => route.abort());
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const json = (status: number, body: unknown) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    if (path === "/api/auth/me")
      return json(200, { hemis_id: "123456789012", full_name: "Sinov Talaba", role: "student", direction: 1, must_change_password: false });
    if (path === "/api/me/membership") return json(200, { membership: null });
    if (path === "/api/course/topics")
      return json(200, {
        course: { slug: "ml", title: "Machine Learning" },
        topics: [{ code: "M01", title: "ML asoslari", order: 1, steps: 2, questions: 0, lab: null }],
      });
    if (path === "/api/course/topics/M01/lecture")
      return json(200, {
        topic: { code: "M01", title: "ML asoslari" },
        title: "ML asoslari",
        prev: null,
        next: null,
        steps: [
          { order: 1, title: "Kirish", body: "Mashinali o'qitish — **ma'lumotdan** o'rganish.", question: null },
          { order: 2, title: "Savol", body: "", question: { question: "2 + 2?", options: ["3", "4"], answer: 1, explain: "" } },
        ],
      });
    return json(404, {});
  });

  await page.goto("/");
  await page.getByRole("link", { name: messages["nav.topics"] }).click();
  await page.getByRole("link", { name: "M01. ML asoslari" }).click();
  await expect(page.getByRole("heading", { name: "Kirish" })).toBeVisible();
  await page.getByRole("button", { name: messages["lecture.next"] }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "Savol" })).toBeFocused();
  await page.getByRole("radio", { name: "B) 4" }).check();
  await page.getByRole("button", { name: messages["lecture.check"] }).click();
  await expect(page.getByRole("status")).toHaveText(messages["lecture.correct"]);
  await expect(page.getByText(messages["lecture.end"])).toBeVisible();
});

/** CNT-03: vizual qadam — slayder klaviatura bilan boshqariladi, MSE yangilanadi. */
test("CNT-03: interaktiv vizual qadam", async ({ page }) => {
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
        steps: [{ order: 1, title: "Vizual", body: '```visual\n{"widget": "line-fit", "points": [[0, 1], [1, 3], [2, 5]]}\n```', question: null }],
      });
    return json(404, {});
  });
  await page.goto("/topics/M01");
  const mse = page.getByTestId("mse");
  const before = await mse.textContent();
  await page.getByRole("slider", { name: /Qiyalik/ }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("slider", { name: "Qiyalik (w): 0.6" })).toBeVisible();
  await expect(mse).not.toHaveText(before ?? "");
  await page.getByRole("button", { name: messages["visual.lineFit.best"] }).click();
  await expect(mse).toHaveText("O'rtacha kvadrat xato (MSE): 0.00");
});
