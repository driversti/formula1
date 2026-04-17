import { useParams } from "react-router-dom";
import { RaceTile } from "../components/RaceTile";
import { SCHEDULE } from "../data/schedule";
import NotFound from "./NotFound";

export default function Season() {
  const { year } = useParams<{ year: string }>();
  const parsed = Number(year);
  const season = SCHEDULE.find((s) => s.year === parsed);
  if (!season) return <NotFound />;

  return (
    <main className="mx-auto max-w-6xl p-6">
      <header className="mb-6 border-b border-f1-border pb-3">
        <p className="text-xs uppercase tracking-widest text-f1-muted">
          {season.raceCount} races ·
          {" "}Drivers: {season.driversChampion ?? "TBD"} ·
          {" "}Constructors: {season.constructorsChampion ?? "TBD"}
        </p>
        <h1 className="text-2xl font-bold">{season.year} Season</h1>
      </header>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
        {season.races.map((r) => (
          <RaceTile key={r.slug} race={r} />
        ))}
      </div>
    </main>
  );
}
