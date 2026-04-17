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
