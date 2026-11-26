import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import messages from "../i18n/uz.json";
import { mockApi } from "../test-utils";
import SubmitPanel from "./SubmitPanel";
import type { Submission } from "./submissions";

const watcher = vi.hoisted(() => ({
  ids: [] as number[],
  update: null as null | ((s: Submission) => void),
  stops: 0,
}));

vi.mock("./submissions", async (orig) => ({
  ...(await orig<typeof import("./submissions")>()),
  watchSubmission: (id: number, onUpdate: (s: Submission) => void) => {
    watcher.ids.push(id);
    watcher.update = onUpdate;
    return () => {
      watcher.stops += 1;
    };
  },
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  watcher.ids = [];
  watcher.update = null;
});

const URL = "/api/labs/M01/submissions";
const sub = (over: Partial<Submission>): Submission => ({
  id: 1,
  status: "queued",
  position: 1,
  policy: "on_time",
  score: null,
  final_score: null,
  created_at: "2026-11-26T05:00:00Z",
  finished_at: null,
  understanding: "none",
  ...over,
});

describe("SubmitPanel (AGR-02, AGR-04, AGR-05, AGR-06)", () => {
  it("topshirish → navbat → natija qadamlar bo'yicha, eng yuqori ball", async () => {
    let listed: Submission[] = [];
    let best: string | null = null;
    const calls = mockApi({
      [`GET ${URL}`]: () => ({
        status: 200,
        body: { best_final_score: best, submissions: listed },
      }),
      [`POST ${URL}`]: () => ({
        status: 202,
        body: sub({ id: 5, position: 3 }),
      }),
    });
    const onGraded = vi.fn();
    render(
      <SubmitPanel code="M01" getCode={() => "df = 1"} onGraded={onGraded} />,
    );
    const button = await screen.findByRole("button", {
      name: messages["lab.submit.button"],
    });
    await userEvent.click(button);
    expect(await screen.findByText(/Navbatda: 3-o'rin/)).toBeInTheDocument();
    expect(button).toBeDisabled();
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({
      code: "df = 1",
    });
    expect(watcher.ids).toEqual([5]);
    act(() => watcher.update?.(sub({ id: 5, status: "running", position: 0 })));
    expect(
      screen.getByText(messages["lab.submit.running"]),
    ).toBeInTheDocument();
    const done = sub({
      id: 5,
      status: "done",
      position: 0,
      score: 70,
      final_score: "70.00",
      result: {
        code_error: null,
        steps: [
          {
            key: "load",
            title: "Yuklash",
            points: 40,
            score: 40,
            passed: 1,
            total: 1,
            tests: [
              { name: "test_loaded", visible: true, passed: true, message: "" },
            ],
          },
          {
            key: "clean",
            title: "Tozalash",
            points: 60,
            score: 30,
            passed: 1,
            total: 2,
            tests: [
              {
                name: "yashirin test 1",
                visible: false,
                passed: false,
                message: "O'tmadi",
              },
              {
                name: "yashirin test 2",
                visible: false,
                passed: true,
                message: "",
              },
            ],
          },
        ],
      },
    });
    listed = [done];
    best = "70.00";
    act(() => watcher.update?.(done));
    expect(await screen.findByText("Ball: 70.00 / 100")).toBeInTheDocument();
    expect(onGraded).toHaveBeenCalledOnce();
    expect(
      screen.getByText(/30 \/ 60 ball \(1 \/ 2 test\)/),
    ).toBeInTheDocument();
    expect(screen.getByText(/O'tmadi/)).toBeInTheDocument();
    expect(
      await screen.findByText("Eng yuqori rasmiy ball: 70.00"),
    ).toBeInTheDocument();
    expect(screen.getByText("Urinishlar (1)")).toBeInTheDocument();
    expect(button).toBeEnabled();
  });

  it("ochiq urinish bilan qaytsa — kuzatish davom etadi; kechikkan va mashq belgilari", async () => {
    mockApi({
      [`GET ${URL}`]: () => ({
        status: 200,
        body: {
          best_final_score: "90.00",
          submissions: [
            sub({ id: 9, status: "running", position: 0 }),
            sub({
              id: 8,
              status: "done",
              final_score: "50.00",
              policy: "practice",
            }),
            sub({ id: 7, status: "error" }),
          ],
        },
      }),
    });
    render(<SubmitPanel code="M01" getCode={() => "x = 1"} />);
    expect(
      await screen.findByText(messages["lab.submit.running"]),
    ).toBeInTheDocument();
    expect(watcher.ids).toEqual([9]);
    expect(screen.getByText(/50.00 ball/)).toBeInTheDocument();
    expect(screen.getByText(/xato \(qayta topshiring\)/)).toBeInTheDocument();
    act(() =>
      watcher.update?.(
        sub({ id: 9, status: "done", final_score: "63.00", policy: "late" }),
      ),
    );
    expect(await screen.findByText(/Ball: 63.00 \/ 100/)).toBeInTheDocument();
    expect(screen.getByText(/kechikkan — jarima bilan/)).toBeInTheDocument();
    act(() => watcher.update?.(sub({ id: 9, status: "error" })));
    expect(screen.getByText(messages["lab.submit.error"])).toBeInTheDocument();
  });

  it.each([
    [409, { code: "submission_pending" }, messages["lab.submit.pending"]],
    [403, { code: "lab_closed" }, messages["save.closed"]],
    [429, {}, messages["lab.submit.tooMany"]],
    [500, null, messages["common.unexpectedError"]],
  ])("rad javobi %i — tushunarli xabar", async (status, body, text) => {
    mockApi({
      [`GET ${URL}`]: () => ({
        status: 200,
        body: { best_final_score: null, submissions: [] },
      }),
      [`POST ${URL}`]: () => ({ status, body }),
    });
    render(<SubmitPanel code="M01" getCode={() => "x = 1"} />);
    await userEvent.click(
      await screen.findByRole("button", {
        name: messages["lab.submit.button"],
      }),
    );
    expect(await screen.findByText(text)).toBeInTheDocument();
  });

  it("bo'sh kod yuborilmaydi; tarix yuklanmasa ham tugma ishlaydi", async () => {
    const calls = mockApi({});
    render(<SubmitPanel code="M01" getCode={() => "   "} />);
    await userEvent.click(
      await screen.findByRole("button", {
        name: messages["lab.submit.button"],
      }),
    );
    expect(screen.getByText(messages["lab.submit.empty"])).toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });

  it("tushunish savollari: javob yuboriladi, natija ko'rsatiladi (INT-02)", async () => {
    const pending = sub({
      id: 4,
      status: "done",
      score: 100,
      final_score: "100.00",
      understanding: "pending",
      questions: [
        {
          text: "`removed` qanday hisoblanadi?",
          options: ["len(clean)", "len(df) - len(clean)"],
        },
        {
          text: "Indeks nega tiklanadi?",
          options: ["0 dan ketma-ket", "Tezlik"],
        },
      ],
    });
    const calls = mockApi({
      [`GET ${URL}`]: () => ({
        status: 200,
        body: { best_final_score: null, submissions: [] },
      }),
      [`POST ${URL}`]: () => ({ status: 202, body: sub({ id: 4 }) }),
      "POST /api/submissions/4/answers": () => ({
        status: 200,
        body: {
          ...pending,
          understanding: "failed",
          final_score: "50.00",
          questions: undefined,
        },
      }),
    });
    const onGraded = vi.fn();
    render(
      <SubmitPanel code="M01" getCode={() => "x = 1"} onGraded={onGraded} />,
    );
    await userEvent.click(
      await screen.findByRole("button", {
        name: messages["lab.submit.button"],
      }),
    );
    act(() => watcher.update?.(pending));
    const send = await screen.findByRole("button", {
      name: messages["lab.understanding.send"],
    });
    expect(send).toBeDisabled();
    await userEvent.click(screen.getByLabelText("len(df) - len(clean)"));
    await userEvent.click(screen.getByLabelText("Tezlik"));
    expect(send).toBeEnabled();
    await userEvent.click(send);
    expect(
      await screen.findByText(messages["lab.understanding.failed"]),
    ).toBeInTheDocument();
    expect(screen.getByText("Ball: 50.00 / 100")).toBeInTheDocument();
    expect(
      calls.find((c) => c.path === "/api/submissions/4/answers")?.body,
    ).toEqual({
      answers: [1, 1],
    });
    expect(
      screen.queryByRole("button", {
        name: messages["lab.understanding.send"],
      }),
    ).toBeNull();
    expect(onGraded).toHaveBeenCalledTimes(2);
  });

  it("tushunish: to'g'ri javob xabari va yuborishda xato", async () => {
    const pending = sub({
      id: 6,
      status: "done",
      final_score: "90.00",
      understanding: "pending",
      questions: [
        { text: "A?", options: ["x", "y"] },
        { text: "B?", options: ["p", "q"] },
      ],
    });
    let fail = true;
    mockApi({
      [`GET ${URL}`]: () => ({
        status: 200,
        body: { best_final_score: null, submissions: [pending] },
      }),
      "GET /api/submissions/6": () => ({ status: 200, body: pending }),
      "POST /api/submissions/6/answers": () =>
        fail
          ? { status: 500, body: null }
          : { status: 200, body: { ...pending, understanding: "passed" } },
    });
    render(<SubmitPanel code="M01" getCode={() => "x = 1"} />);
    await userEvent.click(await screen.findByLabelText("x"));
    await userEvent.click(screen.getByLabelText("q"));
    await userEvent.click(
      screen.getByRole("button", { name: messages["lab.understanding.send"] }),
    );
    expect(
      await screen.findByText(messages["common.unexpectedError"]),
    ).toBeInTheDocument();
    fail = false;
    await userEvent.click(
      screen.getByRole("button", { name: messages["lab.understanding.send"] }),
    );
    expect(
      await screen.findByText(messages["lab.understanding.passed"]),
    ).toBeInTheDocument();
  });
});
