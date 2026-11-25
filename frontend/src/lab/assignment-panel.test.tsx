import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import messages from "../i18n/uz.json";
import { mockApi } from "../test-utils";
import AssignmentPanel from "./AssignmentPanel";
import type { CheckResult } from "./checker";

const fake = vi.hoisted(() => ({
  next: null as null | (() => Promise<CheckResult>),
  args: [] as unknown[],
}));

vi.mock("./checker", async (orig) => ({
  ...(await orig<typeof import("./checker")>()),
  runCheck: (...args: unknown[]) => {
    fake.args = args;
    return fake.next?.();
  },
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const ASSIGNMENT = {
  code: "A01",
  title: "Pandas bilan tozalash",
  level: "basic",
  statement: "`iris` datasetidagi `c3` ustunini tozalang.",
  params: { dataset: "iris", column: "c3" },
  steps: [
    {
      key: "load",
      title: "Yuklash",
      points: 40,
      visible_test: "def test_loaded(ns, params): ...",
    },
    { key: "clean", title: "Tozalash", points: 60, visible_test: null },
  ],
};
const notebook = {
  format: 1 as const,
  cells: [{ id: "a", type: "code" as const, source: "df = 1" }],
};

function show(body: unknown = ASSIGNMENT, status = 200) {
  mockApi({ "GET /api/labs/M01/assignment": () => ({ status, body }) });
  render(<AssignmentPanel code="M01" getNotebook={() => notebook} />);
}

describe("AssignmentPanel (AGR-01, LAB-07)", () => {
  it("shart, daraja, qadamlar va Tekshirish natijasi", async () => {
    fake.next = async () => ({
      status: "ok",
      error: null,
      stdout: "",
      tests: [
        { step: "load", name: "test_loaded", passed: true, message: "", ms: 2 },
        {
          step: "load",
          name: "test_rows",
          passed: false,
          message: "150 qator kutilgan",
          ms: 1,
        },
      ],
    });
    show();
    expect(
      await screen.findByText("A01. Pandas bilan tozalash"),
    ).toBeInTheDocument();
    expect(screen.getByText("Daraja: asosiy")).toBeInTheDocument();
    expect(screen.getByText("Yuklash — 40 ball")).toBeInTheDocument();
    expect(screen.getAllByText("c3")).toHaveLength(2); // shartda va variant parametrlarida
    expect(screen.getByText(messages["lab.task.params"])).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: messages["lab.check.button"] }),
    );
    expect(
      await screen.findByText("Ko'rinadigan testlar: 1 / 2 o'tdi"),
    ).toBeInTheDocument();
    expect(screen.getByText(/150 qator kutilgan/)).toBeInTheDocument();
    expect(screen.getByLabelText("o'tmadi")).toBeInTheDocument();
    // Faqat ko'rinadigan test va notebook kodi yuboriladi.
    expect(fake.args.slice(1)).toEqual([
      "df = 1",
      [{ step: "load", source: "def test_loaded(ns, params): ..." }],
      { dataset: "iris", column: "c3" },
    ]);
  });

  it("kod xatosi va vaqt chegarasi", async () => {
    fake.next = async () => ({
      status: "code_error",
      error: "NameError: name 'pd' is not defined (1-qator)",
      stdout: "",
      tests: [],
    });
    show();
    const button = await screen.findByRole("button", {
      name: messages["lab.check.button"],
    });
    await userEvent.click(button);
    expect(await screen.findByText(/NameError: name 'pd'/)).toBeInTheDocument();
    fake.next = async () => ({
      status: "timeout",
      error: null,
      stdout: "",
      tests: [],
    });
    await userEvent.click(button);
    expect(await screen.findByText(/Vaqt tugadi \(30 s\)/)).toBeInTheDocument();
    fake.next = async () => ({
      status: "failed",
      error: "x",
      stdout: "",
      tests: [],
    });
    await userEvent.click(button);
    expect(
      await screen.findByText(messages["lab.check.failed"]),
    ).toBeInTheDocument();
  });

  it("ko'rinadigan test yo'q — tugma yo'q, izoh bor", async () => {
    show({ ...ASSIGNMENT, steps: [{ ...ASSIGNMENT.steps[1] }] });
    expect(
      await screen.findByText(messages["lab.check.none"]),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: messages["lab.check.button"] }),
    ).not.toBeInTheDocument();
    // Topshirish baribir mumkin (yashirin testlar serverda).
    expect(
      screen.getByRole("button", { name: messages["lab.submit.button"] }),
    ).toBeInTheDocument();
  });

  it("topshiriq yo'q (404) va xato", async () => {
    show({ code: "no_assignment" }, 404);
    expect(
      await screen.findByText(messages["lab.task.placeholder"]),
    ).toBeInTheDocument();
    cleanup();
    show({}, 500);
    expect(
      await screen.findByText(messages["common.unexpectedError"]),
    ).toBeInTheDocument();
  });
});
