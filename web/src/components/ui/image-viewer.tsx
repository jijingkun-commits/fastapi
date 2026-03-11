"use client";

import Image from "next/image";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { ZoomIn, ZoomOut, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { CloseButton } from "@/components/ui/close-button";

interface ImageViewerProps {
  src: string;
  alt?: string;
  className?: string;
  isActive?: boolean;
  onRequestClose?: () => void;
}

interface ImageLightboxProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  src: string;
  alt?: string;
  className?: string;
}

interface Point {
  x: number;
  y: number;
}

interface Size {
  width: number;
  height: number;
}

const MIN_SCALE = 1;
const MAX_SCALE = 5;
const SCALE_STEP = 0.2;
const WHEEL_SCALE_STEP = 0.1;
const DOUBLE_TAP_SCALE = 2;
const DRAG_THRESHOLD = 3;

function getPointerDistance(points: Point[]) {
  if (points.length < 2) {
    return 0;
  }

  const [firstPoint, secondPoint] = points;
  return Math.hypot(secondPoint.x - firstPoint.x, secondPoint.y - firstPoint.y);
}

function getContainScale(imageSize: Size, containerSize: Size) {
  if (
    imageSize.width <= 0 ||
    imageSize.height <= 0 ||
    containerSize.width <= 0 ||
    containerSize.height <= 0
  ) {
    return 1;
  }

  return Math.min(
    containerSize.width / imageSize.width,
    containerSize.height / imageSize.height,
  );
}

