import React, { useState } from "react";
import { File, X as XIcon } from "lucide-react";
import { ContentBlock } from "@langchain/core/messages";
import { cn } from "@/lib/utils";
import Image from "next/image";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";

export interface MultimodalPreviewProps {
  block: ContentBlock.Multimodal.Data;
  removable?: boolean;
  onRemove?: () => void;
  className?: string;
  size?: "sm" | "md" | "lg";
}

export const MultimodalPreview: React.FC<MultimodalPreviewProps> = ({
  block,
  removable = false,
  onRemove,
  className,
  size = "md",
}) => {
  // 扩展 block 类型以支持 previewUrl
  const extBlock = block as ContentBlock.Multimodal.Data & { previewUrl?: string };

  // 图片放大弹窗状态
  const [lightboxOpen, setLightboxOpen] = useState(false);

  // 判断是否为图片类型（更宽容的检测）
  const isImageBlock =
    block.type === "image" ||
    (typeof block.mimeType === "string" && block.mimeType.startsWith("image/"));

  // Image block
  if (isImageBlock) {
    // 获取 MIME 类型，默认为 image/png
    const mimeType = block.mimeType || "image/png";
    // 优先使用 previewUrl (ObjectURL)，否则回退到 base64
    const url = extBlock.previewUrl || (block.data ? `data:${mimeType};base64,${block.data}` : "");
    let imgClass: string = "rounded-md object-cover h-16 w-16 text-lg cursor-pointer hover:opacity-80 transition-opacity";
    if (size === "sm") imgClass = "rounded-md object-cover h-10 w-10 text-base cursor-pointer hover:opacity-80 transition-opacity";
    if (size === "lg") imgClass = "rounded-md object-cover h-24 w-24 text-xl cursor-pointer hover:opacity-80 transition-opacity";

    const imageName = String(block.metadata?.name || "uploaded image");

    return (
      <>
        <div className={cn("relative inline-block", className)}>
          <Image
            src={url}
            alt={imageName}
            className={imgClass}
            width={size === "sm" ? 40 : size === "md" ? 64 : 96}
            height={size === "sm" ? 40 : size === "md" ? 64 : 96}
            unoptimized // ObjectURL 需要关闭优化
            onClick={() => setLightboxOpen(true)}
          />
          {removable && (
            <button
              type="button"
              className="absolute top-1 right-1 z-10 rounded-full bg-gray-500 text-white hover:bg-gray-700"
              onClick={(e) => {
                e.stopPropagation();
                onRemove?.();
              }}
              aria-label="Remove image"
            >
              <XIcon className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* 图片放大弹窗 */}
        <Dialog open={lightboxOpen} onOpenChange={setLightboxOpen}>
          <DialogContent className="max-w-[90vw] max-h-[90vh] p-2 bg-black/90 border-none">
            <DialogTitle className="sr-only">{imageName}</DialogTitle>
            <div className="flex items-center justify-center">
              <Image
                src={url}
                alt={imageName}
                className="max-w-full max-h-[85vh] object-contain rounded-lg"
                width={1200}
                height={800}
                unoptimized
              />
            </div>
          </DialogContent>
        </Dialog>
      </>
    );
  }

  // PDF block
  if (block.type === "file" && block.mimeType === "application/pdf") {
    const filename =
      block.metadata?.filename || block.metadata?.name || "PDF file";
    return (
      <div
        className={cn(
          "relative flex items-start gap-2 rounded-md border bg-gray-100 px-3 py-2",
          className,
        )}
      >
        <div className="flex flex-shrink-0 flex-col items-start justify-start">
          <File
            className={cn(
              "text-red-600",
              size === "sm" ? "h-5 w-5" : "h-7 w-7",
            )}
          />
        </div>
        <span
          className={cn("min-w-0 flex-1 text-sm break-all text-gray-800")}
          style={{ wordBreak: "break-all", whiteSpace: "pre-wrap" }}
        >
          {String(filename)}
        </span>
        {removable && (
          <button
            type="button"
            className="ml-2 self-start rounded-full bg-gray-200 p-1 text-red-600 hover:bg-gray-300"
            onClick={onRemove}
            aria-label="Remove PDF"
          >
            <XIcon className="h-4 w-4" />
          </button>
        )}
      </div>
    );
  }

  // Excel / CSV / 其他表格文件
  const isSpreadsheet = block.mimeType?.includes("spreadsheet") ||
    block.mimeType?.includes("excel") ||
    block.mimeType === "text/csv";
  if (block.type === "file" && isSpreadsheet) {
    const filename = block.metadata?.filename || block.metadata?.name || "Spreadsheet";
    return (
      <div
        className={cn(
          "relative flex items-start gap-2 rounded-md border bg-green-50 px-3 py-2",
          className,
        )}
      >
        <div className="flex flex-shrink-0 flex-col items-start justify-start">
          <File
            className={cn(
              "text-green-600",
              size === "sm" ? "h-5 w-5" : "h-7 w-7",
            )}
          />
        </div>
        <span
          className={cn("min-w-0 flex-1 text-sm break-all text-gray-800")}
          style={{ wordBreak: "break-all", whiteSpace: "pre-wrap" }}
        >
          {String(filename)}
        </span>
        {removable && (
          <button
            type="button"
            className="ml-2 self-start rounded-full bg-gray-200 p-1 text-green-600 hover:bg-gray-300"
            onClick={onRemove}
            aria-label="Remove file"
          >
            <XIcon className="h-4 w-4" />
          </button>
        )}
      </div>
    );
  }

  // Fallback for unknown types
  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-md border bg-gray-100 px-3 py-2 text-gray-500",
        className,
      )}
    >
      <File className="h-5 w-5 flex-shrink-0" />
      <span className="truncate text-xs">Unsupported file type</span>
      {removable && (
        <button
          type="button"
          className="ml-2 rounded-full bg-gray-200 p-1 text-gray-500 hover:bg-gray-300"
          onClick={onRemove}
          aria-label="Remove file"
        >
          <XIcon className="h-4 w-4" />
        </button>
      )}
    </div>
  );
};
