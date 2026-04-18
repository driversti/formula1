import "@testing-library/jest-dom/vitest";

// jsdom does not ship ResizeObserver; @visx/responsive (ParentSize) requires it.
// Provide a no-op stub so components that use ParentSize can render in unit tests.
// The stub calls the callback once with an empty entry list so the initial render
// is triggered, but width stays 0 – components guard with `if (width === 0) return null`.
if (typeof window !== "undefined" && !window.ResizeObserver) {
  window.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
