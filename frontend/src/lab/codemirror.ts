/** CodeMirror 6 sozlamasi (ADR-0006). Faqat laboratoriya sahifasida dinamik `import()` bilan yuklanadi. */
import { markdown } from "@codemirror/lang-markdown";
import { python } from "@codemirror/lang-python";
import { EditorState, Prec } from "@codemirror/state";
import { EditorView, keymap } from "@codemirror/view";
import { basicSetup } from "codemirror";
import { pasteSize } from "./paste";

export interface EditorOptions {
  parent: HTMLElement;
  value: string;
  language: "python" | "markdown";
  label: string;
  onChange: (value: string) => void;
  onRun: () => void;
  /** INT-01: joylashtirilayotgan matn hajmi; `false` — rad etiladi. Berilmasa cheklov yo'q (ma'ruza). */
  onPaste?: (size: number) => boolean;
}

/** Paste va sudrab tashlash (drop) bir xil tekshiriladi — ikkalasi ham tashqi matn. */
function guard(
  onPaste: (size: number) => boolean,
  event: ClipboardEvent | DragEvent,
): boolean {
  const data =
    "clipboardData" in event ? event.clipboardData : event.dataTransfer;
  const text = data?.getData("text/plain") ?? "";
  if (onPaste(pasteSize(text))) return false; // CodeMirror o'zi joylashtiradi
  event.preventDefault();
  return true;
}

function pasteGuard(onPaste: ((size: number) => boolean) | undefined) {
  if (!onPaste) return [];
  return [
    EditorView.domEventHandlers({
      paste: (event) => guard(onPaste, event),
      drop: (event) => guard(onPaste, event),
    }),
  ];
}

export function createEditor(options: EditorOptions): { destroy(): void } {
  const view = new EditorView({
    parent: options.parent,
    state: EditorState.create({
      doc: options.value,
      extensions: [
        // Shift+Enter — katakni ishga tushirish (Jupyter odati), boshqa tugmalardan oldin.
        Prec.highest(
          keymap.of([
            {
              key: "Shift-Enter",
              run: () => {
                options.onRun();
                return true;
              },
            },
          ]),
        ),
        basicSetup,
        options.language === "python" ? python() : markdown(),
        EditorView.contentAttributes.of({ "aria-label": options.label }),
        ...pasteGuard(options.onPaste),
        EditorView.updateListener.of((update) => {
          if (update.docChanged) options.onChange(update.state.doc.toString());
        }),
      ],
    }),
  });
  return view;
}
