import { Link } from "react-router-dom";
import { Breadcrumbs } from "./Breadcrumbs";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-f1-border bg-f1-panel px-5 py-3">
      <Link to="/" className="flex shrink-0 items-center gap-2 text-sm font-bold tracking-wide">
        <span
          aria-hidden="true"
          className="inline-block h-2.5 w-2.5 rounded-sm bg-compound-soft"
        />
        F1 DASHBOARD
      </Link>
      <Breadcrumbs />
    </header>
  );
}
