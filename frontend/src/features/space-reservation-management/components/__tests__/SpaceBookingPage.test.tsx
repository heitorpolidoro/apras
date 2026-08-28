import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import SpaceBookingPage from "../SpaceBookingPage";
import {
  useReservableSpaces,
  useSpaceReservations,
  useCreateSpaceReservation,
  useApproveReservation,
  useRejectReservation,
  useCancelReservation,
} from "../../hooks/useReservations";
import { useAuth, UserRole } from "../../../user-administration/context/AuthContext";

vi.mock("../../hooks/useReservations", () => ({
  useReservableSpaces: vi.fn(),
  useSpaceReservations: vi.fn(),
  useCreateSpaceReservation: vi.fn(),
  useApproveReservation: vi.fn(),
  useRejectReservation: vi.fn(),
  useCancelReservation: vi.fn(),
}));

vi.mock(
  "../../../user-administration/context/AuthContext",
  async () => {
    const actual = await vi.importActual<
      typeof import("../../../user-administration/context/AuthContext")
    >("../../../user-administration/context/AuthContext");
    return {
      ...actual,
      useAuth: vi.fn(() => ({
        user: { id: "resident-1", role: actual.UserRole.RESIDENT },
      })),
    };
  },
);

vi.mock("../../../user-administration/context/SimulationContext", () => ({
  useSimulation: vi.fn(() => ({
    simulatedRole: null,
    simulatedUserTypeIds: [],
    isSimulating: false,
    setSimulatedRole: vi.fn(),
    setSimulatedUserTypeIds: vi.fn(),
    stopSimulation: vi.fn(),
  })),
}));

vi.mock("../../../../hooks/useUserTypes", () => ({
  useUserTypes: vi.fn(() => ({ data: [] })),
}));

const mockSpaces = [
  {
    id: "space-1",
    name: "Salão de Festas",
    description: null,
    capacity: 50,
    requires_approval: false,
    is_active: true,
    created_at: "2026-01-01T00:00:00",
  },
];

const mockReservation = {
  id: "res-1",
  space_id: "space-1",
  space_name: "Salão de Festas",
  reserved_by_id: "resident-1",
  reserved_by_name: "Resident One",
  lot_id: null,
  start_time: "2026-06-01T10:00:00",
  end_time: "2026-06-01T11:00:00",
  status: "CONFIRMED",
  notes: null,
  decided_by_id: null,
  decided_at: null,
  cancelled_at: null,
  created_at: "2026-01-01T00:00:00",
};

const maskedReservation = {
  ...mockReservation,
  id: "res-masked",
  reserved_by_id: null,
  reserved_by_name: null,
};

const pendingReservation = {
  ...mockReservation,
  id: "res-pending",
  status: "PENDING",
};

const makeMutationHooks = (overrides: {
  create?: Partial<{ mutate: ReturnType<typeof vi.fn>; isPending: boolean }>;
  approve?: Partial<{ mutate: ReturnType<typeof vi.fn>; isPending: boolean }>;
  reject?: Partial<{ mutate: ReturnType<typeof vi.fn>; isPending: boolean }>;
  cancel?: Partial<{ mutate: ReturnType<typeof vi.fn>; isPending: boolean }>;
} = {}) => {
  vi.mocked(useCreateSpaceReservation).mockReturnValue({
    mutate: overrides.create?.mutate ?? vi.fn(),
    isPending: overrides.create?.isPending ?? false,
  } as any);
  vi.mocked(useApproveReservation).mockReturnValue({
    mutate: overrides.approve?.mutate ?? vi.fn(),
    isPending: overrides.approve?.isPending ?? false,
  } as any);
  vi.mocked(useRejectReservation).mockReturnValue({
    mutate: overrides.reject?.mutate ?? vi.fn(),
    isPending: overrides.reject?.isPending ?? false,
  } as any);
  vi.mocked(useCancelReservation).mockReturnValue({
    mutate: overrides.cancel?.mutate ?? vi.fn(),
    isPending: overrides.cancel?.isPending ?? false,
  } as any);
};

