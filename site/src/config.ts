/**
 * The race currently built end-to-end. Every other race in the catalogue
 * renders as a "Coming soon" tile until a manifest is produced.
 *
 * Keep in sync with the Python defaults in `seasons/fetch_race.py` and
 * `precompute/src/f1/build.py`.
 */
export const FEATURED_RACE_SLUG = "australia-2026";

export function isFeatured(slug: string): boolean {
  return slug === FEATURED_RACE_SLUG;
}
