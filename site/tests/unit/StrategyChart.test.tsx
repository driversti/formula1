import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
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
    sprint_final_position: null,
    sprint_dnf_at_lap: null,
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
    render(<StrategyChart drivers={[VER, HAM, LEC_DNF]} sessionKey="R" totalLaps={57} statusBands={[]} />);
    expect(screen.getAllByTestId("strategy-row")).toHaveLength(3);
  });

  it("sorts finishers ahead of DNFs and by final_position asc", () => {
    render(<StrategyChart drivers={[LEC_DNF, HAM, VER]} sessionKey="R" totalLaps={57} statusBands={[]} />);
    const rows = screen.getAllByTestId("strategy-row");
    expect(rows.map((r) => r.getAttribute("data-tla"))).toEqual(["VER", "HAM", "LEC"]);
  });

  it("skips drivers with no stints for the requested session", () => {
    const GAS = makeDriver({ tla: "GAS", final_position: 8, race_stints: [], sprint_stints: [] });
    render(<StrategyChart drivers={[VER, GAS]} sessionKey="R" totalLaps={57} statusBands={[]} />);
    const rows = screen.getAllByTestId("strategy-row");
    expect(rows.map((r) => r.getAttribute("data-tla"))).toEqual(["VER"]);
  });

  it("renders a RET trailer for DNF drivers", () => {
    render(<StrategyChart drivers={[VER, LEC_DNF]} sessionKey="R" totalLaps={57} statusBands={[]} />);
    expect(screen.getByText("RET L12")).toBeInTheDocument();
  });

  it("renders a finishing position trailer for finishers", () => {
    render(<StrategyChart drivers={[VER, HAM]} sessionKey="R" totalLaps={57} statusBands={[]} />);
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
    render(<StrategyChart drivers={[sprinter]} sessionKey="S" totalLaps={19} statusBands={[]} />);
    expect(screen.getAllByTestId("strategy-row")).toHaveLength(1);
  });

  it("uses sprint-specific position fields when sessionKey=S", () => {
    // This driver is a Race DNF but a Sprint finisher. On the Sprint tab the
    // trailer should show the Sprint P-position, NOT the Race RET.
    const driver = makeDriver({
      tla: "VER",
      final_position: null,
      dnf_at_lap: 48,
      sprint_final_position: 1,
      sprint_dnf_at_lap: null,
      sprint_stints: [
        { stint_idx: 0, compound: "MEDIUM", start_lap: 1, end_lap: 18, laps: 18, new: true },
      ],
    });
    render(<StrategyChart drivers={[driver]} sessionKey="S" totalLaps={18} statusBands={[]} />);
    expect(screen.getByText("P1")).toBeInTheDocument();
    expect(screen.queryByText(/RET L48/)).not.toBeInTheDocument();
  });

  it("shows tooltip content on segment hover", () => {
    const { container } = render(
      <StrategyChart drivers={[VER, LEC_DNF]} sessionKey="R" totalLaps={57} statusBands={[]} />
    );

    // VER has two stints; find the first stint-segment rect in the VER row.
    // Rows are sorted by final_position (VER=1 first), so the first
    // stint-segment in the DOM belongs to VER stint 0 (MEDIUM, laps 1-18).
    const segments = container.querySelectorAll<SVGRectElement>('[data-testid="stint-segment"]');
    expect(segments.length).toBeGreaterThan(0);
    const firstSegment = segments[0];

    // Hover over the first segment
    fireEvent.mouseMove(firstSegment, { clientX: 100, clientY: 50 });

    // Tooltip should show TLA in the stint header line (e.g. "VER · Stint 1 / 2")
    expect(screen.getByText(/VER · Stint 1 \/ 2/)).toBeInTheDocument();
    // Compound line (e.g. "MEDIUM · laps 1–18 (18 laps)")
    expect(screen.getByText(/MEDIUM · laps 1/)).toBeInTheDocument();
    // New/used set line
    expect(screen.getByText("New set")).toBeInTheDocument();

    // Mouse leave should hide the tooltip
    fireEvent.mouseLeave(firstSegment);
    expect(screen.queryByText(/MEDIUM · laps 1/)).not.toBeInTheDocument();
  });

  it("renders no overlay elements when statusBands is empty", () => {
    render(<StrategyChart drivers={[VER]} sessionKey="R" totalLaps={57} statusBands={[]} />);
    expect(screen.queryByTestId("status-band")).toBeNull();
    expect(screen.queryByTestId("status-strip-segment")).toBeNull();
  });

  it("renders one band and one strip segment per StatusBand", () => {
    render(
      <StrategyChart
        drivers={[VER]}
        sessionKey="R"
        totalLaps={57}
        statusBands={[
          { status: "SCDeployed", start_lap: 10, end_lap: 14 },
          { status: "Yellow",     start_lap: 20, end_lap: 22 },
        ]}
      />,
    );
    expect(screen.getAllByTestId("status-band")).toHaveLength(2);
    expect(screen.getAllByTestId("status-strip-segment")).toHaveLength(2);
    const bands = screen.getAllByTestId("status-band");
    expect(bands[0].getAttribute("data-status")).toBe("SCDeployed");
    expect(bands[1].getAttribute("data-status")).toBe("Yellow");
  });

  it("shows status tooltip content on band hover", () => {
    const { container } = render(
      <StrategyChart
        drivers={[VER]}
        sessionKey="R"
        totalLaps={57}
        statusBands={[{ status: "SCDeployed", start_lap: 10, end_lap: 14 }]}
      />,
    );
    const band = container.querySelector<SVGRectElement>('[data-testid="status-band"]');
    expect(band).not.toBeNull();
    fireEvent.mouseMove(band!, { clientX: 100, clientY: 50 });
    // Expected tooltip: "Safety Car · lap 10–14 (5 laps)"
    expect(screen.getByText(/Safety Car · lap 10.*14 \(5 laps\)/)).toBeInTheDocument();
    fireEvent.mouseLeave(band!);
    expect(screen.queryByText(/Safety Car · lap 10.*14/)).not.toBeInTheDocument();
  });
});
