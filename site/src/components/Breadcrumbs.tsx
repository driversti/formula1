import { Link } from "react-router-dom";
import { useBreadcrumbs } from "../lib/breadcrumbs";

export function Breadcrumbs() {
  const trail = useBreadcrumbs();

  return (
    <nav
      aria-label="Breadcrumb"
      className="min-w-0 overflow-x-auto whitespace-nowrap text-sm text-f1-muted [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
    >
      <ol className="flex items-center gap-1">
        {trail.map((crumb, i) => (
          <li key={crumb.href} className="flex items-center gap-1">
            {i > 0 && (
              <span aria-hidden="true" className="text-f1-border">
                ›
              </span>
            )}
            {crumb.current ? (
              <span
                aria-current="page"
                className="rounded px-1.5 py-0.5 text-compound-medium"
              >
                {crumb.label}
              </span>
            ) : (
              <Link
                to={crumb.href}
                className="rounded px-1.5 py-0.5 text-f1-text hover:bg-white/5"
              >
                {crumb.label}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
