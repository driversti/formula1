import { useEffect, useState } from "react";
import { RaceHeader } from "../components/RaceHeader";
import { DriverGrid } from "../components/DriverGrid";
import { loadManifest } from "../lib/data";
import type { Manifest } from "../lib/schemas";

export default function Home() {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadManifest("/data/australia-2026.json")
      .then(setManifest)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

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
      <DriverGrid drivers={manifest.race.drivers} />
    </main>
  );
}
