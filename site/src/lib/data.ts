import { z } from "zod";
import { ManifestSchema, type Manifest } from "./schemas";

export const EXPECTED_SCHEMA_VERSION = "1.0.0";

// Full nested schemas to compensate for the auto-generated ManifestSchema
// using z.any() for the race field. Defined here to provide strict validation
// without modifying the auto-generated schemas.ts.
const SessionKeySchema = z.enum(["FP1", "FP2", "FP3", "SQ", "S", "Q", "R"]);

const TyreSetSchema = z.object({
  set_id: z.string(),
  compound: z.enum(["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"]),
  laps: z.number().int().min(0),
  new_at_first_use: z.boolean(),
  first_seen_session: SessionKeySchema,
  last_seen_session: SessionKeySchema,
});

const RaceStintSchema = z.object({
  stint_idx: z.number().int().min(0),
  compound: z.enum(["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"]),
  start_lap: z.number().int().min(1),
  end_lap: z.number().int().min(1),
  laps: z.number().int().min(1),
  new: z.boolean(),
});

const DriverInventorySchema = z.object({
  racing_number: z.string().min(1),
  tla: z.string().min(3).max(3),
  full_name: z.string(),
  team_name: z.string(),
  team_color: z.string().regex(/^#[0-9A-Fa-f]{6}$/),
  grid_position: z.union([z.number().int().min(1).max(22), z.null()]).default(null),
  sets: z.array(TyreSetSchema),
  race_stints: z.array(RaceStintSchema).default([]),
  sprint_stints: z.array(RaceStintSchema).default([]),
  final_position: z.union([z.number().int().min(1).max(22), z.null()]).default(null),
  dnf_at_lap: z.union([z.number().int().min(1), z.null()]).default(null),
  sprint_final_position: z.union([z.number().int().min(1).max(22), z.null()]).default(null),
  sprint_dnf_at_lap: z.union([z.number().int().min(1), z.null()]).default(null),
});

const RaceSchema = z.object({
  slug: z.string(),
  name: z.string(),
  location: z.string(),
  country: z.string(),
  season: z.number().int(),
  round: z.number().int(),
  date: z.string(),
  sessions: z.array(
    z.object({
      key: SessionKeySchema,
      name: z.string(),
      path: z.string(),
      start_utc: z.string(),
    }),
  ),
  drivers: z.array(DriverInventorySchema),
});

const FullManifestSchema = ManifestSchema.extend({ race: RaceSchema });

/**
 * Fetch and validate a Manifest JSON artifact.
 * @throws Error with a context-rich message on HTTP, schema, or version failures.
 */
export async function loadManifest(url: string): Promise<Manifest> {
  const resp = await fetch(url, { cache: "no-cache" });
  if (!resp.ok) {
    throw new Error(`failed to load ${url}: HTTP ${resp.status}`);
  }
  const raw: unknown = await resp.json();
  const parsed = FullManifestSchema.parse(raw);
  if (parsed.schema_version !== EXPECTED_SCHEMA_VERSION) {
    throw new Error(
      `schema_version mismatch: got ${parsed.schema_version}, expected ${EXPECTED_SCHEMA_VERSION}. Rebuild the data artifact.`,
    );
  }
  return parsed;
}
