// AUTO-GENERATED from precompute/out/schema.json — do not edit by hand.
// Regenerate with: npm run gen:zod

import { z } from "zod"

export const ManifestSchema = z.object({ "schema_version": z.string().default("1.0.0"), "generated_at": z.string(), "source_commit": z.union([z.string(), z.null()]).default(null), "race": z.any() }).strict().describe("Top-level JSON artifact.")

export type Manifest = import("zod").z.infer<typeof ManifestSchema>;
