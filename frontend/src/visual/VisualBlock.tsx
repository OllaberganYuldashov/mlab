import { t } from "../i18n";
import Knn from "./Knn";
import LineFit from "./LineFit";
import type { Point } from "./math";

interface Spec {
  widget: string;
  title?: string;
  points?: Point[];
  seed?: number;
  k_max?: number;
}

function parse(source: string): Spec | null {
  try {
    return JSON.parse(source) as Spec;
  } catch {
    return null;
  }
}

/** CNT-03: ```visual bloki (backend importda tekshirib JSON qilgan) → mos vidjet. */
export default function VisualBlock({ source }: { source: string }) {
  const spec = parse(source);
  if (spec?.widget === "line-fit") return <LineFit points={spec.points} title={spec.title} />;
  if (spec?.widget === "knn") return <Knn seed={spec.seed} kMax={spec.k_max} title={spec.title} />;
  return <p className="muted">{t("visual.unknown")}</p>;
}
