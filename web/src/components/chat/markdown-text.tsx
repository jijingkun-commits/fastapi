"use client";

import "./markdown-styles.css";

import Image from "next/image";
import ReactMarkdown, { Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";
import { FC, memo, useState } from "react";
import { ChevronDownIcon, ChevronRightIcon, BrainIcon } from "lucide-react";
import { CodeBlock } from "@/components/chat/code-block";

import { cn } from "@/lib/utils";
import { ImageLightbox } from "@/components/ui/image-viewer";

import "katex/dist/katex.min.css";

/**
 * 思考内容块组件
 * 用于渲染 <think></think> 标签中的内容
 */
interface ThinkingBlockProps {
  content: string;
  defaultExpanded?: boolean;
}

const ThinkingBlock: FC<ThinkingBlockProps> = ({
  content,
  defaultExpanded = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className="my-3 rounded-lg border border-purple-200 bg-purple-50 dark:border-purple-800 dark:bg-purple-950/30">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center gap-2 rounded-t-lg px-3 py-2 text-left text-sm font-medium text-purple-700 transition-colors hover:bg-purple-100 dark:text-purple-300 dark:hover:bg-purple-900/30"
      >
        {isExpanded ? (
          <ChevronDownIcon className="h-4 w-4" />
        ) : (
          <ChevronRightIcon className="h-4 w-4" />
        )}
        <BrainIcon className="h-4 w-4" />
        <span>思考过程</span>
        {!isExpanded && (
          <span className="ml-2 text-xs text-purple-500 dark:text-purple-400">
            (点击展开)
          </span>
        )}
      </button>
      {isExpanded && (
        <div className="border-t border-purple-200 px-4 pb-3 text-sm text-purple-800 dark:border-purple-800 dark:text-purple-200">
          <div className="pt-3 leading-relaxed whitespace-pre-wrap">
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
      parts.push({
        type: "text",
        content: text.slice(currentIndex, startIndex),
      });
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
  let fixed = text.replace(/\|\|/g, "|\n|");

  // 步骤 2: 修复 "| |" -> "|\n|" 的情况（两个管道符号之间有空格但应该是换行）
  // 但要小心不要误伤正常的空单元格，所以只在特定情况下处理
  // 例如 "级 | | 日期" 这种情况（行尾 | 后面有空格再 | 再有实际内容）
  // 使用回溯检测：如果 | 后面紧跟另一个完整的表格行模式
  fixed = fixed.replace(/\| \|(?=\s*[^\n|]+\s*\|)/g, "|\n|");

  return fixed;
}

/**
 * 图片组件：缩略图 + 点击放大（Lightbox）
 * 与 MultimodalPreview 保持一致的交互体验
 */
interface ImageWithLightboxProps {
  src?: string;
  alt?: string;
  className?: string;
}

const ImageWithLightbox: FC<ImageWithLightboxProps> = ({
  src,
  alt,
  className,
}) => {
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const imageName = alt || "图片";

  if (!src) return null;

  return (
    <>
      {/* 缩略图 */}
      <Image
        src={src}
        alt={imageName}
        width={480}
        height={320}
        unoptimized
        className={cn(
          "my-2 max-h-48 max-w-xs cursor-pointer rounded-lg border shadow-sm transition-opacity hover:opacity-90",
          loadError && "hidden",
          className,
        )}
        loading="lazy"
        onClick={() => setLightboxOpen(true)}
        onError={() => setLoadError(true)}
      />
      {loadError && (
        <span className="text-xs text-gray-400">[图片加载失败]</span>
      )}

      <ImageLightbox
        open={lightboxOpen}
        onOpenChange={setLightboxOpen}
        src={src}
        alt={imageName}
      />
    </>
  );
};

const defaultComponents: Partial<Components> = {
  h1: ({ className, ...props }: { className?: string }) => (
    <h1
      className={className}
      {...props}
    />
  ),
  h2: ({ className, ...props }: { className?: string }) => (
    <h2
      className={className}
      {...props}
    />
  ),
  h3: ({ className, ...props }: { className?: string }) => (
    <h3
      className={className}
      {...props}
    />
  ),
  h4: ({ className, ...props }: { className?: string }) => (
    <h4
      className={className}
      {...props}
    />
  ),
  h5: ({ className, ...props }: { className?: string }) => (
    <h5
      className={className}
      {...props}
    />
  ),
  h6: ({ className, ...props }: { className?: string }) => (
    <h6
      className={className}
      {...props}
    />
  ),
  p: ({ className, ...props }: { className?: string }) => (
    <p
      className={className}
      {...props}
    />
  ),
  a: ({ className, ...props }: { className?: string }) => (
    <a
      className={className}
      {...props}
    />
  ),
  blockquote: ({ className, ...props }: { className?: string }) => (
    <blockquote
      className={className}
      {...props}
    />
  ),
  ul: ({ className, ...props }: { className?: string }) => (
    <ul
      className={className}
      {...props}
    />
  ),
  ol: ({ className, ...props }: { className?: string }) => (
    <ol
      className={className}
      {...props}
    />
  ),
  hr: ({ className, ...props }: { className?: string }) => (
    <hr
      className={className}
      {...props}
    />
  ),
  table: ({ className, ...props }: { className?: string }) => (
    <table
      className={className}
      {...props}
    />
  ),
  th: ({ className, ...props }: { className?: string }) => (
    <th
      className={className}
      {...props}
    />
  ),
  td: ({ className, ...props }: { className?: string }) => (
    <td
      className={className}
      {...props}
    />
  ),
  tr: ({ className, ...props }: { className?: string }) => (
    <tr
      className={className}
      {...props}
    />
  ),
  img: ({
    src,
    alt,
    className,
    ...props
  }: {
    src?: string | Blob;
    alt?: string;
    className?: string;
  }) => {
    // 修复 MinIO 预签名 URL 被重复编码的问题
    const fixMinioUrl = (url: string | undefined | Blob) => {
      if (typeof url !== "string") return url;
      if (!url) return undefined;

      // 检查是否是被重复编码的 MinIO URL
      if (url.includes("%3F") && url.includes("X-Amz-Algorithm")) {
        try {
          let fixed = url.replace("%3F", "?");
          fixed = fixed.replace(/%26/g, "&");
          fixed = fixed.replace(/%3D/g, "=");
          return fixed;
        } catch (e) {
          console.error("Error fixing MinIO URL:", e);
          return url;
        }
      }
      return url;
    };

    const finalSrc = fixMinioUrl(src);
    const imageSrc = typeof finalSrc === "string" ? finalSrc : undefined;

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
  pre: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
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
        <CodeBlock
          language={language}
          code={code}
          className="my-[1.3rem] max-w-4xl"
          bodyClassName={className}
        />
      );
    }

    return (
      <code
        className={className}
        {...props}
      >
        {children}
      </code>
    );
  },
};

const MarkdownTextImpl: FC<{ children: string; className?: string }> = ({
  children,
  className,
}) => {
  // 解析 <think></think> 标签
  const parts = parseThinkTags(children);

  return (
    <div className={cn("markdown-content", className)}>
      {parts.map((part, index) => {
        if (part.type === "thinking") {
          return (
            <ThinkingBlock
              key={index}
              content={part.content}
            />
          );
        }
        // 修复 Markdown 表格格式（AI 可能返回缺少换行的表格）
        // 同时移除开头的空白换行（防止后端消息格式问题导致显示异常）
        const fixedContent = fixMarkdownTable(part.content).trimStart();
        // 如果 trim 后为空，跳过渲染
        if (!fixedContent) {
          return null;
        }
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
