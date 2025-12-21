import React, {
  createContext,
  useContext,
  ReactNode,
  useState,
  useEffect,
  useRef,
} from "react";
import { useStream } from "@langchain/langgraph-sdk/react";
import { type Message } from "@langchain/langgraph-sdk";
import {
  uiMessageReducer,
  isUIMessage,
  isRemoveUIMessage,
  type UIMessage,
  type RemoveUIMessage,
} from "@langchain/langgraph-sdk/react-ui";
import { useQueryState } from "nuqs";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { LangGraphLogoSVG } from "@/components/icons/langgraph";
import { Label } from "@/components/ui/label";
import { ArrowRight } from "lucide-react";
import { PasswordInput } from "@/components/ui/password-input";
import { getApiKey } from "@/lib/api-key";
import { useThreads } from "./Thread";
import { toast } from "sonner";
import { startLLMStream } from "@/lib/backend";
import { v4 as uuidv4 } from "uuid";

export type StateType = { messages: Message[]; ui?: UIMessage[] };

const useTypedStream = useStream<
  StateType,
  {
    UpdateType: {
      messages?: Message[] | Message | string;
      ui?: (UIMessage | RemoveUIMessage)[] | UIMessage | RemoveUIMessage;
      context?: Record<string, unknown>;
    };
    CustomEventType: UIMessage | RemoveUIMessage;
  }
>;

type StreamContextType = ReturnType<typeof useTypedStream>;
const StreamContext = createContext<StreamContextType | undefined>(undefined);

async function sleep(ms = 4000) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function checkGraphStatus(
  apiUrl: string,
  apiKey: string | null,
): Promise<boolean> {
  try {
    const res = await fetch(`${apiUrl}/info`, {
      ...(apiKey && {
        headers: {
          "X-Api-Key": apiKey,
        },
      }),
    });

    return res.ok;
  } catch (e) {
    console.error(e);
    return false;
  }
}

// Mode selection: if NEXT_PUBLIC_API_URL is not set, default to SSE mode to reuse FastAPI stream.
const MODE =
  (process.env.NEXT_PUBLIC_LG_MODE as "langgraph" | "sse" | undefined) ??
  (process.env.NEXT_PUBLIC_API_URL ? "langgraph" : "sse");

const StreamSessionSSE = ({ children }: { children: ReactNode }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<unknown>(undefined);
  const stopRef = useRef<(() => void) | null>(null);
  const currentAiIdRef = useRef<string | null>(null);

  const getMessagesMetadata = (_msg: Message) => {
    return {
      firstSeenState: { parent_checkpoint: null, values: { messages } },
      branch: undefined,
      branchOptions: undefined,
    } as any;
  };

  const setBranch = (_branch: unknown) => {
    // no-op in SSE mode
  };

  const stop = () => {
    stopRef.current?.();
    stopRef.current = null;
    currentAiIdRef.current = null;
    setIsLoading(false);
  };

  const extractText = (m: Message | string | Message[] | undefined): string => {
    if (!m) return "";
    if (typeof m === "string") return m;
    const msg = Array.isArray(m) ? m[m.length - 1] : m;
    if (!msg) return "";
    const c = (msg as Message).content as any;
    if (typeof c === "string") return c;
    if (Array.isArray(c)) {
      return c
        .filter((b: any) => b && b.type === "text" && typeof b.text === "string")
        .map((b: any) => b.text)
        .join("\n");
    }
    return "";
  };

  const submit = (
    update?: { messages?: Message[] | Message | string; context?: Record<string, unknown> },
    _options?: any,
  ) => {
    try {
      if (update?.messages) {
        if (typeof update.messages === "string") {
          setMessages((prev) => [
            ...prev,
            { type: "human", content: update.messages } as Message,
          ]);
        } else if (Array.isArray(update.messages)) {
          setMessages((prev) => [...prev, ...(update.messages as Message[])]);
        } else {
          setMessages((prev) => [...prev, update.messages as Message]);
        }
      }

      const prompt = extractText(update?.messages);
      if (!prompt.trim()) return;

      const aiId = uuidv4();
      currentAiIdRef.current = aiId;
      setMessages((prev) => [...prev, { id: aiId, type: "ai", content: "" } as Message]);
      setIsLoading(true);

      stopRef.current = startLLMStream(
        prompt,
        (token) => {
          setMessages((prev) => {
            const idx = prev.findIndex((m) => m.id === aiId);
            if (idx < 0) return prev;
            const before = prev.slice(0, idx);
            const after = prev.slice(idx + 1);
            const ai = prev[idx];
            const content = typeof ai.content === "string"
              ? ai.content
              : Array.isArray(ai.content)
              ? ai.content.filter((b: any) => b.type === "text").map((b: any) => b.text).join("\n")
              : "";
            const next: Message = { ...ai, content: content + token } as Message;
            return [...before, next, ...after];
          });
        },
        50,
      );
    } catch (e) {
      setError(e);
      setIsLoading(false);
    }
  };

  const values: StateType = { messages, ui: [] };
  const streamValue = {
    messages,
    values,
    isLoading,
    error,
    interrupt: undefined,
    submit,
    stop,
    getMessagesMetadata,
    setBranch,
  } as any;

  return (
    <StreamContext.Provider value={streamValue}>{children}</StreamContext.Provider>
  );
};

