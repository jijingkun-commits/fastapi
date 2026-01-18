"use client";

import { ArtifactProvider } from "@/components/chat/artifact";
import { ThreadProvider } from "@/providers/Thread";
import { StreamProvider } from "@/providers/Stream";
import { Thread } from "@/components/chat";

export function ChatContainer() {
  return (
    <ArtifactProvider>
      <ThreadProvider>
        <StreamProvider>
          <Thread />
        </StreamProvider>
      </ThreadProvider>
    </ArtifactProvider>
  );
}

