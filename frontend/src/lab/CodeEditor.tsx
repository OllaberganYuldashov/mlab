import { useEffect, useRef } from "react";

interface Props {
  value: string;
  language: "python" | "markdown";
  label: string;
  onChange: (value: string) => void;
  onRun: () => void;
  onPaste?: (size: number) => boolean;
}

/** CodeMirror'ni dangasa yuklaydigan muharrir. Boshqaruv bir tomonlama: boshlang'ich qiymat, keyin `onChange`. */
export default function CodeEditor({
  value,
  language,
  label,
  onChange,
  onRun,
  onPaste,
}: Props) {
  const host = useRef<HTMLDivElement>(null);
  const latest = useRef({ onChange, onRun, onPaste });
  useEffect(() => {
    latest.current = { onChange, onRun, onPaste };
  }, [onChange, onRun, onPaste]);
  const guarded = onPaste !== undefined;

  useEffect(() => {
    let editor: { destroy(): void } | null = null;
    let cancelled = false;
    void import("./codemirror").then(({ createEditor }) => {
      if (cancelled || !host.current) return;
      editor = createEditor({
        parent: host.current,
        value,
        language,
        label,
        onChange: (v) => latest.current.onChange(v),
        onRun: () => latest.current.onRun(),
        ...(guarded
          ? {
              onPaste: (size: number) => latest.current.onPaste?.(size) ?? true,
            }
          : {}),
      });
    });
    return () => {
      cancelled = true;
      editor?.destroy();
    };
    // Muharrir faqat bir marta yaratiladi; keyingi qiymatlar uning o'zida.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language]);

  return <div ref={host} className="code-editor" />;
}