describe("SpaceBookingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "resident-1", role: UserRole.RESIDENT },
    } as any);
    vi.mocked(useReservableSpaces).mockReturnValue({
      data: mockSpaces,
      isLoading: false,
    } as any);
    vi.mocked(useSpaceReservations).mockReturnValue({
      data: [],
      isLoading: false,
    } as any);
    makeMutationHooks();
  });

  it("renders title and space buttons", () => {
    render(<SpaceBookingPage />);
    expect(screen.getByText("Reservas de Espaços")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salão de Festas" })).toBeInTheDocument();
  });

  it("shows booking form for non-GUEST roles after selecting a space", () => {
    render(<SpaceBookingPage />);
    fireEvent.click(screen.getByRole("button", { name: "Salão de Festas" }));
    expect(screen.getByText("Nova Reserva")).toBeInTheDocument();
  });

  it("hides booking form for GUEST role", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "guest-1", role: UserRole.GUEST },
    } as any); // skipcq: JS-0323
    render(<SpaceBookingPage />);
    fireEvent.click(screen.getByRole("button", { name: "Salão de Festas" }));
    expect(screen.queryByText("Nova Reserva")).not.toBeInTheDocument();
  });

  it("does not render 'My Reservations' section for GUEST", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "guest-1", role: UserRole.GUEST },
    } as any); // skipcq: JS-0323
    render(<SpaceBookingPage />);
    expect(screen.queryByText("Minhas Reservas")).not.toBeInTheDocument();
  });

  it("renders 'Pending Approvals' section only for ADMINISTRATOR/DIRECTOR", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "admin-1", role: UserRole.ADMINISTRATOR },
    } as any); // skipcq: JS-0323
    vi.mocked(useSpaceReservations).mockReturnValue({
      data: [pendingReservation],
      isLoading: false,
    } as any);
    render(<SpaceBookingPage />);
    expect(screen.getByText("Aprovações Pendentes")).toBeInTheDocument();
  });

  it("does not render 'Pending Approvals' for RESIDENT", () => {
    render(<SpaceBookingPage />);
    expect(screen.queryByText("Aprovações Pendentes")).not.toBeInTheDocument();
  });

  it("renders masked reservation rows without identity", () => {
    vi.mocked(useSpaceReservations).mockReturnValue({
      data: [maskedReservation],
      isLoading: false,
    } as any);
    render(<SpaceBookingPage />);
    fireEvent.click(screen.getByRole("button", { name: "Salão de Festas" }));
    expect(screen.getByText(/Reservado/)).toBeInTheDocument();
  });

  it("submits booking form and calls createSpaceReservation", () => {
    const mutate = vi.fn((_data, options) => options?.onSuccess?.());
    makeMutationHooks({ create: { mutate } });
    render(<SpaceBookingPage />);

    fireEvent.click(screen.getByRole("button", { name: "Salão de Festas" }));

    const startInput = document.querySelectorAll("input[type='datetime-local']")[0];
    const endInput = document.querySelectorAll("input[type='datetime-local']")[1];
    fireEvent.change(startInput, { target: { value: "2026-06-01T10:00" } });
    fireEvent.change(endInput, { target: { value: "2026-06-01T11:00" } });

    fireEvent.click(screen.getByRole("button", { name: "Reservar" }));

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({ space_id: "space-1" }),
      expect.any(Object),
    );
  });

  it("shows conflict error message via AlertModal on 409", async () => {
    const mutate = vi.fn((_data, options) =>
      options?.onError?.({
        response: { data: { detail: "This space is already booked" } },
      }),
    );
    makeMutationHooks({ create: { mutate } });
    render(<SpaceBookingPage />);

    fireEvent.click(screen.getByRole("button", { name: "Salão de Festas" }));
    const startInput = document.querySelectorAll("input[type='datetime-local']")[0];
    const endInput = document.querySelectorAll("input[type='datetime-local']")[1];
    fireEvent.change(startInput, { target: { value: "2026-06-01T10:00" } });
    fireEvent.change(endInput, { target: { value: "2026-06-01T11:00" } });
    fireEvent.click(screen.getByRole("button", { name: "Reservar" }));

    await waitFor(() => {
      expect(screen.getByText("This space is already booked")).toBeInTheDocument();
    });
  });

  it("shows cancel button for own future reservation and calls cancel mutation", () => {
    const futureReservation = {
      ...mockReservation,
      start_time: new Date(Date.now() + 86400000).toISOString(),
    };
    vi.mocked(useSpaceReservations).mockImplementation(
      (_spaceId?: string, mine?: boolean) =>
        ({
          data: mine ? [futureReservation] : [],
          isLoading: false,
        }) as any,
    );
    const mutate = vi.fn();
    makeMutationHooks({ cancel: { mutate } });
    render(<SpaceBookingPage />);

    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(mutate).toHaveBeenCalledWith("res-1", expect.any(Object));
  });

  it("does not show cancel button for past reservation", () => {
    const pastReservation = {
      ...mockReservation,
      start_time: new Date(Date.now() - 86400000).toISOString(),
      end_time: new Date(Date.now() - 82800000).toISOString(),
    };
    vi.mocked(useSpaceReservations).mockImplementation(
      (_spaceId?: string, mine?: boolean) =>
        ({
          data: mine ? [pastReservation] : [],
          isLoading: false,
        }) as any,
    );
    render(<SpaceBookingPage />);
    expect(screen.queryByRole("button", { name: "Cancelar" })).not.toBeInTheDocument();
  });

  it("approve/reject buttons call the respective mutations", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "admin-1", role: UserRole.ADMINISTRATOR },
    } as any); // skipcq: JS-0323
    vi.mocked(useSpaceReservations).mockReturnValue({
      data: [pendingReservation],
      isLoading: false,
    } as any);
    const approveMutate = vi.fn();
    const rejectMutate = vi.fn();
    makeMutationHooks({ approve: { mutate: approveMutate }, reject: { mutate: rejectMutate } });
    render(<SpaceBookingPage />);

    fireEvent.click(screen.getByRole("button", { name: "Aprovar" }));
    expect(approveMutate).toHaveBeenCalledWith("res-pending", expect.any(Object));

    fireEvent.click(screen.getByRole("button", { name: "Rejeitar" }));
    expect(rejectMutate).toHaveBeenCalledWith("res-pending", expect.any(Object));
  });
});
