import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api, fieldErrors } from "./api";
import { Link } from "./Link";
import { navigate } from "./router";

afterEach(() => vi.unstubAllGlobals());

describe("api", () => {
  it("JSON bo'lmagan javob xatosiz o'qiladi", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("<html>", { status: 502 })));
    expect(await api("/x")).toEqual({ ok: false, status: 502, data: null });
  });

  it("GET so'rovda CSRF sarlavhasi yuborilmaydi", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => new Response("[]", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await api("/x");
    const init = fetchMock.mock.calls[0]?.[1];
    expect(init?.headers).not.toHaveProperty("X-CSRFToken");
  });
});

describe("fieldErrors", () => {
  it("DRF xatolarini birinchi xabarga keltiradi, begona shaklni tashlaydi", () => {
    expect(fieldErrors({ a: ["x", "y"], b: "z", c: [1], d: 5 })).toEqual({ a: "x", b: "z" });
    expect(fieldErrors(null)).toEqual({});
  });
});

describe("Link", () => {
  it("oddiy bosish sahifani yangilamaydi, manzilni almashtiradi", () => {
    render(<Link to="/register">Havola</Link>);
    fireEvent.click(screen.getByRole("link", { name: "Havola" }));
    expect(window.location.pathname).toBe("/register");
  });

  it("Ctrl+bosish brauzerning odatiy xatti-harakatiga qoladi", () => {
    navigate("/");
    render(<Link to="/register">Havola</Link>);
    fireEvent.click(screen.getByRole("link", { name: "Havola" }), { ctrlKey: true });
    expect(window.location.pathname).toBe("/");
  });
});
