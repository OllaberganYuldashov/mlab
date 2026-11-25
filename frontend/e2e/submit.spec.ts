import { expect, test } from "@playwright/test";
import messages from "../src/i18n/uz.json" with { type: "json" };

/**
 * AGR-02, AGR-04, AGR-05, AGR-06 (I3-09): "Topshirish" oqimi soxta backend bilan. WebSocket ataylab yopiq —
 * holat zaxira so'rov (`GET /api/submissions/{id}`) bilan yangilanishi tekshiriladi.
 */
test("AGR-02: Topshirish — navbat, natija qadamlar bo'yicha, eng yuqori ball", async ({
  page,
}) => {
  test.setTimeout(60_000);
  await page
    .context()
    .addCookies([
      { name: "csrftoken", value: "e2e", url: "http://localhost:4173" },
    ]);
  await page.route("**/ws/**", (route) => route.abort());
  let submitted: unknown = null;
  let polls = 0;
  const done = {
    id: 5,
    status: "done",
    position: 0,
    policy: "on_time",
    score: 70,
    final_score: "70.00",
    created_at: new Date().toISOString(),
    finished_at: new Date().toISOString(),
    result: {
      code_error: null,
      steps: [
        {
          key: "sum",
          title: "Yig'indi",
          points: 100,
          score: 70,
          passed: 7,
          total: 10,
          tests: [
            { name: "test_sum", visible: true, passed: true, message: "" },
            {
              name: "yashirin test 1",
              visible: false,
              passed: false,
              message: "O'tmadi",
            },
          ],
        },
      ],
    },
  };
  await page.route("**/api/**", async (route) => {
    const req = route.request();
    const key = `${req.method()} ${new URL(req.url()).pathname}`;
    const json = (status: number, body: unknown) =>
      route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    switch (key) {
      case "GET /api/auth/me":
        return json(200, {
          hemis_id: "123456789012",
          full_name: "Sinov Talaba",
          role: "student",
          direction: 1,
          must_change_password: false,
        });
      case "GET /api/course/topics":
        return json(200, {
          course: { slug: "ml", title: "ML" },
          topics: [
            {
              code: "M01",
              title: "ML asoslari",
              order: 1,
              steps: 1,
              questions: 0,
              lab: { status: "open", opens_at: null, closes_at: null },
            },
          ],
        });
      case "GET /api/labs/M01/work":
        return json(200, {
          version: 0,
          notebook: null,
          saved_at: null,
          policy: "on_time",
          paste_limit: 200,
          proctored: false,
        });
      case "PUT /api/labs/M01/work":
        return json(200, {
          version: 1,
          saved_at: new Date().toISOString(),
          policy: "on_time",
        });
      case "GET /api/labs/M01/assignment":
        return json(200, {
          code: "A01",
          title: "Yig'indi",
          level: "basic",
          statement: "`x` ga **{n}** ni yozing.".replace("{n}", "3"),
          params: { n: 3 },
          steps: [
            { key: "sum", title: "Yig'indi", points: 100, visible_test: null },
          ],
        });
      case "GET /api/labs/M01/submissions":
        return json(200, {
          best_final_score: submitted ? "70.00" : null,
          submissions: submitted ? [done] : [],
        });
      case "POST /api/labs/M01/submissions":
        submitted = req.postDataJSON();
        return json(202, {
          ...done,
          status: "queued",
          position: 2,
          score: null,
          final_score: null,
          result: undefined,
        });
      case "GET /api/submissions/5":
        polls += 1;
        return json(200, done);
    }
    return json(404, {});
  });
  await page.goto("/labs/M01");
  await expect(
    page.getByRole("heading", { name: "A01. Yig'indi" }),
  ).toBeVisible();
  await page.getByText(messages["lab.task.params"]).click();
  await expect(page.locator(".task-params")).toContainText("n");
  await page.getByRole("textbox", { name: "Kod katagi 1" }).click();
  await page.keyboard.type("x = 3");
  await page
    .getByRole("button", { name: messages["lab.submit.button"] })
    .click();
  await expect(
    page.getByText("Navbatda: 2-o'rin", { exact: false }),
  ).toBeVisible();
  expect(submitted).toEqual({ code: "x = 3" });
  await expect(page.getByText("Ball: 70.00 / 100")).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByText(/70 \/ 100 ball \(7 \/ 10 test\)/)).toBeVisible();
  await expect(page.getByText("yashirin test 1")).toBeVisible();
  await expect(page.getByText("Eng yuqori rasmiy ball: 70.00")).toBeVisible();
  expect(polls).toBeGreaterThanOrEqual(1);
});
