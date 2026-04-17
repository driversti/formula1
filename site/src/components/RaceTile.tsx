import { Link } from "react-router-dom";
import { isFeatured } from "../config";
import type { Race } from "../data/schedule";

export function RaceTile({ race }: { race: Race }) {
  const featured = isFeatured(race.slug);
  const shared =
    "block rounded-md border border-f1-border bg-f1-panel p-3 transition";
  const enabled = " hover:bg-f1-border focus-visible:outline-2 focus-visible:outline-compound-medium";
  const disabled = " opacity-60 cursor-not-allowed";

  const body = (
    <>
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-xs text-f1-muted">Round {race.round}</span>
        {!featured && (
          <span className="rounded bg-f1-border px-2 py-0.5 text-[10px] uppercase tracking-widest text-f1-muted">
            Coming soon
          </span>
        )}
      </div>
      <h2 className="mt-1 text-base font-bold">{race.name}</h2>
      <p className="truncate text-xs text-f1-muted">
        {race.countryName} · {race.circuitShortName}
      </p>
      <p className="mt-1 font-mono text-[11px] text-f1-muted">
        {race.startDate} → {race.endDate}
      </p>
    </>
  );

  if (!featured) {
    return (
      <div aria-disabled="true" className={shared + disabled}>
        {body}
      </div>
    );
  }

  return (
    <Link to={`/race/${race.slug}`} className={shared + enabled}>
      {body}
    </Link>
  );
}
