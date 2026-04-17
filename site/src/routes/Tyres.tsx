import { useEffect, useState } from "react";
import { Navigate, useParams } from "react-router-dom";
import { RaceHeader } from "../components/RaceHeader";
import { DriverGrid } from "../components/DriverGrid";
import { loadManifest } from "../lib/data";
import type { Manifest } from "../lib/schemas";
import { isFeatured } from "../config";
import { SCHEDULE } from "../data/schedule";
import NotFound from "./NotFound";

export default function Tyres() {
  const { slug = "" } = useParams<{ slug: string }>();
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <main className="mx-auto max-w-6xl p-6">
      <RaceHeader race={manifest.race} />
      <DriverGrid drivers={manifest.race.drivers} raceSlug={slug} />
    </main>
  );
}
