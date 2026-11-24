import { expect, test } from "@playwright/test";
import messages from "../src/i18n/uz.json" with { type: "json" };

/**
 * AGR-01, LAB-07 (I3-04): "Tekshirish" — ko'rinadigan testlar haqiqiy Pyodide'da. Talaba kodi numpy import
 * qiladi (paket kod satridan emas, talaba kodidan aniqlanishi tekshiriladi); bitta test o'tadi, biri assert xabari
 * bilan o'tmaydi. Topshiriq API'si faqat ko'rinadigan testni beradi.
 */
test("AGR-01: Tekshirish — ko'rinadigan testlar brauzerda", async ({
  page,
}) => {
  test.setTimeout(180_000);
  await page.route("**/ws/**", (route) => route.abort());
  await page.route("**/api/**", async (route) => {
    const req = route.request();
    const key = `${req.method()} ${new URL(req.url()).pathname}`;
    const json = (status: number, body: unknown) =>
      route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    if (key === "GET /api/auth/me")
      return json(200, {
        hemis_id: "123456789012",
        full_name: "Sinov Talaba",
        role: "student",
        direction: 1,
        must_change_password: false,
      });
    if (key === "GET /api/course/topics")
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
    if (key === "GET /api/labs/M01/work")
      return json(200, {
        version: 0,
        notebook: null,
        saved_at: null,
        policy: "on_time",
        paste_limit: 200,
        proctored: false,
      });
    if (key === "PUT /api/labs/M01/work")
      return json(200, {
        version: 1,
        saved_at: new Date().toISOString(),
        policy: "on_time",
      });
    if (key === "GET /api/labs/M01/assignment")
      return json(200, {
        code: "A01",
        title: "NumPy yig'indisi",
        level: "basic",
        statement:
          "`0..2` sonlar yig'indisini `x` ga yozing (kutilgan: **3**).",
        params: { n: 3 },
        steps: [
          {
            key: "sum",
            title: "Yig'indi",
            points: 100,
            visible_test: [
              "def test_sum(ns, params):",
              "    assert int(ns['x']) == params['n']",
              "",
              "def test_type(ns, params):",
              "    assert isinstance(ns['x'], int), 'x oddiy int bo‘lishi kerak'",
              "",
            ].join("\n"),
          },
        ],
      });
    return json(404, {});
  });
  await page.goto("/labs/M01");
  await expect(
    page.getByRole("heading", { name: "A01. NumPy yig'indisi" }),
  ).toBeVisible();
  await page.getByRole("textbox", { name: "Kod katagi 1" }).click();
  await page.keyboard.type("import numpy as np\nx = np.arange(3).sum()");
  await page
    .getByRole("button", { name: messages["lab.check.button"] })
    .click();
  await expect(page.getByText("Ko'rinadigan testlar: 1 / 2 o'tdi")).toBeVisible(
    { timeout: 120_000 },
  );
  await expect(page.getByText("x oddiy int bo‘lishi kerak")).toBeVisible();
  await expect(page.getByLabel("o'tdi", { exact: true })).toBeVisible();
});
