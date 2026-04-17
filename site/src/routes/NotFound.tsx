import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <main className="mx-auto max-w-6xl p-6">
      <h1 className="text-3xl font-bold">404</h1>
      <p className="mt-2 text-f1-muted">That page does not exist.</p>
      <Link to="/" className="mt-4 inline-block text-compound-medium underline">
        Back to grid
      </Link>
    </main>
  );
}
