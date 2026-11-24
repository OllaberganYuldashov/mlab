import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "@playwright/test";
import messages from "../src/i18n/uz.json" with { type: "json" };

/**
 * CNT-04: `content/topics/*` dagi har bir "O'zing sinab ko'r" (```python try) bloki haqiqiy Pyodide'da xatosiz
 * ishlashi kerak. Bloklar ma'ruzadagi tartibda, bitta muhitda (talaba qanday ishlatsa, shunday) bajariladi.
 * `mlab.load()` — `content/datasets/*.csv` dan.
 */
const CONTENT = join(import.meta.dirname, "..", "..", "content");
const FENCE = /^```python try\n([\s\S]*?)^```/gm;

const topics = readdirSync(join(CONTENT, "topics"))
  .sort()
  .map((dir) => {
    const text = readFileSync(join(CONTENT, "topics", dir, "lecture.md"), "utf8");
    return { code: dir.slice(0, 3), blocks: [...text.matchAll(FENCE)].map((m) => m[1] ?? "") };
  })
  .filter((t) => t.blocks.length > 0);

for (const topic of topics) {
  test(`CNT-04: ${topic.code} kod bloklari Pyodide'da ishlaydi`, async ({ page }) => {
    test.setTimeout(240_000);
    await page.route("**/ws/**", (route) => route.abort());
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      const json = (status: number, body: unknown) =>
        route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
      if (path === "/api/auth/me")
        return json(200, { hemis_id: "123456789012", full_name: "Sinov", role: "student", direction: 1, must_change_password: false });
      const dataset = /^\/api\/datasets\/([a-z0-9_]+)\/file$/.exec(path);
      if (dataset) {
        try {
          return route.fulfill({ status: 200, contentType: "text/csv", body: readFileSync(join(CONTENT, "datasets", `${dataset[1]}.csv`)) });
        } catch {
          return json(404, {});
        }
      }
      if (path === `/api/course/topics/${topic.code}/lecture`)
        return json(200, {
          topic: { code: topic.code, title: topic.code },
          title: topic.code,
          prev: null,
          next: null,
          steps: [{ order: 1, title: "Kod", body: topic.blocks.map((b) => "```python try\n" + b + "```").join("\n\n"), question: null }],
        });
      return json(404, {});
    });
    await page.goto(`/topics/${topic.code}`);
    const blocks = page.locator(".runnable");
    await expect(blocks).toHaveCount(topic.blocks.length);
    for (let i = 0; i < topic.blocks.length; i++) {
      const block = blocks.nth(i);
      const run = block.getByRole("button", { name: messages["lab.run"] });
      await run.click();
      await expect(run).toBeEnabled({ timeout: 180_000 });
      const alerts = block.getByRole("alert");
      const error = (await alerts.count()) > 0 ? await alerts.first().textContent() : null;
      expect(error, `${topic.code}, ${i + 1}-blok:\n${topic.blocks[i]}`).toBeNull();
    }
  });
}
