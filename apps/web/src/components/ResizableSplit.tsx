import { useCallback, useRef, useState, ReactNode } from "react";
import { cn } from "../lib/utils";

interface ResizableSplitProps {
  left: ReactNode;
  right: ReactNode;
  defaultLeftPct?: number; // 0-100
  minLeftPct?: number;
  maxLeftPct?: number;
}

export default function ResizableSplit({
  left,
  right,
  defaultLeftPct = 38,
  minLeftPct = 24,
  maxLeftPct = 60,
}: ResizableSplitProps) {
  const [leftPct, setLeftPct] = useState(defaultLeftPct);
  const [dragging, setDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    e.preventDefault();
    setDragging(true);
    (e.target as Element).setPointerCapture(e.pointerId);
  }, []);

  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!dragging || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      setLeftPct(Math.min(maxLeftPct, Math.max(minLeftPct, pct)));
    },
    [dragging, minLeftPct, maxLeftPct]
  );

  const onPointerUp = useCallback(() => setDragging(false), []);

  return (
    <div
      ref={containerRef}
      className="flex h-full w-full min-h-0"
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerLeave={onPointerUp}
    >
      <div style={{ width: `${leftPct}%` }} className="h-full min-w-0 border-r border-[var(--hairline)]">
        {left}
      </div>

      <div
        onPointerDown={onPointerDown}
        className={cn(
          "w-1.5 shrink-0 h-full cursor-col-resize relative group",
          dragging ? "bg-[var(--thread)]/30" : "bg-transparent"
        )}
      >
        <div
          className={cn(
            "absolute inset-y-0 left-1/2 -translate-x-1/2 w-px transition-colors",
            dragging ? "bg-[var(--thread)]" : "bg-[var(--hairline)] group-hover:bg-[var(--hairline-strong)]"
          )}
        />
      </div>

      <div style={{ width: `${100 - leftPct}%` }} className="h-full min-w-0">
        {right}
      </div>
    </div>
  );
}
