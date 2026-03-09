import { useCallback } from "react";
import { Message } from "@langchain/langgraph-sdk";
import { v4 as uuidv4 } from "uuid";

const MARKDOWN_IMAGE_REGEX = /!\[[^\]]*\]\(([^)]+)\)/g;

function getMessageTextContent(content: Message["content"]): string {
    if (typeof content === "string") {
        return content;
    }

    if (!Array.isArray(content)) {
        return "";
    }

    return content
        .filter((block: any) => block.type === "text")
        .map((block: any) => block.text)
        .join("\n");
}

function filterDuplicateImageMarkdown(token: string, existingContent: string): string {
    if (!token || !existingContent || !token.includes("![")) {
        return token;
    }

    return token.replace(MARKDOWN_IMAGE_REGEX, (fullMatch, url: string) => {
        if (!url) {
            return fullMatch;
        }
        return existingContent.includes(url) ? "" : fullMatch;
    });
}

export function appendTokenToMessages(prev: Message[], aiId: string, token: string): Message[] {
    const idx = prev.findIndex((m) => m.id === aiId);
    if (idx < 0) return prev;
    const ai = prev[idx] as any;
    const content = getMessageTextContent(ai.content);
    const filteredToken = filterDuplicateImageMarkdown(token, content);
    if (!filteredToken) {
        return prev;
    }

    const next: Message = { ...ai, content: content + filteredToken } as Message;
    return [...prev.slice(0, idx), next, ...prev.slice(idx + 1)];
}

export function appendImageToMessages(prev: Message[], aiId: string, imageUrl: string, alt = "生成图片"): Message[] {
    if (!imageUrl || !imageUrl.trim()) {
        return prev;
    }

    const idx = prev.findIndex((m) => m.id === aiId);
    if (idx < 0) return prev;

    const ai = prev[idx] as any;
    const content = getMessageTextContent(ai.content);
    if (content.includes(imageUrl)) {
        return prev;
    }

    const imageMarkdown = `![${alt}](${imageUrl})`;
    const trimmed = content.trimEnd();
    const separator = trimmed.length > 0 ? "\n\n" : "";
    const nextContent = `${trimmed}${separator}${imageMarkdown}`;

    const next: Message = { ...ai, content: nextContent } as Message;
    return [...prev.slice(0, idx), next, ...prev.slice(idx + 1)];
}

export function addToolCallToMessages(prev: Message[], aiId: string, name: string, input: any): Message[] {
    const idx = prev.findIndex((m) => m.id === aiId);
    if (idx < 0) return prev;
    const ai = prev[idx] as any;
    const existingToolCalls = ai.tool_calls || [];

    const existingIdx = existingToolCalls.findIndex((tc: any) => tc.name === name);
    if (existingIdx >= 0) {
        const updatedToolCalls = [...existingToolCalls];
        updatedToolCalls[existingIdx] = {
            ...updatedToolCalls[existingIdx],
            args: { ...updatedToolCalls[existingIdx].args, ...input },
        };
        console.debug(`工具调用更新: ${name}`);
        return [...prev.slice(0, idx), { ...ai, tool_calls: updatedToolCalls }, ...prev.slice(idx + 1)];
    }

    const newToolCall = {
        id: uuidv4(),
        name,
        args: input || {},
        type: "tool_call",
    };
    const next = {
        ...ai,
        tool_calls: [...existingToolCalls, newToolCall],
    };
    return [...prev.slice(0, idx), next, ...prev.slice(idx + 1)];
}

export function appendThinkingToMessages(prev: Message[], aiId: string, content: string): Message[] {
    const idx = prev.findIndex((m) => m.id === aiId);
    if (idx < 0) return prev;
    const ai = prev[idx];
    const currentContent = typeof ai.content === "string" ? ai.content : "";

    if (currentContent.startsWith("<think>")) {
        const endThinkIdx = currentContent.indexOf("</think>");
        if (endThinkIdx > 0) {
            const thinkPart = currentContent.slice(0, endThinkIdx);
            const restPart = currentContent.slice(endThinkIdx);
            const next: Message = { ...ai, content: thinkPart + content + restPart } as Message;
            return [...prev.slice(0, idx), next, ...prev.slice(idx + 1)];
        }
    }

    const thinkingBlock = `<think>\n${content}\n</think>\n\n`;
    const next: Message = { ...ai, content: thinkingBlock + currentContent } as Message;
    return [...prev.slice(0, idx), next, ...prev.slice(idx + 1)];
}

/**
 * Hook to manage message state updates
 */
export function useMessageUpdater(setMessages: React.Dispatch<React.SetStateAction<Message[]>>) {
    const appendToAiMessage = useCallback((aiId: string, token: string) => {
        setMessages((prev) => appendTokenToMessages(prev, aiId, token));
    }, [setMessages]);

    const appendImageToAiMessage = useCallback((aiId: string, imageUrl: string, alt = "生成图片") => {
        setMessages((prev) => appendImageToMessages(prev, aiId, imageUrl, alt));
    }, [setMessages]);

    const addToolCallToMessage = useCallback((aiId: string, name: string, input: any) => {
        setMessages((prev) => addToolCallToMessages(prev, aiId, name, input));
    }, [setMessages]);

    const handleThinking = useCallback((aiId: string, content: string) => {
        setMessages((prev) => appendThinkingToMessages(prev, aiId, content));
    }, [setMessages]);

    return {
        appendToAiMessage,
        appendImageToAiMessage,
        addToolCallToMessage,
        handleThinking,
    };
}