export const ImageViewer: React.FC<ImageViewerProps> = ({
  src,
  alt,
  className,
  isActive = true,
  onRequestClose,
}) => {
  const [scale, setScale] = useState(MIN_SCALE);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [imageSize, setImageSize] = useState<Size>({ width: 0, height: 0 });
  const [containerSize, setContainerSize] = useState<Size>({
    width: 0,
    height: 0,
  });
  const containerRef = useRef<HTMLDivElement>(null);
  const activePointerIdRef = useRef<number | null>(null);
  const pointerPositionsRef = useRef<Map<number, Point>>(new Map());
  const pinchStartDistanceRef = useRef<number | null>(null);
  const pinchStartScaleRef = useRef(MIN_SCALE);
  const dragMovedRef = useRef(false);

  const containScale = getContainScale(imageSize, containerSize);
  const renderedScale = scale * containScale;
  const imageReady = imageSize.width > 0 && imageSize.height > 0;

  const clampScale = useCallback((nextScale: number) => {
    return Math.max(MIN_SCALE, Math.min(MAX_SCALE, nextScale));
  }, []);

  const setAbsoluteScale = useCallback(
    (nextScale: number) => {
      setScale(clampScale(nextScale));
    },
    [clampScale],
  );

  const updateScale = useCallback(
    (delta: number) => {
      setScale((prev) => clampScale(prev + delta));
    },
    [clampScale],
  );

  const handleReset = useCallback(() => {
    setScale(MIN_SCALE);
    setPosition({ x: 0, y: 0 });
    setIsDragging(false);
    activePointerIdRef.current = null;
    pointerPositionsRef.current.clear();
    pinchStartDistanceRef.current = null;
    pinchStartScaleRef.current = MIN_SCALE;
    dragMovedRef.current = false;
  }, []);

  const handleWheel = useCallback(
    (e: WheelEvent) => {
      e.preventDefault();
      updateScale(e.deltaY > 0 ? -WHEEL_SCALE_STEP : WHEEL_SCALE_STEP);
    },
    [updateScale],
  );

  const handlePointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      pointerPositionsRef.current.set(e.pointerId, {
        x: e.clientX,
        y: e.clientY,
      });
      e.currentTarget.setPointerCapture(e.pointerId);

      const pointerCount = pointerPositionsRef.current.size;
      if (pointerCount === 2) {
        pinchStartDistanceRef.current = getPointerDistance(
          Array.from(pointerPositionsRef.current.values()),
        );
        pinchStartScaleRef.current = scale;
        setIsDragging(false);
        activePointerIdRef.current = null;
        dragMovedRef.current = false;
        return;
      }

      if (pointerCount !== 1 || scale <= MIN_SCALE) {
        return;
      }

      activePointerIdRef.current = e.pointerId;
      dragMovedRef.current = false;
      setIsDragging(true);
      setDragStart({
        x: e.clientX - position.x,
        y: e.clientY - position.y,
      });
    },
    [position.x, position.y, scale],
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!pointerPositionsRef.current.has(e.pointerId)) {
        return;
      }

      pointerPositionsRef.current.set(e.pointerId, {
        x: e.clientX,
        y: e.clientY,
      });

      if (pointerPositionsRef.current.size === 2) {
        const pinchDistance = getPointerDistance(
          Array.from(pointerPositionsRef.current.values()),
        );
        const pinchStartDistance = pinchStartDistanceRef.current;

        if (pinchStartDistance && pinchDistance > 0) {
          setAbsoluteScale(
            pinchStartScaleRef.current * (pinchDistance / pinchStartDistance),
          );
        }
        return;
      }

      if (!isDragging || activePointerIdRef.current !== e.pointerId) {
        return;
      }

      const nextPosition = {
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      };

      if (
        Math.abs(nextPosition.x - position.x) > DRAG_THRESHOLD ||
        Math.abs(nextPosition.y - position.y) > DRAG_THRESHOLD
      ) {
        dragMovedRef.current = true;
      }

      setPosition(nextPosition);
    },
    [
      dragStart.x,
      dragStart.y,
      isDragging,
      position.x,
      position.y,
      setAbsoluteScale,
    ],
  );

  const stopDragging = useCallback(
    (e?: React.PointerEvent<HTMLDivElement>) => {
      if (e) {
        pointerPositionsRef.current.delete(e.pointerId);

        try {
          e.currentTarget.releasePointerCapture(e.pointerId);
        } catch {
          // noop
        }
      }

      if (pointerPositionsRef.current.size >= 2) {
        pinchStartDistanceRef.current = getPointerDistance(
          Array.from(pointerPositionsRef.current.values()),
        );
        pinchStartScaleRef.current = scale;
        setIsDragging(false);
        activePointerIdRef.current = null;
        return;
      }

      pinchStartDistanceRef.current = null;

      if (pointerPositionsRef.current.size === 1 && scale > MIN_SCALE) {
        const [remainingPointerId, remainingPointer] = Array.from(
          pointerPositionsRef.current.entries(),
        )[0];

        activePointerIdRef.current = remainingPointerId;
        setIsDragging(true);
        setDragStart({
          x: remainingPointer.x - position.x,
          y: remainingPointer.y - position.y,
        });
        return;
      }

      activePointerIdRef.current = null;
      setIsDragging(false);
    },
    [position.x, position.y, scale],
  );

  const handleStageClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target !== e.currentTarget) {
        return;
      }

      if (dragMovedRef.current) {
        dragMovedRef.current = false;
        return;
      }

      onRequestClose?.();
    },
    [onRequestClose],
  );

  const handleStageDoubleClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      e.preventDefault();
      if (scale > MIN_SCALE) {
        handleReset();
        return;
      }

      setAbsoluteScale(DOUBLE_TAP_SCALE);
    },
    [handleReset, scale, setAbsoluteScale],
  );

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    container.addEventListener("wheel", handleWheel, { passive: false });
    return () => {
      container.removeEventListener("wheel", handleWheel);
    };
  }, [handleWheel]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const updateContainerSize = () => {
      setContainerSize({
        width: container.clientWidth,
        height: container.clientHeight,
      });
    };

    updateContainerSize();

    const observer = new ResizeObserver(() => {
      updateContainerSize();
    });

    observer.observe(container);
    return () => {
      observer.disconnect();
    };
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const key = e.key;

      if (key === "Escape") {
        onRequestClose?.();
        return;
      }

      if (key === "+" || key === "=" || key === "NumpadAdd") {
        e.preventDefault();
        updateScale(SCALE_STEP);
        return;
      }

      if (key === "-" || key === "_" || key === "NumpadSubtract") {
        e.preventDefault();
        updateScale(-SCALE_STEP);
        return;
      }

      if (key === "0" || key === "Numpad0") {
        e.preventDefault();
        handleReset();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [handleReset, onRequestClose, updateScale]);

  useEffect(() => {
    if (scale <= MIN_SCALE) {
      setPosition({ x: 0, y: 0 });
      setIsDragging(false);
      activePointerIdRef.current = null;
      dragMovedRef.current = false;
    }
  }, [scale]);

  useEffect(() => {
    if (isActive) {
      handleReset();
    }
  }, [handleReset, isActive, src]);

  return (
    <div
      className={cn(
        "relative flex size-full min-h-0 flex-col bg-black",
        className,
      )}
    >
      <div
        ref={containerRef}
        className="flex min-h-0 flex-1 items-center justify-center overflow-hidden"
        onClick={handleStageClick}
        onDoubleClick={handleStageDoubleClick}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={stopDragging}
        onPointerCancel={stopDragging}
        style={{
          cursor:
            scale > MIN_SCALE ? (isDragging ? "grabbing" : "grab") : "default",
          touchAction: "none",
        }}
      >
        <Image
          src={src}
          alt={alt || "图片"}
          width={1600}
          height={1200}
          unoptimized
          className={cn(
            "object-contain transition-transform duration-200 will-change-transform",
            !imageReady && "opacity-0",
          )}
          onLoad={(e) => {
            setImageSize({
              width: e.currentTarget.naturalWidth,
              height: e.currentTarget.naturalHeight,
            });
          }}
          style={{
            width: imageReady ? imageSize.width : undefined,
            height: imageReady ? imageSize.height : undefined,
            transform: `translate(${position.x}px, ${position.y}px) scale(${renderedScale})`,
            userSelect: "none",
          }}
          draggable={false}
        />
      </div>

      <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 flex justify-center px-4 pb-[calc(env(safe-area-inset-bottom)+1rem)]">
        <div className="pointer-events-auto flex max-w-full items-center gap-1.5 rounded-full bg-black/70 px-3 py-2 text-white backdrop-blur-md sm:gap-2 sm:px-4">
          <button
            onClick={() => updateScale(-SCALE_STEP)}
            className="rounded-full p-2 transition-colors hover:bg-white/20"
            aria-label="缩小"
          >
            <ZoomOut className="h-5 w-5" />
          </button>

          <span className="min-w-14 text-center text-sm tabular-nums">
            {Math.round(scale * 100)}%
          </span>

          <button
            onClick={() => updateScale(SCALE_STEP)}
            className="rounded-full p-2 transition-colors hover:bg-white/20"
            aria-label="放大"
          >
            <ZoomIn className="h-5 w-5" />
          </button>

          <div className="mx-1 h-6 w-px bg-white/30" />

          <button
            onClick={handleReset}
            className="rounded-full p-2 transition-colors hover:bg-white/20"
            aria-label="重置"
          >
            <RotateCcw className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  );
};

export const ImageLightbox: React.FC<ImageLightboxProps> = ({
  open,
  onOpenChange,
  src,
  alt,
  className,
}) => {
  const imageName = alt || "图片";

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
    >
      <DialogContent
        fullscreen
        className={cn("bg-black", className)}
        showClose={false}
      >
        <DialogTitle className="sr-only">{imageName}</DialogTitle>
        <div className="relative h-full w-full overflow-hidden pt-[env(safe-area-inset-top)] pr-[env(safe-area-inset-right)] pb-[env(safe-area-inset-bottom)] pl-[env(safe-area-inset-left)]">
          <ImageViewer
            src={src}
            alt={imageName}
            isActive={open}
            onRequestClose={() => onOpenChange(false)}
          />
          <CloseButton
            onClick={() => onOpenChange(false)}
            className="absolute top-4 right-4 z-20 bg-black/60 backdrop-blur-md md:top-6 md:right-6"
            size="lg"
          />
        </div>
      </DialogContent>
    </Dialog>
  );
};
