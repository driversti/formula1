import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StrategyChart } from "../../src/components/StrategyChart";

type Driver = Parameters<typeof StrategyChart>[0]["drivers"][number];

function makeDriver(overrides: Partial<Driver> & { tla: string }): Driver {
  return {
    racing_number: "99",
    full_name: overrides.tla + " Fullname",
    team_name: "Team",
    team_color: "#888888",
    grid_position: null,
    sets: [],
    race_stints: [],
    sprint_stints: [],
    final_position: null,
    dnf_at_lap: null,
    ...overrides,
  };
}

const VER = makeDriver({
  tla: "VER",
  final_position: 1,
  race_stints: [
    { stint_idx: 0, compound: "MEDIUM", start_lap: 1,  end_lap: 18, laps: 18, new: true  },
    { stint_idx: 1, compound: "HARD",   start_lap: 19, end_lap: 57, laps: 39, new: true  },
  ],
});

const LEC_DNF = makeDriver({
  tla: "LEC",
  final_position: null,
  dnf_at_lap: 12,
  race_stints: [
    { stint_idx: 0, compound: "MEDIUM", start_lap: 1, end_lap: 12, laps: 12, new: true },
  ],
});

const HAM = makeDriver({
  tla: "HAM",
  final_position: 2,
  race_stints: [
    { stint_idx: 0, compound: "HARD", start_lap: 1, end_lap: 57, laps: 57, new: true },
  ],
});

describe("<StrategyChart />", () => {
  it("renders one row per driver with race_stints", () => {
    render(<StrategyChart drivers={[VER, HAM, LEC_DNF]} sessionKey="R" totalLaps={57} />);
    expect(screen.getAllByTestId("strategy-row")).toHaveLength(3);
  });

  it("sorts finishers ahead of DNFs and by final_position asc", () => {
    render(<StrategyChart drivers={[LEC_DNF, HAM, VER]} sessionKey="R" totalLaps={57} />);
    const rows = screen.getAllByTestId("strategy-row");
    expect(rows.map((r) => r.getAttribute("data-tla"))).toEqual(["VER", "HAM", "LEC"]);
  });

  it("skips drivers with no stints for the requested session", () => {
    const GAS = makeDriver({ tla: "GAS", final_position: 8, race_stints: [], sprint_stints: [] });
    render(<StrategyChart drivers={[VER, GAS]} sessionKey="R" totalLaps={57} />);
    const rows = screen.getAllByTestId("strategy-row");
    expect(rows.map((r) => r.getAttribute("data-tla"))).toEqual(["VER"]);
  });

  it("renders a RET trailer for DNF drivers", () => {
    render(<StrategyChart drivers={[VER, LEC_DNF]} sessionKey="R" totalLaps={57} />);
    expect(screen.getByText("RET L12")).toBeInTheDocument();
  });

  it("renders a finishing position trailer for finishers", () => {
    render(<StrategyChart drivers={[VER, HAM]} sessionKey="R" totalLaps={57} />);
    expect(screen.getByText("P1")).toBeInTheDocument();
    expect(screen.getByText("P2")).toBeInTheDocument();
  });

  it("uses sprint_stints when sessionKey=S", () => {
    const sprinter = makeDriver({
      tla: "NOR",
      final_position: 3,
      race_stints: [],
      sprint_stints: [
        { stint_idx: 0, compound: "MEDIUM", start_lap: 1, end_lap: 19, laps: 19, new: true },
      ],
    });
    render(<StrategyChart drivers={[sprinter]} sessionKey="S" totalLaps={19} />);
    expect(screen.getAllByTestId("strategy-row")).toHaveLength(1);
  });
});
