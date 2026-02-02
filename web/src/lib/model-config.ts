/**
 * 模型配置（中文注释）
 * 
 * 从后端 API 动态获取模型列表，替代硬编码方式。
 * 提供 React Hook 和工具函数。
 */

import { useEffect, useState } from "react";
import { getModels, ModelInfo } from "./backend";

/** 模型推理能力类型 */
export type ThinkingCapability =
    | "always"    // 始终推理（如 deepseek-reasoner），不可关闭
    | "never"     // 不支持推理（如 deepseek-chat），不可开启
    | "optional"; // 可选推理（如 qwen-plus），用户可切换

/** 前端使用的模型配置接口 */
export interface ModelConfig {
    /** 模型标识，用于 API 调用 */
    id: string;
    /** 显示名称 */
    name: string;
    /** 提供商 */
    provider: string;
    /** 推理能力 */
    thinking: ThinkingCapability;
    /** 是否为默认模型 */
    isDefault?: boolean;
}

/** 默认模型 ID（undefined 表示使用后端默认模型） */
export const DEFAULT_MODEL_ID: string | undefined = undefined;

/** 模型列表缓存 */
let _cachedModels: ModelConfig[] | null = null;

/**
 * 将后端模型信息转换为前端模型配置
 */
function convertToModelConfig(info: ModelInfo): ModelConfig {
    // 根据 provider 和 supports_thinking 推断 thinking capability
    let thinking: ThinkingCapability = "never";

    // 特殊处理：推理模型（如 deepseek-reasoner）始终开启
    if (info.model_code.includes("reasoner") || info.model_code.includes("r1")) {
        thinking = "always";
    } else if (info.supports_thinking) {
        // 支持思考但不是推理专用模型 = 可选
        thinking = "optional";
    }

    return {
        id: info.model_code,
        name: info.model_name,
        provider: info.provider,
        thinking,
        isDefault: info.is_default,
    };
}

/**
 * 从后端获取模型列表（带缓存）
 */
export async function fetchModels(): Promise<ModelConfig[]> {
    if (_cachedModels) {
        return _cachedModels;
    }

    try {
        const models = await getModels();
        // 只保留 chat 和 reasoning 类型的模型（用于聊天模型选择器）
        const chatModels = models.filter(m => m.model_type === "chat" || m.model_type === "reasoning");
        _cachedModels = chatModels.map(convertToModelConfig);
        return _cachedModels;
    } catch (error) {
        console.error("获取模型列表失败:", error);
        // 返回最小后备列表
        return [
            { id: "deepseek-chat", name: "DeepSeek Chat", provider: "deepseek", thinking: "never" },
        ];
    }
}

/**
 * 清除模型缓存（用于刷新）
 */
export function clearModelCache() {
    _cachedModels = null;
}

/**
 * React Hook: 获取模型列表
 */
export function useModels() {
    const [models, setModels] = useState<ModelConfig[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let mounted = true;

        fetchModels()
            .then((list) => {
                if (mounted) {
                    setModels(list);
                    setLoading(false);
                }
            })
            .catch((err) => {
                if (mounted) {
                    setError(err.message);
                    setLoading(false);
                }
            });

        return () => { mounted = false; };
    }, []);

    return { models, loading, error };
}

/**
 * 根据模型 ID 获取配置（从缓存）
 */
export function getModelConfig(modelId: string): ModelConfig | undefined {
    return _cachedModels?.find(m => m.id === modelId);
}

/**
 * 根据模型能力获取深度思考开关的默认值
 */
export function getDefaultThinkingState(capability: ThinkingCapability): boolean {
    return capability === "always";
}

/**
 * 检查深度思考开关是否可切换
 */
export function isThinkingToggleable(capability: ThinkingCapability): boolean {
    return capability === "optional";
}

/**
 * 获取默认模型
 */
export function getDefaultModel(models: ModelConfig[]): ModelConfig | undefined {
    return models.find(m => m.isDefault) || models[0];
}
