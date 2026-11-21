import { describe, expect, it } from "vitest";
import messages from "./uz.json";
import { t } from "./index";

describe("NFR-14: o'zbekcha tarjima fayli", () => {
  it("har kalitning qiymati bo'sh bo'lmagan matn", () => {
    for (const [key, value] of Object.entries(messages)) {
      expect(typeof value, key).toBe("string");
      expect(value.trim(), key).not.toBe("");
    }
  });

  it("t() kalit bo'yicha matnni qaytaradi", () => {
    expect(t("app.title")).toBe(messages["app.title"]);
  });

  it("t() {nom} o'rinbosarlarini qiymat bilan almashtiradi", () => {
    expect(t("app.greeting", { name: "Oʻgʻiloy" })).toBe("Salom, Oʻgʻiloy!");
  });

  it("berilmagan o'rinbosar o'zgarishsiz qoladi", () => {
    expect(t("app.greeting")).toBe("Salom, {name}!");
  });

  it("noma'lum kalit xato beradi (jimgina kalit chiqmaydi)", () => {
    // @ts-expect-error — TypeScript noma'lum kalitni kompilyatsiyada ham rad etadi
    expect(() => t("yoq.kalit")).toThrow(/yoq\.kalit/);
  });
});
