import { expect, test } from "@playwright/test";
import messages from "../src/i18n/uz.json" with { type: "json" };

/**
 * I2 uchidan-uchiga (CNT-02, CNT-06, LAB-01, LAB-04, LAB-05): talaba mavzular ro'yxatidan ma'ruzani ochadi, "O'zing
 * sinab ko'r" kodini ishga tushiradi, mavzu testini topshiradi, laboratoriyada mlab.load bilan kod yozadi — ish
 * saqlanadi va sahifa qayta ochilganda joyida. Holatli soxta backend, haqiqiy Pyodide.
 */
test("I2: ma'ruza → kod → test → laboratoriya → saqlash", async ({ page, context }) => {
  test.setTimeout(240_000);
  let work = { version: 0, notebook: null as unknown };
  let submitted = false;
  await context.addCookies([{ name: "csrftoken", value: "e2e", url: "http://localhost:4173" }]);
  await page.route("**/ws/**", (route) => route.abort());
  await page.route("**/api/**", async (route) => {
    const req = route.request();
    const key = `${req.method()} ${new URL(req.url()).pathname}`;
    const json = (status: number, body: unknown) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    const attempt = () => ({
      id: 1,
      number: 1,
      deadline: new Date(Date.now() + 600_000).toISOString(),
      server_time: new Date().toISOString(),
      submitted_at: submitted ? new Date().toISOString() : null,
      score: submitted ? 1 : null,
      max_score: 1,
      questions: [{ position: 1, text: "ML qayerdan o'rganadi?", options: ["Qoidalardan", "Ma'lumotlardan"], ...(submitted ? { chosen: 1, answer: 1, correct: true } : {}) }],
    });
    switch (key) {
      case "GET /api/auth/me":
        return json(200, { hemis_id: "123456789012", full_name: "Sinov Talaba", role: "student", direction: 1, must_change_password: false });
      case "GET /api/me/membership":
        return json(200, { membership: { status: "approved", section: "ML-21", instructor: "Ustoz" } });
      case "GET /api/me/next-window":
        return json(200, { server_time: new Date().toISOString(), open: [], next: null });
      case "GET /api/course/topics":
        return json(200, {
          course: { slug: "ml", title: "Machine Learning" },
          topics: [{ code: "M01", title: "ML asoslari", order: 1, steps: 1, questions: 1, lab: { status: "open", opens_at: null, closes_at: null } }],
        });
      case "GET /api/course/topics/M01/lecture":
        return json(200, {
          topic: { code: "M01", title: "ML asoslari" },
          title: "ML asoslari",
          prev: null,
          next: null,
          steps: [{ order: 1, title: "Sinab ko'r", body: "```python try\nprint(sum([1, 2, 3]))\n```", question: null }],
        });
      case "GET /api/course/topics/M01/quiz":
        return json(200, {
          settings: { questions: 10, minutes: 10, attempts: 3 },
          available_questions: 1,
          used_attempts: submitted ? 1 : 0,
          active_attempt: null,
          attempts: submitted ? [{ id: 1, number: 1, score: 1, max_score: 1, submitted_at: new Date().toISOString() }] : [],
        });
      case "POST /api/course/topics/M01/quiz/attempts":
        return json(201, attempt());
      case "POST /api/course/quiz/attempts/1/submit":
        submitted = true;
        return json(200, attempt());
      case "GET /api/labs/M01/work":
        return json(200, { ...work, saved_at: null, policy: "on_time" });
      case "PUT /api/labs/M01/work": {
        const body = req.postDataJSON();
        work = { version: work.version + 1, notebook: body.notebook };
        return json(200, { version: work.version, saved_at: new Date().toISOString(), policy: "on_time" });
      }
      case "GET /api/datasets/iris/file":
        return route.fulfill({ status: 200, contentType: "text/csv", body: "sepal_length,species\n5.1,setosa\n6.0,versicolor\n" });
    }
    return json(404, {});
  });

  // 1. Ma'ruza va "O'zing sinab ko'r".
  await page.goto("/");
  await page.getByRole("link", { name: messages["nav.topics"] }).click();
  await page.getByRole("link", { name: "M01. ML asoslari" }).click();
  await page.getByRole("button", { name: messages["lab.run"] }).click();
  await expect(page.getByTestId("run-output")).toContainText("6", { timeout: 90_000 });

  // 2. Mavzu testi.
  await page.goto("/topics");
  await page.getByRole("link", { name: messages["topics.quiz"] }).click();
  await page.getByRole("button", { name: messages["quiz.start"] }).click();
  await page.getByRole("radio", { name: "B) Ma'lumotlardan" }).check();
  await page.getByRole("button", { name: messages["quiz.submit"] }).click();
  await expect(page.getByRole("status")).toHaveText("Natija: 1 / 1");

  // 3. Laboratoriya: mlab.load, ishga tushirish → saqlanadi; qayta ochilganda ish joyida.
  await page.goto("/labs/M01");
  await page.getByRole("textbox", { name: "Kod katagi 1" }).click();
  await page.keyboard.type("import mlab\nprint(mlab.load('iris').shape)");
  await page.keyboard.press("Shift+Enter");
  await expect(page.getByTestId("cell-output")).toContainText("(2, 2)", { timeout: 90_000 });
  await expect(page.getByText(/Saqlandi:/)).toBeVisible();
  await page.reload();
  await expect(page.getByRole("textbox", { name: "Kod katagi 1" })).toContainText("mlab.load('iris')");
});
