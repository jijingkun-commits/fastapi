import { useState, useEffect, useCallback } from "react";
import {
    DEFAULT_MODEL_ID,
    getModelConfig,
    getDefaultThinkingState,
    ThinkingCapability
} from "@/lib/model-config";

/**
 * Hook to manage selected model and its thinking capability
 * selectedModel 为 undefined 时表示使用后端默认模型
 */
export function useModelConfig() {
    // Initial state: undefined 表示使用后端默认模型
    const [selectedModel, setSelectedModel] = useState<string | undefined>(DEFAULT_MODEL_ID);
    const [enableThinking, setEnableThinking] = useState(false);

    // Initial load from local storage
    useEffect(() => {
        if (typeof window !== "undefined") {
            const savedModel = localStorage.getItem("chat:selectedModel");
            // 只有当用户显式选择过模型时才使用 localStorage 的值
            // 旧值 "deepseek-chat" 不再作为有效选择（让后端使用默认）
            if (savedModel && savedModel !== "deepseek-chat") {
                setSelectedModel(savedModel);
            }
        }
    }, []);

    // Get current capability (undefined 模型表示使用后端默认，默认不支持 thinking)
    const thinkingCapability: ThinkingCapability = selectedModel 
        ? (getModelConfig(selectedModel)?.thinking ?? "never") 
        : "never";

    /**
     * Handle Model Change
     */
    const handleModelChange = useCallback((modelId: string) => {
        setSelectedModel(modelId);
        if (typeof window !== "undefined") {
            localStorage.setItem("chat:selectedModel", modelId);
        }
        const config = getModelConfig(modelId);
        if (config) {
            setEnableThinking(getDefaultThinkingState(config.thinking));
        }
    }, []);

    return {
        selectedModel,
        enableThinking,
        setEnableThinking,
        thinkingCapability,
        handleModelChange
    };
}
