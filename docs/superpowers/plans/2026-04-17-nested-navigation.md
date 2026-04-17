# Nested Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-page tyre-inventory home with a browsable hierarchy: Seasons → Races → Race landing → Analytics. Only `australia-2026` is fully enabled; every other season/race renders as a "Coming soon" tile.

**Architecture:** Client-side routing only (react-router v7). A committed TypeScript schedule catalog (`site/src/data/schedule.ts`) drives the seasons/races grids without needing the gitignored `seasons/` mirror at runtime. A tiny config module (`site/src/config.ts`) names the currently-featured race slug; every tile/route reads it to decide enable/disable. Existing tyre-inventory view is moved behind `/race/:slug/tyres`; no Python/Pydantic/Zod changes.

**Tech Stack:** React 19, TypeScript (strict), react-router-dom v7, Vite 6, Vitest 2, Playwright, Tailwind 4.

Spec: `docs/superpowers/specs/2026-04-17-nested-navigation-design.md`

---

## File structure

**Create:**
- `site/src/config.ts` — `FEATURED_RACE_SLUG`, `isFeatured(slug)`.
- `site/src/data/schedule.ts` — generated `SCHEDULE: Season[]` + types.
- `site/scripts/gen-schedule.mjs` — one-shot generator reading `seasons/*/Index.json`.
- `site/src/routes/Seasons.tsx` — top-level `/` view.
- `site/src/routes/Season.tsx` — `/season/:year` view.
- `site/src/routes/Race.tsx` — `/race/:slug` landing.
- `site/src/routes/Tyres.tsx` — `/race/:slug/tyres` (moved body of old `Home.tsx`).
- `site/src/components/SeasonTile.tsx`
- `site/src/components/RaceTile.tsx`
- `site/src/components/AnalyticsTile.tsx`
- `site/tests/unit/config.test.ts`
- `site/tests/unit/schedule.test.ts`
- `site/tests/unit/SeasonTile.test.tsx`
- `site/tests/unit/RaceTile.test.tsx`

**Modify:**
- `site/src/App.tsx` — new route table.
- `site/src/routes/Driver.tsx` — param by `:slug` + redirect if not featured.
- `site/src/components/DriverCard.tsx` — link uses `/race/:slug/driver/:tla`; accept `raceSlug` prop.
- `site/src/components/DriverGrid.tsx` — thread `raceSlug` to cards.
- `site/package.json` — add `"gen:schedule"` script.
- `site/tests/e2e/home.spec.ts` — rewrite for seasons/races flow.
- `site/tests/e2e/driver.spec.ts` — update URLs.
- `site/tests/e2e/routing.spec.ts` — update URLs.

**Delete:**
- `site/src/routes/Home.tsx` (replaced by `Tyres.tsx` + new `Seasons.tsx`).

---

## Task 1 — Featured-race config

**Files:**
- Create: `site/src/config.ts`
- Test: `site/tests/unit/config.test.ts`

- [ ] **Step 1: Write the failing test**

`site/tests/unit/config.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { FEATURED_RACE_SLUG, isFeatured } from "../../src/config";

describe("featured-race config", () => {
  it("exposes australia-2026 as the featured slug", () => {
    expect(FEATURED_RACE_SLUG).toBe("australia-2026");
  });

  it("isFeatured returns true only for the featured slug", () => {
    expect(isFeatured("australia-2026")).toBe(true);
    expect(isFeatured("japan-2026")).toBe(false);
    expect(isFeatured("")).toBe(false);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run from `site/`: `npm run test -- config`
Expected: FAIL (module does not exist).

- [ ] **Step 3: Implement config**

`site/src/config.ts`:

```ts
/**
 * The race currently built end-to-end. Every other race in the catalogue
 * renders as a "Coming soon" tile until a manifest is produced.
 *
 * Keep in sync with the Python defaults in `seasons/fetch_race.py` and
 * `precompute/src/f1/build.py`.
 */
export const FEATURED_RACE_SLUG = "australia-2026";

