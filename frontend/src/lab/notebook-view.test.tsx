import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import messages from "../i18n/uz.json";
import Notebook from "./Notebook";
import type { Notebook as NotebookState } from "./notebook";
import type { RunEvent, RunResult } from "./runtime";

const fake = vi.hoisted(() => ({
  run: null as null | ((code: string, emit: (e: RunEvent) => void) => Promise<RunResult>),
  restarted: 0,
}));

vi.mock("./runtime", () => ({
  getRuntime: () => ({
    status: "ready",
    onStatus: () => () => undefined,
    run: (code: string, emit: (e: RunEvent) => void) => fake.run?.(code, emit),
    restart: () => {
      fake.restarted += 1;
    },
  }),
}));

// CodeMirror o'rniga textarea (haqiqiy muharrir — Playwright'da).
vi.mock("./CodeEditor", () => ({
  default: ({ value, label, onChange, onRun }: { value: string; label: string; onChange: (v: string) => void; onRun: () => void }) => (
    <textarea
      aria-label={label}
      defaultValue={value}
      onChange={(e) => onChange(e.target.value)}
      onKeyDown={(e) => {
        if (e.key === "Enter" && e.shiftKey) {
          e.preventDefault();
          onRun();
        }
      }}
    />
  ),
}));

afterEach(cleanup);

const INITIAL: NotebookState = { format: 1, cells: [{ id: "c1", type: "code", source: "print(1)" }] };

describe("Notebook (LAB-01)", () => {
  it("▶ va Shift+Enter: chiqish, grafik, natija, tartib raqami", async () => {
    fake.run = async (code, emit) => {
      emit({ kind: "stdout", text: `ishladi: ${code}` });
      emit({ kind: "figure", png: "AAA" });
      return { ok: true, result: "7", error: null };
    };
    const runs: NotebookState[] = [];
    const user = userEvent.setup();
    render(<Notebook initial={INITIAL} onRun={(nb) => runs.push(nb)} />);
    await user.click(screen.getByRole("button", { name: "1-katakni ishga tushirish" }));
    expect(await screen.findByText("ishladi: print(1)")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Grafik 1" })).toBeInTheDocument();
    expect(screen.getByText("[1]")).toBeInTheDocument();
    expect(runs).toHaveLength(1);

    const editor = screen.getByRole("textbox", { name: "Kod katagi 1" });
    fireEvent.change(editor, { target: { value: "2 + 2" } });
    fireEvent.keyDown(editor, { key: "Enter", shiftKey: true });
    expect(await screen.findByText("ishladi: 2 + 2")).toBeInTheDocument();
    expect(screen.getByText("[2]")).toBeInTheDocument();
  });

  it("katak qo'shish, ko'chirish, o'chirish va onChange", async () => {
    const changes: NotebookState[] = [];
    const user = userEvent.setup();
    render(<Notebook initial={INITIAL} onChange={(nb) => changes.push(nb)} />);
    await user.click(screen.getByRole("button", { name: messages["lab.cell.addCode"] }));
    expect(screen.getAllByRole("region")).toHaveLength(2);
    await user.click(screen.getByRole("button", { name: "2-katakni yuqoriga" }));
    expect(changes.at(-1)?.cells[1]?.id).toBe("c1");
    await user.click(screen.getByRole("button", { name: "1-katakni o'chirish" }));
    expect(changes.at(-1)?.cells.map((c) => c.id)).toEqual(["c1"]);
    expect(screen.getByRole("button", { name: "1-katakni o'chirish" })).toBeDisabled();
  });

  it("matn katagi: yozish → Shift+Enter → ko'rinish → tahrirlash", async () => {
    const user = userEvent.setup();
    render(<Notebook initial={INITIAL} />);
    await user.click(screen.getByRole("button", { name: messages["lab.cell.addMarkdown"] }));
    const md = screen.getByRole("textbox", { name: "Matn katagi 2" });
    fireEvent.change(md, { target: { value: "**Xulosa**" } });
    fireEvent.keyDown(md, { key: "Enter", shiftKey: true });
    const region = screen.getByRole("region", { name: "Matn katagi 2" });
    expect(within(region).getByText("Xulosa").tagName).toBe("STRONG");
    await user.click(within(region).getByRole("button", { name: messages["lab.cell.edit"] }));
    expect(within(region).getByRole("textbox")).toBeInTheDocument();
  });

  it("xato va to'xtatish", async () => {
    let finish: (r: RunResult) => void = () => undefined;
    fake.run = () => new Promise((resolve) => (finish = resolve));
    const user = userEvent.setup();
    render(<Notebook initial={INITIAL} />);
    await user.click(screen.getByRole("button", { name: "1-katakni ishga tushirish" }));
    expect(screen.getByText("[*]")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: messages["lab.stop"] }));
    expect(fake.restarted).toBe(1);
    finish({ ok: false, result: null, error: null, interrupted: true });
    expect(await screen.findByRole("alert")).toHaveTextContent(messages["lab.interrupted"]);
    fake.run = async () => ({ ok: false, result: null, error: "NameError: x" });
    await user.click(screen.getByRole("button", { name: "1-katakni ishga tushirish" }));
    expect(await screen.findByText("NameError: x")).toBeInTheDocument();
  });
});
