import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import messages from "../i18n/uz.json";
import { type Point, knnPredict, leastSquares, mse, seeded, trainingAccuracy, twoClasses } from "./math";
import VisualBlock from "./VisualBlock";

afterEach(cleanup);

describe("vizual hisoblar (CNT-03)", () => {
  it("MSE va eng kichik kvadratlar", () => {
    const points: Point[] = [
      [0, 1],
      [1, 3],
      [2, 5],
    ];
    expect(mse(points, 2, 1)).toBe(0);
    expect(mse(points, 0, 0)).toBeCloseTo((1 + 9 + 25) / 3);
    const best = leastSquares(points);
    expect(best.w).toBeCloseTo(2);
    expect(best.b).toBeCloseTo(1);
    expect(leastSquares([[1, 2], [1, 4]])).toEqual({ w: 0, b: 3 });
  });

  it("tasodif takrorlanadi; k=1 o'quv to'plamida 100%, katta k — kamroq yoki teng", () => {
    expect(seeded(1)()).toBe(seeded(1)());
    const train = twoClasses(42);
    expect(train).toHaveLength(40);
    expect(train.every((p) => p.x > 0 && p.x < 1 && p.y > 0 && p.y < 1)).toBe(true);
    expect(trainingAccuracy(train, 1)).toBe(1);
    expect(trainingAccuracy(train, 15)).toBeLessThanOrEqual(1);
    expect(knnPredict(train, 0.05, 0.05, 3)).toBe(0);
    expect(knnPredict(train, 0.95, 0.95, 3)).toBe(1);
  });
});

describe("vidjetlar", () => {
  it("line-fit: slayder MSE'ni o'zgartiradi, eng yaxshi chiziq tugmasi", async () => {
    const user = userEvent.setup();
    render(<VisualBlock source={'{"widget":"line-fit","title":"Chiziq","points":[[0,1],[1,3],[2,5]]}'} />);
    expect(screen.getByText("Chiziq")).toBeInTheDocument();
    const before = screen.getByTestId("mse").textContent;
    fireEvent.change(screen.getByRole("slider", { name: "Qiyalik (w): 0.5" }), { target: { value: "1.5" } });
    expect(screen.getByRole("slider", { name: "Qiyalik (w): 1.5" })).toBeInTheDocument();
    expect(screen.getByTestId("mse").textContent).not.toBe(before);
    await user.click(screen.getByRole("button", { name: messages["visual.lineFit.best"] }));
    expect(screen.getByTestId("mse")).toHaveTextContent("MSE): 0.00");
    expect(screen.getByRole("img", { name: "Nuqtalar va y = 2.0·x + 1.0 chizig'i" })).toBeInTheDocument();
  });

  it("knn: k slayderi aniqlikni yangilaydi", () => {
    render(<VisualBlock source={'{"widget":"knn","seed":42,"k_max":9}'} />);
    expect(screen.getByTestId("knn-accuracy")).toHaveTextContent("100%");
    const slider = screen.getByRole("slider", { name: "Qo'shnilar soni (k): 1" });
    expect(slider).toHaveAttribute("max", "9");
    fireEvent.change(slider, { target: { value: "9" } });
    expect(screen.getByRole("img", { name: /k = 9/ })).toBeInTheDocument();
  });

  it("noma'lum yoki buzuq spetsifikatsiya", () => {
    render(<VisualBlock source="{buzuq" />);
    expect(screen.getByText(messages["visual.unknown"])).toBeInTheDocument();
  });
});
