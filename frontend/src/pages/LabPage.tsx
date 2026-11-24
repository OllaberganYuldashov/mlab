import { useState } from "react";
import { t } from "../i18n";
import Notebook from "../lab/Notebook";
import { emptyNotebook } from "../lab/notebook";
import { Link } from "../Link";

/** LAB-01: laboratoriya sahifasi (notebook). Topshiriq paneli va saqlash — I2-17, I2-18. */
export default function LabPage({ code }: { code: string }) {
  const [initial] = useState(emptyNotebook);
  return (
    <main className="app lab">
      <p className="links">
        <Link to={`/topics/${code}`}>{t("quiz.backToLecture")}</Link>
      </p>
      <h1>{t("lab.title.page", { code })}</h1>
      <Notebook initial={initial} />
    </main>
  );
}
