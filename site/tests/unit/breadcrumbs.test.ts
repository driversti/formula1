import { describe, it, expect } from "vitest";
import { buildTrail } from "../../src/lib/breadcrumbs";
import { SCHEDULE } from "../../src/data/schedule";

describe("buildTrail", () => {
  it("returns just Home for /", () => {
    expect(buildTrail("/", SCHEDULE)).toEqual([
      { label: "Home", href: "/", current: true },
    ]);
  });

  it("returns Home + year (current) for /season/:year", () => {
    expect(buildTrail("/season/2026", SCHEDULE)).toEqual([
      { label: "Home", href: "/", current: false },
      { label: "2026", href: "/season/2026", current: true },
    ]);
  });

  it("returns Home > year > race (current) for /race/:slug", () => {
    expect(buildTrail("/race/australia-2026", SCHEDULE)).toEqual([
      { label: "Home", href: "/", current: false },
      { label: "2026", href: "/season/2026", current: false },
      { label: "Australian GP", href: "/race/australia-2026", current: true },
    ]);
  });

  it("returns full trail with Tyres leaf for /race/:slug/tyres", () => {
    expect(buildTrail("/race/australia-2026/tyres", SCHEDULE)).toEqual([
      { label: "Home", href: "/", current: false },
      { label: "2026", href: "/season/2026", current: false },
      { label: "Australian GP", href: "/race/australia-2026", current: false },
      { label: "Tyres", href: "/race/australia-2026/tyres", current: true },
    ]);
  });

  it("returns full trail with Driver · TLA leaf for /race/:slug/driver/:tla", () => {
    expect(buildTrail("/race/australia-2026/driver/VER", SCHEDULE)).toEqual([
      { label: "Home", href: "/", current: false },
      { label: "2026", href: "/season/2026", current: false },
      { label: "Australian GP", href: "/race/australia-2026", current: false },
      { label: "Driver · VER", href: "/race/australia-2026/driver/VER", current: true },
    ]);
  });

  it("uses race.name verbatim when it does not end in 'Grand Prix'", () => {
    const fakeSchedule = [
      {
        year: 2099,
        races: [
          {
            slug: "special-2099",
            round: 1,
            name: "Special Event",
            countryCode: "XXX",
            countryName: "Xland",
            circuitShortName: "Xtrack",
            startDate: "2099-01-01",
            endDate: "2099-01-02",
          },
        ],
        driversChampion: null,
        constructorsChampion: null,
        raceCount: 1,
      },
    ];
    expect(buildTrail("/race/special-2099", fakeSchedule)).toEqual([
      { label: "Home", href: "/", current: false },
      { label: "2099", href: "/season/2099", current: false },
      { label: "Special Event", href: "/race/special-2099", current: true },
    ]);
  });

  it("abbreviates '70th Anniversary Grand Prix' using the name prefix, not countryName", () => {
    expect(buildTrail("/race/70th-anniversary-2020", SCHEDULE)).toEqual([
      { label: "Home", href: "/", current: false },
      { label: "2020", href: "/season/2020", current: false },
      { label: "70th Anniversary GP", href: "/race/70th-anniversary-2020", current: true },
    ]);
  });

  it("falls back to Home-only for an unknown slug", () => {
    expect(buildTrail("/race/does-not-exist", SCHEDULE)).toEqual([
      { label: "Home", href: "/", current: true },
    ]);
  });

  it("falls back to Home-only for an unknown year", () => {
    expect(buildTrail("/season/1999", SCHEDULE)).toEqual([
      { label: "Home", href: "/", current: true },
    ]);
  });

  it("falls back to Home-only for a completely unknown path", () => {
    expect(buildTrail("/totally-unknown", SCHEDULE)).toEqual([
      { label: "Home", href: "/", current: true },
    ]);
  });
});
