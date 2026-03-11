import { parseAsBoolean, useQueryState } from "nuqs";

import { useMediaQuery } from "./useMediaQuery";

export function useChatHistoryOpen() {
  const isLargeScreen = useMediaQuery("(min-width: 1024px)");
  const [chatHistoryOpenParam, setChatHistoryOpenParam] = useQueryState(
    "chatHistoryOpen",
    parseAsBoolean,
  );

  const chatHistoryOpen = chatHistoryOpenParam ?? isLargeScreen;

  const setChatHistoryOpen = (
    next: boolean | ((prev: boolean) => boolean),
  ) => {
    const nextValue = typeof next === "function" ? next(chatHistoryOpen) : next;
    return setChatHistoryOpenParam(nextValue);
  };

  return { chatHistoryOpen, setChatHistoryOpen, isLargeScreen };
}