const StreamSessionLG = ({
  children,
  apiKey,
  apiUrl,
  assistantId,
}: {
  children: ReactNode;
  apiKey: string | null;
  apiUrl: string;
  assistantId: string;
}) => {
  const [threadId, setThreadId] = useQueryState("threadId");
  const { getThreads, setThreads } = useThreads();
  const streamValue = useTypedStream({
    apiUrl,
    apiKey: apiKey ?? undefined,
    assistantId,
    threadId: threadId ?? null,
    fetchStateHistory: true,
    onCustomEvent: (event, options) => {
      if (isUIMessage(event) || isRemoveUIMessage(event)) {
        options.mutate((prev) => {
          const ui = uiMessageReducer(prev.ui ?? [], event);
          return { ...prev, ui };
        });
      }
    },
    onThreadId: (id) => {
      setThreadId(id);
      sleep().then(() => getThreads().then(setThreads).catch(console.error));
    },
  });

  useEffect(() => {
    checkGraphStatus(apiUrl, apiKey).then((ok) => {
      if (!ok) {
        toast.error("Failed to connect to LangGraph server", {
          description: () => (
            <p>
              Please ensure your graph is running at <code>{apiUrl}</code> and
              your API key is correctly set (if connecting to a deployed graph).
            </p>
          ),
          duration: 10000,
          richColors: true,
          closeButton: true,
        });
      }
    });
  }, [apiKey, apiUrl]);

  return (
    <StreamContext.Provider value={streamValue}>{children}</StreamContext.Provider>
  );
};

const StreamSession = ({
  children,
  apiKey,
  apiUrl,
  assistantId,
}: {
  children: ReactNode;
  apiKey: string | null;
  apiUrl: string;
  assistantId: string;
}) => {
  return MODE === "sse" ? (
    <StreamSessionSSE>{children}</StreamSessionSSE>
  ) : (
    <StreamSessionLG apiKey={apiKey} apiUrl={apiUrl} assistantId={assistantId}>
      {children}
    </StreamSessionLG>
  );
};

// Default values for the form
const DEFAULT_API_URL = "http://localhost:2024";
const DEFAULT_ASSISTANT_ID = "agent";

