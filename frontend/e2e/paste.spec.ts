import { expect, test, type Page } from "@playwright/test";
import messages from "../src/i18n/uz.json" with { type: "json" };

/** INT-01, ACC-09: haqiqiy CodeMirror'da paste ushlanadi — chegaradan katta rad etiladi, har paste qayd qilinadi. */
async function setup(page: Page, proctored: boolean) {
  const events: unknown[] = [];
  await page
    .context()
    .addCookies([
      { name: "csrftoken", value: "e2e", url: "http://localhost:4173" },
    ]);
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
            title: "ML",
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
        paste_limit: 10,
        proctored,
      });
    if (key === "PUT /api/labs/M01/work")
      return json(200, {
        version: 1,
        saved_at: new Date().toISOString(),
        policy: "on_time",
      });
    if (key === "POST /api/labs/M01/events") {
      events.push(req.postDataJSON());
      return json(201, { blocked: false });
    }
    return json(404, {});
  });
  await page.goto("/labs/M01");
  await page.getByRole("textbox", { name: "Kod katagi 1" }).click();
  return events;
}

async function paste(page: Page, text: string) {
  // e2e tsconfig'da DOM turlari yo'q — brauzerda bajariladigan kod satr ko'rinishida.
  await page.evaluate(`(() => {
    const data = new DataTransfer();
    data.setData("text/plain", ${JSON.stringify(text)});
    document.querySelector(".cm-content").dispatchEvent(
      new ClipboardEvent("paste", { clipboardData: data, bubbles: true, cancelable: true }),
    );
  })()`);
}

test("INT-01: kichik paste joylashadi, katta — rad va xabar; ikkalasi qayd", async ({
  page,
}) => {
  const events = await setup(page, false);
  const cell = page.getByRole("textbox", { name: "Kod katagi 1" });
  await paste(page, "x = 1");
  await expect(cell).toContainText("x = 1");
  await paste(page, "y = 'juda uzun matn'");
  await expect(page.getByRole("alert")).toContainText("ko'pi bilan 10 belgi");
  await expect(cell).not.toContainText("juda uzun");
  await expect.poll(() => events.length).toBe(2);
  expect(events).toEqual([
    { kind: "paste", size: 5, cell: expect.any(String) },
    { kind: "paste", size: 20, cell: expect.any(String) },
  ]);
  expect(JSON.stringify(events)).not.toContain("juda uzun"); // matn serverga ketmaydi
});

test("ACC-09: nazorat rejimida har qanday paste taqiq", async ({ page }) => {
  await setup(page, true);
  await expect(page.getByText(messages["lab.proctored"])).toBeVisible();
  await paste(page, "a");
  await expect(page.getByRole("alert")).toHaveText(
    messages["lab.paste.proctored"],
  );
  await expect(
    page.getByRole("textbox", { name: "Kod katagi 1" }),
  ).not.toContainText("a");
});