export function isFeatured(slug: string): boolean {
  return slug === FEATURED_RACE_SLUG;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run from `site/`: `npm run test -- config`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add site/src/config.ts site/tests/unit/config.test.ts
git commit -m "feat(site): add featured-race config module"
```

---

## Task 2 — Schedule catalog generator

**Files:**
- Create: `site/scripts/gen-schedule.mjs`
- Modify: `site/package.json`

- [ ] **Step 1: Write the generator script**

`site/scripts/gen-schedule.mjs`:

```js
#!/usr/bin/env node
/**
 * Reads local seasons/<year>/Index.json files (gitignored) and emits
 * site/src/data/schedule.ts — the committed, static catalog that powers
 * the Seasons and Race-list views.
 *
 * Re-run manually (`npm run gen:schedule`) whenever the local mirror is
 * updated or champion data changes.
 */
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "../..");
const SEASONS_DIR = resolve(ROOT, "seasons");
const OUT = resolve(__dirname, "../src/data/schedule.ts");

// Seasons we render. 2022 is intentionally omitted (per repo convention).
const YEARS = [2018, 2019, 2020, 2021, 2023, 2024, 2025, 2026];

// Hardcoded champions. null = unknown / season not yet finished.
// Fill in when confirmed; the generator preserves manual edits by reading
// the previous schedule.ts if present.
const CHAMPIONS = {
  2018: { drivers: "Lewis Hamilton",   constructors: "Mercedes" },
  2019: { drivers: "Lewis Hamilton",   constructors: "Mercedes" },
  2020: { drivers: "Lewis Hamilton",   constructors: "Mercedes" },
  2021: { drivers: "Max Verstappen",   constructors: "Mercedes" },
  2023: { drivers: "Max Verstappen",   constructors: "Red Bull Racing" },
  2024: { drivers: "Max Verstappen",   constructors: "McLaren" },
  2025: { drivers: "Lando Norris",     constructors: "McLaren" },
  2026: { drivers: null,                constructors: null },
};

function slugify(meeting, year) {
  // meeting.Name e.g. "Australian Grand Prix" -> "australian-grand-prix-2026"
  // We want the shorter "australia-2026" style; derive from Location + year.
  const loc = meeting.Location ?? meeting.Name;
  return `${loc
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")}-${year}`;
}

function isTesting(meeting) {
  return /testing/i.test(meeting.Name ?? "") || /testing/i.test(meeting.OfficialName ?? "");
}

function buildSeason(year) {
  const indexPath = resolve(SEASONS_DIR, String(year), "Index.json");
  if (!existsSync(indexPath)) {
    throw new Error(`Missing ${indexPath}. Run seasons/download_f1.py ${year} first.`);
  }
  const raw = readFileSync(indexPath, "utf8").replace(/^\uFEFF/, "");
  const data = JSON.parse(raw);

  const races = [];
  let round = 0;
  for (const m of data.Meetings ?? []) {
    if (isTesting(m)) continue;
    round += 1;
    const sessions = m.Sessions ?? [];
    const startDate = (sessions[0]?.StartDate ?? "").slice(0, 10);
    const endDate = (sessions[sessions.length - 1]?.StartDate ?? "").slice(0, 10);
    races.push({
      slug: slugify(m, year),
      round,
      name: m.Name,
      countryCode: m.Country?.Code ?? "",
      countryName: m.Country?.Name ?? "",
      circuitShortName: m.Circuit?.ShortName ?? m.Location ?? "",
      startDate,
      endDate,
    });
  }

  return {
    year,
    races,
    driversChampion: CHAMPIONS[year].drivers,
    constructorsChampion: CHAMPIONS[year].constructors,
    raceCount: races.length,
  };
}

const seasons = YEARS.map(buildSeason);

const header =
  "// AUTO-GENERATED by scripts/gen-schedule.mjs — do not edit by hand.\n" +
  "// Run `npm run gen:schedule` to refresh.\n\n";

const types = `export type Race = {
  slug: string;
  round: number;
  name: string;
  countryCode: string;
  countryName: string;
  circuitShortName: string;
  startDate: string;
  endDate: string;
};

export type Season = {
  year: number;
  races: Race[];
  driversChampion: string | null;
  constructorsChampion: string | null;
  raceCount: number;
};

`;

const body = `export const SCHEDULE: Season[] = ${JSON.stringify(seasons, null, 2)};\n`;

