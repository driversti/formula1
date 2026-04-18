import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SessionTabs } from "../../src/components/SessionTabs";

describe("<SessionTabs />", () => {
  it("renders SPRINT and RACE buttons", () => {
    render(<SessionTabs value="R" onChange={() => {}} />);
    expect(screen.getByRole("button", { name: /SPRINT/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /RACE/ })).toBeInTheDocument();
  });

  it("marks the active button as selected", () => {
    render(<SessionTabs value="S" onChange={() => {}} />);
    const sprintBtn = screen.getByRole("button", { name: /SPRINT/ });
    expect(sprintBtn).toHaveAttribute("aria-pressed", "true");
    const raceBtn = screen.getByRole("button", { name: /RACE/ });
    expect(raceBtn).toHaveAttribute("aria-pressed", "false");
  });

  it("calls onChange with the clicked key", () => {
    const spy = vi.fn();
    render(<SessionTabs value="R" onChange={spy} />);
    fireEvent.click(screen.getByRole("button", { name: /SPRINT/ }));
    expect(spy).toHaveBeenCalledWith("S");
  });
});
