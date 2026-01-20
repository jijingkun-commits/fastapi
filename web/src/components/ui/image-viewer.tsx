"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import { ZoomIn, ZoomOut, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";

interface ImageViewerProps {
    src: string;
    alt?: string;
    className?: string;
}

/**
 * 独立的图片查看器组件
 * 支持缩放、拖拽、重置等功能
 */
export const ImageViewer: React.FC<ImageViewerProps> = ({ src, alt, className }) => {
    const [scale, setScale] = useState(1);
    const [position, setPosition] = useState({ x: 0, y: 0 });
    const [isDragging, setIsDragging] = useState(false);
    const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
    const containerRef = useRef<HTMLDivElement>(null);

    const handleWheel = useCallback((e: WheelEvent) => {
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        setScale((prev) => Math.max(0.5, Math.min(5, prev + delta)));
    }, []);

    const handleZoomIn = () => {
        setScale((prev) => Math.min(5, prev + 0.2));
    };

    const handleZoomOut = () => {
        setScale((prev) => Math.max(0.5, prev - 0.2));
    };

    const handleReset = () => {
        setScale(1);
        setPosition({ x: 0, y: 0 });
    };

    const handleMouseDown = (e: React.MouseEvent) => {
        if (scale > 1) {
            setIsDragging(true);
            setDragStart({
                x: e.clientX - position.x,
                y: e.clientY - position.y,
            });
        }
    };

    const handleMouseMove = useCallback(
        (e: MouseEvent) => {
            if (isDragging) {
                setPosition({
                    x: e.clientX - dragStart.x,
                    y: e.clientY - dragStart.y,
                });
            }
        },
        [isDragging, dragStart]
    );

    const handleMouseUp = useCallback(() => {
        setIsDragging(false);
    }, []);

    useEffect(() => {
        const container = containerRef.current;
        if (container) {
            container.addEventListener("wheel", handleWheel, { passive: false });
            return () => {
                container.removeEventListener("wheel", handleWheel);
            };
        }
    }, [handleWheel]);

    useEffect(() => {
        if (isDragging) {
            document.addEventListener("mousemove", handleMouseMove);
            document.addEventListener("mouseup", handleMouseUp);
            return () => {
                document.removeEventListener("mousemove", handleMouseMove);
                document.removeEventListener("mouseup", handleMouseUp);
            };
        }
    }, [isDragging, handleMouseMove, handleMouseUp]);

    return (
        <div className={cn("relative w-full h-full flex flex-col", className)}>
            <div
                ref={containerRef}
                className="flex-1 flex items-center justify-center overflow-hidden bg-black/90 rounded-lg"
                onMouseDown={handleMouseDown}
                style={{ cursor: scale > 1 ? (isDragging ? "grabbing" : "grab") : "default" }}
            >
                <img
                    src={src}
                    alt={alt || "图片"}
                    className="max-w-full max-h-full object-contain transition-transform duration-200"
                    style={{
                        transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
                        userSelect: "none",
                    }}
                    draggable={false}
                />
            </div>

            <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex items-center gap-2 bg-black/70 rounded-full px-4 py-2">
                <button
                    onClick={handleZoomOut}
                    className="p-2 text-white hover:bg-white/20 rounded-full transition-colors"
                    aria-label="缩小"
                >
                    <ZoomOut className="w-5 h-5" />
                </button>

                <span className="text-white text-sm min-w-16 text-center">
                    {Math.round(scale * 100)}%
                </span>

                <button
                    onClick={handleZoomIn}
                    className="p-2 text-white hover:bg-white/20 rounded-full transition-colors"
                    aria-label="放大"
                >
                    <ZoomIn className="w-5 h-5" />
                </button>

                <div className="w-px h-6 bg-white/30 mx-1" />

                <button
                    onClick={handleReset}
                    className="p-2 text-white hover:bg-white/20 rounded-full transition-colors"
                    aria-label="重置"
                >
                    <RotateCcw className="w-5 h-5" />
                </button>
            </div>
        </div>
    );
};
