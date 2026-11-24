/** Vizual qadamlar uchun sof hisoblar (CNT-03). Pyodide kerak emas — hammasi TS'da, darhol. */
export type Point = [number, number];

export function mse(points: Point[], w: number, b: number): number {
  return points.reduce((sum, [x, y]) => sum + (w * x + b - y) ** 2, 0) / points.length;
}

/** Eng kichik kvadratlar: y = w x + b. */
export function leastSquares(points: Point[]): { w: number; b: number } {
  const n = points.length;
  const mx = points.reduce((s, [x]) => s + x, 0) / n;
  const my = points.reduce((s, [, y]) => s + y, 0) / n;
  const sxx = points.reduce((s, [x]) => s + (x - mx) ** 2, 0);
  const sxy = points.reduce((s, [x, y]) => s + (x - mx) * (y - my), 0);
  const w = sxx === 0 ? 0 : sxy / sxx;
  return { w, b: my - w * mx };
}

/** Takrorlanadigan tasodif (mulberry32) — har ochilishda bir xil nuqtalar. */
export function seeded(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export interface Labeled {
  x: number;
  y: number;
  label: 0 | 1;
}

/** Ikki sinf: markazlari (0.32, 0.35) va (0.66, 0.62), har biri 20 nuqta, [0, 1] oralig'ida. */
export function twoClasses(seed: number, perClass = 20): Labeled[] {
  const rand = seeded(seed);
  const spread = () => (rand() + rand() + rand() - 1.5) * 0.22;
  const clamp = (v: number) => Math.min(0.98, Math.max(0.02, v));
  const out: Labeled[] = [];
  for (const [label, cx, cy] of [
    [0, 0.32, 0.35],
    [1, 0.66, 0.62],
  ] as const) {
    for (let i = 0; i < perClass; i++) out.push({ x: clamp(cx + spread()), y: clamp(cy + spread()), label });
  }
  return out;
}

/** k-NN: k ta eng yaqin qo'shnining ko'pchiligi; teng bo'lsa — eng yaqinining sinfi. */
export function knnPredict(train: Labeled[], x: number, y: number, k: number): 0 | 1 {
  const nearest = train
    .map((p) => ({ d: (p.x - x) ** 2 + (p.y - y) ** 2, label: p.label }))
    .sort((a, b) => a.d - b.d)
    .slice(0, Math.max(1, Math.min(k, train.length)));
  const ones = nearest.filter((n) => n.label === 1).length;
  const zeros = nearest.length - ones;
  if (ones === zeros) return nearest[0]?.label ?? 0;
  return ones > zeros ? 1 : 0;
}

export function trainingAccuracy(train: Labeled[], k: number): number {
  const right = train.filter((p) => knnPredict(train, p.x, p.y, k) === p.label).length;
  return right / train.length;
}
