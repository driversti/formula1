import { TyreSet } from "./TyreSet";

type SessionKey = "FP1" | "FP2" | "FP3" | "Q" | "R";
type Compound = "SOFT" | "MEDIUM" | "HARD" | "INTERMEDIATE" | "WET";

type Set = {
  set_id: string;
  compound: Compound;
  laps: number;
  new_at_first_use: boolean;
  first_seen_session: SessionKey;
  last_seen_session: SessionKey;
};

type Driver = {
  sets: readonly Set[];
};

const COMPOUND_ORDER: Compound[] = ["HARD", "MEDIUM", "SOFT", "INTERMEDIATE", "WET"];

export function InventoryView({ driver }: { driver: Driver }) {
  if (driver.sets.length === 0) {
    return <p className="text-f1-muted">No tyre data available.</p>;
  }
  const grouped: Record<Compound, Set[]> = {
    HARD: [],
    MEDIUM: [],
    SOFT: [],
    INTERMEDIATE: [],
    WET: [],
  };
  for (const s of driver.sets) grouped[s.compound].push(s);

  return (
    <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {COMPOUND_ORDER.filter((c) => grouped[c].length > 0).map((c) => (
        <div key={c}>
          <h3 className="mb-2 text-xs font-mono uppercase tracking-widest text-f1-muted">{c}</h3>
          <div className="flex flex-col gap-2">
            {grouped[c].map((s) => (
              <TyreSet key={s.set_id} set={s} />
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}
