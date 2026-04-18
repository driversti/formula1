import { useEffect, useState } from "react";
import { Navigate, useParams } from "react-router-dom";
import { RaceHeader } from "../components/RaceHeader";
import { SessionTabs } from "../components/SessionTabs";
import { StrategyChart } from "../components/StrategyChart";
import { loadManifest } from "../lib/data";
import type { Manifest } from "../lib/schemas";
import { isFeatured } from "../config";
import { SCHEDULE } from "../data/schedule";
import NotFound from "./NotFound";

export default function Strategy() {
  const { slug = "" } = useParams<{ slug: string }>();
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<"R" | "S">("R");

  const known = SCHEDULE.some((s) => s.races.some((r) => r.slug === slug));

  useEffect(() => {
    if (!isFeatured(slug)) return;
    loadManifest(`${import.meta.env.BASE_URL}data/${slug}.json`)
      .then(setManifest)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)));
  }, [slug]);

  if (!known) return <NotFound />;
  if (!isFeatured(slug)) return <Navigate to={`/race/${slug}`} replace />;

  if (error) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-compound-soft">Data unavailable: {error}</p>
      </main>
    );
  }
  if (!manifest) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-f1-muted">Loading…</p>
      </main>
    );
  }

  const drivers = manifest.race.drivers as Parameters<typeof StrategyChart>[0]["drivers"];
  const hasSprint = drivers.some((d) => d.sprint_stints.length > 0);
  const hasRace   = drivers.some((d) => d.race_stints.length > 0);

  if (!hasRace && !hasSprint) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <RaceHeader race={manifest.race} />
        <p className="mt-4 rounded-md border border-f1-border bg-f1-panel p-4 text-sm text-f1-muted">
          Race not run yet — strategy will appear after the chequered flag.
        </p>
      </main>
    );
  }

  const active: "R" | "S" = hasRace ? session : "S";
  const stints = drivers.flatMap((d) => (active === "R" ? d.race_stints : d.sprint_stints));
  const totalLaps = stints.length > 0 ? Math.max(...stints.map((s) => s.end_lap)) : 0;

  return (
    <main className="mx-auto max-w-6xl p-6">
      <RaceHeader race={manifest.race} />
      {hasSprint && hasRace && (
        <SessionTabs value={session} onChange={setSession} />
      )}
      <StrategyChart
        drivers={drivers}
        sessionKey={active}
        totalLaps={totalLaps}
        statusBands={active === "R" ? manifest.race.race_status_bands : manifest.race.sprint_status_bands}
      />
    </main>
  );
}
