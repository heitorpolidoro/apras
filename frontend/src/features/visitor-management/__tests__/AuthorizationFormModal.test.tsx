import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthorizationFormModal } from "../components/AuthorizationFormModal";

const mutateAsync = vi.fn();
const useVisitorsMock = vi.fn();

vi.mock("../hooks/useVisitors", () => ({
  useVisitors: () => useVisitorsMock(),
  useCreateVisitor: () => ({ mutateAsync }),
}));

const visitorsPage = {
  items: [
    {
      id: "vis-1",
      full_name: "Carlos Visitante",
      cpf: "52998224725",
      company_name: "Alfa Tech",
    },
    {
      id: "vis-2",
      full_name: "Ana Entregadora",
      cpf: null,
      company_name: null,
    },
  ],
  total: 2,
  skip: 0,
  limit: 20,
};

const renderModal = (
  props: Partial<React.ComponentProps<typeof AuthorizationFormModal>> = {},
) => {
  const onSubmit = vi.fn().mockResolvedValue(undefined);
  const onClose = vi.fn();
  const utils = render(
    <AuthorizationFormModal
      isOpen
      onClose={onClose}
      onSubmit={onSubmit}
      lotId="lot-1"
      {...props}
    />,
  );
  return { ...utils, onSubmit, onClose };
};

const submit = () =>
  fireEvent.click(screen.getByRole("button", { name: "Salvar Autorização" }));

const startCreatingVisitor = () =>
  fireEvent.click(screen.getByRole("button", { name: "Novo Visitante" }));

const selectExistingVisitor = (id: string) =>
  fireEvent.change(screen.getByRole("combobox"), { target: { value: id } });

