import { useCallback, useEffect, useState } from "react";
import { api, type Me } from "./api";
import { t } from "./i18n";
import ChangePasswordPage from "./pages/ChangePasswordPage";
import LoginPage from "./pages/LoginPage";
import PolicyPage from "./pages/PolicyPage";
import RegisterPage from "./pages/RegisterPage";
import DatasetsPage from "./pages/DatasetsPage";
import JoinPage from "./pages/JoinPage";
import LabPage from "./pages/LabPage";
import LecturePage from "./pages/LecturePage";
import QuizPage from "./pages/QuizPage";
import TopicsPage from "./pages/TopicsPage";
import SectionPage from "./pages/SectionPage";
import StudentHome from "./pages/StudentHome";
import { nextParam } from "./nav";
import SectionsPage from "./pages/SectionsPage";
import { Link } from "./Link";
import { clearLabDrafts } from "./lab/autosave";
import { navigate, usePath } from "./router";
import "./App.css";

function Home({
  me,
  onLogout,
  failed,
}: {
  me: Me | null;
  onLogout: () => void;
  failed: boolean;
}) {
  return (
    <main className="app">
      <h1>{t("app.title")}</h1>
      <p className="tagline">{t("app.tagline")}</p>
      {me ? (
        <>
          <p>{t("app.greeting", { name: me.full_name })}</p>
          {me.role === "student" && <StudentHome />}
          <p className="links">
            <Link to="/topics">{t("nav.topics")}</Link>
            {me.role === "instructor" && <Link to="/sections">{t("nav.sections")}</Link>}
            <Link to="/change-password">{t("password.title")}</Link>
          </p>
          <button type="button" onClick={onLogout}>
            {t("nav.logout")}
          </button>
          {failed && (
            <p role="alert" className="error">
              {t("common.unexpectedError")}
            </p>
          )}
        </>
      ) : (
        <>
          <p className="status">{t("app.status")}</p>
          <p className="links">
            <Link to="/login">{t("nav.login")}</Link>
            <Link to="/register">{t("nav.register")}</Link>
          </p>
        </>
      )}
    </main>
  );
}

export default function App() {
  const path = usePath();
  const [me, setMe] = useState<Me | null>(null);
  const [ready, setReady] = useState(false);
  const [logoutFailed, setLogoutFailed] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const result = await api<Me>("/api/auth/me");
      setMe(result.ok ? result.data : null);
    } catch {
      setMe(null);
    } finally {
      setReady(true);
    }
  }, []);

  useEffect(() => {
    let active = true;
    void (async () => {
      let user: Me | null = null;
      try {
        const result = await api<Me>("/api/auth/me");
        if (result.ok) user = result.data;
      } catch {
        user = null;
      }
      if (active) {
        setMe(user);
        setReady(true);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  // Vaqtinchalik parol bilan kirgan foydalanuvchi parolni almashtirmaguncha boshqa sahifaga o'tmaydi (AUTH-04).
  useEffect(() => {
    if (ready && me?.must_change_password && path !== "/change-password") {
      navigate("/change-password", true);
    }
  }, [ready, me, path]);

  useEffect(() => {
    if (ready && !me && path === "/change-password") navigate("/login", true);
  }, [ready, me, path]);

  async function logout() {
    try {
      const result = await api("/api/auth/logout", { method: "POST" });
      if (!result.ok) {
        setLogoutFailed(true);
        return;
      }
    } catch {
      setLogoutFailed(true);
      return;
    }
    setLogoutFailed(false);
    clearLabDrafts();
    setMe(null);
    navigate("/login");
  }

  if (!ready) {
    return (
      <main className="app">
        <p role="status">{t("common.loading")}</p>
      </main>
    );
  }

  const forcedPath = me?.must_change_password ? "/change-password" : path;
  const joinMatch = /^\/join\/([A-Za-z0-9_-]{1,64})$/.exec(forcedPath);
  if (joinMatch?.[1]) return <JoinPage token={joinMatch[1]} me={me} />;
  const labMatch = /^\/labs\/([A-Z][0-9]{2})$/.exec(forcedPath);
  if (labMatch?.[1] && me?.role === "student") return <LabPage code={labMatch[1]} />;
  const quizMatch = /^\/topics\/([A-Z][0-9]{2})\/quiz$/.exec(forcedPath);
  if (quizMatch?.[1] && me?.role === "student") return <QuizPage code={quizMatch[1]} />;
  const topicMatch = /^\/topics\/([A-Z][0-9]{2})$/.exec(forcedPath);
  if (topicMatch?.[1] && me) return <LecturePage code={topicMatch[1]} />;
  const sectionMatch = /^\/sections\/(\d+)$/.exec(forcedPath);
  if (sectionMatch && me?.role === "instructor") {
    return <SectionPage sectionId={Number(sectionMatch[1])} />;
  }
  switch (forcedPath) {
    case "/":
      return <Home me={me} onLogout={logout} failed={logoutFailed} />;
    case "/login":
      return (
        <>
          {new URLSearchParams(window.location.search).has("registered") && (
            <p role="status" className="app">
              {t("register.success")}
            </p>
          )}
          <LoginPage
            onLogin={(user) => {
              clearLabDrafts();
              setMe(user);
              navigate(user.must_change_password ? "/change-password" : (nextParam() ?? "/"));
            }}
          />
        </>
      );
    case "/policy":
      return <PolicyPage />;
    case "/register":
      return <RegisterPage />;
    case "/change-password":
      if (!me) return null;
      return (
        <ChangePasswordPage
          forced={me.must_change_password}
          onChanged={() => {
            void refresh().then(() => navigate("/"));
          }}
        />
      );
    case "/datasets":
      if (me) return <DatasetsPage />;
      return <NotFound />;
    case "/topics":
      if (me) return <TopicsPage />;
      return <NotFound />;
    case "/sections":
      if (me?.role === "instructor") return <SectionsPage />;
      return <NotFound />;
    default:
      return <NotFound />;
  }
}

function NotFound() {
  return (
    <main className="app">
      <h1>{t("notFound.title")}</h1>
      <p>
        <Link to="/">{t("notFound.back")}</Link>
      </p>
    </main>
  );
}
