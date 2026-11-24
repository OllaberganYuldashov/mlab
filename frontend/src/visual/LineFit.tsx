import { useState } from "react";
import { t } from "../i18n";
import { type Point, leastSquares, mse } from "./math";

const DEFAULT_POINTS: Point[] = [
  [1, 1.8],
  [2, 3.1],
  [3, 3.9],
  [4, 5.2],
  [5, 5.8],
  [6, 7.1],
];
const W = 320;
const H = 220;
const PAD = 28;

/** CNT-03 `line-fit`: qiyalik (w) va siljish (b) slayderlari, chiziq va o'rtacha kvadrat xato (MSE). */
export default function LineFit({ points = DEFAULT_POINTS, title }: { points?: Point[]; title?: string }) {
  const [w, setW] = useState(0.5);
  const [b, setB] = useState(0);
  const xs = points.map((p) => p[0]);
  const ys = points.map((p) => p[1]);
  const [x0, x1] = [Math.min(...xs, 0), Math.max(...xs) * 1.1];
  const [y0, y1] = [Math.min(...ys, 0), Math.max(...ys) * 1.15];
  const sx = (x: number) => PAD + ((x - x0) / (x1 - x0)) * (W - 2 * PAD);
  const sy = (y: number) => H - PAD - ((y - y0) / (y1 - y0)) * (H - 2 * PAD);
  const error = mse(points, w, b);
  return (
    <figure className="visual">
      {title && <figcaption>{title}</figcaption>}
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t("visual.lineFit.alt", { w: w.toFixed(1), b: b.toFixed(1) })}>
        <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="#8a94a3" />
        <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="#8a94a3" />
        {points.map(([x, y], i) => (
          <g key={i}>
            <line x1={sx(x)} y1={sy(y)} x2={sx(x)} y2={sy(w * x + b)} stroke="#d9822b" strokeDasharray="3 2" />
            <circle cx={sx(x)} cy={sy(y)} r={4} fill="#3a6ea5" />
          </g>
        ))}
        <line x1={sx(x0)} y1={sy(w * x0 + b)} x2={sx(x1)} y2={sy(w * x1 + b)} stroke="#1d6b35" strokeWidth={2} />
      </svg>
      <label className="slider">
        {t("visual.lineFit.w", { value: w.toFixed(1) })}
        <input type="range" min={-1} max={3} step={0.1} value={w} onChange={(e) => setW(Number(e.target.value))} />
      </label>
      <label className="slider">
        {t("visual.lineFit.b", { value: b.toFixed(1) })}
        <input type="range" min={-3} max={3} step={0.1} value={b} onChange={(e) => setB(Number(e.target.value))} />
      </label>
      <p aria-live="polite" data-testid="mse">
        {t("visual.lineFit.mse", { value: error.toFixed(2) })}
      </p>
      <button
        type="button"
        onClick={() => {
          const best = leastSquares(points);
          setW(Math.round(best.w * 10) / 10);
          setB(Math.round(best.b * 10) / 10);
        }}
      >
        {t("visual.lineFit.best")}
      </button>
    </figure>
  );
}
