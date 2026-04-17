import { useLocation } from "react-router-dom";
import { SCHEDULE, type Season } from "../data/schedule";

export type Crumb = {
  label: string;
  href: string;
  current: boolean;
};

/** Shorten "X Grand Prix" → "X GP"; leave other names verbatim. */
function raceLabel(name: string): string {
  return name.endsWith("Grand Prix") ? name.slice(0, -"Grand Prix".length).trimEnd() + " GP" : name;
}

function homeOnly(): Crumb[] {
  return [{ label: "Home", href: "/", current: true }];
}

export function buildTrail(pathname: string, schedule: Season[]): Crumb[] {
  if (pathname === "/" || pathname === "") return homeOnly();

  const seasonMatch = pathname.match(/^\/season\/(\d+)\/?$/);
  if (seasonMatch) {
    const year = Number(seasonMatch[1]);
    const season = schedule.find((s) => s.year === year);
    if (!season) return homeOnly();
    return [
      { label: "Home", href: "/", current: false },
      { label: String(year), href: `/season/${year}`, current: true },
    ];
  }

  const raceMatch = pathname.match(/^\/race\/([^/]+)(?:\/(tyres|driver\/([A-Za-z0-9]+)))?\/?$/);
  if (raceMatch) {
    const slug = raceMatch[1];
    const leaf = raceMatch[2];
    const season = schedule.find((s) => s.races.some((r) => r.slug === slug));
    const race = season?.races.find((r) => r.slug === slug);
    if (!season || !race) return homeOnly();

    const year = season.year;
    const trail: Crumb[] = [
      { label: "Home", href: "/", current: false },
      { label: String(year), href: `/season/${year}`, current: false },
      {
        label: raceLabel(race.name),
        href: `/race/${slug}`,
        current: !leaf,
      },
    ];

    if (leaf === "tyres") {
      trail.push({ label: "Tyres", href: `/race/${slug}/tyres`, current: true });
    } else if (leaf?.startsWith("driver/")) {
      const tla = leaf.slice("driver/".length).toUpperCase();
      trail.push({
        label: `Driver · ${tla}`,
        href: `/race/${slug}/driver/${tla}`,
        current: true,
      });
    }
    return trail;
  }

  return homeOnly();
}

export function useBreadcrumbs(): Crumb[] {
  const { pathname } = useLocation();
  return buildTrail(pathname, SCHEDULE);
}
