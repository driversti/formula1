import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TyreDot } from "../../src/components/TyreDot";

describe("<TyreDot />", () => {
  it("renders with the SOFT background class", () => {
    render(<TyreDot compound="SOFT" aria-label="soft tyre" />);
    const el = screen.getByLabelText("soft tyre");
    expect(el.className).toMatch(/bg-compound-soft/);
  });

  it("renders the HARD variant with a ring for visibility on dark bg", () => {
    render(<TyreDot compound="HARD" aria-label="hard tyre" />);
    const el = screen.getByLabelText("hard tyre");
    expect(el.className).toMatch(/bg-compound-hard/);
    expect(el.className).toMatch(/ring-/);
  });

  it("applies size-sm dimensions by default", () => {
    render(<TyreDot compound="MEDIUM" aria-label="med" />);
    const el = screen.getByLabelText("med");
    expect(el.className).toMatch(/w-3/);
    expect(el.className).toMatch(/h-3/);
  });

  it("applies size-lg dimensions when size='lg'", () => {
    render(<TyreDot compound="MEDIUM" size="lg" aria-label="med lg" />);
    const el = screen.getByLabelText("med lg");
    expect(el.className).toMatch(/w-6/);
    expect(el.className).toMatch(/h-6/);
  });
});
