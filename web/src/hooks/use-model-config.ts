import { useState, useEffect, useCallback } from "react";
import {
    DEFAULT_MODEL_ID,
    getModelConfig,
    getDefaultThinkingState,
    ThinkingCapability
} from "@/lib/model-config";

/**
 * Hook to manage selected model and its thinking capability
 */
export function useModelConfig() {
    // Initial state with default to avoid hydration mismatch
    const [selectedModel, setSelectedModel] = useState(DEFAULT_MODEL_ID);
    const [enableThinking, setEnableThinking] = useState(false);

    // Initial load from local storage
    useEffect(() => {
        if (typeof window !== "undefined") {
            const savedModel = localStorage.getItem("chat:selectedModel");
            if (savedModel && savedModel !== DEFAULT_MODEL_ID) {
                setSelectedModel(savedModel);
                // Also restore thinking state based on model default if needed
                // But simplified: just set model, handleModelChange logic handles the rest usually
            }
        }
    }, []);

    // Get current capability
    const thinkingCapability: ThinkingCapability = getModelConfig(selectedModel)?.thinking ?? "never";

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
