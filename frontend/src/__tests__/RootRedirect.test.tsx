import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { RootRedirect } from "../App";
import * as AuthHook from "../features/user-administration/context/AuthContext";
import { UserRole } from "../features/user-administration/context/AuthContext";

const renderRoot = () =>
  render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        <Route path="/dashboard" element={<div>Dashboard Page</div>} />
        <Route path="/welcome" element={<div>Welcome Page</div>} />
        <Route path="/gate" element={<div>Gate Page</div>} />
      </Routes>
    </MemoryRouter>,
  );

describe("RootRedirect", () => {
  it("sends an active GUEST (real role) to /welcome", () => {
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

    renderRoot();

    expect(screen.getByText("Welcome Page")).toBeInTheDocument();
    expect(screen.queryByText("Dashboard Page")).toBeNull();
  });

  it("sends an active PORTEIRO (real role) to /gate", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "porteiro-1",
        email: "porteiro@example.com",
        full_name: "Porteiro User",
        role: UserRole.PORTEIRO,
        is_active: true,
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });

    renderRoot();

    expect(screen.getByText("Gate Page")).toBeInTheDocument();
    expect(screen.queryByText("Dashboard Page")).toBeNull();
    expect(screen.queryByText("Welcome Page")).toBeNull();
  });

  it("sends every other real role to /dashboard (unchanged behavior)", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "director-1",
        email: "director@example.com",
        full_name: "Director User",
        role: UserRole.DIRECTOR,
        is_active: true,
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });

    renderRoot();

    expect(screen.getByText("Dashboard Page")).toBeInTheDocument();
    expect(screen.queryByText("Welcome Page")).toBeNull();
  });

  it("defaults to /dashboard while the user is still undefined (isLoading window)", () => {
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
      user: undefined as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });

    renderRoot();

    expect(screen.getByText("Dashboard Page")).toBeInTheDocument();
  });

  it("uses the real role, not a simulated one, for an Administrator's own root redirect", () => {
    // Even if some other part of the app is simulating GUEST, RootRedirect
    // reads useAuth() directly (real identity) and is unaffected.
    vi.spyOn(AuthHook, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: "admin-1",
        email: "admin@example.com",
        full_name: "Admin User",
        role: UserRole.ADMINISTRATOR,
        is_active: true,
      } as any,
      login: vi.fn() as any,
      logout: vi.fn(),
    });

    renderRoot();

    expect(screen.getByText("Dashboard Page")).toBeInTheDocument();
    expect(screen.queryByText("Welcome Page")).toBeNull();
  });
});
