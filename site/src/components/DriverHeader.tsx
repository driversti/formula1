import { Link } from "react-router-dom";

type Driver = {
  racing_number: string;
  tla: string;
  full_name: string;
  team_name: string;
  team_color: string;
  grid_position: number | null;
};

export function DriverHeader({ driver }: { driver: Driver }) {
  return (
    <section
      style={{ borderLeftColor: driver.team_color }}
      className="mb-6 flex items-baseline justify-between rounded-md border-l-4 bg-f1-panel p-4"
    >
      <div>
        <p className="text-xs uppercase tracking-widest text-f1-muted">#{driver.racing_number}</p>
        <h2 className="text-2xl font-bold">{driver.full_name}</h2>
        <p className="text-sm text-f1-muted">{driver.team_name}</p>
      </div>
      <div className="text-right">
        {driver.grid_position != null ? (
          <p className="font-mono text-lg">P{driver.grid_position}</p>
        ) : (
          <p className="font-mono text-lg text-f1-muted">—</p>
        )}
        <Link to="/" className="text-xs text-f1-muted underline">
          ← back to grid
        </Link>
      </div>
    </section>
  );
}
