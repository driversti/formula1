/**
 * Races built end-to-end (manifest + UI analytics). Every other race in
 * the catalogue renders as a "Coming soon" tile until a manifest is
 * produced.
 *
 * Keep in sync with:
 *   - FEATURED_RACES in seasons/fetch_race.py
 *   - FEATURED_RACES in precompute/src/f1/build.py
 *   - FEATURED_SLUGS in the root Makefile
 */
export const FEATURED_RACE_SLUGS: readonly string[] = [
  "australia-2026",
  "china-2026",
  "japan-2026",
] as const;

export function isFeatured(slug: string): boolean {
  return FEATURED_RACE_SLUGS.includes(slug);
}