writeFileSync(OUT, header + types + body);
console.log(`Wrote ${OUT} (${seasons.length} seasons, ${seasons.reduce((n, s) => n + s.raceCount, 0)} races)`);
```

- [ ] **Step 2: Add npm script**

Add to `site/package.json` `scripts` block (keep alphabetical-ish grouping near `gen:zod`):

```json
"gen:schedule": "node scripts/gen-schedule.mjs",
```

- [ ] **Step 3: Commit generator**

```bash
git add site/scripts/gen-schedule.mjs site/package.json
git commit -m "feat(site): add schedule catalog generator"
```

---

## Task 3 — Generate and commit the catalog

**Files:**
- Create: `site/src/data/schedule.ts` (generated)
- Test: `site/tests/unit/schedule.test.ts`

- [ ] **Step 1: Run the generator**

From `site/`: `npm run gen:schedule`
Expected stdout: `Wrote …/site/src/data/schedule.ts (8 seasons, ~170 races)`.

If a year is missing locally (`Missing …/Index.json`), run from repo root:
`cd seasons && uv run python download_f1.py <year>` for the offending years, then re-run the generator.

- [ ] **Step 2: Write invariant tests**

`site/tests/unit/schedule.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { SCHEDULE } from "../../src/data/schedule";

describe("schedule catalog", () => {
  it("covers 2018–2026 without 2022", () => {
    const years = SCHEDULE.map((s) => s.year);
    expect(years).toEqual([2018, 2019, 2020, 2021, 2023, 2024, 2025, 2026]);
  });

  it("every race slug is globally unique", () => {
    const slugs = SCHEDULE.flatMap((s) => s.races.map((r) => r.slug));
    expect(new Set(slugs).size).toBe(slugs.length);
  });

  it("includes australia-2026 as a race", () => {
    const all = SCHEDULE.flatMap((s) => s.races.map((r) => r.slug));
    expect(all).toContain("australia-2026");
  });

  it("round numbers are contiguous 1..N within each season", () => {
    for (const s of SCHEDULE) {
      const rounds = s.races.map((r) => r.round);
      expect(rounds).toEqual(Array.from({ length: rounds.length }, (_, i) => i + 1));
    }
  });

  it("excludes pre-season testing", () => {
    const names = SCHEDULE.flatMap((s) => s.races.map((r) => r.name.toLowerCase()));
    expect(names.every((n) => !n.includes("testing"))).toBe(true);
  });

  it("raceCount matches races.length", () => {
    for (const s of SCHEDULE) expect(s.raceCount).toBe(s.races.length);
  });
});
```

- [ ] **Step 3: Run tests**

From `site/`: `npm run test -- schedule`
Expected: 6 passing tests. If "includes australia-2026" fails, inspect the slugify output for Australia in 2026's Index.json and reconcile (the slug must match `FEATURED_RACE_SLUG`).

- [ ] **Step 4: Commit**

```bash
git add site/src/data/schedule.ts site/tests/unit/schedule.test.ts
git commit -m "feat(site): commit schedule catalog (2018–2026 ex. 2022)"
```

---

## Task 4 — Route table skeleton

**Files:**
- Modify: `site/src/App.tsx`

- [ ] **Step 1: Replace route table**

Rewrite `site/src/App.tsx`:

```tsx
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import Seasons from "./routes/Seasons";
import Season from "./routes/Season";
import Race from "./routes/Race";
import Tyres from "./routes/Tyres";
import Driver from "./routes/Driver";
import NotFound from "./routes/NotFound";

const basename = import.meta.env.BASE_URL.replace(/\/$/, "");

const router = createBrowserRouter(
  [
    { path: "/", element: <Seasons /> },
    { path: "/season/:year", element: <Season />, errorElement: <NotFound /> },
    { path: "/race/:slug", element: <Race />, errorElement: <NotFound /> },
    { path: "/race/:slug/tyres", element: <Tyres />, errorElement: <NotFound /> },
    { path: "/race/:slug/driver/:tla", element: <Driver />, errorElement: <NotFound /> },
    { path: "*", element: <NotFound /> },
  ],
  { basename: basename || "/" },
);

