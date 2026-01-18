/**
 * Stream Provider（中文注释）
 * 
 * 提供消息流的 Provider 组件，使用 SSE 模式处理流式响应。
 */

import React, { ReactNode } from "react";

// 导入拆分出去的模块
import { StreamContext, StateType, useStreamContext } from "./StreamContext";
import { useSSEStream } from "@/hooks/useSSEStream";

// 重新导出以保持向后兼容
export { useStreamContext };
export type { StateType };

/**
 * SSE 模式 Session 组件
 * 使用拆分后的 useSSEStream hook
 */
const StreamSession = ({ children }: { children: ReactNode }) => {
  const streamValue = useSSEStream();

  return (
    <StreamContext.Provider value={streamValue}>
      {children}
    </StreamContext.Provider>
  );
};

/**
 * Stream Provider 主组件
 */
export const StreamProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  return (
    <StreamSession>
      {children}
    </StreamSession>
  );
};

export default StreamContext;
