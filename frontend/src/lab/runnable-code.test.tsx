import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import messages from "../i18n/uz.json";
import RunnableCode from "./RunnableCode";
import type { RunEvent, RunResult } from "./runtime";

const fake = vi.hoisted(() => ({
  status: "idle" as string,
  listener: null as null | ((s: string) => void),
  next: null as null | ((events: (e: RunEvent) => void) => Promise<RunResult>),
  restart: (() => undefined) as () => void,
}));

vi.mock("./runtime", () => ({
  getRuntime: () => ({
    get status() {
      return fake.status;
    },
    onStatus: (l: (s: string) => void) => {
      fake.listener = l;
      return () => undefined;
    },
    run: (_code: string, onEvent: (e: RunEvent) => void) =>
      fake.next?.(onEvent),
    restart: () => fake.restart(),
  }),
}));

afterEach(cleanup);

describe("RunnableCode (CNT-02, LAB-02)", () => {
  it("chiqish, grafik va natija", async () => {
    fake.next = async (emit) => {
      fake.listener?.("loading");
      emit({ kind: "stdout", text: "salom" });
      emit({ kind: "figure", png: "AAA" });
      return { ok: true, result: "42", error: null };
    };
    const user = userEvent.setup();
    render(<RunnableCode code="print('salom')" />);
    await user.click(screen.getByRole("button", { name: messages["lab.run"] }));
    expect(await screen.findByText("salom")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Grafik 1" })).toHaveAttribute(
      "src",
      "data:image/png;base64,AAA",
    );
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: messages["lab.run"] }),
    ).toBeEnabled();
  });

  it("xato va to'xtatilgan holat", async () => {
    fake.next = async () => ({
      ok: false,
      result: null,
      error: "Traceback ... ZeroDivisionError",
    });
    const user = userEvent.setup();
    render(<RunnableCode code="1/0" />);
    await user.click(screen.getByRole("button", { name: messages["lab.run"] }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "ZeroDivisionError",
    );
    fake.next = async () => ({
      ok: false,
      result: null,
      error: null,
      interrupted: true,
    });
    await user.click(screen.getByRole("button", { name: messages["lab.run"] }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      messages["lab.interrupted"],
    );
  });

  it("yuklanayotganda holat matni", async () => {
    let finish: (r: RunResult) => void = () => undefined;
    fake.next = () => {
      fake.listener?.("loading");
      return new Promise((resolve) => (finish = resolve));
    };
    const user = userEvent.setup();
    render(<RunnableCode code="1" />);
    await user.click(screen.getByRole("button", { name: messages["lab.run"] }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      messages["lab.loading"],
    );
    act(() => fake.listener?.("ready"));
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent(
        messages["lab.running"],
      ),
    );
    await act(async () => finish({ ok: true, result: null, error: null }));
  });

  it("LAB-06: bajarilayotganda To'xtatish tugmasi muhitni qayta ishga tushiradi", async () => {
    let finish: (r: RunResult) => void = () => undefined;
    fake.next = () => new Promise((resolve) => (finish = resolve));
    fake.restart = () =>
      finish({ ok: false, result: null, error: null, interrupted: true });
    const user = userEvent.setup();
    render(<RunnableCode code="while True: pass" />);
    expect(
      screen.queryByRole("button", { name: messages["lab.stop"] }),
    ).toBeNull();
    await user.click(screen.getByRole("button", { name: messages["lab.run"] }));
    await user.click(
      await screen.findByRole("button", { name: messages["lab.stop"] }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      messages["lab.interrupted"],
    );
    expect(
      screen.queryByRole("button", { name: messages["lab.stop"] }),
    ).toBeNull();
    expect(
      screen.getByRole("button", { name: messages["lab.run"] }),
    ).toBeEnabled();
  });
});