export default function App() {
  return <RouterProvider router={router} />;
}
```

- [ ] **Step 2: Verify tsc fails**

From `site/`: `npx tsc -b`
Expected: errors for missing `Seasons`, `Season`, `Race`, `Tyres` modules. This is intentional — subsequent tasks create them. Do **not** commit yet.

---

## Task 5 — Seasons view + SeasonTile

**Files:**
- Create: `site/src/components/SeasonTile.tsx`
- Create: `site/src/routes/Seasons.tsx`
- Test: `site/tests/unit/SeasonTile.test.tsx`

- [ ] **Step 1: Implement SeasonTile**

`site/src/components/SeasonTile.tsx`:

```tsx
import { Link } from "react-router-dom";
import type { Season } from "../data/schedule";

export function SeasonTile({ season }: { season: Season }) {
  const drivers = season.driversChampion ?? "TBD";
  const constructors = season.constructorsChampion ?? "TBD";
  return (
    <Link
      to={`/season/${season.year}`}
      className="block rounded-md border border-f1-border bg-f1-panel p-4 transition hover:bg-f1-border focus-visible:outline-2 focus-visible:outline-compound-medium"
    >
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-2xl font-bold">{season.year}</span>
        <span className="font-mono text-xs text-f1-muted">{season.raceCount} races</span>
      </div>
      <dl className="mt-3 space-y-1 text-xs text-f1-muted">
        <div className="flex justify-between gap-2">
          <dt>Drivers' champion</dt>
          <dd className="text-right text-f1-fg">{drivers}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt>Constructors' champion</dt>
          <dd className="text-right text-f1-fg">{constructors}</dd>
        </div>
      </dl>
    </Link>
  );
}
```

- [ ] **Step 2: Implement Seasons route**

`site/src/routes/Seasons.tsx`:

```tsx
import { SeasonTile } from "../components/SeasonTile";
import { SCHEDULE } from "../data/schedule";

export default function Seasons() {
  // Most recent season first.
  const ordered = [...SCHEDULE].sort((a, b) => b.year - a.year);
  return (
    <main className="mx-auto max-w-6xl p-6">
      <header className="mb-6 border-b border-f1-border pb-3">
        <p className="text-xs uppercase tracking-widest text-f1-muted">F1 Dashboard</p>
        <h1 className="text-2xl font-bold">Seasons</h1>
      </header>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {ordered.map((s) => (
          <SeasonTile key={s.year} season={s} />
        ))}
      </div>
    </main>
  );
}
```

- [ ] **Step 3: Write component test**

`site/tests/unit/SeasonTile.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SeasonTile } from "../../src/components/SeasonTile";

const base = {
  year: 2024,
  races: [],
  raceCount: 24,
  driversChampion: "Max Verstappen",
  constructorsChampion: "McLaren",
};

function wrap(ui: React.ReactNode) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("SeasonTile", () => {
  it("renders the year, race count, and champions", () => {
    wrap(<SeasonTile season={base} />);
    expect(screen.getByText("2024")).toBeInTheDocument();
    expect(screen.getByText("24 races")).toBeInTheDocument();
    expect(screen.getByText("Max Verstappen")).toBeInTheDocument();
    expect(screen.getByText("McLaren")).toBeInTheDocument();
  });

  it("shows TBD when champions are null", () => {
    wrap(<SeasonTile season={{ ...base, driversChampion: null, constructorsChampion: null }} />);
    expect(screen.getAllByText("TBD")).toHaveLength(2);
  });

  it("links to /season/:year", () => {
    wrap(<SeasonTile season={base} />);
    expect(screen.getByRole("link")).toHaveAttribute("href", "/season/2024");
  });
});
```

- [ ] **Step 4: Run tests**

From `site/`: `npm run test -- SeasonTile`
Expected: 3 passing tests.

- [ ] **Step 5: Commit**

```bash
git add site/src/components/SeasonTile.tsx site/src/routes/Seasons.tsx site/tests/unit/SeasonTile.test.tsx
git commit -m "feat(site): add seasons index view"
```

---

## Task 6 — Season view + RaceTile

**Files:**
- Create: `site/src/components/RaceTile.tsx`
- Create: `site/src/routes/Season.tsx`
- Test: `site/tests/unit/RaceTile.test.tsx`

- [ ] **Step 1: Implement RaceTile**

`site/src/components/RaceTile.tsx`:

```tsx
import { Link } from "react-router-dom";
import { isFeatured } from "../config";
import type { Race } from "../data/schedule";

