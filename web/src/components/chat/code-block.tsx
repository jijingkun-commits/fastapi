import { CheckIcon, CopyIcon } from "lucide-react";
import { type CSSProperties, type FC, useState } from "react";

import { SyntaxHighlighter } from "@/components/chat/syntax-highlighter";
import { TooltipIconButton } from "@/components/chat/tooltip-icon-button";
import { cn } from "@/lib/utils";

interface CodeBlockProps {
  code: string;
  language?: string;
  label?: string;
  className?: string;
  bodyClassName?: string;
  wrapLongLines?: boolean;
}

function useCopyToClipboard(copiedDuration = 3000) {
  const [isCopied, setIsCopied] = useState(false);

  const copyToClipboard = (value: string) => {
    if (!value) {
      return;
    }

    navigator.clipboard.writeText(value).then(() => {
      setIsCopied(true);
      window.setTimeout(() => setIsCopied(false), copiedDuration);
    });
  };

  return { isCopied, copyToClipboard };
}

const codeBlockRootStyle: CSSProperties = {
  background: "var(--chat-code-block-surface)",
  borderColor: "var(--chat-code-block-border)",
};

const codeBlockHeaderStyle: CSSProperties = {
  background: "var(--chat-code-block-header-surface)",
  borderColor: "var(--chat-code-block-border)",
  color: "var(--chat-code-block-header-foreground)",
};

export const CodeBlock: FC<CodeBlockProps> = ({
  code,
  language,
  label,
  className,
  bodyClassName,
  wrapLongLines = false,
}) => {
  const { isCopied, copyToClipboard } = useCopyToClipboard();
  const displayLabel = (label ?? language ?? "text").toLowerCase();

  return (
    <div
      className={cn(
        "min-w-0 overflow-hidden rounded-[1rem] border shadow-[0_1px_2px_rgb(15_23_42_/_0.04)]",
        className,
      )}
      style={codeBlockRootStyle}
    >
      <div
        className="flex items-center justify-between gap-4 border-b px-4 py-3"
        style={codeBlockHeaderStyle}
      >
        <span className="text-xs font-semibold tracking-[0.06em] lowercase">
          {displayLabel}
        </span>
        <TooltipIconButton
          tooltip="复制"
          onClick={() => {
            if (!code || isCopied) {
              return;
            }
            copyToClipboard(code);
          }}
          className="rounded-md p-1.5 transition-colors hover:bg-black/5 dark:hover:bg-white/5"
          style={{ color: "inherit" }}
        >
          {isCopied ? <CheckIcon /> : <CopyIcon />}
        </TooltipIconButton>
      </div>

      <SyntaxHighlighter
        language={language ?? "text"}
        className={bodyClassName}
        wrapLongLines={wrapLongLines}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
};
