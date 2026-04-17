import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SiteFooter } from "../../src/components/SiteFooter";

function renderFooter() {
  return render(
    <MemoryRouter>
      <SiteFooter />
    </MemoryRouter>,
  );
}

describe("<SiteFooter />", () => {
  it("renders inside a <footer> landmark", () => {
    renderFooter();
    expect(screen.getByRole("contentinfo")).toBeInTheDocument();
  });

  it("contains the unofficial-fan-site disclaimer", () => {
    renderFooter();
    expect(
      screen.getByText(/unofficial fan site/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/trademarks belong to their respective owners/i),
    ).toBeInTheDocument();
  });

  it("links 'Read more' to /legal", () => {
    renderFooter();
    const link = screen.getByRole("link", { name: /read more/i });
    expect(link).toHaveAttribute("href", "/legal");
  });
});
