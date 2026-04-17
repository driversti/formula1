import { useParams } from "react-router-dom";
import { AnalyticsTile } from "../components/AnalyticsTile";
import { SCHEDULE } from "../data/schedule";
import { isFeatured } from "../config";
import NotFound from "./NotFound";

export default function Race() {
  const { slug = "" } = useParams<{ slug: string }>();
  const season = SCHEDULE.find((s) => s.races.some((r) => r.slug === slug));
  const race = season?.races.find((r) => r.slug === slug);
  if (!season || !race) return <NotFound />;

  const featured = isFeatured(slug);

  return (
    <main className="mx-auto max-w-6xl p-6">
      <header className="mb-6 flex items-baseline justify-between border-b border-f1-border pb-3">
        <div>
          <p className="text-xs uppercase tracking-widest text-f1-muted">
            Round {race.round} · {season.year}
          </p>
          <h1 className="text-2xl font-bold">{race.name}</h1>
          <p className="text-sm text-f1-muted">
            {race.countryName} · {race.circuitShortName} · {race.startDate} → {race.endDate}
          </p>
        </div>
      </header>

      {featured ? (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-f1-muted">
            Analytics
          </h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
            <AnalyticsTile
              title="Tyre Inventory"
              description="Pre-race tyre allocation for all drivers."
              to={`/race/${slug}/tyres`}
            />
          </div>
        </section>
      ) : (
        <p className="rounded-md border border-f1-border bg-f1-panel p-4 text-sm text-f1-muted">
          No analytics available yet for this race — data will appear when it becomes the featured weekend.
        </p>
      )}
    </main>
  );
}
