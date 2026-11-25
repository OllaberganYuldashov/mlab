/**
 * "Topshirish" (I3-09; AGR-02, AGR-04, AGR-05, AGR-06): server API va urinish holatini kuzatish.
 * Holat manbai — server (`GET /api/submissions/{id}`). WebSocket `submission.status` xabari faqat "hozir qayta
 * so'ra" signali: xabar yo'qolsa ham (Redis uzilishi, tarmoq) zaxira so'rov holatni baribir yangilaydi.
 */
import { api, type ApiResult } from "../api";

export type SubmissionStatus = "queued" | "running" | "done" | "error";
export type SubmissionPolicy = "on_time" | "late" | "practice";

export interface ResultTest {
  name: string;
  visible: boolean;
  passed: boolean;
  message: string;
}

export interface ResultStep {
  key: string;
  title: string;
  points: number;
  score: number;
  passed: number;
  total: number;
  tests: ResultTest[];
}

export interface Submission {
  id: number;
  status: SubmissionStatus;
  position: number;
  policy: SubmissionPolicy;
  score: number | null;
  final_score: string | null;
  created_at: string;
  finished_at: string | null;
  result?: { code_error: string | null; steps: ResultStep[] } | null;
}

export interface SubmissionList {
  best_final_score: string | null;
  submissions: Submission[];
}

export const isOpen = (s: Pick<Submission, "status">): boolean =>
  s.status === "queued" || s.status === "running";

export function listSubmissions(
  code: string,
): Promise<ApiResult<SubmissionList>> {
  return api<SubmissionList>(`/api/labs/${code}/submissions`);
}

export function submitCode(
  code: string,
  source: string,
): Promise<ApiResult<Submission>> {
  return api<Submission>(`/api/labs/${code}/submissions`, {
    method: "POST",
    body: { code: source },
  });
}

export function getSubmission(id: number): Promise<ApiResult<Submission>> {
  return api<Submission>(`/api/submissions/${id}`);
}

interface SocketLike {
  onmessage: ((event: { data: string }) => void) | null;
  onclose: (() => void) | null;
  close(): void;
}

/** Zaxira so'rov oralig'i: WebSocket xabari kelmasa ham holat shuncha vaqtda yangilanadi. */
export const POLL_MS = 5000;

function defaultSocket(): SocketLike | null {
  if (typeof WebSocket === "undefined") return null;
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  return new WebSocket(
    `${scheme}://${window.location.host}/ws/student`,
  ) as unknown as SocketLike;
}

/**
 * Bitta urinishni tugaguncha kuzatadi: WebSocket xabari yoki har `POLL_MS` da — `GET`. Tugagach (done/error)
 * yoki `stop()` da ulanish va taymer yopiladi. Bir vaqtda bitta so'rov (ketma-ket xabarlar so'rov yog'dirmaydi).
 */
export function watchSubmission(
  id: number,
  onUpdate: (submission: Submission) => void,
  options: {
    fetch?: (id: number) => Promise<ApiResult<Submission>>;
    socket?: () => SocketLike | null;
    pollMs?: number;
  } = {},
): () => void {
  const fetchOne = options.fetch ?? getSubmission;
  const pollMs = options.pollMs ?? POLL_MS;
  let stopped = false;
  let inFlight = false;
  let again = false;
  let socket: SocketLike | null = null;

  const stop = () => {
    if (stopped) return;
    stopped = true;
    clearInterval(timer);
    if (socket) {
      socket.onclose = null;
      socket.close();
    }
  };

  const refresh = async () => {
    if (stopped) return;
    if (inFlight) {
      again = true;
      return;
    }
    inFlight = true;
    try {
      const res = await fetchOne(id);
      if (!stopped && res.ok) {
        onUpdate(res.data);
        if (!isOpen(res.data)) stop();
      }
    } finally {
      inFlight = false;
      if (again && !stopped) {
        again = false;
        void refresh();
      }
    }
  };

  const connect = () => {
    if (stopped) return;
    socket = (options.socket ?? defaultSocket)();
    if (!socket) return;
    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as {
          type?: string;
          id?: number;
        };
        if (message.type === "submission.status" && message.id === id)
          void refresh();
      } catch {
        // Tushunarsiz xabar — e'tiborsiz (holat baribir so'rov bilan yangilanadi).
      }
    };
    // Uzilsa — keyingi zaxira so'rovda qayta ulanamiz (server 15 daqiqada yopadi).
    socket.onclose = () => {
      socket = null;
    };
  };

  const timer = setInterval(() => {
    if (!socket) connect();
    void refresh();
  }, pollMs);
  connect();
  return stop;
}
