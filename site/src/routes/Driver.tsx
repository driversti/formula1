import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { DriverHeader } from "../components/DriverHeader";
import { InventoryView } from "../components/InventoryView";
import { RaceHeader } from "../components/RaceHeader";
import { loadManifest } from "../lib/data";
import type { Manifest } from "../lib/schemas";
import NotFound from "./NotFound";

export default function Driver() {
  const { tla } = useParams<{ tla: string }>();
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadManifest(`${import.meta.env.BASE_URL}data/australia-2026.json`)
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

  const driver = manifest.race.drivers.find((d: { tla: string }) => d.tla === tla);
  if (!driver) return <NotFound />;

  return (
    <main className="mx-auto max-w-6xl p-6">
      <RaceHeader race={manifest.race} />
      <DriverHeader driver={driver} />
      <InventoryView driver={driver} />
    </main>
  );
}
