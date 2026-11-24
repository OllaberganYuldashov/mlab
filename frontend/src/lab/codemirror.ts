/** CodeMirror 6 sozlamasi (ADR-0006). Faqat laboratoriya sahifasida dinamik `import()` bilan yuklanadi. */
import { markdown } from "@codemirror/lang-markdown";
import { python } from "@codemirror/lang-python";
import { EditorState, Prec } from "@codemirror/state";
import { EditorView, keymap } from "@codemirror/view";
import { basicSetup } from "codemirror";

export interface EditorOptions {
  parent: HTMLElement;
  value: string;
  language: "python" | "markdown";
  label: string;
  onChange: (value: string) => void;
  onRun: () => void;
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
        EditorView.updateListener.of((update) => {
          if (update.docChanged) options.onChange(update.state.doc.toString());
        }),
      ],
    }),
  });
  return view;
}
