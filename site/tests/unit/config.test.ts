import { describe, it, expect } from "vitest";
import { FEATURED_RACE_SLUG, isFeatured } from "../../src/config";

describe("featured-race config", () => {
  it("exposes australia-2026 as the featured slug", () => {
    expect(FEATURED_RACE_SLUG).toBe("australia-2026");
  });

  it("isFeatured returns true only for the featured slug", () => {
    expect(isFeatured("australia-2026")).toBe(true);
    expect(isFeatured("japan-2026")).toBe(false);
    expect(isFeatured("")).toBe(false);
  });
});
