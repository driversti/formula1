import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { DriverCard } from "../../src/components/DriverCard";

const driver = {
  racing_number: "16",
  tla: "LEC",
  full_name: "Charles Leclerc",
  team_name: "Ferrari",
  team_color: "#ED1131",
  grid_position: 1,
  sets: [
    { set_id: "LEC-MED-1", compound: "MEDIUM", laps: 0, new_at_first_use: true, first_seen_session: "R", last_seen_session: "R" },
    { set_id: "LEC-HARD-1", compound: "HARD", laps: 12, new_at_first_use: true, first_seen_session: "FP2", last_seen_session: "FP2" },
  ],
} as const;

describe("<DriverCard />", () => {
  it("shows the TLA, team name and grid position", () => {
    render(
      <MemoryRouter>
        <DriverCard driver={driver} />
      </MemoryRouter>,
    );
    expect(screen.getByText("LEC")).toBeInTheDocument();
    expect(screen.getByText(/Ferrari/)).toBeInTheDocument();
    expect(screen.getByText(/P1/)).toBeInTheDocument();
  });

  it("renders one TyreDot per set", () => {
    const { container } = render(
      <MemoryRouter>
        <DriverCard driver={driver} />
      </MemoryRouter>,
    );
    const dots = container.querySelectorAll('[data-testid="tyre-dot"]');
    expect(dots.length).toBe(2);
  });

  it("links to /driver/:tla", () => {
    render(
      <MemoryRouter>
        <DriverCard driver={driver} />
      </MemoryRouter>,
    );
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/driver/LEC");
  });

  it("uses the team_color as left border inline style", () => {
    render(
      <MemoryRouter>
        <DriverCard driver={driver} />
      </MemoryRouter>,
    );
    const link = screen.getByRole("link");
    expect(link.style.borderLeftColor).toBe("rgb(237, 17, 49)");
  });
});
