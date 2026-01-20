import React from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface CloseButtonProps {
    onClick?: () => void;
    className?: string;
    size?: "sm" | "md" | "lg";
}

/**
 * 统一的关闭按钮组件
 * 用于所有弹窗和对话框，确保样式一致
 */
export const CloseButton: React.FC<CloseButtonProps> = ({
    onClick,
    className,
    size = "md"
}) => {
    const sizeClasses = {
        sm: "w-6 h-6",
        md: "w-8 h-8",
        lg: "w-10 h-10",
    };

    const iconSizes = {
        sm: "w-3 h-3",
        md: "w-4 h-4",
        lg: "w-5 h-5",
    };

    return (
        <button
            onClick={onClick}
            className={cn(
                "rounded-full bg-black/50 text-white hover:bg-black/70 transition-all duration-200",
                "flex items-center justify-center",
                "focus:outline-none focus:ring-2 focus:ring-white/50",
                sizeClasses[size],
                className
            )}
            aria-label="关闭"
        >
            <X className={iconSizes[size]} />
        </button>
    );
};
