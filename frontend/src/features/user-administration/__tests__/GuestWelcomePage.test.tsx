import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import GuestWelcomePage from "../pages/GuestWelcomePage";
import * as AuthHook from "../context/AuthContext";
import { UserRole } from "../context/AuthContext";

describe("GuestWelcomePage", () => {
  it("renders the user's name and email plus an explanatory message", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "guest-1",
        email: "guest@example.com",
        full_name: "Guest User",
        role: UserRole.GUEST,
        is_active: true,
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });

    render(
      <MemoryRouter>
        <GuestWelcomePage />
      </MemoryRouter>,
    );

    expect(screen.getByText("Guest User")).toBeInTheDocument();
    expect(screen.getByText("guest@example.com")).toBeInTheDocument();
    expect(screen.getByText("Bem-vindo(a)")).toBeInTheDocument();
  });

  it("calls logout when the logout button is clicked", () => {
    const logout = vi.fn();
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "guest-1",
        email: "guest@example.com",
        full_name: "Guest User",
        role: UserRole.GUEST,
        is_active: true,
      } as any,
      login: vi.fn() as any,
      logout,
    });

    render(
      <MemoryRouter>
        <GuestWelcomePage />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByText("Sair"));
    expect(logout).toHaveBeenCalledTimes(1);
  });
});
