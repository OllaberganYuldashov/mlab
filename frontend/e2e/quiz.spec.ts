import { expect, test } from "@playwright/test";
import messages from "../src/i18n/uz.json" with { type: "json" };

/** CNT-06: talaba mavzu testini boshlaydi, javob beradi, topshiradi va natijani ko'radi. Holatli soxta API. */
test("CNT-06: mavzu testi", async ({ page }) => {
  let submitted = false;
  const question = { position: 1, text: "2 + 2?", options: ["3", "4"] };
  await page.context().addCookies([{ name: "csrftoken", value: "e2e", url: "http://localhost:4173" }]);
  await page.route("**/ws/**", (route) => route.abort());
  await page.route("**/api/**", async (route) => {
    const req = route.request();
    const key = `${req.method()} ${new URL(req.url()).pathname}`;
    const json = (status: number, body: unknown) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    const attempt = () => ({
      id: 7,
      number: 1,
      deadline: new Date(Date.now() + 600_000).toISOString(),
      server_time: new Date().toISOString(),
      submitted_at: submitted ? new Date().toISOString() : null,
      score: submitted ? 1 : null,
      max_score: 1,
      questions: [submitted ? { ...question, chosen: 1, answer: 1, correct: true } : question],
    });
    if (key === "GET /api/auth/me")
      return json(200, { hemis_id: "123456789012", full_name: "Sinov Talaba", role: "student", direction: 1, must_change_password: false });
    if (key === "GET /api/course/topics/M01/quiz")
      return json(200, {
        settings: { questions: 10, minutes: 10, attempts: 2 },
        available_questions: 1,
        used_attempts: submitted ? 1 : 0,
        active_attempt: null,
        attempts: submitted ? [{ id: 7, number: 1, score: 1, max_score: 1, submitted_at: new Date().toISOString() }] : [],
      });
    if (key === "POST /api/course/topics/M01/quiz/attempts") return json(201, attempt());
    if (key === "POST /api/course/quiz/attempts/7/submit") {
      expect(req.postDataJSON()).toEqual({ answers: { "1": 1 } });
      submitted = true;
      return json(200, attempt());
    }
    return json(404, {});
  });

  await page.goto("/topics/M01/quiz");
  await page.getByRole("button", { name: messages["quiz.start"] }).click();
  await expect(page.getByText(/Qolgan vaqt:/)).toBeVisible();
  await page.getByRole("radio", { name: "B) 4" }).check();
  await page.getByRole("button", { name: messages["quiz.submit"] }).click();
  await expect(page.getByRole("status")).toHaveText("Natija: 1 / 1");
  await expect(page.getByText("1-urinish: 1 / 1")).toBeVisible();
});
