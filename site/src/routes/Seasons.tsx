import { SeasonTile } from "../components/SeasonTile";
import { SCHEDULE } from "../data/schedule";

export default function Seasons() {
  const ordered = [...SCHEDULE].sort((a, b) => b.year - a.year);
  return (
    <main className="mx-auto max-w-6xl p-6">
      <header className="mb-6 border-b border-f1-border pb-3">
        <p className="text-xs uppercase tracking-widest text-f1-muted">F1 Dashboard</p>
        <h1 className="text-2xl font-bold">Seasons</h1>
      </header>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {ordered.map((s) => (
          <SeasonTile key={s.year} season={s} />
        ))}
      </div>
    </main>
  );
}
