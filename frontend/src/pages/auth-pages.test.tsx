import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import messages from "../i18n/uz.json";
import { mockApi } from "../test-utils";

const ME = {
  hemis_id: "123456789012",
  full_name: "Test Talaba",
  role: "student",
  direction: 1,
  must_change_password: false,
};
const NO_SESSION = { "GET /api/auth/me": () => ({ status: 403, body: { detail: "x" } }) };
const CSRF = { "GET /api/auth/csrf": () => ({ status: 204 }) };

function visit(path: string) {
  window.history.replaceState(null, "", path);
}

beforeEach(() => {
  document.cookie = "csrftoken=tok123";
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
});

describe("/login (AUTH-02)", () => {
  it("to'g'ri ma'lumot bilan kiradi va CSRF sarlavhasini yuboradi", async () => {
    const calls = mockApi({
      ...NO_SESSION,
      "POST /api/auth/login": () => ({ status: 200, body: ME }),
    });
    visit("/login");
    render(<App />);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(messages["field.hemisId"]), "123456789012");
    await user.type(screen.getByLabelText(messages["field.password"]), "maxfiy-parol-1");
    await user.click(screen.getByRole("button", { name: messages["login.submit"] }));
    expect(await screen.findByText("Salom, Test Talaba!")).toBeInTheDocument();
    const login = calls.find((c) => c.path === "/api/auth/login");
    expect(login?.csrf).toBe("tok123");
    expect(login?.body).toEqual({ hemis_id: "123456789012", password: "maxfiy-parol-1" });
  });

  it("noto'g'ri parol — uz.json dagi xabar", async () => {
    mockApi({ ...NO_SESSION, "POST /api/auth/login": () => ({ status: 400, body: {} }) });
    visit("/login");
    render(<App />);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(messages["field.hemisId"]), "1");
    await user.type(screen.getByLabelText(messages["field.password"]), "x");
    await user.click(screen.getByRole("button", { name: messages["login.submit"] }));
    expect(await screen.findByRole("alert")).toHaveTextContent(messages["login.failed"]);
  });

  it("lockout (429) — alohida xabar", async () => {
    mockApi({ ...NO_SESSION, "POST /api/auth/login": () => ({ status: 429, body: {} }) });
    visit("/login");
    render(<App />);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(messages["field.hemisId"]), "1");
    await user.type(screen.getByLabelText(messages["field.password"]), "x");
    await user.click(screen.getByRole("button", { name: messages["login.submit"] }));
    expect(await screen.findByRole("alert")).toHaveTextContent(messages["login.locked"]);
  });

  it("tarmoq xatosi — tushunarli xabar", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string) => {
        if (input === "/api/auth/me") return new Response(null, { status: 403 });
        throw new TypeError("network");
      }),
    );
    visit("/login");
    render(<App />);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(messages["field.hemisId"]), "1");
    await user.type(screen.getByLabelText(messages["field.password"]), "x");
    await user.click(screen.getByRole("button", { name: messages["login.submit"] }));
    expect(await screen.findByRole("alert")).toHaveTextContent(messages["common.networkError"]);
  });

  it("vaqtinchalik parol bilan kirgan foydalanuvchi /change-password ga yo'naltiriladi", async () => {
    mockApi({
      ...NO_SESSION,
      "POST /api/auth/login": () => ({ status: 200, body: { ...ME, must_change_password: true } }),
    });
    visit("/login");
    render(<App />);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(messages["field.hemisId"]), "1");
    await user.type(screen.getByLabelText(messages["field.password"]), "x");
    await user.click(screen.getByRole("button", { name: messages["login.submit"] }));
    expect(
      await screen.findByRole("heading", { name: messages["password.title"] }),
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe("/change-password");
    expect(screen.getByText(messages["password.required"])).toBeInTheDocument();
  });

  it("majburiy almashtirish: boshqa sahifaga o'tib bo'lmaydi", async () => {
    mockApi({ "GET /api/auth/me": () => ({ status: 200, body: { ...ME, must_change_password: true } }) });
    visit("/");
    render(<App />);
    await waitFor(() => expect(window.location.pathname).toBe("/change-password"));
  });
});

