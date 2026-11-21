import { t } from "./i18n";
import "./App.css";

export default function App() {
  return (
    <main className="app">
      <h1>{t("app.title")}</h1>
      <p className="tagline">{t("app.tagline")}</p>
      <p className="status">{t("app.status")}</p>
    </main>
  );
}
