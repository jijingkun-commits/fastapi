import {
  XIcon,
  SendHorizontal,
  RefreshCcw,
  Pencil,
  Copy,
  CopyCheck,
  ChevronLeft,
  ChevronRight,
  ThumbsUp,
  ThumbsDown,
} from "lucide-react";
import { submitFeedback } from "@/lib/backend";
import { toast } from "sonner";

import { TooltipIconButton } from "../tooltip-icon-button";
import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import { Button } from "@/components/ui/button";

function ContentCopyable({
  content,
  disabled,
}: {
  content: string;
  disabled: boolean;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e: React.MouseEvent<HTMLButtonElement, MouseEvent>) => {
    e.stopPropagation();
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <TooltipIconButton
      onClick={(e) => handleCopy(e)}
      variant="ghost"
      tooltip="复制内容"
      disabled={disabled}
      className="chat-message-tool-button"
    >
      <AnimatePresence
        mode="wait"
        initial={false}
      >
        {copied ? (
          <motion.div
            key="check"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.15 }}
          >
            <CopyCheck className="text-green-500" />
          </motion.div>
        ) : (
          <motion.div
            key="copy"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.15 }}
          >
            <Copy />
          </motion.div>
        )}
      </AnimatePresence>
    </TooltipIconButton>
  );
}

function FeedbackButtons({
  messageId,
  initialScore = 0,
  disabled,
}: {
  messageId: number | string;
  initialScore?: number;
  disabled: boolean;
}) {
  // score: 1(like), -1(dislike), 0(none)
  const [score, setScore] = useState(initialScore);

  const handleFeedback = async (newScore: number) => {
    // Toggle: if clicking same button, cancel it (set to 0)
    const finalScore = score === newScore ? 0 : newScore;

    // Optimistic update
    setScore(finalScore);

    try {
      await submitFeedback(messageId, finalScore);
      // toast.success(finalScore === 0 ? "已取消" : "感谢反馈");
    } catch {
      // Revert on error
      setScore(score);
      toast.error("反馈失败");
    }
  };

  return (
    <>
      <TooltipIconButton
        disabled={disabled}
        tooltip="这条回答有帮助"
        variant="ghost"
        onClick={() => handleFeedback(1)}
        className={
          score === 1
            ? "chat-message-tool-button bg-green-50 text-green-600"
            : "chat-message-tool-button"
        }
      >
        <ThumbsUp className={score === 1 ? "fill-current" : ""} />
      </TooltipIconButton>
      <TooltipIconButton
        disabled={disabled}
        tooltip="这条回答没帮助"
        variant="ghost"
        onClick={() => handleFeedback(-1)}
        className={
          score === -1
            ? "chat-message-tool-button bg-red-50 text-red-600"
            : "chat-message-tool-button"
        }
      >
        <ThumbsDown className={score === -1 ? "fill-current" : ""} />
      </TooltipIconButton>
    </>
  );
}

export function BranchSwitcher({
  branch,
  branchOptions,
  onSelect,
  isLoading,
}: {
  branch: string | undefined;
  branchOptions: string[] | undefined;
  onSelect: (branch: string) => void;
  isLoading: boolean;
}) {
  if (!branchOptions || !branch) return null;
  const index = branchOptions.indexOf(branch);

  return (
    <div className="chat-branch-switcher flex items-center gap-0.5">
      <Button
        variant="ghost"
        size="icon"
        className="chat-message-tool-button size-6 rounded-full p-0"
        onClick={() => {
          const prevBranch = branchOptions[index - 1];
          if (!prevBranch) return;
          onSelect(prevBranch);
        }}
        disabled={isLoading}
      >
        <ChevronLeft />
      </Button>
      <span className="text-muted-foreground min-w-[38px] text-center text-[11px] font-medium">
        {index + 1} / {branchOptions.length}
      </span>
      <Button
        variant="ghost"
        size="icon"
        className="chat-message-tool-button size-6 rounded-full p-0"
        onClick={() => {
          const nextBranch = branchOptions[index + 1];
          if (!nextBranch) return;
          onSelect(nextBranch);
        }}
        disabled={isLoading}
      >
        <ChevronRight />
      </Button>
    </div>
  );
}

export function CommandBar({
  content,
  isHumanMessage,
  isAiMessage,
  isEditing,
  setIsEditing,
  handleSubmitEdit,
  handleRegenerate,
  isLoading,
  messageId,
  feedbackScore,
}: {
  content: string;
  isHumanMessage?: boolean;
  isAiMessage?: boolean;
  isEditing?: boolean;
  setIsEditing?: React.Dispatch<React.SetStateAction<boolean>>;
  handleSubmitEdit?: () => void;
  handleRegenerate?: () => void;
  messageId?: number | string;
  feedbackScore?: number;
  isLoading: boolean;
}) {
  if (isHumanMessage && isAiMessage) {
    throw new Error(
      "Can only set one of isHumanMessage or isAiMessage to true, not both.",
    );
  }

  if (!isHumanMessage && !isAiMessage) {
    throw new Error(
      "One of isHumanMessage or isAiMessage must be set to true.",
    );
  }

  if (
    isHumanMessage &&
    (isEditing === undefined ||
      setIsEditing === undefined ||
      handleSubmitEdit === undefined)
  ) {
    throw new Error(
      "If isHumanMessage is true, all of isEditing, setIsEditing, and handleSubmitEdit must be set.",
    );
  }

  const showEdit =
    isHumanMessage &&
    isEditing !== undefined &&
    !!setIsEditing &&
    !!handleSubmitEdit;

  if (isHumanMessage && isEditing && !!setIsEditing && !!handleSubmitEdit) {
    return (
      <div className="flex items-center gap-1">
        <TooltipIconButton
          disabled={isLoading}
          tooltip="取消编辑"
          variant="ghost"
          className="chat-message-tool-button"
          onClick={() => {
            setIsEditing(false);
          }}
        >
          <XIcon />
        </TooltipIconButton>
        <TooltipIconButton
          disabled={isLoading}
          tooltip="提交"
          variant="secondary"
          className="chat-message-tool-button"
          onClick={handleSubmitEdit}
        >
          <SendHorizontal />
        </TooltipIconButton>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1">
      <ContentCopyable
        content={content}
        disabled={isLoading}
      />
      {isAiMessage && !!handleRegenerate && (
        <TooltipIconButton
          disabled={isLoading}
          tooltip="重新生成"
          variant="ghost"
          className="chat-message-tool-button"
          onClick={handleRegenerate}
        >
          <RefreshCcw />
        </TooltipIconButton>
      )}
      {isAiMessage && messageId && (
        <FeedbackButtons
          messageId={messageId}
          initialScore={feedbackScore ?? 0}
          disabled={isLoading}
        />
      )}
      {showEdit && (
        <TooltipIconButton
          disabled={isLoading}
          tooltip="编辑"
          variant="ghost"
          className="chat-message-tool-button"
          onClick={() => {
            setIsEditing?.(true);
          }}
        >
          <Pencil />
        </TooltipIconButton>
      )}
    </div>
  );
}