describe("/register (AUTH-01)", () => {
  const registerApi = {
    ...NO_SESSION,
    ...CSRF,
    "GET /api/directions": () => ({ status: 200, body: [{ id: 7, name: "Dasturiy injiniring" }] }),
    "GET /api/policy": () => ({ status: 200, body: { version: "2026-11-22" } }),
  };

  async function fillForm() {
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(messages["field.hemisId"]), "123456789012");
    await user.type(screen.getByLabelText(messages["field.fullName"]), "Test Talaba");
    await user.selectOptions(screen.getByLabelText(messages["field.direction"]), "7");
    await user.type(screen.getByLabelText(messages["field.password"]), "uzun-maxfiy-parol-9");
    return user;
  }

  it("rozilik belgisisiz tugma faol emas; belgilanganda faol", async () => {
    mockApi(registerApi);
    visit("/register");
    render(<App />);
    const user = await fillForm();
    const button = screen.getByRole("button", { name: messages["register.submit"] });
    await waitFor(() => expect(screen.getByRole("option", { name: "Dasturiy injiniring" })).toBeInTheDocument());
    expect(button).toBeDisabled();
    await user.click(screen.getByLabelText(messages["register.consentCheckbox"]));
    expect(button).toBeEnabled();
  });

  it("siyosat sahifasiga havola bor", async () => {
    mockApi(registerApi);
    visit("/register");
    render(<App />);
    const link = await screen.findByRole("link", { name: messages["register.policyLink"] });
    expect(link).toHaveAttribute("href", "/policy");
  });

  it("yuboriladi: siyosat versiyasi backend'dan, CSRF bilan; so'ng /login", async () => {
    const calls = mockApi({
      ...registerApi,
      "POST /api/auth/register": () => ({ status: 201, body: {} }),
    });
    visit("/register");
    render(<App />);
    const user = await fillForm();
    await waitFor(() => expect(screen.getByRole("option", { name: "Dasturiy injiniring" })).toBeInTheDocument());
    await user.click(screen.getByLabelText(messages["register.consentCheckbox"]));
    await user.click(screen.getByRole("button", { name: messages["register.submit"] }));
    await waitFor(() => expect(window.location.pathname).toBe("/login"));
    const post = calls.find((c) => c.path === "/api/auth/register");
    expect(post?.csrf).toBe("tok123");
    expect(post?.body).toEqual({
      hemis_id: "123456789012",
      full_name: "Test Talaba",
      direction: 7,
      password: "uzun-maxfiy-parol-9",
      consent: true,
      policy_version: "2026-11-22",
    });
    expect(await screen.findByText(messages["register.success"])).toBeInTheDocument();
  });

  it("maydon xatolari tegishli maydon yonida ko'rsatiladi", async () => {
    mockApi({
      ...registerApi,
      "POST /api/auth/register": () => ({
        status: 400,
        body: { hemis_id: ["Bu Hemis ID bilan foydalanuvchi allaqachon bor."] },
      }),
    });
    visit("/register");
    render(<App />);
    const user = await fillForm();
    await waitFor(() => expect(screen.getByRole("option", { name: "Dasturiy injiniring" })).toBeInTheDocument());
    await user.click(screen.getByLabelText(messages["register.consentCheckbox"]));
    await user.click(screen.getByRole("button", { name: messages["register.submit"] }));
    const input = screen.getByLabelText(messages["field.hemisId"]);
    await waitFor(() => expect(input).toHaveAttribute("aria-invalid", "true"));
    expect(input).toHaveAccessibleDescription(/allaqachon bor/);
  });

  it("xatosiz 400 / 500 — umumiy xabar", async () => {
    mockApi({ ...registerApi, "POST /api/auth/register": () => ({ status: 500 }) });
    visit("/register");
    render(<App />);
    const user = await fillForm();
    await waitFor(() => expect(screen.getByRole("option", { name: "Dasturiy injiniring" })).toBeInTheDocument());
    await user.click(screen.getByLabelText(messages["register.consentCheckbox"]));
    await user.click(screen.getByRole("button", { name: messages["register.submit"] }));
    expect(await screen.findByRole("alert")).toHaveTextContent(messages["common.unexpectedError"]);
  });

  it("siyosat versiyasi yuklanmasa yuborib bo'lmaydi", async () => {
    mockApi({ ...registerApi, "GET /api/policy": () => ({ status: 500 }) });
    visit("/register");
    render(<App />);
    const user = await fillForm();
    await user.click(screen.getByLabelText(messages["register.consentCheckbox"]));
    expect(await screen.findByRole("alert")).toHaveTextContent(messages["register.policyUnavailable"]);
    expect(screen.getByRole("button", { name: messages["register.submit"] })).toBeDisabled();
  });
});

