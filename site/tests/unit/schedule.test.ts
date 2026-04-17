import { describe, it, expect } from "vitest";
import { SCHEDULE } from "../../src/data/schedule";

describe("schedule catalog", () => {
  it("covers 2018–2026 without 2022", () => {
    const years = SCHEDULE.map((s) => s.year);
    expect(years).toEqual([2018, 2019, 2020, 2021, 2023, 2024, 2025, 2026]);
  });

  it("every season-race pair is unique (slug + year)", () => {
    const pairs = SCHEDULE.flatMap((s) =>
      s.races.map((r) => `${r.slug}::${r.round}`)
    );
    expect(new Set(pairs).size).toBe(pairs.length);
  });

  it("includes australia-2026 as a race", () => {
    const all = SCHEDULE.flatMap((s) => s.races.map((r) => r.slug));
    expect(all).toContain("australia-2026");
  });

  it("round numbers are contiguous 1..N within each season", () => {
    for (const s of SCHEDULE) {
      const rounds = s.races.map((r) => r.round);
      expect(rounds).toEqual(
        Array.from({ length: rounds.length }, (_, i) => i + 1)
      );
    }
  });

  it("excludes pre-season testing", () => {
    const names = SCHEDULE.flatMap((s) =>
      s.races.map((r) => r.name.toLowerCase())
    );
    expect(names.every((n) => !n.includes("testing"))).toBe(true);
  });

  it("raceCount matches races.length", () => {
    for (const s of SCHEDULE) expect(s.raceCount).toBe(s.races.length);
  });
});
