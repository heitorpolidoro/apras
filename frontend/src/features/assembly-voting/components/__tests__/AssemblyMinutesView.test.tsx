import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AssemblyMinutesView from "../AssemblyMinutesView";
import {
  useAssemblyMinutes,
  useSaveAssemblyMinutes,
} from "../../hooks/useVoting";
import type { AssemblyRead } from "../../../../types/voting";

vi.mock("../../hooks/useVoting", () => ({
  useAssemblyMinutes: vi.fn(),
  useSaveAssemblyMinutes: vi.fn(),
}));

const assembly: AssemblyRead = {
  id: "assembly-1",
  title: "AGO 2026",
  type: "AGO",
  held_on: "2026-03-01",
  agenda: null,
  status: "CLOSED",
  created_by_id: "admin-1",
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
  closed_at: "2026-03-02T00:00:00",
};

describe("AssemblyMinutesView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useAssemblyMinutes).mockReturnValue({
      data: "<h1>Minuta de Ata</h1>",
      isLoading: false,
    } as never);
    vi.mocked(useSaveAssemblyMinutes).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as never);
  });

  it("tells the user the minutes are unavailable before the assembly closes", () => {
    render(<AssemblyMinutesView assembly={{ ...assembly, status: "OPEN" }} />);
    expect(
      screen.getByText(
        "A minuta fica disponível depois do encerramento da assembleia.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("minutes-frame")).not.toBeInTheDocument();
  });

  it("renders the generated minutes in a sandboxed frame", () => {
    render(<AssemblyMinutesView assembly={assembly} />);
    const frame = screen.getByTestId("minutes-frame");
    expect(frame).toHaveAttribute("srcdoc", "<h1>Minuta de Ata</h1>");
    expect(frame).toHaveAttribute("sandbox", "");
  });

  it("saves the minutes to the Document Center", () => {
    const mutate = vi.fn();
    vi.mocked(useSaveAssemblyMinutes).mockReturnValue({
      mutate,
      isPending: false,
    } as never);

    render(<AssemblyMinutesView assembly={assembly} />);
    fireEvent.click(
      screen.getByRole("button", { name: "Salvar na Central de Documentos" }),
    );

    expect(mutate).toHaveBeenCalledWith("assembly-1", expect.anything());
  });

  it("shows the loading state while the minutes are generated", () => {
    vi.mocked(useAssemblyMinutes).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as never);

    render(<AssemblyMinutesView assembly={assembly} />);
    expect(screen.getByText("Gerando minuta...")).toBeInTheDocument();
  });

  it("confirms the save and surfaces failures", () => {
    const ok = vi.fn((_id, options) => options?.onSuccess?.());
    vi.mocked(useSaveAssemblyMinutes).mockReturnValue({
      mutate: ok,
      isPending: false,
    } as never);
    const { unmount } = render(<AssemblyMinutesView assembly={assembly} />);
    fireEvent.click(
      screen.getByRole("button", { name: "Salvar na Central de Documentos" }),
    );
    expect(
      screen.getByText("Minuta salva na Central de Documentos."),
    ).toBeInTheDocument();
    unmount();

    const failing = vi.fn((_id, options) =>
      options?.onError?.({
        response: { data: { detail: "Erro do servidor" } },
      }),
    );
    vi.mocked(useSaveAssemblyMinutes).mockReturnValue({
      mutate: failing,
      isPending: false,
    } as never);
    render(<AssemblyMinutesView assembly={assembly} />);
    fireEvent.click(
      screen.getByRole("button", { name: "Salvar na Central de Documentos" }),
    );
    expect(screen.getByText("Erro do servidor")).toBeInTheDocument();
  });
});
