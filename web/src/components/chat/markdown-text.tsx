"use client";

import "./markdown-styles.css";

import ReactMarkdown, { Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";
import { FC, memo, useState } from "react";
import { CheckIcon, CopyIcon, ChevronDownIcon, ChevronRightIcon, BrainIcon } from "lucide-react";
import { SyntaxHighlighter } from "@/components/chat/syntax-highlighter";

import { TooltipIconButton } from "@/components/chat/tooltip-icon-button";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";

import "katex/dist/katex.min.css";

/**
 * 思考内容块组件
 * 用于渲染 <think></think> 标签中的内容
 */
interface ThinkingBlockProps {
  content: string;
  defaultExpanded?: boolean;
}

const ThinkingBlock: FC<ThinkingBlockProps> = ({ content, defaultExpanded = false }) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className="my-3 rounded-lg border border-purple-200 bg-purple-50 dark:border-purple-800 dark:bg-purple-950/30">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-medium text-purple-700 dark:text-purple-300 hover:bg-purple-100 dark:hover:bg-purple-900/30 rounded-t-lg transition-colors"
      >
        {isExpanded ? (
          <ChevronDownIcon className="h-4 w-4" />
        ) : (
          <ChevronRightIcon className="h-4 w-4" />
        )}
        <BrainIcon className="h-4 w-4" />
        <span>思考过程</span>
        {!isExpanded && (
          <span className="text-xs text-purple-500 dark:text-purple-400 ml-2">
            (点击展开)
          </span>
        )}
      </button>
      {isExpanded && (
        <div className="px-4 pb-3 text-sm text-purple-800 dark:text-purple-200 border-t border-purple-200 dark:border-purple-800">
          <div className="pt-3 whitespace-pre-wrap leading-relaxed">
            {content}
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * 解析内容中的 <think></think> 标签
 * 返回包含普通文本和思考内容的混合数组
 */
interface ParsedPart {
  type: "text" | "thinking";
  content: string;
}

function parseThinkTags(text: string): ParsedPart[] {
  const parts: ParsedPart[] = [];
  // 简单状态机处理，支持流式输出中未闭合的标签
  const START_TAG = "<think>";
  const END_TAG = "</think>";

  let currentIndex = 0;

  while (currentIndex < text.length) {
    // 查找下一个开始标签
    const startIndex = text.indexOf(START_TAG, currentIndex);

    if (startIndex === -1) {
      // 没有更多思考标签，剩余全是文本
      const remainingText = text.slice(currentIndex);
      if (remainingText) {
        parts.push({ type: "text", content: remainingText });
      }
      break;
    }

    // 添加开始标签前的文本
    if (startIndex > currentIndex) {
      parts.push({ type: "text", content: text.slice(currentIndex, startIndex) });
    }

    // 查找对应的结束标签（从开始标签之后找）
    const contentStartIndex = startIndex + START_TAG.length;
    const endIndex = text.indexOf(END_TAG, contentStartIndex);

    if (endIndex === -1) {
      // 标签未闭合（流式传输中），剩余部分全是思考内容
      const thinkingContent = text.slice(contentStartIndex);
      parts.push({ type: "thinking", content: thinkingContent });
      break;
    } else {
      // 标签已闭合
      const thinkingContent = text.slice(contentStartIndex, endIndex);
      parts.push({ type: "thinking", content: thinkingContent });
      currentIndex = endIndex + END_TAG.length;
    }
  }

  if (parts.length === 0) {
    parts.push({ type: "text", content: text });
  }

  return parts;
}

/**
 * 修复 Markdown 表格格式
 * 当 AI 返回的表格缺少必要的换行符时，自动修复
 * 
 * 问题示例：
 * "| 日期 | 星期 ||------|------|| 数据 | 数据 |"
 * 应该变成：
 * "| 日期 | 星期 |\n|------|------|\n| 数据 | 数据 |"
 */
function fixMarkdownTable(text: string): string {
  // 核心修复：在 "| |" 或 "|  |" 模式处添加换行
  // 这种模式表示一行结束后紧接着下一行开始
  // 匹配：结尾的 | 后面紧跟（可能有空格）另一个 | 开头的新行

  // 步骤 1: 修复 "||" -> "|\n|" 的情况（两个管道符号直接相连）
  let fixed = text.replace(/\|\|/g, '|\n|');

  // 步骤 2: 修复 "| |" -> "|\n|" 的情况（两个管道符号之间有空格但应该是换行）
  // 但要小心不要误伤正常的空单元格，所以只在特定情况下处理
  // 例如 "级 | | 日期" 这种情况（行尾 | 后面有空格再 | 再有实际内容）
  // 使用回溯检测：如果 | 后面紧跟另一个完整的表格行模式
  fixed = fixed.replace(/\| \|(?=\s*[^\n|]+\s*\|)/g, '|\n|');

  return fixed;
}

interface CodeHeaderProps {
  language?: string;
  code: string;
}

const useCopyToClipboard = ({
  copiedDuration = 3000,
}: {
  copiedDuration?: number;
} = {}) => {
  const [isCopied, setIsCopied] = useState<boolean>(false);

  const copyToClipboard = (value: string) => {
    if (!value) return;

    navigator.clipboard.writeText(value).then(() => {
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), copiedDuration);
    });
  };

  return { isCopied, copyToClipboard };
};

const CodeHeader: FC<CodeHeaderProps> = ({ language, code }) => {
  const { isCopied, copyToClipboard } = useCopyToClipboard();
  const onCopy = () => {
    if (!code || isCopied) return;
    copyToClipboard(code);
  };

  return (
    <div className="flex items-center justify-between gap-4 rounded-t-lg bg-zinc-900 px-4 py-2 text-sm font-semibold text-white">
      <span className="lowercase [&>span]:text-xs">{language}</span>
      <TooltipIconButton
        tooltip="Copy"
        onClick={onCopy}
      >
        {!isCopied && <CopyIcon />}
        {isCopied && <CheckIcon />}
      </TooltipIconButton>
    </div>
  );
};

/**
 * 图片组件：缩略图 + 点击放大（Lightbox）
 * 与 MultimodalPreview 保持一致的交互体验
 */
interface ImageWithLightboxProps {
  src?: string;
  alt?: string;
  className?: string;
}

const ImageWithLightbox: FC<ImageWithLightboxProps> = ({ src, alt, className }) => {
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const imageName = alt || "图片";

  if (!src) return null;

  return (
    <>
      {/* 缩略图 */}
      <img
        src={src}
        alt={imageName}
        className={cn(
          "max-w-xs max-h-48 rounded-lg my-2 cursor-pointer hover:opacity-90 transition-opacity shadow-sm border",
          className
        )}
        loading="lazy"
        onClick={() => setLightboxOpen(true)}
      />

      {/* 点击放大弹窗 */}
      <Dialog open={lightboxOpen} onOpenChange={setLightboxOpen}>
        <DialogContent className="max-w-[90vw] max-h-[90vh] p-2 bg-black/90 border-none">
          <DialogTitle className="sr-only">{imageName}</DialogTitle>
          <div className="flex items-center justify-center">
            <img
              src={src}
              alt={imageName}
              className="max-w-full max-h-[85vh] object-contain rounded-lg"
            />
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

const defaultComponents: Partial<Components> = {
  h1: ({ className, ...props }: { className?: string }) => (
    <h1
      className={cn(
        "mb-8 scroll-m-20 text-4xl font-extrabold tracking-tight last:mb-0",
        className,
      )}
      {...props}
    />
  ),
  h2: ({ className, ...props }: { className?: string }) => (
    <h2
      className={cn(
        "mt-8 mb-4 scroll-m-20 text-3xl font-semibold tracking-tight first:mt-0 last:mb-0",
        className,
      )}
      {...props}
    />
  ),
  h3: ({ className, ...props }: { className?: string }) => (
    <h3
      className={cn(
        "mt-6 mb-4 scroll-m-20 text-2xl font-semibold tracking-tight first:mt-0 last:mb-0",
        className,
      )}
      {...props}
    />
  ),
  h4: ({ className, ...props }: { className?: string }) => (
    <h4
      className={cn(
        "mt-6 mb-4 scroll-m-20 text-xl font-semibold tracking-tight first:mt-0 last:mb-0",
        className,
      )}
      {...props}
    />
  ),
  h5: ({ className, ...props }: { className?: string }) => (
    <h5
      className={cn(
        "my-4 text-lg font-semibold first:mt-0 last:mb-0",
        className,
      )}
      {...props}
    />
  ),
  h6: ({ className, ...props }: { className?: string }) => (
    <h6
      className={cn("my-4 font-semibold first:mt-0 last:mb-0", className)}
      {...props}
    />
  ),
  p: ({ className, ...props }: { className?: string }) => (
    <p
      className={cn("mt-5 mb-5 leading-7 first:mt-0 last:mb-0", className)}
      {...props}
    />
  ),
  a: ({ className, ...props }: { className?: string }) => (
    <a
      className={cn(
        "text-primary font-medium underline underline-offset-4",
        className,
      )}
      {...props}
    />
  ),
  blockquote: ({ className, ...props }: { className?: string }) => (
    <blockquote
      className={cn("border-l-2 pl-6 italic", className)}
      {...props}
    />
  ),
  ul: ({ className, ...props }: { className?: string }) => (
    <ul
      className={cn("my-5 ml-6 list-disc [&>li]:mt-2", className)}
      {...props}
    />
  ),
  ol: ({ className, ...props }: { className?: string }) => (
    <ol
      className={cn("my-5 ml-6 list-decimal [&>li]:mt-2", className)}
      {...props}
    />
  ),
  hr: ({ className, ...props }: { className?: string }) => (
    <hr
      className={cn("my-5 border-b", className)}
      {...props}
    />
  ),
  table: ({ className, ...props }: { className?: string }) => (
    <table
      className={cn(
        "my-5 w-full border-separate border-spacing-0 overflow-y-auto",
        className,
      )}
      {...props}
    />
  ),
  th: ({ className, ...props }: { className?: string }) => (
    <th
      className={cn(
        "bg-muted px-4 py-2 text-left font-bold first:rounded-tl-lg last:rounded-tr-lg [&[align=center]]:text-center [&[align=right]]:text-right",
        className,
      )}
      {...props}
    />
  ),
  td: ({ className, ...props }: { className?: string }) => (
    <td
      className={cn(
        "border-b border-l px-4 py-2 text-left last:border-r [&[align=center]]:text-center [&[align=right]]:text-right",
        className,
      )}
      {...props}
    />
  ),
  tr: ({ className, ...props }: { className?: string }) => (
    <tr
      className={cn(
        "m-0 border-b p-0 first:border-t [&:last-child>td:first-child]:rounded-bl-lg [&:last-child>td:last-child]:rounded-br-lg",
        className,
      )}
      {...props}
    />
  ),
  img: ({ src, alt, className, ...props }: { src?: string | Blob; alt?: string; className?: string }) => {
    // 修复 MinIO 预签名 URL 被重复编码的问题
    const fixMinioUrl = (url: string | undefined | Blob) => {
      if (typeof url !== 'string') return url;
      if (!url) return undefined;

      // 检查是否是被重复编码的 MinIO URL
      if (url.includes('%3F') && url.includes('X-Amz-Algorithm')) {
        try {
          let fixed = url.replace('%3F', '?');
          fixed = fixed.replace(/%26/g, '&');
          fixed = fixed.replace(/%3D/g, '=');
          return fixed;
        } catch (e) {
          console.error('Error fixing MinIO URL:', e);
          return url;
        }
      }
      return url;
    };

    const finalSrc = fixMinioUrl(src);
    const imageSrc = typeof finalSrc === 'string' ? finalSrc : undefined;

    // 使用内联的图片组件，支持点击放大
    return (
      <ImageWithLightbox
        src={imageSrc}
        alt={alt}
        className={className}
        {...props}
      />
    );
  },
  sup: ({ className, ...props }: { className?: string }) => (
    <sup
      className={cn("[&>a]:text-xs [&>a]:no-underline", className)}
      {...props}
    />
  ),
  pre: ({ className, ...props }: { className?: string }) => (
    <pre
      className={cn(
        "max-w-4xl overflow-x-auto rounded-lg bg-black text-white",
        className,
      )}
      {...props}
    />
  ),
  code: ({
    className,
    children,
    ...props
  }: {
    className?: string;
    children?: React.ReactNode;
  }) => {
    const match = /language-(\w+)/.exec(className || "");

    if (match) {
      const language = match[1];
      const code = String(children).replace(/\n$/, "");

      return (
        <>
          <CodeHeader
            language={language}
            code={code}
          />
          <SyntaxHighlighter
            language={language}
            className={className}
          >
            {code}
          </SyntaxHighlighter>
        </>
      );
    }

    return (
      <code
        className={cn("rounded font-semibold", className)}
        {...props}
      >
        {children}
      </code>
    );
  },
};

const MarkdownTextImpl: FC<{ children: string }> = ({ children }) => {
  // 解析 <think></think> 标签
  const parts = parseThinkTags(children);

  return (
    <div className="markdown-content">
      {parts.map((part, index) => {
        if (part.type === "thinking") {
          return <ThinkingBlock key={index} content={part.content} />;
        }
        // 修复 Markdown 表格格式（AI 可能返回缺少换行的表格）
        const fixedContent = fixMarkdownTable(part.content);
        return (
          <ReactMarkdown
            key={index}
            remarkPlugins={[remarkGfm, remarkMath]}
            rehypePlugins={[rehypeKatex]}
            components={defaultComponents}
          >
            {fixedContent}
          </ReactMarkdown>
        );
      })}
    </div>
  );
};

export const MarkdownText = memo(MarkdownTextImpl);
