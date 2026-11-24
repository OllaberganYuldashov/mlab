import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import messages from "../i18n/uz.json";
import { mockApi } from "../test-utils";

const STUDENT = { hemis_id: "123456789012", full_name: "Test Talaba", role: "student", direction: 1, must_change_password: false };

beforeEach(() => vi.stubGlobal("WebSocket", undefined));
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("datasetlar (DAT-02)", () => {
  it("manba, litsenziya, ustunlar va mlab.load namunasi", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      "GET /api/datasets": () => ({
        status: 200,
        body: [
          {
            name: "iris",
            title: "Iris gullari",
            description: "150 o'lchov",
            source_url: "https://archive.ics.uci.edu/dataset/53/iris",
            license: "CC-BY-4.0",
            license_url: "https://creativecommons.org/licenses/by/4.0/",
            rows: 150,
            columns: ["sepal_length", "species"],
            size: 3858,
          },
        ],
      }),
    });
    window.history.replaceState(null, "", "/datasets");
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Iris gullari" })).toBeInTheDocument();
    expect(screen.getByText('df = mlab.load("iris")')).toBeInTheDocument();
    expect(screen.getByText(/150 qator, 2 ustun: sepal_length, species/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "CC-BY-4.0" })).toHaveAttribute("href", "https://creativecommons.org/licenses/by/4.0/");
    expect(screen.getByRole("link", { name: "https://archive.ics.uci.edu/dataset/53/iris" })).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("bo'sh va ruxsatsiz", async () => {
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      "GET /api/datasets": () => ({ status: 200, body: [] }),
    });
    window.history.replaceState(null, "", "/datasets");
    render(<App />);
    expect(await screen.findByText(messages["datasets.empty"])).toBeInTheDocument();
    cleanup();
    mockApi({
      "GET /api/auth/me": () => ({ status: 200, body: STUDENT }),
      "GET /api/datasets": () => ({ status: 403, body: {} }),
    });
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent(messages["topics.noAccess"]);
  });
});
