/** Ma'ruza Markdown'i komponenti — qoidalar va xavfsizlik `markdown.tsx` da. */
import { Fragment, type ReactNode } from "react";
import { type CodeBlockInfo, parseBlocks, renderInline } from "./markdown";

export function Markdown({
  text,
  renderCode,
}: {
  text: string;
  renderCode?: (info: CodeBlockInfo) => ReactNode;
}) {
  return (
    <>
      {parseBlocks(text).map((block, i) => {
        const key = `b${i}`;
        switch (block.kind) {
          case "heading":
            return block.level === 3 ? (
              <h3 key={key}>{renderInline(block.text, key)}</h3>
            ) : (
              <h4 key={key}>{renderInline(block.text, key)}</h4>
            );
          case "paragraph":
            return <p key={key}>{renderInline(block.text, key)}</p>;
          case "list": {
            const items = block.items.map((item, j) => <li key={j}>{renderInline(item, `${key}-${j}`)}</li>);
            return block.ordered ? <ol key={key}>{items}</ol> : <ul key={key}>{items}</ul>;
          }
          case "code":
            return (
              <Fragment key={key}>
                {renderCode ? (
                  renderCode(block.info)
                ) : (
                  <pre>
                    <code>{block.info.code}</code>
                  </pre>
                )}
              </Fragment>
            );
        }
      })}
    </>
  );
}
