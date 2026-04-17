import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Legal from "../../src/routes/Legal";

function renderLegal() {
  return render(
    <MemoryRouter>
      <Legal />
    </MemoryRouter>,
  );
}

describe("<Legal />", () => {
  it("renders the page heading", () => {
    renderLegal();
    expect(screen.getByRole("heading", { level: 1, name: /legal/i })).toBeInTheDocument();
  });

  it("renders all six section headings", () => {
    renderLegal();
    const expected = [
      /trademark/i,
      /no affiliation/i,
      /purpose/i,
      /data source/i,
      /code/i,
      /contact/i,
    ];
    for (const name of expected) {
      expect(screen.getByRole("heading", { level: 2, name })).toBeInTheDocument();
    }
  });

  it("links to the GitHub repository", () => {
    renderLegal();
    const link = screen.getByRole("link", { name: /github\.com\/driversti\/formula1/i });
    expect(link).toHaveAttribute("href", "https://github.com/driversti/formula1");
  });

  it("links to the livetiming data source", () => {
    renderLegal();
    const link = screen.getByRole("link", { name: /livetiming\.formula1\.com/i });
    expect(link.getAttribute("href")).toContain("livetiming.formula1.com");
  });

  it("exposes the takedown contact as a mailto link", () => {
    renderLegal();
    const link = screen.getByRole("link", { name: /copyright@seniorjava\.dev/i });
    expect(link).toHaveAttribute("href", "mailto:copyright@seniorjava.dev");
  });
});