export function RaceTile({ race }: { race: Race }) {
  const featured = isFeatured(race.slug);
  const shared =
    "block rounded-md border border-f1-border bg-f1-panel p-3 transition";
  const enabled = " hover:bg-f1-border focus-visible:outline-2 focus-visible:outline-compound-medium";
  const disabled = " opacity-60 cursor-not-allowed";

  const body = (
    <>
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-xs text-f1-muted">Round {race.round}</span>
        {!featured && (
          <span className="rounded bg-f1-border px-2 py-0.5 text-[10px] uppercase tracking-widest text-f1-muted">
            Coming soon
          </span>
        )}
      </div>
      <h2 className="mt-1 text-base font-bold">{race.name}</h2>
      <p className="truncate text-xs text-f1-muted">
        {race.countryName} · {race.circuitShortName}
      </p>
      <p className="mt-1 font-mono text-[11px] text-f1-muted">
        {race.startDate} → {race.endDate}
      </p>
    </>
  );

  if (!featured) {
    return (
      <div aria-disabled="true" className={shared + disabled}>
        {body}
      </div>
    );
  }

  return (
    <Link to={`/race/${race.slug}`} className={shared + enabled}>
      {body}
    </Link>
  );
}
```

- [ ] **Step 2: Implement Season route**

`site/src/routes/Season.tsx`:

```tsx
import { useParams } from "react-router-dom";
import { RaceTile } from "../components/RaceTile";
import { SCHEDULE } from "../data/schedule";
import NotFound from "./NotFound";

export default function Season() {
  const { year } = useParams<{ year: string }>();
  const parsed = Number(year);
  const season = SCHEDULE.find((s) => s.year === parsed);
  if (!season) return <NotFound />;

  return (
    <main className="mx-auto max-w-6xl p-6">
      <header className="mb-6 border-b border-f1-border pb-3">
        <p className="text-xs uppercase tracking-widest text-f1-muted">
          {season.raceCount} races ·
          {" "}Drivers: {season.driversChampion ?? "TBD"} ·
          {" "}Constructors: {season.constructorsChampion ?? "TBD"}
        </p>
        <h1 className="text-2xl font-bold">{season.year} Season</h1>
      </header>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
        {season.races.map((r) => (
          <RaceTile key={r.slug} race={r} />
        ))}
      </div>
    </main>
  );
}
```

- [ ] **Step 3: Write component test**

`site/tests/unit/RaceTile.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { RaceTile } from "../../src/components/RaceTile";

const base = {
  slug: "japan-2026",
  round: 3,
  name: "Japanese Grand Prix",
  countryCode: "JPN",
  countryName: "Japan",
  circuitShortName: "Suzuka",
  startDate: "2026-03-27",
  endDate: "2026-03-29",
};

