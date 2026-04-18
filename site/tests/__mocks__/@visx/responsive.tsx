// Mock for @visx/responsive in jsdom test environment.
// ParentSize normally uses ResizeObserver + requestAnimationFrame which don't
// work in jsdom. This stub renders children immediately with width=800 so that
// components guarded by `if (width === 0) return null` still render in tests.
import React from "react";

type ParentSizeProps = {
  children: (args: { width: number; height: number }) => React.ReactNode;
};

export function ParentSize({ children }: ParentSizeProps) {
  return <>{children({ width: 800, height: 400 })}</>;
}
