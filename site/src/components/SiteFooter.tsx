import { Link } from "react-router-dom";

export function SiteFooter() {
  return (
    <footer className="mt-8 border-t border-f1-border bg-f1-panel px-5 py-3 text-xs text-f1-muted">
      <p>
        Unofficial fan site. All trademarks belong to their respective owners.{" "}
        <Link to="/legal" className="text-f1-text underline hover:text-compound-soft">
          Read more
        </Link>
      </p>
    </footer>
  );
}