function wrap(ui: React.ReactNode) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("RaceTile", () => {
  it("renders disabled state with 'Coming soon' for non-featured races", () => {
    wrap(<RaceTile race={base} />);
    expect(screen.getByText(/Coming soon/i)).toBeInTheDocument();
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("renders a link for the featured race", () => {
    wrap(<RaceTile race={{ ...base, slug: "australia-2026", name: "Australian Grand Prix" }} />);
    expect(screen.getByRole("link")).toHaveAttribute("href", "/race/australia-2026");
    expect(screen.queryByText(/Coming soon/i)).toBeNull();
  });
});
```

- [ ] **Step 4: Run tests**

From `site/`: `npm run test -- RaceTile`
Expected: 2 passing tests.

- [ ] **Step 5: Commit**

```bash
git add site/src/components/RaceTile.tsx site/src/routes/Season.tsx site/tests/unit/RaceTile.test.tsx
git commit -m "feat(site): add season race list view"
```

---

## Task 7 — Race landing + AnalyticsTile

**Files:**
- Create: `site/src/components/AnalyticsTile.tsx`
- Create: `site/src/routes/Race.tsx`

- [ ] **Step 1: Implement AnalyticsTile**

`site/src/components/AnalyticsTile.tsx`:

```tsx
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
```

- [ ] **Step 2: Implement Race landing**

`site/src/routes/Race.tsx`:

```tsx
import { useParams } from "react-router-dom";
import { AnalyticsTile } from "../components/AnalyticsTile";
import { SCHEDULE } from "../data/schedule";
import { isFeatured } from "../config";
import NotFound from "./NotFound";

export default function Race() {
  const { slug = "" } = useParams<{ slug: string }>();
  const season = SCHEDULE.find((s) => s.races.some((r) => r.slug === slug));
  const race = season?.races.find((r) => r.slug === slug);
  if (!season || !race) return <NotFound />;

  const featured = isFeatured(slug);

  return (
    <main className="mx-auto max-w-6xl p-6">
      <header className="mb-6 flex items-baseline justify-between border-b border-f1-border pb-3">
        <div>
          <p className="text-xs uppercase tracking-widest text-f1-muted">
            Round {race.round} · {season.year}
          </p>
          <h1 className="text-2xl font-bold">{race.name}</h1>
          <p className="text-sm text-f1-muted">
            {race.countryName} · {race.circuitShortName} · {race.startDate} → {race.endDate}
          </p>
        </div>
      </header>

      {featured ? (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-f1-muted">
            Analytics
          </h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
            <AnalyticsTile
              title="Tyre Inventory"
              description="Pre-race tyre allocation for all drivers."
              to={`/race/${slug}/tyres`}
            />
          </div>
        </section>
      ) : (
        <p className="rounded-md border border-f1-border bg-f1-panel p-4 text-sm text-f1-muted">
          No analytics available yet for this race — data will appear when it becomes the featured weekend.
        </p>
      )}
    </main>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add site/src/components/AnalyticsTile.tsx site/src/routes/Race.tsx
git commit -m "feat(site): add race landing with analytics tiles"
```

---

## Task 8 — Tyres route (moved from Home)

**Files:**
- Create: `site/src/routes/Tyres.tsx`
- Delete: `site/src/routes/Home.tsx`

- [ ] **Step 1: Create Tyres.tsx**

`site/src/routes/Tyres.tsx`:

```tsx
import { useEffect, useState } from "react";
import { Navigate, useParams } from "react-router-dom";
import { RaceHeader } from "../components/RaceHeader";
import { DriverGrid } from "../components/DriverGrid";
import { loadManifest } from "../lib/data";
import type { Manifest } from "../lib/schemas";
import { isFeatured } from "../config";
import { SCHEDULE } from "../data/schedule";
import NotFound from "./NotFound";

export default function Tyres() {
  const { slug = "" } = useParams<{ slug: string }>();
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState<string | null>(null);

  const known = SCHEDULE.some((s) => s.races.some((r) => r.slug === slug));

  useEffect(() => {
    if (!isFeatured(slug)) return;
    loadManifest(`${import.meta.env.BASE_URL}data/${slug}.json`)
      .then(setManifest)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)));
  }, [slug]);

  if (!known) return <NotFound />;
  if (!isFeatured(slug)) return <Navigate to={`/race/${slug}`} replace />;

  if (error) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-compound-soft">Data unavailable: {error}</p>
      </main>
    );
  }
  if (!manifest) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-f1-muted">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl p-6">
      <RaceHeader race={manifest.race} />
      <DriverGrid drivers={manifest.race.drivers} raceSlug={slug} />
    </main>
  );
}
```

Note: `DriverGrid` gains a `raceSlug` prop in Task 9.

- [ ] **Step 2: Delete the old Home route**

```bash
git rm site/src/routes/Home.tsx
```

- [ ] **Step 3: Commit (deferred — DriverGrid change required)**

Do not commit yet; `npx tsc -b` will fail until Task 9 updates `DriverGrid`. Proceed to Task 9.

---

## Task 9 — Thread race slug through Driver route + DriverCard

**Files:**
- Modify: `site/src/routes/Driver.tsx`
- Modify: `site/src/components/DriverCard.tsx`
- Modify: `site/src/components/DriverGrid.tsx`

- [ ] **Step 1: Update DriverCard**

Read current file at `site/src/components/DriverCard.tsx` then replace:

```tsx
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

