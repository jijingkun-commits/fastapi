"use client";

import { ArtifactProvider } from "@/components/thread/artifact";
import { ThreadProvider } from "@/providers/Thread";
import { StreamProvider } from "@/providers/Stream";
import { Thread } from "@/components/thread";

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

