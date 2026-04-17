import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Breadcrumbs } from "../../src/components/Breadcrumbs";

function renderAt(pathname: string) {
  return render(
    <MemoryRouter initialEntries={[pathname]}>
      <Breadcrumbs />
    </MemoryRouter>,
  );
}

describe("<Breadcrumbs />", () => {
  it("wraps the trail in a <nav> with aria-label='Breadcrumb'", () => {
    renderAt("/");
    expect(screen.getByRole("navigation", { name: "Breadcrumb" })).toBeInTheDocument();
  });

  it("marks the current item with aria-current='page' and renders it as text, not a link", () => {
    renderAt("/race/australia-2026/tyres");
    const current = screen.getByText("Tyres");
    expect(current).toHaveAttribute("aria-current", "page");
    expect(current.tagName).not.toBe("A");
  });

  it("renders non-current items as links with expected hrefs", () => {
    renderAt("/race/australia-2026/tyres");
    const nav = screen.getByRole("navigation", { name: "Breadcrumb" });
    expect(within(nav).getByRole("link", { name: "Home" })).toHaveAttribute("href", "/");
    expect(within(nav).getByRole("link", { name: "2026" })).toHaveAttribute(
      "href",
      "/season/2026",
    );
    expect(within(nav).getByRole("link", { name: "Australian GP" })).toHaveAttribute(
      "href",
      "/race/australia-2026",
    );
  });

  it("renders a single non-linked 'Home' on the home route", () => {
    renderAt("/");
    const nav = screen.getByRole("navigation", { name: "Breadcrumb" });
    expect(within(nav).queryByRole("link")).toBeNull();
    expect(within(nav).getByText("Home")).toHaveAttribute("aria-current", "page");
  });

  it("includes separators marked aria-hidden between items", () => {
    renderAt("/season/2026");
    const nav = screen.getByRole("navigation", { name: "Breadcrumb" });
    const separators = within(nav).getAllByText("›");
    expect(separators.every((el) => el.getAttribute("aria-hidden") === "true")).toBe(true);
    expect(separators.length).toBeGreaterThanOrEqual(1);
  });
});