describe("/change-password (AUTH-04)", () => {
  it("parolni almashtiradi, so'ng bosh sahifa", async () => {
    let changed = false;
    const calls = mockApi({
      "GET /api/auth/me": () => ({
        status: 200,
        body: { ...ME, must_change_password: !changed },
      }),
      "POST /api/auth/change-password": () => {
        changed = true;
        return { status: 204 };
      },
    });
    visit("/change-password");
    render(<App />);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(messages["field.oldPassword"]), "vaqtincha");
    await user.type(screen.getByLabelText(messages["field.newPassword"]), "yangi-uzun-parol-5");
    await user.click(screen.getByRole("button", { name: messages["password.submit"] }));
    await waitFor(() => expect(window.location.pathname).toBe("/"));
    const post = calls.find((c) => c.path === "/api/auth/change-password");
    expect(post?.body).toEqual({ old_password: "vaqtincha", new_password: "yangi-uzun-parol-5" });
  });

  it("xato maydon yonida ko'rsatiladi", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: ME }),
      ...CSRF,
      "POST /api/auth/change-password": () => ({
        status: 400,
        body: { old_password: ["Joriy parol noto'g'ri."], new_password: ["Juda qisqa."] },
      }),
    });
    visit("/change-password");
    render(<App />);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(messages["field.oldPassword"]), "x");
    await user.type(screen.getByLabelText(messages["field.newPassword"]), "y");
    await user.click(screen.getByRole("button", { name: messages["password.submit"] }));
    expect(await screen.findByText("Joriy parol noto'g'ri.")).toBeInTheDocument();
    expect(screen.getByText("Juda qisqa.")).toBeInTheDocument();
  });

  it("kirmagan foydalanuvchi /login ga yo'naltiriladi", async () => {
    mockApi(NO_SESSION);
    visit("/change-password");
    render(<App />);
    await waitFor(() => expect(window.location.pathname).toBe("/login"));
  });
});

describe("chiqish va noma'lum sahifa", () => {
  it("chiqish tugmasi /logout ni CSRF bilan chaqiradi", async () => {
    const calls = mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: ME }),
      "POST /api/auth/logout": () => ({ status: 204 }),
    });
    visit("/");
    render(<App />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: messages["nav.logout"] }));
    await waitFor(() => expect(window.location.pathname).toBe("/login"));
    expect(calls.find((c) => c.path === "/api/auth/logout")?.csrf).toBe("tok123");
  });

  it("chiqish muvaffaqiyatsiz bo'lsa foydalanuvchi kirgan holda qoladi va xabar ko'rinadi", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: ME }),
      "POST /api/auth/logout": () => ({ status: 500 }),
    });
    visit("/");
    render(<App />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: messages["nav.logout"] }));
    expect(await screen.findByRole("alert")).toHaveTextContent(messages["common.unexpectedError"]);
    expect(window.location.pathname).toBe("/");
  });

  it("noma'lum manzil — 'topilmadi' sahifasi", async () => {
    mockApi(NO_SESSION);
    visit("/yoq-sahifa");
    render(<App />);
    expect(await screen.findByRole("heading", { name: messages["notFound.title"] })).toBeInTheDocument();
  });

  it("CSRF cookie yo'q bo'lsa avval /api/auth/csrf chaqiriladi", async () => {
    document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    const calls = mockApi({
      ...NO_SESSION,
      "GET /api/auth/csrf": () => {
        document.cookie = "csrftoken=fresh";
        return { status: 204 };
      },
      "POST /api/auth/login": () => ({ status: 400, body: {} }),
    });
    visit("/login");
    render(<App />);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(messages["field.hemisId"]), "1");
    await user.type(screen.getByLabelText(messages["field.password"]), "x");
    await user.click(screen.getByRole("button", { name: messages["login.submit"] }));
    await screen.findByRole("alert");
    expect(calls.map((c) => c.path)).toContain("/api/auth/csrf");
    expect(calls.find((c) => c.path === "/api/auth/login")?.csrf).toBe("fresh");
  });
});
