import { expect, test } from "@playwright/test";

/**
 * NFR-02 (I2-20): laboratoriya ochilishi (taxminiy o'lchov). Sahifa ochilgandan pandas bilan birinchi katak natijasigacha:
 * birinchi ochilish (bo'sh kesh) ≤ 2 daqiqa, keyingisi ≤ 15 soniya. Og'ir importlar (scikit-learn, matplotlib) vaqti
 * ma'lumot uchun yoziladi. CPU sekinlashtirish: `CPU_RATE` (default 1; CDP worker oqimini sekinlashtirmaydi).
 * Haqiqiy monoblok o'lchovi — egasida (`docs/learn/pyodide.md`, 6-bo'lim).
 */
const FIRST = "import mlab, pandas\nprint('tayyor')";
const HEAVY = "import sklearn, matplotlib.pyplot\nprint('og`ir tayyor')";

test("NFR-02: laboratoriya birinchi va keyingi ochilishi", async ({ browser }) => {
  test.setTimeout(300_000);
  const context = await browser.newContext({ viewport: { width: 1366, height: 768 } });
  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: Number(process.env.CPU_RATE ?? 1) });
  await page.route("**/ws/**", (route) => route.abort());
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const json = (status: number, body: unknown) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    if (path === "/api/auth/me")
      return json(200, { hemis_id: "123456789012", full_name: "Sinov", role: "student", direction: 1, must_change_password: false });
    if (path === "/api/course/topics")
      return json(200, { course: { slug: "ml", title: "ML" }, topics: [{ code: "M01", title: "ML", order: 1, steps: 1, questions: 0, lab: { status: "open", opens_at: null, closes_at: null } }] });
    if (path === "/api/labs/M01/work")
      return json(200, {
        version: 1,
        notebook: { format: 1, cells: [{ id: "a", type: "code", source: FIRST }, { id: "b", type: "code", source: HEAVY }] },
        saved_at: null,
        policy: "practice",
      });
    return json(404, {});
  });

  async function open(): Promise<{ first: number; heavy: number }> {
    const start = Date.now();
    await page.goto("/labs/M01");
    await page.getByRole("button", { name: "1-katakni ishga tushirish" }).click();
    await expect(page.getByTestId("cell-output").first()).toContainText("tayyor", { timeout: 240_000 });
    const first = (Date.now() - start) / 1000;
    const heavyStart = Date.now();
    await page.getByRole("button", { name: "2-katakni ishga tushirish" }).click();
    await expect(page.getByTestId("cell-output").nth(1)).toContainText("og`ir tayyor", { timeout: 240_000 });
    return { first, heavy: (Date.now() - heavyStart) / 1000 };
  }

  const cold = await open();
  const warm = await open();
  const note =
    `birinchi ochilish: ${cold.first.toFixed(1)} s (+ sklearn/matplotlib ${cold.heavy.toFixed(1)} s), ` +
    `keyingi: ${warm.first.toFixed(1)} s (+ ${warm.heavy.toFixed(1)} s)`;
  console.log(`NFR-02 o'lchovi — ${note}`);
  test.info().annotations.push({ type: "NFR-02", description: note });
  expect(cold.first).toBeLessThanOrEqual(120);
  expect(warm.first).toBeLessThanOrEqual(15);
  await context.close();
});