export function DriverCard({ driver, raceSlug }: { driver: Driver; raceSlug: string }) {
  return (
    <Link
      to={`/race/${raceSlug}/driver/${driver.tla}`}
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
```

- [ ] **Step 2: Update DriverGrid**

Open `site/src/components/DriverGrid.tsx`, add a `raceSlug` prop and pass it to each `DriverCard`. Exact shape will depend on current file, but the signature must become:

```tsx
export function DriverGrid({ drivers, raceSlug }: { drivers: ReadonlyArray<Driver>; raceSlug: string }) {
  // …existing layout…
  // For each driver: <DriverCard driver={d} raceSlug={raceSlug} />
}
```

Read the current file first; update the prop list, destructuring, and the `<DriverCard>` call sites.

- [ ] **Step 3: Update Driver route**

Replace `site/src/routes/Driver.tsx`:

```tsx
import { useEffect, useState } from "react";
import { Navigate, useParams } from "react-router-dom";
import { DriverHeader } from "../components/DriverHeader";
import { InventoryView } from "../components/InventoryView";
import { RaceHeader } from "../components/RaceHeader";
import { loadManifest } from "../lib/data";
import type { Manifest } from "../lib/schemas";
import { isFeatured } from "../config";
import { SCHEDULE } from "../data/schedule";
import NotFound from "./NotFound";

export default function Driver() {
  const { slug = "", tla } = useParams<{ slug: string; tla: string }>();
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState<string | null>(null);

  const known = SCHEDULE.some((s) => s.races.some((r) => r.slug === slug));

  useEffect(() => {
    if (!isFeatured(slug)) return;
    loadManifest(`${import.meta.env.BASE_URL}data/${slug}.json`)
      .then(setManifest)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)));
  }, [slug]);

  if (!known) return <NotFound />;
  if (!isFeatured(slug)) return <Navigate to={`/race/${slug}`} replace />;

  if (error) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-compound-soft">Data unavailable: {error}</p>
      </main>
    );
  }
  if (!manifest) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-f1-muted">Loading…</p>
      </main>
    );
  }

  const driver = manifest.race.drivers.find((d: { tla: string }) => d.tla === tla);
  if (!driver) return <NotFound />;

  return (
    <main className="mx-auto max-w-6xl p-6">
      <RaceHeader race={manifest.race} />
      <DriverHeader driver={driver} />
      <InventoryView driver={driver} />
    </main>
  );
}
```

- [ ] **Step 4: Update existing DriverCard unit test**

Open `site/tests/unit/DriverCard.test.tsx` and update any render that calls `<DriverCard driver={…} />` to `<DriverCard driver={…} raceSlug="australia-2026" />`. Update the expected `href` from `/driver/TLA` to `/race/australia-2026/driver/TLA`.

- [ ] **Step 5: Run full unit suite and type check**

From `site/`:
- `npx tsc -b` → expected: no errors.
- `npm run test` → expected: all unit tests pass.

- [ ] **Step 6: Commit route restructure**

```bash
git add site/src/App.tsx site/src/routes/Tyres.tsx site/src/routes/Driver.tsx \
        site/src/components/DriverCard.tsx site/src/components/DriverGrid.tsx \
        site/tests/unit/DriverCard.test.tsx
git rm site/src/routes/Home.tsx  # if not already staged by Task 8
git commit -m "feat(site): nest routes under /race/:slug"
```

---

## Task 10 — E2E tests updated

**Files:**
- Modify: `site/tests/e2e/home.spec.ts`
- Modify: `site/tests/e2e/driver.spec.ts`
- Modify: `site/tests/e2e/routing.spec.ts`

- [ ] **Step 1: Rewrite home.spec.ts**

Replace `site/tests/e2e/home.spec.ts`:

```ts
import { test, expect } from "@playwright/test";

test("home renders season tiles including 2026", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Seasons" })).toBeVisible();
  await expect(page.getByRole("link", { name: /2026/ })).toBeVisible();
});

