import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "@playwright/test";
import messages from "../src/i18n/uz.json" with { type: "json" };

/**
 * AGR-07 (I3-15): kontentdagi haqiqiy topshiriqlarning ko'rinadigan testlari brauzerdagi Python'da (Pyodide) ham
 * o'tadi — yechim shablonini variant parametrlari bilan to'ldirib, "Tekshirish" bosiladi. Server tomonidagi tekshiruv
 * (yashirin testlar ham) — `manage.py check_lab_solutions`.
 */
const CONTENT = join(import.meta.dirname, "..", "..", "content");
const LABS = join(CONTENT, "labs");

function render(template: string, params: Record<string, unknown>): string {
  return template.replace(/\{([a-z_][a-z0-9_]*)\}/g, (match, name: string) => {
    if (!(name in params)) return match;
    const value = params[name];
    // Python ro'yxat literali (`str(list)` bilan bir xil ko'rinish) — shart serverda shunday to'ldiriladi.
    return Array.isArray(value)
      ? `[${value.map((v) => `'${String(v)}'`).join(", ")}]`
      : String(value);
  });
}

for (const dir of readdirSync(LABS).sort()) {
  const [code] = dir.split("-");
  test(`AGR-07: ${code} — yechim ko'rinadigan testlardan brauzerda o'tadi`, async ({
    page,
  }) => {
    test.setTimeout(240_000);
    const params = JSON.parse(
      readFileSync(join(LABS, dir, "variants", "basic-1.yaml"), "utf8").replace(
        /^params:\s*/,
        "",
      ),
    ) as Record<string, unknown>;
    const solution = render(
      readFileSync(join(LABS, dir, "solutions", "solution.py"), "utf8"),
      params,
    );
    const steps = readdirSync(join(LABS, dir, "tests", "visible")).map(
      (file) => ({
        key: file.replace(/\.py$/, ""),
        title: file,
        points: 1,
        visible_test: readFileSync(
          join(LABS, dir, "tests", "visible", file),
          "utf8",
        ),
      }),
    );
    await page.route("**/ws/**", (route) => route.abort());
    await page.route("**/api/**", async (route) => {
      const req = route.request();
      const path = new URL(req.url()).pathname;
      const json = (status: number, body: unknown) =>
        route.fulfill({
          status,
          contentType: "application/json",
          body: JSON.stringify(body),
        });
      const dataset = /^\/api\/datasets\/([a-z_]+)\/file$/.exec(path);
      if (dataset)
        return route.fulfill({
          status: 200,
          contentType: "text/csv",
          body: readFileSync(join(CONTENT, "datasets", `${dataset[1]}.csv`)),
        });
      if (path === "/api/auth/me")
        return json(200, {
          hemis_id: "123456789012",
          full_name: "Sinov Talaba",
          role: "student",
          direction: 1,
          must_change_password: false,
        });
      if (path === "/api/course/topics")
        return json(200, { course: { slug: "ml", title: "ML" }, topics: [] });
      if (path === "/api/labs/M01/work")
        return json(200, {
          version: 1,
          notebook: {
            format: 1,
            cells: [{ id: "c1", type: "code", source: solution }],
          },
          saved_at: null,
          policy: "on_time",
          paste_limit: 200,
          proctored: false,
        });
      if (path === "/api/labs/M01/assignment")
        return json(200, {
          code,
          title: dir,
          level: "basic",
          statement: "",
          params,
          steps,
        });
      if (path === "/api/labs/M01/submissions")
        return json(200, { best_final_score: null, submissions: [] });
      if (req.method() === "PUT")
        return json(200, { version: 2, saved_at: null, policy: "on_time" });
      return json(404, {});
    });
    await page.goto("/labs/M01");
    await page
      .getByRole("button", { name: messages["lab.check.button"] })
      .click();
    const summary = page.getByText(/Ko'rinadigan testlar: \d+ \/ \d+ o'tdi/);
    await expect(summary).toBeVisible({ timeout: 200_000 });
    const [, passed, total] =
      /(\d+) \/ (\d+)/.exec((await summary.textContent()) ?? "") ?? [];
    expect(Number(total)).toBeGreaterThan(0);
    expect(passed).toBe(total);
  });
}
