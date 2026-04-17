import { DriverCard } from "./DriverCard";

type Drivers = React.ComponentProps<typeof DriverCard>["driver"][];

export function DriverGrid({ drivers }: { drivers: Drivers }) {
  const sorted = [...drivers].sort((a, b) => {
    const ag = a.grid_position ?? 99;
    const bg = b.grid_position ?? 99;
    if (ag !== bg) return ag - bg;
    return a.tla.localeCompare(b.tla);
  });
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
      {sorted.map((d) => (
        <DriverCard key={d.racing_number} driver={d} />
      ))}
    </div>
  );
}