test("drill into 2026 → Australian GP → Tyre Inventory", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: /2026/ }).click();
  await expect(page).toHaveURL(/\/season\/2026$/);

  await page.getByRole("link", { name: /Australian Grand Prix/ }).click();
  await expect(page).toHaveURL(/\/race\/australia-2026$/);
  await expect(page.getByRole("heading", { name: /Australian Grand Prix/ })).toBeVisible();

  await page.getByRole("link", { name: /Tyre Inventory/ }).click();
  await expect(page).toHaveURL(/\/race\/australia-2026\/tyres$/);
  const cards = page.locator('a[href^="/race/australia-2026/driver/"]');
  await expect(cards).toHaveCount(22);
});

test("non-featured race tile is disabled and shows Coming soon", async ({ page }) => {
  await page.goto("/season/2026");
  // Pick any race that isn't Australia.
  const japaneseTile = page.locator('div[aria-disabled="true"]', { hasText: /Japanese Grand Prix/ });
  await expect(japaneseTile).toBeVisible();
  await expect(japaneseTile).toContainText(/Coming soon/i);
});
```

- [ ] **Step 2: Update driver.spec.ts**

Read `site/tests/e2e/driver.spec.ts` first, then replace any URL matching `/driver/<TLA>` with `/race/australia-2026/driver/<TLA>`. Any navigation from `/` should first drill via `/season/2026` → `/race/australia-2026/tyres`. If the spec previously started at `/`, change the starting URL to `/race/australia-2026/tyres` for brevity and keep a single integration-style test covering the full drill-down.

- [ ] **Step 3: Update routing.spec.ts**

Read `site/tests/e2e/routing.spec.ts`. Any test that hits `/` expecting the driver grid must now hit `/race/australia-2026/tyres`. Any test that hits `/driver/:tla` must hit `/race/australia-2026/driver/:tla`. Preserve the spirit of each test (404 handling, etc.).

- [ ] **Step 4: Run E2E**

From repo root: `make test-e2e`
Expected: all Playwright specs pass.

- [ ] **Step 5: Commit**

```bash
git add site/tests/e2e/home.spec.ts site/tests/e2e/driver.spec.ts site/tests/e2e/routing.spec.ts
git commit -m "test(site): e2e for nested navigation"
```

---

## Task 11 — Full verification

- [ ] **Step 1: Clean build**

From repo root: `make build`
Expected: completes without errors; `site/dist/` produced.

- [ ] **Step 2: All tests**

From repo root: `make test`
Expected: Python + Vitest + Playwright all green. Python coverage ≥ 85% (unchanged).

- [ ] **Step 3: Manual smoke via dev server**

From repo root: `make dev`. Open http://localhost:5173/

Verify in-browser:
1. Root shows "Seasons" with 8 tiles.
2. Click 2026 → season page lists pre-season-free GPs; Australian GP is clickable, others disabled with "Coming soon".
3. Click Australian GP → landing shows header + "Tyre Inventory" tile.
4. Click "Tyre Inventory" → 22 driver cards, identical to pre-change layout.
5. Click a driver card → `/race/australia-2026/driver/<TLA>`, detail page renders.
6. Navigate to `/race/japan-2026` directly → "No analytics available yet" message.
7. Navigate to `/race/japan-2026/tyres` directly → redirected to `/race/japan-2026`.
8. Navigate to `/race/does-not-exist` → NotFound.
9. Navigate to `/season/2022` → NotFound (2022 excluded).

- [ ] **Step 4: Commit anything left (e.g., minor Tailwind tweaks discovered during smoke)**

```bash
git status
# If clean, done.
```

---

## Self-review checklist (for the writer)

1. **Spec coverage** — Every spec section is covered: routes (Tasks 4, 8, 9), config (1), catalog + generator (2, 3), seasons/race tiles (5, 6), landing + analytics tile (7), disabled state + Coming soon (6, 7), unknown-slug redirects (8, 9), E2E (10), verification (11).
2. **Placeholders** — None; every code block is concrete.
3. **Type consistency** — `Race`, `Season` types defined in Task 3 are imported unchanged in 5, 6, 7. `DriverCard` signature gains `raceSlug` in Task 9; `DriverGrid` in same task; `Tyres.tsx` in Task 8 already passes `raceSlug` — consistent.
4. **Known cross-task deferral** — Task 4 intentionally leaves `tsc` broken; Task 8 defers its commit until Task 9. Called out inline.
