import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { t } from "../i18n";
import { formatLeft } from "../time";

interface Membership {
  status: "pending" | "approved" | "rejected" | "removed";
  section: string;
  instructor: string;
}

interface WindowRow {
  topic: { code: string; title: string };
  state: { opens_at: string | null; closes_at: string | null };
}

interface NextWindow {
  server_time: string;
  open: WindowRow[];
  next: WindowRow | null;
}

/** ACC-05: a'zolik holati va laboratoriya vaqti. Soat farqi server vaqti bilan tuzatiladi. */
export default function StudentHome() {
  const [membership, setMembership] = useState<Membership | null | undefined>(
    undefined,
  );
  const [windows, setWindows] = useState<NextWindow | null>(null);
  const [offset, setOffset] = useState(0); // server - mijoz (ms)
  const [now, setNow] = useState(() => Date.now());
  const socket = useRef<WebSocket | null>(null);

  const loadWindows = useCallback(async () => {
    const result = await api<NextWindow>("/api/me/next-window");
    if (result.ok) {
      setWindows(result.data);
      setOffset(new Date(result.data.server_time).getTime() - Date.now());
    }
  }, []);

  useEffect(() => {
    let active = true;
    void (async () => {
      const result = await api<{ membership: Membership | null }>(
        "/api/me/membership",
      );
      if (!active) return;
      setMembership(result.ok ? result.data.membership : null);
      if (result.ok && result.data.membership?.status === "approved")
        await loadWindows();
    })();
    return () => {
      active = false;
    };
  }, [loadWindows]);

  // Real vaqt: oyna o'zgarsa qayta so'raymiz; ulanish uzilsa (15 daqiqa umr) qayta ulanadi.
  useEffect(() => {
    if (membership?.status !== "approved" || typeof WebSocket === "undefined")
      return;
    let stopped = false;
    let retry = 1000;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const connect = () => {
      const scheme = window.location.protocol === "https:" ? "wss" : "ws";
      const ws = new WebSocket(
        `${scheme}://${window.location.host}/ws/student`,
      );
      socket.current = ws;
      ws.onopen = () => {
        retry = 1000;
      };
      ws.onmessage = () => {
        void loadWindows();
      };
      ws.onclose = () => {
        if (stopped) return;
        timer = setTimeout(connect, retry);
        retry = Math.min(retry * 2, 30000);
      };
    };
    connect();
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
      socket.current?.close();
    };
  }, [membership, loadWindows]);

  // Har soniya: qolgan vaqtni yangilash; rejalashtirilgan ochilish lahzasi kelsa holatni qayta so'rash
  // (server push — I3). Bir lahza uchun bir marta.
  const opensAtRef = useRef<number | null>(null);
  const offsetRef = useRef(0);
  const refetchedFor = useRef<number | null>(null);
  useEffect(() => {
    const id = setInterval(() => {
      const current = Date.now();
      setNow(current);
      const opensAt = opensAtRef.current;
      if (
        opensAt !== null &&
        current + offsetRef.current >= opensAt &&
        refetchedFor.current !== opensAt
      ) {
        refetchedFor.current = opensAt;
        void loadWindows();
      }
    }, 1000);
    return () => clearInterval(id);
  }, [loadWindows]);

  const serverNow = now + offset;
  const next = windows?.next;
  const opensAt = next?.state.opens_at
    ? new Date(next.state.opens_at).getTime()
    : null;
  const opensIn = opensAt !== null ? opensAt - serverNow : null;
  useEffect(() => {
    opensAtRef.current = opensAt;
    offsetRef.current = offset;
  }, [opensAt, offset]);

  if (membership === undefined)
    return <p role="status">{t("common.loading")}</p>;
  return (
    <section aria-labelledby="my-group">
      <h2 id="my-group">{t("membership.title")}</h2>
      {membership === null ? (
        <p>{t("membership.none")}</p>
      ) : (
        <p>
          {t(`membership.${membership.status}`, {
            section: membership.section,
            instructor: membership.instructor,
          })}
        </p>
      )}
      {membership?.status === "approved" && windows && (
        <div aria-live="polite">
          <h3>{t("lab.title")}</h3>
          {windows.open.map((w) => (
            <p key={w.topic.code}>
              {t("lab.open", { topic: `${w.topic.code} ${w.topic.title}` })}
              {w.state.closes_at &&
                ` — ${t("lab.closesIn", { time: formatLeft(new Date(w.state.closes_at).getTime() - serverNow) })}`}
            </p>
          ))}
          {next && opensIn !== null && opensIn > 0 && (
            <p>
              {t("lab.next", {
                topic: `${next.topic.code} ${next.topic.title}`,
                time: formatLeft(opensIn),
              })}
            </p>
          )}
          {windows.open.length === 0 && !next && <p>{t("lab.none")}</p>}
        </div>
      )}
    </section>
  );
}
