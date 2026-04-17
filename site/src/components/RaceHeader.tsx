type Race = {
  slug: string;
  name: string;
  location: string;
  country: string;
  season: number;
  round: number;
  date: string;
  sessions: Array<{ key: string; name: string; path: string; start_utc: string }>;
  drivers: Array<unknown>;
};

export function RaceHeader({ race }: { race: Race }) {
  return (
    <header className="mb-6 flex items-baseline justify-between border-b border-f1-border pb-3">
      <div>
        <p className="text-xs uppercase tracking-widest text-f1-muted">Round {race.round} · {race.season}</p>
        <h1 className="text-2xl font-bold">{race.name}</h1>
        <p className="text-sm text-f1-muted">{race.location}, {race.country} · {race.date}</p>
      </div>
      <p className="font-mono text-xs text-f1-muted">Pre-race tyre inventory</p>
    </header>
  );
}
