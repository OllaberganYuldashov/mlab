import { describe, expect, it } from "vitest";
import { MAX_CELLS, addCell, emptyNotebook, moveCell, removeCell, setSource } from "./notebook";

describe("notebook amallari (LAB-01)", () => {
  it("qo'shish, ko'chirish, manba, o'chirish", () => {
    let nb = emptyNotebook();
    expect(nb.format).toBe(1);
    nb = addCell(nb, 0, "markdown");
    nb = addCell(nb, 1, "code");
    const [a, b, c] = nb.cells.map((cell) => cell.id);
    expect(nb.cells.map((cell) => cell.type)).toEqual(["code", "markdown", "code"]);
    expect(new Set([a, b, c]).size).toBe(3);
    nb = moveCell(nb, 2, -1);
    expect(nb.cells.map((cell) => cell.id)).toEqual([a, c, b]);
    expect(moveCell(nb, 0, -1)).toBe(nb);
    expect(moveCell(nb, 2, 1)).toBe(nb);
    nb = setSource(nb, c as string, "print(1)");
    expect(nb.cells[1]?.source).toBe("print(1)");
    nb = removeCell(nb, 0);
    expect(nb.cells).toHaveLength(2);
  });

  it("oxirgi katak o'chmaydi, 200 tadan oshmaydi", () => {
    const nb = emptyNotebook();
    expect(removeCell(nb, 0)).toBe(nb);
    let big = nb;
    for (let i = 0; i < MAX_CELLS + 5; i++) big = addCell(big, 0, "code");
    expect(big.cells).toHaveLength(MAX_CELLS);
  });
});
