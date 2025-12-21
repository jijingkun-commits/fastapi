"use client";

import { useMemo, useRef, useState } from "react";
import { startLLMStream } from "@/lib/backend";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export function SseCard() {
  const [prompt, setPrompt] = useState("");
  const [delayMs, setDelayMs] = useState<number>(50);
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const stopRef = useRef<(() => void) | null>(null);

  const canStream = useMemo(() => prompt.trim().length > 0 && !streaming, [prompt, streaming]);

  const onStartStream = () => {
    if (!canStream) return;
    setStreamText("");
    setStreaming(true);
    stopRef.current = startLLMStream(
      prompt,
      (t) => setStreamText((p) => p + t),
      delayMs,
    );
  };

  const onStopStream = () => {
    stopRef.current?.();
    stopRef.current = null;
    setStreaming(false);
  };

  const onClear = () => {
    setStreamText("");
    setPrompt("");
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>LLM 流式对话（FastAPI）</CardTitle>
        <CardDescription>使用后端 /api/v1/llm/stream 进行 token 推送</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <Label htmlFor="prompt">提示词</Label>
          <Textarea id="prompt" value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="输入提示词，回车或点击开始" />
        </div>
        <div className="flex items-center gap-3">
          <Label htmlFor="delay">延迟 ms</Label>
          <Input id="delay" type="number" value={delayMs} onChange={(e) => setDelayMs(Number(e.target.value) || 0)} className="w-28" />
          {streaming ? (
            <Button onClick={onStopStream} variant="destructive">停止</Button>
          ) : (
            <Button onClick={onStartStream} disabled={!canStream} variant="brand">开始</Button>
          )}
          <Button onClick={onClear} variant="outline">清空</Button>
        </div>
        <div className="rounded-md bg-muted p-3 text-sm whitespace-pre-wrap break-words min-h-[120px]">{streamText || ""}</div>
      </CardContent>
    </Card>
  );
}

