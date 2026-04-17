import { Link } from "react-router-dom";

export function AnalyticsTile({
  title,
  description,
  to,
}: {
  title: string;
  description: string;
  to: string;
}) {
  return (
    <Link
      to={to}
      className="block rounded-md border border-f1-border bg-f1-panel p-4 transition hover:bg-f1-border focus-visible:outline-2 focus-visible:outline-compound-medium"
    >
      <h3 className="text-base font-bold">{title}</h3>
      <p className="mt-1 text-xs text-f1-muted">{description}</p>
    </Link>
  );
}
