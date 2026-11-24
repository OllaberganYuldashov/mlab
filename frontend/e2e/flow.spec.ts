import { expect, test, type Page, type Route, type WebSocketRoute } from "@playwright/test";
import messages from "../src/i18n/uz.json" with { type: "json" };

/**
 * I1 uchidan-uchiga oqimi (SEC-01..04, ACC-01/05/07): o'qituvchi guruh yaratadi → talaba havola orqali
 * so'rov yuboradi → o'qituvchi tasdiqlaydi → o'qituvchi oynani "Hozir ochish" qiladi → talaba sahifasi
 * WebSocket xabari bilan "Hozir ochiq" ni ko'rsatadi. Ikki brauzer konteksti bitta holatli soxta backend'ni
 * bo'lishadi (frontend CI job'ida haqiqiy backend yo'q; backend oqimi `backend/tests/sections` da).
 */
test("I1: guruh → havola → tasdiq → oyna ochildi → talabada real vaqtda ochiq", async ({ browser }) => {
  const db = {
    section: null as null | Record<string, unknown>,
    joinPath: "",
    membership: null as null | { id: number; status: "pending" | "approved" },
    window: { mode: "closed", status: "closed", opens_at: null as string | null },
  };
  const sockets: WebSocketRoute[] = [];
  const topic = { code: "M01", title: "Kirish", order: 1 };
  const values = { ai_enabled: true, ai_max_mode: "explain", practice_after_close: false, late_hours: 0, chat_enabled: true };
  const student = { id: 7, hemis_id: "123456789012", full_name: "Sinov Talaba" };

  const backend = (role: "instructor" | "student") => async (route: Route) => {
    const req = route.request();
    const url = new URL(req.url());
    const key = `${req.method()} ${url.pathname}`;
    const json = (status: number, body: unknown) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    const approved = db.membership?.status === "approved";

    if (key === "GET /api/auth/me")
      return role === "instructor"
        ? json(200, { hemis_id: "100000000001", full_name: "Ustoz Sinov", role, direction: null, must_change_password: false })
        : json(200, { ...student, role, direction: 1, must_change_password: false });

    if (role === "instructor") {
      if (key === "GET /api/directions") return json(200, [{ id: 1, name: "Dasturiy injiniring" }]);
      if (key === "GET /api/sections") return json(200, { results: db.section ? [db.section] : [] });
      if (key === "POST /api/sections") {
        const body = req.postDataJSON();
        db.section = { id: 5, name: body.name, direction: body.direction, capacity: body.capacity, join_enabled: true, approved_count: 0, has_join_token: false };
        return json(201, db.section);
      }
      if (key === "GET /api/sections/5") return json(200, { ...db.section, approved_count: approved ? 1 : 0 });
      if (key === "POST /api/sections/5/join-token") {
        db.joinPath = "/join/e2eFlowToken1234567890";
        db.section = { ...db.section, has_join_token: true };
        return json(201, { token: "t", join_path: db.joinPath });
      }
      if (key === "GET /api/sections/5/members") {
        const wanted = url.searchParams.get("status");
        const rows = db.membership && db.membership.status === wanted ? [{ id: db.membership.id, status: wanted, student }] : [];
        return json(200, { results: rows });
      }
      if (key === "POST /api/sections/5/members/decide") {
        const body = req.postDataJSON();
        if (db.membership && body.decision === "approve" && body.ids.includes(db.membership.id)) db.membership.status = "approved";
        return json(200, { approved: body.ids, rejected: [], skipped: [] });
      }
      if (key === "GET /api/sections/5/settings") return json(200, { course_defaults: values, overrides: {}, effective: values });
      if (key === "GET /api/sections/5/deadlines") return json(200, { deadlines: [] });
      if (key === "GET /api/sections/5/windows")
        return json(200, { server_time: new Date().toISOString(), windows: [windowRow()] });
      if (key === "POST /api/sections/5/windows/M01/open-now") {
        db.window = { mode: "open_now", status: "open", opens_at: new Date().toISOString() };
        // Backend `transaction.on_commit` dan keyin guruh kanaliga yuboradigan xabar.
        for (const ws of sockets) ws.send(JSON.stringify({ type: "window.changed", topic: "M01" }));
        return json(200, windowRow());
      }
    } else {
      if (key === `GET /api/join${db.joinPath.slice("/join".length)}`)
        return json(200, { section: "ML-21", instructor: "Ustoz Sinov", join_enabled: true, is_full: false });
      if (key === `POST /api/join${db.joinPath.slice("/join".length)}`) {
        db.membership = { id: 11, status: "pending" };
        return json(201, { status: "pending" });
      }
      if (key === "GET /api/me/membership")
        return json(200, { membership: db.membership ? { status: db.membership.status, section: "ML-21", instructor: "Ustoz Sinov" } : null });
      if (key === "GET /api/me/next-window") {
        const open = db.window.status === "open" ? [windowRow()] : [];
        return json(200, { server_time: new Date().toISOString(), open, next: null });
      }
    }
    return json(404, { detail: `soxta API: ${key}` });
  };

  function windowRow() {
    return {
      topic,
      mode: db.window.mode,
      proctored: false,
      state: { status: db.window.status, opens_at: db.window.opens_at, closes_at: null },
    };
  }

  async function openAs(role: "instructor" | "student"): Promise<Page> {
    const context = await browser.newContext();
    await context.addCookies([{ name: "csrftoken", value: "e2e", url: "http://localhost:4173" }]);
    const page = await context.newPage();
    await page.route("**/api/**", backend(role));
    await page.routeWebSocket("**/ws/student", (ws) => {
      sockets.push(ws);
    });
    return page;
  }

  const teacher = await openAs("instructor");
  const pupil = await openAs("student");

  // 1. O'qituvchi guruh yaratadi va havola oladi.
  await teacher.goto("/sections");
  await teacher.getByLabel(messages["sections.field.name"]).fill("ML-21");
  await teacher.getByLabel(messages["field.direction"]).selectOption({ label: "Dasturiy injiniring" });
  await teacher.getByRole("button", { name: messages["sections.create.submit"] }).click();
  await teacher.getByRole("link", { name: messages["sections.open"] }).click();
  await teacher.getByRole("button", { name: messages["section.link.rotate"] }).click();
  const joinUrl = await teacher.getByTestId("join-url").textContent();
  expect(joinUrl).toMatch(/\/join\/e2eFlowToken1234567890$/);

  // 2. Talaba havolani ochadi va so'rov yuboradi.
  await pupil.goto(new URL(joinUrl ?? "").pathname);
  await expect(pupil.getByText("Guruh: ML-21")).toBeVisible();
  await pupil.getByRole("button", { name: messages["join.submit"] }).click();
  await expect(pupil.getByText(messages["join.sent"])).toBeVisible();

  // 3. O'qituvchi so'rovni ko'radi va tasdiqlaydi.
  await teacher.reload();
  await teacher.getByRole("checkbox", { name: student.full_name }).check();
  await teacher.getByRole("button", { name: messages["section.requests.approve"] }).click();
  await expect(teacher.getByText("Tasdiqlandi: 1, rad etildi: 0.")).toBeVisible();

  // 4. Talaba a'zo bo'lganini ko'radi; laboratoriya hali yopiq.
  await pupil.goto("/");
  await expect(pupil.getByText(/guruhi a'zosisiz/)).toBeVisible();
  await expect(pupil.getByText(messages["lab.none"])).toBeVisible();
  await expect.poll(() => sockets.length).toBeGreaterThan(0);

  // 5. O'qituvchi oynani ochadi → talaba sahifasi qayta yuklanmasdan "Hozir ochiq" ni ko'rsatadi.
  await teacher.getByRole("row", { name: /M01 Kirish/ }).getByRole("button", { name: messages["windows.openNow"] }).click();
  await expect(teacher.getByRole("row", { name: /M01 Kirish/ })).toContainText(messages["windows.open"]);
  await expect(pupil.getByText("Hozir ochiq: M01 Kirish")).toBeVisible();
});
