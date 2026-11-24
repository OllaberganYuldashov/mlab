import { useMemo, useState } from "react";
import { t } from "../i18n";
import { knnPredict, trainingAccuracy, twoClasses } from "./math";

const SIZE = 260;
const GRID = 24;
const COLORS = ["#3a6ea5", "#d9822b"] as const;
const AREAS = ["#dbe6f2", "#f7e3cf"] as const;

/** CNT-03 `knn`: k slayderi — qaror hududlari qanday o'zgaradi (kichik k — shovqinga sezgir, katta k — silliq). */
export default function Knn({ seed = 42, kMax = 15, title }: { seed?: number; kMax?: number; title?: string }) {
  const [k, setK] = useState(1);
  const train = useMemo(() => twoClasses(seed), [seed]);
  const cells = useMemo(() => {
    const out: { x: number; y: number; label: 0 | 1 }[] = [];
    for (let i = 0; i < GRID; i++)
      for (let j = 0; j < GRID; j++) {
        const x = (i + 0.5) / GRID;
        const y = (j + 0.5) / GRID;
        out.push({ x, y, label: knnPredict(train, x, y, k) });
      }
    return out;
  }, [train, k]);
  const accuracy = Math.round(trainingAccuracy(train, k) * 100);
  const cell = SIZE / GRID;
  return (
    <figure className="visual">
      {title && <figcaption>{title}</figcaption>}
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label={t("visual.knn.alt", { k })}>
        {cells.map((c, i) => (
          <rect
            key={i}
            x={c.x * SIZE - cell / 2}
            y={SIZE - c.y * SIZE - cell / 2}
            width={cell}
            height={cell}
            fill={AREAS[c.label]}
          />
        ))}
        {train.map((p, i) => (
          <circle key={i} cx={p.x * SIZE} cy={SIZE - p.y * SIZE} r={4} fill={COLORS[p.label]} stroke="#fff" />
        ))}
      </svg>
      <label className="slider">
        {t("visual.knn.k", { k })}
        <input type="range" min={1} max={kMax} step={1} value={k} onChange={(e) => setK(Number(e.target.value))} />
      </label>
      <p aria-live="polite" data-testid="knn-accuracy">
        {t("visual.knn.accuracy", { value: accuracy })}
      </p>
    </figure>
  );
}
