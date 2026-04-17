import { Link } from "react-router-dom";
import type { Season } from "../data/schedule";

export function SeasonTile({ season }: { season: Season }) {
  const drivers = season.driversChampion ?? "TBD";
  const constructors = season.constructorsChampion ?? "TBD";
  return (
    <Link
      to={`/season/${season.year}`}
      className="block rounded-md border border-f1-border bg-f1-panel p-4 transition hover:bg-f1-border focus-visible:outline-2 focus-visible:outline-compound-medium"
    >
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-2xl font-bold">{season.year}</span>
        <span className="font-mono text-xs text-f1-muted">{season.raceCount} races</span>
      </div>
      <dl className="mt-3 space-y-1 text-xs text-f1-muted">
        <div className="flex justify-between gap-2">
          <dt>Drivers' champion</dt>
          <dd className="text-right text-f1-fg">{drivers}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt>Constructors' champion</dt>
          <dd className="text-right text-f1-fg">{constructors}</dd>
        </div>
      </dl>
    </Link>
  );
}