export const StreamProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  // Get environment variables
  const envApiUrl: string | undefined = process.env.NEXT_PUBLIC_API_URL;
  const envAssistantId: string | undefined =
    process.env.NEXT_PUBLIC_ASSISTANT_ID;

  // Use URL params with env var fallbacks
  const [apiUrl, setApiUrl] = useQueryState("apiUrl", {
    defaultValue: envApiUrl || "",
  });
  const [assistantId, setAssistantId] = useQueryState("assistantId", {
    defaultValue: envAssistantId || "",
  });

  // For API key, use localStorage with env var fallback
  const [apiKey, _setApiKey] = useState(() => {
    const storedKey = getApiKey();
    return storedKey || "";
  });

  const setApiKey = (key: string) => {
    window.localStorage.setItem("lg:chat:apiKey", key);
    _setApiKey(key);
  };

  // Determine final values to use, prioritizing URL params then env vars
  const finalApiUrl = apiUrl || envApiUrl;
  const finalAssistantId = assistantId || envAssistantId;

  // Show the form if we: don't have an API URL, or don't have an assistant ID
  if (MODE !== "sse" && (!finalApiUrl || !finalAssistantId)) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center p-4">
        <div className="animate-in fade-in-0 zoom-in-95 bg-background flex max-w-3xl flex-col rounded-lg border shadow-lg">
          <div className="mt-14 flex flex-col gap-2 border-b p-6">
            <div className="flex flex-col items-start gap-2">
              <LangGraphLogoSVG className="h-7" />
              <h1 className="text-xl font-semibold tracking-tight">
                Agent Chat
              </h1>
            </div>
            <p className="text-muted-foreground">
              Welcome to Agent Chat! Before you get started, you need to enter
              the URL of the deployment and the assistant / graph ID.
            </p>
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();

              const form = e.target as HTMLFormElement;
              const formData = new FormData(form);
              const apiUrl = formData.get("apiUrl") as string;
              const assistantId = formData.get("assistantId") as string;
              const apiKey = formData.get("apiKey") as string;

              setApiUrl(apiUrl);
              setApiKey(apiKey);
              setAssistantId(assistantId);

              form.reset();
            }}
            className="bg-muted/50 flex flex-col gap-6 p-6"
          >
            <div className="flex flex-col gap-2">
              <Label htmlFor="apiUrl">
                Deployment URL<span className="text-rose-500">*</span>
              </Label>
              <p className="text-muted-foreground text-sm">
                This is the URL of your LangGraph deployment. Can be a local, or
                production deployment.
              </p>
              <Input
                id="apiUrl"
                name="apiUrl"
                className="bg-background"
                defaultValue={apiUrl || DEFAULT_API_URL}
                required
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="assistantId">
                Assistant / Graph ID<span className="text-rose-500">*</span>
              </Label>
              <p className="text-muted-foreground text-sm">
                This is the ID of the graph (can be the graph name), or
                assistant to fetch threads from, and invoke when actions are
                taken.
              </p>
              <Input
                id="assistantId"
                name="assistantId"
                className="bg-background"
                defaultValue={assistantId || DEFAULT_ASSISTANT_ID}
                required
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="apiKey">LangSmith API Key</Label>
              <p className="text-muted-foreground text-sm">
                This is <strong>NOT</strong> required if using a local LangGraph
                server. This value is stored in your browser's local storage and
                is only used to authenticate requests sent to your LangGraph
                server.
              </p>
              <PasswordInput
                id="apiKey"
                name="apiKey"
                defaultValue={apiKey ?? ""}
                className="bg-background"
                placeholder="lsv2_pt_..."
              />
            </div>

            <div className="mt-2 flex justify-end">
              <Button
                type="submit"
                size="lg"
              >
                Continue
                <ArrowRight className="size-5" />
              </Button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  return (
    <StreamSession
      apiKey={MODE === "sse" ? null : apiKey}
      apiUrl={MODE === "sse" ? "" : apiUrl}
      assistantId={MODE === "sse" ? "" : assistantId}
    >
      {children}
    </StreamSession>
  );
};

// Create a custom hook to use the context
export const useStreamContext = (): StreamContextType => {
  const context = useContext(StreamContext);
  if (context === undefined) {
    throw new Error("useStreamContext must be used within a StreamProvider");
  }
  return context;
};

export default StreamContext;
