import { Link } from "react-router-dom";
import { TyreDot } from "./TyreDot";

type Set = {
  set_id: string;
  compound: "SOFT" | "MEDIUM" | "HARD" | "INTERMEDIATE" | "WET";
  laps: number;
  new_at_first_use: boolean;
  first_seen_session: "FP1" | "FP2" | "FP3" | "Q" | "R";
  last_seen_session: "FP1" | "FP2" | "FP3" | "Q" | "R";
};

type Driver = {
  racing_number: string;
  tla: string;
  full_name: string;
  team_name: string;
  team_color: string;
  grid_position: number | null;
  sets: readonly Set[];
};

export function DriverCard({ driver }: { driver: Driver }) {
  return (
    <Link
      to={`/driver/${driver.tla}`}
      style={{ borderLeftColor: driver.team_color }}
      className="block rounded-md border-l-4 border-transparent bg-f1-panel p-3 transition hover:bg-f1-border focus-visible:outline-2 focus-visible:outline-compound-medium"
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-lg font-bold">{driver.tla}</span>
        {driver.grid_position != null && (
          <span className="font-mono text-xs text-f1-muted">P{driver.grid_position}</span>
        )}
      </div>
      <p className="truncate text-xs text-f1-muted">{driver.team_name}</p>
      <div className="mt-2 flex flex-wrap gap-1">
        {driver.sets.map((s) => (
          <span key={s.set_id} data-testid="tyre-dot">
            <TyreDot compound={s.compound} aria-label={`${s.compound} ${s.laps} laps`} />
          </span>
        ))}
      </div>
    </Link>
  );
}
