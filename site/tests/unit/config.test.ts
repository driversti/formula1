import { describe, it, expect } from "vitest";
import { FEATURED_RACE_SLUGS, isFeatured } from "../../src/config";

describe("featured-race config", () => {
  it("lists australia-2026 and china-2026 as the featured slugs", () => {
    expect(FEATURED_RACE_SLUGS).toEqual(["australia-2026", "china-2026"]);
  });

  it("isFeatured returns true for each featured slug", () => {
    expect(isFeatured("australia-2026")).toBe(true);
    expect(isFeatured("china-2026")).toBe(true);
  });

  it("isFeatured returns false for slugs not in the list", () => {
    expect(isFeatured("japan-2026")).toBe(false);
    expect(isFeatured("")).toBe(false);
  });
});
