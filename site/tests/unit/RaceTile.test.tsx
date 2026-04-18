import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { RaceTile } from "../../src/components/RaceTile";

const base = {
  slug: "japan-2025",
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
