export default function Legal() {
  return (
    <main className="mx-auto max-w-3xl px-5 py-8 text-f1-text">
      <h1 className="mb-6 text-2xl font-bold tracking-wide">Legal</h1>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold">Trademark disclaimer</h2>
        <p className="text-sm text-f1-muted">
          "F1", "FORMULA 1", "FIA", the Formula 1 logo, all team names, driver names, and
          associated logos or marks are trademarks of their respective owners. This site makes
          no claim to any such marks.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold">No affiliation</h2>
        <p className="text-sm text-f1-muted">
          This site is not affiliated with, endorsed by, sponsored by, or otherwise connected
          to Formula 1, the Fédération Internationale de l'Automobile (FIA), Formula One
          Management, or any Formula 1 team or driver.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold">Purpose</h2>
        <p className="text-sm text-f1-muted">
          This is a non-commercial, educational fan project for exploring Formula 1 timing
          data. It is provided as-is with no warranty of any kind.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold">Data source</h2>
        <p className="text-sm text-f1-muted">
          Timing data is sourced from{" "}
          <a
            href="https://livetiming.formula1.com/static/"
            className="text-f1-text underline hover:text-compound-soft"
            target="_blank"
            rel="noopener noreferrer"
          >
            livetiming.formula1.com/static/
          </a>
          . All rights to the underlying data belong to its owners.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold">Code</h2>
        <p className="text-sm text-f1-muted">
          The source code of this site is open source under the MIT license:{" "}
          <a
            href="https://github.com/driversti/formula1"
            className="text-f1-text underline hover:text-compound-soft"
            target="_blank"
            rel="noopener noreferrer"
          >
            github.com/driversti/formula1
          </a>
          .
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold">Contact and takedown requests</h2>
        <p className="text-sm text-f1-muted">
          For takedown requests or questions about this site, contact{" "}
          <a
            href="mailto:copyright@seniorjava.dev"
            className="text-f1-text underline hover:text-compound-soft"
          >
            copyright@seniorjava.dev
          </a>
          .
        </p>
      </section>
    </main>
  );
}
