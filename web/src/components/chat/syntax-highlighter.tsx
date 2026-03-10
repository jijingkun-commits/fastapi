import { PrismAsyncLight as SyntaxHighlighterPrism } from "react-syntax-highlighter";
import tsx from "react-syntax-highlighter/dist/esm/languages/prism/tsx";
import python from "react-syntax-highlighter/dist/esm/languages/prism/python";
import sql from "react-syntax-highlighter/dist/esm/languages/prism/sql";
import { oneLight } from "react-syntax-highlighter/dist/cjs/styles/prism";
import { FC } from "react";

// Register languages you want to support
SyntaxHighlighterPrism.registerLanguage("js", tsx);
SyntaxHighlighterPrism.registerLanguage("jsx", tsx);
SyntaxHighlighterPrism.registerLanguage("ts", tsx);
SyntaxHighlighterPrism.registerLanguage("tsx", tsx);
SyntaxHighlighterPrism.registerLanguage("python", python);
SyntaxHighlighterPrism.registerLanguage("sql", sql);

interface SyntaxHighlighterProps {
  children: string;
  language: string;
  className?: string;
  wrapLongLines?: boolean;
}

export const SyntaxHighlighter: FC<SyntaxHighlighterProps> = ({
  children,
  language,
  className,
  wrapLongLines = false,
}) => {
  return (
    <SyntaxHighlighterPrism
      language={language}
      style={oneLight}
      PreTag="div"
      CodeTag="code"
      wrapLongLines={wrapLongLines}
      customStyle={{
        margin: 0,
        width: "100%",
        background: "transparent",
        padding: "1rem 1rem 1.1rem",
        fontSize: "0.92rem",
        lineHeight: "1.72",
        whiteSpace: wrapLongLines ? "pre-wrap" : "pre",
        overflowWrap: wrapLongLines ? "anywhere" : "normal",
        wordBreak: wrapLongLines ? "break-word" : "normal",
      }}
      className={className}
    >
      {children}
    </SyntaxHighlighterPrism>
  );
};
