import { describe, it, expect, vi, afterEach } from "vitest";
import { loadManifest } from "../../src/lib/data";

const validFixture = {
  schema_version: "1.0.0",
  generated_at: "2026-04-17T00:00:00Z",
  source_commit: null,
  race: {
    slug: "australia-2026",
    name: "Australian Grand Prix",
    location: "Melbourne",
    country: "Australia",
    season: 2026,
    round: 1,
    date: "2026-03-08",
    sessions: [
      { key: "R", name: "Race", path: "2026/.../Race/", start_utc: "2026-03-08T04:00:00Z" },
    ],
    drivers: [
      {
        racing_number: "1",
        tla: "VER",
        full_name: "Max Verstappen",
        team_name: "Red Bull Racing",
        team_color: "#4781D7",
        grid_position: 2,
        sets: [],
      },
    ],
  },
};

afterEach(() => vi.restoreAllMocks());

describe("loadManifest", () => {
  it("parses and validates a well-formed payload", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => validFixture,
    }));
    const m = await loadManifest("/data/australia-2026.json");
    expect(m.race.drivers[0].tla).toBe("VER");
  });

  it("throws a descriptive error on HTTP failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 404 }));
    await expect(loadManifest("/missing.json")).rejects.toThrow(/404/);
  });

  it("throws when schema_version does not match", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ...validFixture, schema_version: "2.0.0" }),
    }));
    await expect(loadManifest("/data/x.json")).rejects.toThrow(/schema_version/);
  });

  it("rejects payloads that fail Zod validation", async () => {
    const bad = { ...validFixture, race: { ...validFixture.race, drivers: [{ tla: "X" }] } };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => bad }));
    await expect(loadManifest("/data/x.json")).rejects.toThrow();
  });
});