describe("AuthorizationFormModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useVisitorsMock.mockReturnValue({ data: visitorsPage });
  });

  it("renders nothing when isOpen is false", () => {
    const { container } = renderModal({ isOpen: false });
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the authorization form when open", () => {
    renderModal();
    expect(screen.getByText("Nova Autorização")).toBeInTheDocument();
    expect(screen.getByRole("combobox")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Salvar Autorização" }),
    ).toBeInTheDocument();
  });

  it("submits the selected existing visitor with every day and the full-day shift", async () => {
    const { onSubmit, onClose } = renderModal();

    selectExistingVisitor("vis-1");
    submit();

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit).toHaveBeenCalledWith({
      visitor_id: "vis-1",
      auth_type: "SINGLE",
      allowed_days: ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"],
      allowed_shifts: ["FULL_DAY"],
      valid_from: null,
      valid_until: null,
      notes: null,
    });
    await waitFor(() => expect(onClose).toHaveBeenCalled());
  });

  it("drops a day from the payload when it is toggled off and restores it when toggled back on", async () => {
    const { onSubmit } = renderModal();

    selectExistingVisitor("vis-1");
    fireEvent.click(screen.getByRole("button", { name: "Seg" }));
    submit();

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit.mock.calls[0][0].allowed_days).toEqual([
      "TUE",
      "WED",
      "THU",
      "FRI",
      "SAT",
      "SUN",
    ]);

    fireEvent.click(screen.getByRole("button", { name: "Seg" }));
    submit();

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(2));
    // Toggling back on appends the day at the end of the list.
    expect(onSubmit.mock.calls[1][0].allowed_days).toEqual([
      "TUE",
      "WED",
      "THU",
      "FRI",
      "SAT",
      "SUN",
      "MON",
    ]);
  });

  it("adds and removes shifts as they are toggled", async () => {
    const { onSubmit } = renderModal();

    selectExistingVisitor("vis-1");
    fireEvent.click(
      screen.getByRole("button", { name: "Manhã (06:00 - 11:59)" }),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Dia Todo (00:00 - 23:59)" }),
    );
    submit();

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit.mock.calls[0][0].allowed_shifts).toEqual(["MORNING"]);
  });

  it("submits the PERMANENT type, the validity range as ISO strings and trimmed notes", async () => {
    const { onSubmit, container } = renderModal();

    // The validity labels carry no htmlFor in the component, so the two
    // datetime-local inputs are addressed positionally (from, until).
    const [validFrom, validUntil] = Array.from(
      container.querySelectorAll<HTMLInputElement>(
        'input[type="datetime-local"]',
      ),
    );

    selectExistingVisitor("vis-2");
    fireEvent.click(
      screen.getByRole("button", { name: "Permanente (Recorrente)" }),
    );
    fireEvent.change(validFrom, { target: { value: "2026-09-01T08:00" } });
    fireEvent.change(validUntil, { target: { value: "2026-09-30T18:00" } });
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "  Piscineiro  " },
    });
    submit();

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    const payload = onSubmit.mock.calls[0][0];
    expect(payload.visitor_id).toBe("vis-2");
    expect(payload.auth_type).toBe("PERMANENT");
    expect(payload.notes).toBe("Piscineiro");
    expect(payload.valid_from).toBe(
      new Date("2026-09-01T08:00").toISOString(),
    );
    expect(payload.valid_until).toBe(
      new Date("2026-09-30T18:00").toISOString(),
    );
  });

  it("blocks submission with the selectVisitor message when no visitor is chosen", async () => {
    const { onSubmit } = renderModal();

    submit();

    expect(
      await screen.findByText("Selecione um visitante"),
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  describe("creating a new visitor inline", () => {
    it("requires a full name and does not call onSubmit", async () => {
      const { onSubmit } = renderModal();

      startCreatingVisitor();
      fireEvent.change(screen.getByPlaceholderText("Nome Completo *"), {
        target: { value: "   " },
      });
      submit();

      expect(
        await screen.findByText("O nome completo é obrigatório."),
      ).toBeInTheDocument();
      expect(mutateAsync).not.toHaveBeenCalled();
      expect(onSubmit).not.toHaveBeenCalled();
    });

    it("creates the visitor and feeds the new id into the authorization payload", async () => {
      mutateAsync.mockResolvedValue({ id: "vis-new" });
      const { onSubmit } = renderModal();

      startCreatingVisitor();
      fireEvent.change(screen.getByPlaceholderText("Nome Completo *"), {
        target: { value: "  Novo Prestador  " },
      });
      fireEvent.change(screen.getByPlaceholderText("CPF"), {
        target: { value: " 52998224725 " },
      });
      fireEvent.change(screen.getByPlaceholderText("Empresa"), {
        target: { value: " Beta Ltda " },
      });
      fireEvent.change(screen.getByPlaceholderText("Placa do Veículo"), {
        target: { value: " XYZ-9876 " },
      });
      submit();

      await waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1));
      expect(mutateAsync).toHaveBeenCalledWith({
        full_name: "Novo Prestador",
        cpf: "52998224725",
        company_name: "Beta Ltda",
        vehicle_plate: "XYZ-9876",
      });
      await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
      expect(onSubmit.mock.calls[0][0].visitor_id).toBe("vis-new");
    });

    it("sends the optional visitor fields as undefined when they are left empty", async () => {
      mutateAsync.mockResolvedValue({ id: "vis-new" });
      renderModal();

      startCreatingVisitor();
      fireEvent.change(screen.getByPlaceholderText("Nome Completo *"), {
        target: { value: "Só o nome" },
      });
      submit();

      await waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1));
      expect(mutateAsync).toHaveBeenCalledWith({
        full_name: "Só o nome",
        cpf: undefined,
        company_name: undefined,
        vehicle_plate: undefined,
      });
    });

    it("shows the api detail message and skips onSubmit when the creation fails", async () => {
      mutateAsync.mockRejectedValue({
        response: { data: { detail: "CPF já cadastrado" } },
      });
      const { onSubmit } = renderModal();

      startCreatingVisitor();
      fireEvent.change(screen.getByPlaceholderText("Nome Completo *"), {
        target: { value: "Duplicado" },
      });
      submit();

      expect(await screen.findByText("CPF já cadastrado")).toBeInTheDocument();
      expect(onSubmit).not.toHaveBeenCalled();
    });

    it("falls back to a generic message when the creation error has no detail", async () => {
      mutateAsync.mockRejectedValue(new Error("boom"));
      renderModal();

      startCreatingVisitor();
      fireEvent.change(screen.getByPlaceholderText("Nome Completo *"), {
        target: { value: "Sem detalhe" },
      });
      submit();

      expect(
        await screen.findByText("Error creating visitor profile"),
      ).toBeInTheDocument();
    });

    it("goes back to the visitor selector when the toggle is pressed again", () => {
      renderModal();

      startCreatingVisitor();
      expect(screen.queryByRole("combobox")).toBeNull();

      fireEvent.click(
        screen.getByRole("button", { name: "Visitante / Prestador" }),
      );
      expect(screen.getByRole("combobox")).toBeInTheDocument();
    });
  });

  it("shows the api detail message when onSubmit rejects and keeps the modal open", async () => {
    const onSubmit = vi.fn().mockRejectedValue({
      response: { data: { detail: "Lote sem permissão" } },
    });
    const { onClose } = renderModal({ onSubmit });

    selectExistingVisitor("vis-1");
    submit();

    expect(await screen.findByText("Lote sem permissão")).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("falls back to a generic message when the onSubmit error has no detail", async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error("boom"));
    renderModal({ onSubmit });

    selectExistingVisitor("vis-1");
    submit();

    expect(
      await screen.findByText("Error creating authorization"),
    ).toBeInTheDocument();
  });

  it("renders an empty selector when the visitors query has no data yet", () => {
    useVisitorsMock.mockReturnValue({ data: undefined });
    renderModal();

    expect(screen.getAllByRole("option")).toHaveLength(1);
  });

  it("disables the actions and shows the saving label while isLoading", () => {
    renderModal({ isLoading: true });

    expect(screen.getByRole("button", { name: "Salvando..." })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancelar" })).toBeDisabled();
  });

  it("calls onClose from the cancel button and from the header close control", () => {
    const { onClose, getAllByRole } = renderModal();

    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(onClose).toHaveBeenCalledTimes(1);

    // The header close control is the icon-only button rendered first.
    fireEvent.click(getAllByRole("button")[0]);
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
