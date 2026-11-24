/** Notebook holati (LAB-01) — server `apps/labs/notebook.py` bilan bir xil shakl: faqat kataklar manbasi. */
export type CellType = "code" | "markdown";

export interface Cell {
  id: string;
  type: CellType;
  source: string;
}

export interface Notebook {
  format: 1;
  cells: Cell[];
}

export const MAX_CELLS = 200;

let counter = 0;
export function newCellId(): string {
  counter += 1;
  return `c${Date.now().toString(36)}${counter.toString(36)}`;
}

export function emptyNotebook(): Notebook {
  return { format: 1, cells: [{ id: newCellId(), type: "code", source: "" }] };
}

export function addCell(nb: Notebook, after: number, type: CellType): Notebook {
  if (nb.cells.length >= MAX_CELLS) return nb;
  const cells = [...nb.cells];
  cells.splice(after + 1, 0, { id: newCellId(), type, source: "" });
  return { ...nb, cells };
}

export function removeCell(nb: Notebook, index: number): Notebook {
  if (nb.cells.length <= 1) return nb;
  return { ...nb, cells: nb.cells.filter((_, i) => i !== index) };
}

export function moveCell(nb: Notebook, index: number, delta: -1 | 1): Notebook {
  const target = index + delta;
  if (target < 0 || target >= nb.cells.length) return nb;
  const cells = [...nb.cells];
  const [cell] = cells.splice(index, 1);
  if (cell) cells.splice(target, 0, cell);
  return { ...nb, cells };
}

export function setSource(nb: Notebook, id: string, source: string): Notebook {
  return { ...nb, cells: nb.cells.map((c) => (c.id === id ? { ...c, source } : c)) };
}
